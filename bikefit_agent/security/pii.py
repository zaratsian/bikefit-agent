"""PII (Personally Identifiable Information) Redaction Engine.

Sanitizes text, dictionaries, and nested objects to prevent leaking emails, phone numbers,
IP addresses, credit card numbers, and rider identities into log streams and telemetry.
"""

import re
from typing import Any, Dict, List, Union

# Regex patterns for common PII
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

# Keys commonly holding sensitive personal identification
SENSITIVE_KEYS = {
    "email", "phone", "name", "rider_name", "first_name", "last_name",
    "address", "password", "token", "api_key", "secret", "credit_card"
}


def redact_pii_text(text: str) -> str:
    """Scrub PII entities from string text.

    Args:
        text: Raw text string.

    Returns:
        Redacted string with sensitive patterns replaced with safe tokens.
    """
    if not isinstance(text, str):
        return text

    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", text)
    text = SSN_PATTERN.sub("[REDACTED_SSN]", text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    text = IP_PATTERN.sub("[REDACTED_IP]", text)
    return text


def sanitize_payload(payload: Any) -> Any:
    """Recursively sanitize dictionary or list payload for safe logging and telemetry.

    Args:
        payload: Arbitrary data structure (dict, list, str, primitive).

    Returns:
        Deep sanitized copy of payload with PII redacted.
    """
    if isinstance(payload, str):
        return redact_pii_text(payload)
    elif isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if any(sens in key.lower() for sens in SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED_PII]"
            else:
                sanitized[key] = sanitize_payload(value)
        return sanitized
    elif isinstance(payload, (list, tuple, set)):
        return [sanitize_payload(item) for item in payload]
    elif hasattr(payload, "model_dump"):
        # Support Pydantic models
        return sanitize_payload(payload.model_dump())
    elif hasattr(payload, "__dict__"):
        return sanitize_payload(payload.__dict__)
    return payload
