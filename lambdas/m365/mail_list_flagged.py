"""
M365 Mail Tool: List Flagged Emails

Lists flagged (important) emails from the user's Outlook mailbox.
"""

import json
from datetime import datetime, timezone, timedelta
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
)


# Input schema
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "since": {
            "type": "string",
            "format": "date-time",
            "description": "List emails since this timestamp (ISO8601)",
        },
        "trace_id": {"type": "string"},
    },
    "additionalProperties": False,
}


@tracer.capture_method
@retry_with_backoff
def list_flagged_emails(since: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List flagged emails from Outlook.

    Args:
        since: Optional ISO8601 timestamp to filter emails

    Returns:
        List of email summaries
    """
    graph_client = get_graph_client()

    # Build filter query
    filter_query = "importance eq 'high' or flag/flagStatus eq 'flagged'"

    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        filter_query += f" and receivedDateTime ge {since_dt.isoformat()}"
    else:
        # Default: last 7 days
        since_dt = datetime.now(timezone.utc) - timedelta(days=7)
        filter_query += f" and receivedDateTime ge {since_dt.isoformat()}"

    # Query Graph API
    messages = (
        graph_client.me.messages.get(
            request_configuration={
                "query_parameters": {
                    "$filter": filter_query,
                    "$select": "id,subject,from,receivedDateTime,webLink,hasAttachments",
                    "$top": 50,
                    "$orderby": "receivedDateTime desc",
                }
            }
        )
        .value
    )

    # Format results
    results = []
    for msg in messages:
        results.append(
            {
                "id": msg.id,
                "subject": msg.subject,
                "from": msg.from_.email_address.address if msg.from_ else "Unknown",
                "received_at": msg.received_date_time.isoformat() if msg.received_date_time else None,
                "url": msg.web_link,
                "has_attachments": msg.has_attachments or False,
            }
        )

    logger.info(f"Listed {len(results)} flagged emails")
    return results


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for mail.list_flagged tool.

    Input:
        {
          "since": "2024-01-01T00:00:00Z",  // optional
          "trace_id": "abc123"              // optional
        }

    Output:
        {
          "emails": [
            {
              "id": "AAMkAD...",
              "subject": "Important: Review needed",
              "from": "alice@example.com",
              "received_at": "2024-02-01T10:30:00Z",
              "url": "https://outlook.office365.com/...",
              "has_attachments": false
            }
          ],
          "count": 5
        }
    """
    trace_id = event.get("trace_id", context.request_id)

    try:
        # Validate input
        validate(instance=event, schema=INPUT_SCHEMA)

        since = event.get("since")

        logger.info(
            "Listing flagged emails",
            extra=redact_pii({"trace_id": trace_id, "since": since}),
        )

        # Call Graph API
        emails = list_flagged_emails(since=since)

        return create_lambda_response(
            200,
            {"emails": emails, "count": len(emails)},
            trace_id=trace_id,
        )

    except ValidationError as e:
        logger.error("Input validation failed", extra={"error": str(e)})
        return create_lambda_response(
            400,
            {"error": "bad_args", "message": str(e)},
            trace_id=trace_id,
        )

    except Exception as e:
        logger.error("Failed to list flagged emails", exc_info=e)

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
