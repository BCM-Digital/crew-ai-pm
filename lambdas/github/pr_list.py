"""
GitHub Tool: List Pull Requests (stub implementation)
"""

import json
from typing import Dict, Any
from aws_lambda_powertools.utilities.typing import LambdaContext
from common import logger, tracer, metrics


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for pr.list tool. TODO: Complete implementation."""
    logger.info("GitHub pr.list stub called")
    return {
        "statusCode": 200,
        "body": json.dumps({"prs": [], "message": "Stub implementation - TODO"}),
    }
