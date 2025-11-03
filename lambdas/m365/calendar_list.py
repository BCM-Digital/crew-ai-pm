"""
M365 Calendar Tool: List Events

Lists calendar events for a given time range.
"""

import json
from datetime import datetime, timezone, timedelta
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
)


INPUT_SCHEMA = {
    "type": "object",
    "required": ["start", "end"],
    "properties": {
        "start": {"type": "string", "format": "date-time"},
        "end": {"type": "string", "format": "date-time"},
        "trace_id": {"type": "string"},
    },
    "additionalProperties": False,
}


@tracer.capture_method
@retry_with_backoff
def list_calendar_events(start: str, end: str) -> List[Dict[str, Any]]:
    """List calendar events in time range."""
    graph_client = get_graph_client()

    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

    events = (
        graph_client.me.calendar_view.get(
            request_configuration={
                "query_parameters": {
                    "startDateTime": start_dt.isoformat(),
                    "endDateTime": end_dt.isoformat(),
                    "$select": "id,subject,start,end,organizer,webLink,location",
                    "$top": 100,
                    "$orderby": "start/dateTime",
                }
            }
        )
        .value
    )

    results = []
    for event in events:
        results.append(
            {
                "id": event.id,
                "title": event.subject,
                "start": event.start.date_time if event.start else None,
                "end": event.end.date_time if event.end else None,
                "organiser": event.organizer.email_address.address if event.organizer else "Unknown",
                "url": event.web_link,
                "location": event.location.display_name if event.location else None,
            }
        )

    logger.info(f"Listed {len(results)} calendar events")
    return results


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for calendar.list tool."""
    trace_id = event.get("trace_id", context.request_id)

    try:
        validate(instance=event, schema=INPUT_SCHEMA)

        start = event["start"]
        end = event["end"]

        logger.info("Listing calendar events", extra={"trace_id": trace_id, "start": start, "end": end})

        events = list_calendar_events(start=start, end=end)

        return create_lambda_response(
            200,
            {"events": events, "count": len(events)},
            trace_id=trace_id,
        )

    except ValidationError as e:
        logger.error("Input validation failed", extra={"error": str(e)})
        return create_lambda_response(400, {"error": "bad_args", "message": str(e)}, trace_id=trace_id)

    except Exception as e:
        logger.error("Failed to list calendar events", exc_info=e)
        status_code = getattr(e, "status_code", 500)
        error_code = map_error_code(status_code)
        return create_lambda_response(status_code, {"error": error_code, "message": str(e)}, trace_id=trace_id)
