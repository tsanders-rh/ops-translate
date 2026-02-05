"""Utilities for redacting sensitive data from strings."""

import re

# Patterns for sensitive data that should be redacted
SENSITIVE_PATTERNS = [
    # API keys, tokens, secrets
    (r'(api[_-]?key|token|auth|secret|password)[=:"\s]+\S+', 'REDACTED'),
    # Bearer tokens
    (r'Bearer\s+\S+', 'Bearer REDACTED'),
    # OpenAI API keys
    (r'sk-[a-zA-Z0-9]{20,}', 'sk-REDACTED'),
    # Anthropic API keys
    (r'sk-ant-[a-zA-Z0-9\-]+', 'sk-ant-REDACTED'),
]


def redact_sensitive(text: str) -> str:
    """
    Redact sensitive data from text using pattern matching.

    Args:
        text: Text potentially containing sensitive data

    Returns:
        Text with sensitive data replaced with REDACTED markers

    Example:
        >>> redact_sensitive("api_key=sk-1234567890abcdef")
        'api_key=sk-REDACTED'
    """
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result
