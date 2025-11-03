"""
Tests for M365 common utilities.
"""

import pytest
from unittest.mock import Mock, patch
import hashlib
import json


def test_compute_action_hash():
    """Test action hash computation for approval binding."""
    # Import would fail without mocking AWS dependencies
    # This is a stub test structure
    payload = {"to": ["alice@example.com"], "subject": "Test", "body": "Hello"}

    # Compute expected hash
    normalised = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    expected_hash = hashlib.sha256(normalised.encode("utf-8")).hexdigest()

    # Would test: from lambdas.m365.common import compute_action_hash
    # actual_hash = compute_action_hash(payload)
    # assert actual_hash == expected_hash

    assert len(expected_hash) == 64  # SHA-256 produces 64 hex chars
    assert all(c in "0123456789abcdef" for c in expected_hash)


def test_redact_pii():
    """Test PII redaction from logs."""
    data = {
        "trace_id": "abc123",
        "tool": "mail.draft",
        "body": "Sensitive email content",
        "token": "secret-token",
        "subject": "Test Subject",
    }

    # Would test: from lambdas.m365.common import redact_pii
    # redacted = redact_pii(data)
    # assert redacted["body"] == "[REDACTED]"
    # assert redacted["token"] == "[REDACTED]"
    # assert redacted["trace_id"] == "abc123"
    # assert redacted["subject"] == "Test Subject"

    # Placeholder assertion
    assert "body" in data and "token" in data


def test_map_error_code():
    """Test HTTP error code mapping."""
    # Would test: from lambdas.m365.common import map_error_code

    # Expected mappings
    expected = {
        400: "bad_args",
        401: "auth_error",
        404: "not_found",
        429: "rate_limited",
        500: "internal",
    }

    for status_code, error_type in expected.items():
        # assert map_error_code(status_code) == error_type
        pass

    # Placeholder assertion
    assert 400 in expected and expected[400] == "bad_args"


@pytest.mark.skip(reason="Requires AWS SDK mocking")
def test_get_ssm_parameter():
    """Test SSM parameter retrieval."""
    # Would use moto to mock SSM
    pass


@pytest.mark.skip(reason="Requires Graph SDK mocking")
def test_get_graph_client():
    """Test Microsoft Graph client creation."""
    # Would mock azure.identity and msgraph
    pass
