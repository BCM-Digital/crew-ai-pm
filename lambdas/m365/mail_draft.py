"""
M365 Mail Tool: Draft Email

Drafts an email in Outlook. Requires approval token.
"""

import json
from typing import Dict, Any, List

from aws_lambda_powertools.utilities.typing import LambdaContext
from jsonschema import validate, ValidationError

from common import (
    logger,
    tracer,
    metrics,
    get_graph_client,
    redact_pii,
    map_error_code,
    retry_with_backoff,
    create_lambda_response,
    compute_action_hash,
    validate_approval_token,
    check_idempotency,
    store_idempotency,
)


# Input schema
INPUT_SCHEMA = {
    "type": "object",
    "required": ["to", "subject", "body", "approval_token"],
    "properties": {
        "to": {
            "type": "array",
            "items": {"type": "string", "format": "email"},
            "minItems": 1,
            "maxItems": 50,
        },
        "subject": {"type": "string", "minLength": 1, "maxLength": 255},
        "body": {"type": "string", "minLength": 1, "maxLength": 50000},
        "refs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Email IDs to reference (In-Reply-To)",
        },
        "approval_token": {"type": "string", "minLength": 20},
        "trace_id": {"type": "string"},
        "idempotency_key": {"type": "string"},
    },
    "additionalProperties": False,
}


@tracer.capture_method
@retry_with_backoff
def draft_email(
    to: List[str], subject: str, body: str, refs: List[str] = None
) -> Dict[str, Any]:
    """
    Draft an email in Outlook.

    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Email body (plain text or HTML)
        refs: Optional list of message IDs to reference

    Returns:
        Draft ID and URL
    """
    graph_client = get_graph_client()

    # Build message
    message = {
        "subject": subject,
        "body": {"contentType": "HTML" if "<" in body else "Text", "content": body},
        "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
    }

    if refs:
        # Set In-Reply-To header (requires messages/reply, not implemented here)
        logger.info(f"Email references {len(refs)} previous messages (not implemented)")

    # Create draft
    draft = graph_client.me.messages.post(message)

    logger.info(
        f"Created draft {draft.id}",
        extra={"draft_id": draft.id, "subject": subject, "to_count": len(to)},
    )

    return {
        "draft_id": draft.id,
        "url": draft.web_link or f"https://outlook.office365.com/mail/inbox/id/{draft.id}",
    }


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for mail.draft tool.

    Input:
        {
          "to": ["alice@example.com", "bob@example.com"],
          "subject": "Project Update",
          "body": "Hi team,\n\nStatus update...",
          "refs": ["msg-id-123"],           // optional
          "approval_token": "jwt-token",
          "trace_id": "abc123",             // optional
          "idempotency_key": "key-xyz"      // optional
        }

    Output:
        {
          "draft_id": "AAMkAD...",
          "url": "https://outlook.office365.com/..."
        }
    """
    trace_id = event.get("trace_id", context.request_id)
    idempotency_key = event.get("idempotency_key")

    try:
        # Check idempotency
        if idempotency_key:
            cached_result = check_idempotency(idempotency_key)
            if cached_result:
                logger.info(f"Returning cached result for idempotency key {idempotency_key}")
                return create_lambda_response(200, cached_result, trace_id=trace_id)

        # Validate input
        validate(instance=event, schema=INPUT_SCHEMA)

        to = event["to"]
        subject = event["subject"]
        body = event["body"]
        refs = event.get("refs", [])
        approval_token = event["approval_token"]

        # Compute action hash (for approval binding)
        action_payload = {"to": to, "subject": subject, "body": body}
        action_hash = compute_action_hash(action_payload)

        logger.info(
            "Drafting email",
            extra=redact_pii(
                {
                    "trace_id": trace_id,
                    "to_count": len(to),
                    "subject": subject,
                    "action_hash": action_hash,
                }
            ),
        )

        # Validate approval token
        is_valid, error_msg = validate_approval_token(approval_token, action_hash)
        if not is_valid:
            logger.warning(f"Invalid approval token: {error_msg}")
            return create_lambda_response(
                403,
                {"error": "auth_error", "message": f"Invalid approval token: {error_msg}"},
                trace_id=trace_id,
            )

        # Draft email
        result = draft_email(to=to, subject=subject, body=body, refs=refs)

        # Store idempotency result
        if idempotency_key:
            store_idempotency(idempotency_key, result)

        return create_lambda_response(200, result, trace_id=trace_id)

    except ValidationError as e:
        logger.error("Input validation failed", extra={"error": str(e)})
        return create_lambda_response(
            400,
            {"error": "bad_args", "message": str(e)},
            trace_id=trace_id,
        )

    except Exception as e:
        logger.error("Failed to draft email", exc_info=e)

        status_code = 500
        error_code = "internal"

        if hasattr(e, "status_code"):
            status_code = e.status_code
            error_code = map_error_code(status_code)

        return create_lambda_response(
            status_code,
            {"error": error_code, "message": str(e)},
            trace_id=trace_id,
        )
