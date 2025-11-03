"""
M365 Planner Tool: Create Task

Creates a task in Microsoft Planner. Requires approval token.
"""

import json
from typing import Dict, Any, List, Optional

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
    "required": ["plan", "bucket", "title", "approval_token"],
    "properties": {
        "plan": {"type": "string", "minLength": 1},
        "bucket": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1, "maxLength": 255},
        "due_at": {"type": "string", "format": "date-time"},
        "checklist": {"type": "array", "items": {"type": "string"}},
        "approval_token": {"type": "string", "minLength": 20},
        "trace_id": {"type": "string"},
        "idempotency_key": {"type": "string"},
    },
    "additionalProperties": False,
}


@tracer.capture_method
@retry_with_backoff
def create_planner_task(
    plan: str,
    bucket: str,
    title: str,
    due_at: Optional[str] = None,
    checklist: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create Planner task.

    Note: Requires Planner plan ID and bucket ID lookups.
    This stub implementation needs completion.
    """
    graph_client = get_graph_client()

    # TODO: Implement Planner task creation
    # 1. Look up plan ID from plan name
    # 2. Look up bucket ID from bucket name within plan
    # 3. Create task with Graph API
    # 4. Add checklist items if provided

    logger.warning("Planner task creation not yet fully implemented (stub)")

    # Stub response
    task_id = "stub-task-id"
    return {
        "task_id": task_id,
        "url": f"https://tasks.office.com/tasks/{task_id}",
    }


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for planner.create tool."""
    trace_id = event.get("trace_id", context.request_id)
    idempotency_key = event.get("idempotency_key")

    try:
        if idempotency_key:
            cached_result = check_idempotency(idempotency_key)
            if cached_result:
                return create_lambda_response(200, cached_result, trace_id=trace_id)

        validate(instance=event, schema=INPUT_SCHEMA)

        plan = event["plan"]
        bucket = event["bucket"]
        title = event["title"]
        due_at = event.get("due_at")
        checklist = event.get("checklist", [])
        approval_token = event["approval_token"]

        action_payload = {"plan": plan, "bucket": bucket, "title": title, "due_at": due_at}
        action_hash = compute_action_hash(action_payload)

        logger.info("Creating Planner task", extra=redact_pii({"trace_id": trace_id, "title": title}))

        is_valid, error_msg = validate_approval_token(approval_token, action_hash)
        if not is_valid:
            return create_lambda_response(403, {"error": "auth_error", "message": f"Invalid approval token: {error_msg}"}, trace_id=trace_id)

        result = create_planner_task(plan=plan, bucket=bucket, title=title, due_at=due_at, checklist=checklist)

        if idempotency_key:
            store_idempotency(idempotency_key, result)

        return create_lambda_response(200, result, trace_id=trace_id)

    except ValidationError as e:
        return create_lambda_response(400, {"error": "bad_args", "message": str(e)}, trace_id=trace_id)

    except Exception as e:
        logger.error("Failed to create Planner task", exc_info=e)
        status_code = getattr(e, "status_code", 500)
        error_code = map_error_code(status_code)
        return create_lambda_response(status_code, {"error": error_code, "message": str(e)}, trace_id=trace_id)
