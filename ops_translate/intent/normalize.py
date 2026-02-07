"""
Schema normalization utilities for LLM-extracted intent data.

This module provides functions to normalize LLM output to match expected schema,
handling common deviations like `number` vs `integer` types and `dict` vs `array`
for tags/labels.
"""

from typing import Any


def normalize_intent_schema(intent_data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize intent YAML to fix common LLM schema deviations.

    Common fixes:
    - Convert `number` type to `integer` in input definitions
    - Convert tag dicts to tag arrays
    - Ensure consistent type representations

    Args:
        intent_data: Raw intent data from LLM (with 'intent' key)

    Returns:
        Normalized intent data with schema fixes applied

    Example:
        >>> data = {"intent": {"inputs": {"memory_gb": {"type": "number"}}}}
        >>> normalized = normalize_intent_schema(data)
        >>> normalized["intent"]["inputs"]["memory_gb"]["type"]
        'integer'
    """
    if not isinstance(intent_data, dict) or "intent" not in intent_data:
        return intent_data

    intent = intent_data["intent"]

    # Normalize input types (number → integer)
    if "inputs" in intent and isinstance(intent["inputs"], dict):
        for param_name, param_def in intent["inputs"].items():
            if isinstance(param_def, dict) and param_def.get("type") == "number":
                param_def["type"] = "integer"

    # Normalize metadata tags (dict → array)
    if "metadata" in intent and isinstance(intent["metadata"], dict):
        metadata = intent["metadata"]

        # If tags is a dict, convert to array of {key, value} objects
        if "tags" in metadata and isinstance(metadata["tags"], dict):
            tag_dict = metadata["tags"]
            metadata["tags"] = [{"key": k, "value": v} for k, v in tag_dict.items()]

        # Same for labels
        if "labels" in metadata and isinstance(metadata["labels"], dict):
            label_dict = metadata["labels"]
            metadata["labels"] = [{"key": k, "value": v} for k, v in label_dict.items()]

    return intent_data


def safe_str_lower(value: Any, default: str = "") -> str:
    """
    Safely convert a value to lowercase string.

    Handles cases where LLM output may contain non-string types (dict, list, None).
    This defensive helper prevents AttributeError on .lower() calls.

    Args:
        value: Value to convert (may be str, dict, list, None, etc.)
        default: Default value if conversion fails

    Returns:
        Lowercase string or default if conversion not possible

    Examples:
        >>> safe_str_lower("VM Network")
        'vm network'
        >>> safe_str_lower({"name": "network"})
        ''
        >>> safe_str_lower(None)
        ''
    """
    if isinstance(value, str):
        return value.lower()
    if value is None:
        return default
    # For dict, list, or other types, return default
    return default


def safe_get_string(data: dict[str, Any], key: str, default: str = "") -> str:
    """
    Safely get a string value from a dict.

    Args:
        data: Dictionary to get value from
        key: Key to look up
        default: Default value if key missing or value not a string

    Returns:
        String value or default

    Examples:
        >>> safe_get_string({"name": "test"}, "name")
        'test'
        >>> safe_get_string({"name": {"nested": "value"}}, "name")
        ''
        >>> safe_get_string({}, "missing", "default")
        'default'
    """
    value = data.get(key)
    if isinstance(value, str):
        return value
    return default
