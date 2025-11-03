"""
Common utilities for GitHub tool adapters.
"""

import os
import boto3
from github import Github
from aws_lambda_powertools import Logger, Tracer, Metrics

logger = Logger(service="pm-agent-github")
tracer = Tracer(service="pm-agent-github")
metrics = Metrics(namespace="PMAgent", service="github-tools")

ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "ap-southeast-2"))


def get_github_client() -> Github:
    """Get authenticated GitHub client."""
    token_ssm = os.environ.get("GITHUB_TOKEN_SSM", "/pm-agent/github/token")
    response = ssm.get_parameter(Name=token_ssm, WithDecryption=True)
    token = response["Parameter"]["Value"]
    return Github(token)
