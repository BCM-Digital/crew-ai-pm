"""
M365 Teams Tool: Send Adaptive Card

Sends an Adaptive Card to a Teams chat (typically for approvals).
"""

import json
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
)


INPUT_SCHEMA = {
    "type": "object",
    "required": ["chat_id", "card_json"],
    "properties": {
        "chat_id": {"type": "string", "minLength": 1},
        "card_json": {"type": "object"},
        "trace_id": {"type": "string"},
    },
    "additionalProperties": False,
}


@tracer.capture_method
@retry_with_backoff
def send_adaptive_card(chat_id: str, card_json: Dict[str, Any]) -> Dict[str, Any]:
    """Send Adaptive Card to Teams chat."""
    graph_client = get_graph_client()

    # Build chat message with Adaptive Card
    message_body = {
        "body": {
            "contentType": "html",
            "content": "<attachment id='card'></attachment>",
        },
        "attachments": [
            {
                "id": "card",
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": json.dumps(card_json),
            }
        ],
    }

    # Send message
    sent_message = graph_client.chats.by_chat_id(chat_id).messages.post(message_body)

    logger.info(f"Sent adaptive card to chat {chat_id}", extra={"message_id": sent_message.id})

    return {"submission_id": sent_message.id}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for teams.send_card tool."""
    trace_id = event.get("trace_id", context.request_id)

    try:
        validate(instance=event, schema=INPUT_SCHEMA)

        chat_id = event["chat_id"]
        card_json = event["card_json"]

        logger.info("Sending Teams adaptive card", extra=redact_pii({"trace_id": trace_id, "chat_id": chat_id}))

        result = send_adaptive_card(chat_id=chat_id, card_json=card_json)

        return create_lambda_response(200, result, trace_id=trace_id)

    except ValidationError as e:
        return create_lambda_response(400, {"error": "bad_args", "message": str(e)}, trace_id=trace_id)

    except Exception as e:
        logger.error("Failed to send adaptive card", exc_info=e)
        status_code = getattr(e, "status_code", 500)
        error_code = map_error_code(status_code)
        return create_lambda_response(status_code, {"error": error_code, "message": str(e)}, trace_id=trace_id)
