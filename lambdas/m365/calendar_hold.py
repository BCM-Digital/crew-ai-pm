"""
M365 Calendar Tool: Create Hold

Creates a calendar hold/block. Requires approval token.
"""

import json
from datetime import datetime
from typing import Dict, Any

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


INPUT_SCHEMA = {
    "type": "object",
    "required": ["title", "start", "end", "approval_token"],
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 255},
        "start": {"type": "string", "format": "date-time"},
        "end": {"type": "string", "format": "date-time"},
        "approval_token": {"type": "string", "minLength": 20},
        "trace_id": {"type": "string"},
        "idempotency_key": {"type": "string"},
    },
    "additionalProperties": False,
}


@tracer.capture_method
@retry_with_backoff
def create_calendar_hold(title: str, start: str, end: str) -> Dict[str, Any]:
    """Create calendar hold."""
    graph_client = get_graph_client()

    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

    event = {
        "subject": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Australia/Brisbane"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Australia/Brisbane"},
        "isReminderOn": False,
        "showAs": "busy",
    }

    created_event = graph_client.me.events.post(event)

    logger.info(f"Created calendar hold {created_event.id}", extra={"title": title})

    return {"event_id": created_event.id, "url": created_event.web_link}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for calendar.hold tool."""
    trace_id = event.get("trace_id", context.request_id)
    idempotency_key = event.get("idempotency_key")

    try:
        if idempotency_key:
            cached_result = check_idempotency(idempotency_key)
            if cached_result:
                logger.info(f"Returning cached result for idempotency key {idempotency_key}")
                return create_lambda_response(200, cached_result, trace_id=trace_id)

        validate(instance=event, schema=INPUT_SCHEMA)

        title = event["title"]
        start = event["start"]
        end = event["end"]
        approval_token = event["approval_token"]

        action_payload = {"title": title, "start": start, "end": end}
        action_hash = compute_action_hash(action_payload)

        logger.info("Creating calendar hold", extra=redact_pii({"trace_id": trace_id, "title": title, "action_hash": action_hash}))

        is_valid, error_msg = validate_approval_token(approval_token, action_hash)
        if not is_valid:
            return create_lambda_response(403, {"error": "auth_error", "message": f"Invalid approval token: {error_msg}"}, trace_id=trace_id)

        result = create_calendar_hold(title=title, start=start, end=end)

        if idempotency_key:
            store_idempotency(idempotency_key, result)

        return create_lambda_response(200, result, trace_id=trace_id)

    except ValidationError as e:
        return create_lambda_response(400, {"error": "bad_args", "message": str(e)}, trace_id=trace_id)

    except Exception as e:
        logger.error("Failed to create calendar hold", exc_info=e)
        status_code = getattr(e, "status_code", 500)
        error_code = map_error_code(status_code)
        return create_lambda_response(status_code, {"error": error_code, "message": str(e)}, trace_id=trace_id)
