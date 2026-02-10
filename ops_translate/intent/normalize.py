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

    # Normalize profiles (incomplete conditional → simple string/object)
    if "profiles" in intent and isinstance(intent["profiles"], dict):
        profiles = intent["profiles"]
        for profile_key, profile_value in list(profiles.items()):
            # If profile value is a dict with only 'value' (no 'when'), flatten to simple string
            if (
                isinstance(profile_value, dict)
                and "value" in profile_value
                and "when" not in profile_value
            ):
                # Convert {value: "foo"} to just "foo"
                profiles[profile_key] = profile_value["value"]
            # If profile value is a plain dict without 'value' or 'when', it's invalid
            # Remove it to avoid schema errors (LLM mistake - profiles should be simple strings or conditionals)
            elif (
                isinstance(profile_value, dict)
                and "value" not in profile_value
                and "when" not in profile_value
            ):
                # This is likely a malformed profile - log and remove it
                # E.g., compute: {resource_pool: "Prod-Pool"} should be compute_resource_pool: "Prod-Pool"
                del profiles[profile_key]

    # Normalize metadata tags (dict → array)
    if "metadata" in intent and isinstance(intent["metadata"], dict):
        metadata = intent["metadata"]

        # If tags is a dict, convert to array of {key, value/value_from} objects
        if "tags" in metadata and isinstance(metadata["tags"], dict):
            tag_dict = metadata["tags"]
            tag_array = []

            for key, value in tag_dict.items():
                tag_obj = {"key": key}

                # Handle different tag value formats from LLM
                if isinstance(value, dict):
                    # LLM format: {source: input, parameter: param_name}
                    if value.get("source") == "input" and "parameter" in value:
                        tag_obj["value_from"] = value["parameter"]
                    elif "value" in value:
                        tag_obj["value"] = str(value["value"])
                    else:
                        # Fallback: use the dict as a string value
                        tag_obj["value"] = str(value)
                elif isinstance(value, str):
                    # Simple string value
                    tag_obj["value"] = value
                else:
                    # Other types: convert to string
                    tag_obj["value"] = str(value)

                tag_array.append(tag_obj)

            metadata["tags"] = tag_array

        # Same for labels
        if "labels" in metadata and isinstance(metadata["labels"], dict):
            label_dict = metadata["labels"]
            label_array = []

            for key, value in label_dict.items():
                label_obj = {"key": key}

                # Handle different label value formats from LLM
                if isinstance(value, dict):
                    if value.get("source") == "input" and "parameter" in value:
                        label_obj["value_from"] = value["parameter"]
                    elif "value" in value:
                        label_obj["value"] = str(value["value"])
                    else:
                        label_obj["value"] = str(value)
                elif isinstance(value, str):
                    label_obj["value"] = value
                else:
                    label_obj["value"] = str(value)

                label_array.append(label_obj)

            metadata["labels"] = label_array

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
