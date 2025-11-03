"""
Common utilities for M365 tool adapters.

Provides auth, rate limiting, retries with exponential backoff, telemetry, and PII redaction.
"""

import hashlib
import json
import time
import random
import os
from typing import Dict, Any, Optional, Tuple
from functools import wraps

import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
import httpx


logger = Logger(service="pm-agent-m365")
tracer = Tracer(service="pm-agent-m365")
metrics = Metrics(namespace="PMAgent", service="m365-tools")

# Initialise SSM client for secrets
ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "ap-southeast-2"))

# Idempotency cache (in-memory, Lambda lifetime)
_idempotency_cache: Dict[str, Any] = {}


def get_ssm_parameter(name: str, decrypt: bool = True) -> str:
    """Fetch parameter from SSM Parameter Store."""
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=decrypt)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to fetch SSM parameter {name}", exc_info=e)
        raise


def get_graph_client() -> GraphServiceClient:
    """
    Get authenticated Microsoft Graph client.

    Credentials fetched from SSM Parameter Store.
    """
    tenant_id = os.environ.get("M365_TENANT_ID")
    client_id = os.environ.get("M365_CLIENT_ID")
    client_secret_ssm = os.environ.get("M365_CLIENT_SECRET_SSM")

    if not all([tenant_id, client_id, client_secret_ssm]):
        raise ValueError("M365 credentials not configured in environment")

    client_secret = get_ssm_parameter(client_secret_ssm)

    credential = ClientSecretCredential(
        tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
    )

    scopes = ["https://graph.microsoft.com/.default"]

    return GraphServiceClient(credentials=credential, scopes=scopes)


def redact_pii(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact PII from log data.

    Removes email bodies, tokens, and sensitive fields.
    """
    redacted = data.copy()
    sensitive_keys = ["body", "token", "approval_token", "secret", "password", "authorization"]

    for key in sensitive_keys:
        if key in redacted:
            redacted[key] = "[REDACTED]"

    return redacted


def compute_action_hash(payload: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of normalised action payload.

    Used for approval token binding and idempotency.
    """
    normalised = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def check_idempotency(idempotency_key: str) -> Optional[Any]:
    """
    Check if request with this idempotency key has been processed.

    Returns cached result if found, None otherwise.
    """
    return _idempotency_cache.get(idempotency_key)


def store_idempotency(idempotency_key: str, result: Any) -> None:
    """Store result for idempotency key."""
    _idempotency_cache[idempotency_key] = result


def exponential_backoff_with_jitter(attempt: int, base_ms: int = 1000) -> float:
    """
    Calculate exponential backoff with jitter.

    Args:
        attempt: Retry attempt number (0-indexed)
        base_ms: Base backoff in milliseconds

    Returns:
        Sleep time in seconds
    """
    backoff_ms = base_ms * (2**attempt)
    jitter_ms = random.uniform(0, backoff_ms * 0.1)
    return (backoff_ms + jitter_ms) / 1000.0


def parse_retry_after(response: httpx.Response) -> Optional[int]:
    """
    Parse Retry-After header from response.

    Returns seconds to wait, or None if header not present.
    """
    retry_after = response.headers.get("Retry-After")
    if not retry_after:
        return None

    try:
        return int(retry_after)
    except ValueError:
        # Could be HTTP date format, not supported yet
        logger.warning(f"Unsupported Retry-After format: {retry_after}")
        return None


def map_error_code(status_code: int, vendor_error: Optional[str] = None) -> str:
    """
    Map HTTP/vendor error codes to standard error types.

    Returns: bad_args, not_found, rate_limited, auth_error, conflict, internal
    """
    error_map = {
        400: "bad_args",
        401: "auth_error",
        403: "auth_error",
        404: "not_found",
        409: "conflict",
        429: "rate_limited",
        500: "internal",
        502: "internal",
        503: "internal",
        504: "internal",
    }

    return error_map.get(status_code, "internal")


@tracer.capture_method
def retry_with_backoff(
    func,
    max_attempts: int = 3,
    base_ms: int = 1000,
    retryable_errors: list = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        func: Function to retry
        max_attempts: Maximum retry attempts
        base_ms: Base backoff in milliseconds
        retryable_errors: List of error codes that should trigger retry
    """
    if retryable_errors is None:
        retryable_errors = ["rate_limited", "internal"]

    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(max_attempts):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000

                metrics.add_metric(name=f"{func.__name__}_latency", unit=MetricUnit.Milliseconds, value=latency_ms)
                metrics.add_metric(name=f"{func.__name__}_success", unit=MetricUnit.Count, value=1)

                logger.info(
                    f"{func.__name__} succeeded",
                    extra={"attempt": attempt + 1, "latency_ms": latency_ms},
                )

                return result

            except httpx.HTTPStatusError as e:
                error_code = map_error_code(e.response.status_code)
                last_exception = e

                metrics.add_metric(name=f"{func.__name__}_error", unit=MetricUnit.Count, value=1)

                logger.warning(
                    f"{func.__name__} failed with HTTP {e.response.status_code}",
                    extra={
                        "attempt": attempt + 1,
                        "error_code": error_code,
                        "status": e.response.status_code,
                    },
                )

                if error_code not in retryable_errors:
                    raise

                # Respect Retry-After if present
                retry_after = parse_retry_after(e.response)
                if retry_after:
                    logger.info(f"Respecting Retry-After: {retry_after}s")
                    time.sleep(retry_after)
                elif attempt < max_attempts - 1:
                    sleep_time = exponential_backoff_with_jitter(attempt, base_ms)
                    logger.info(f"Retrying after {sleep_time:.2f}s")
                    time.sleep(sleep_time)

            except Exception as e:
                last_exception = e
                metrics.add_metric(name=f"{func.__name__}_error", unit=MetricUnit.Count, value=1)

                logger.error(
                    f"{func.__name__} failed with exception",
                    extra={"attempt": attempt + 1},
                    exc_info=e,
                )

                if attempt < max_attempts - 1:
                    sleep_time = exponential_backoff_with_jitter(attempt, base_ms)
                    time.sleep(sleep_time)

        # All retries exhausted
        logger.error(f"{func.__name__} failed after {max_attempts} attempts")
        raise last_exception

    return wrapper


def validate_approval_token(token: str, action_hash: str) -> Tuple[bool, Optional[str]]:
    """
    Validate approval token against action hash.

    Returns: (is_valid, error_message)

    In production, this would:
    1. Verify JWT signature
    2. Check expiry (TTL)
    3. Verify token hasn't been used (single-use)
    4. Check action_hash matches token claim

    For now, returns a placeholder implementation.
    """
    # TODO: Implement JWT validation with:
    # - Signature verification (HMAC or RSA)
    # - Expiry check (token_ttl_minutes from config)
    # - Single-use check (store used tokens in DynamoDB or Redis)
    # - Action hash binding check

    if not token or len(token) < 20:
        return False, "Invalid token format"

    # Placeholder: always valid for now
    logger.warning("Approval token validation not yet implemented (placeholder)")
    return True, None


def create_lambda_response(
    status_code: int, body: Dict[str, Any], trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardised Lambda response.

    Args:
        status_code: HTTP status code
        body: Response body dict
        trace_id: Optional trace ID for correlation

    Returns:
        Lambda response dict
    """
    response_body = body.copy()
    if trace_id:
        response_body["trace_id"] = trace_id

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Trace-Id": trace_id or "none",
        },
        "body": json.dumps(response_body),
    }
