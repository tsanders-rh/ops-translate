"""
Intent and artifact validation with detailed error messages.
"""

import json
from pathlib import Path

import yaml
from jsonschema import ValidationError, validate
from jsonschema.exceptions import SchemaError

# Get project root to find schema
PROJECT_ROOT = Path(__file__).parent.parent.parent


def validate_intent(intent_file: Path) -> tuple[bool, list]:
    """
    Validate intent YAML against schema using jsonschema.

    Returns:
        tuple: (is_valid, error_messages)
    """
    try:
        # Load intent YAML
        intent = yaml.safe_load(intent_file.read_text())

        # Load schema
        schema_file = PROJECT_ROOT / "schema/intent.schema.json"
        if not schema_file.exists():
            return (False, [f"Schema file not found: {schema_file}"])

        schema = json.loads(schema_file.read_text())

        # Validate against schema
        try:
            validate(instance=intent, schema=schema)
            return (True, [])
        except ValidationError as e:
            # Format validation error into helpful message
            errors = format_validation_error(e)
            return (False, errors)
        except SchemaError as e:
            return (False, [f"Invalid schema: {e}"])

    except yaml.YAMLError as e:
        return (False, [f"YAML parse error: {e}"])
    except Exception as e:
        return (False, [f"Validation error: {e}"])


def format_validation_error(error: ValidationError) -> list:
    """
    Format jsonschema ValidationError into user-friendly messages with examples.

    Args:
        error: ValidationError from jsonschema

    Returns:
        list: List of formatted error messages with helpful suggestions
    """
    errors = []

    # Build the path to the problematic field
    path = ".".join(str(p) for p in error.path) if error.path else "root"

    # Main error message
    main_error = f"Validation error at '{path}': {error.message}"
    errors.append(main_error)

    # Add context about what was expected
    if error.validator == "required":
        missing_props = error.message.split("'")[1::2]  # Extract property names
        errors.append(f"  Required properties missing: {', '.join(missing_props)}")

        # Add examples for common required fields
        if "schema_version" in missing_props:
            errors.append("  Example: schema_version: 1")
        if "type" in missing_props:
            errors.append("  Example: type: powercli")
        if "workflow_name" in missing_props:
            errors.append("  Example: workflow_name: provision_vm")

    elif error.validator == "type":
        errors.append(f"  Expected type: {error.validator_value}")
        errors.append(f"  Got: {type(error.instance).__name__}")

        # Add type conversion hints
        if error.validator_value == "integer" and isinstance(error.instance, str):
            stripped_value = error.instance.strip().replace('"', "")
            errors.append(
                f"  Hint: Remove quotes around the number: {error.instance} → {stripped_value}"
            )
        elif error.validator_value == "string" and not isinstance(error.instance, str):
            errors.append(
                f'  Hint: Add quotes around the value: {error.instance} → "{error.instance}"'
            )

    elif error.validator == "enum":
        # Type guard: validator_value should be iterable for enum errors
        validator_value = error.validator_value
        if hasattr(validator_value, "__iter__"):
            errors.append(f"  Allowed values: {', '.join(str(v) for v in validator_value)}")
        errors.append(f"  Got: {error.instance}")

        # Suggest closest match if applicable
        if isinstance(error.instance, str) and hasattr(validator_value, "__iter__"):
            close_matches = [
                v for v in validator_value if isinstance(v, str) and v.startswith(error.instance[0])
            ]
            if close_matches:
                errors.append(f"  Did you mean: {close_matches[0]}?")

    elif error.validator == "pattern":
        errors.append(f"  Expected pattern: {error.validator_value}")
        errors.append(f"  Got: {error.instance}")

        # Common pattern hints
        if "snake_case" in str(error.validator_value).lower() or "_" in str(error.validator_value):
            errors.append("  Hint: Use lowercase letters, numbers, and underscores only")
            suggested_value = str(error.instance).lower().replace(" ", "_").replace("-", "_")
            errors.append(f"  Example: {error.instance} → {suggested_value}")

    elif error.validator == "minimum" or error.validator == "maximum":
        errors.append(f"  Constraint: {error.validator} = {error.validator_value}")
        errors.append(f"  Got: {error.instance}")

        # Show valid range
        if error.validator == "minimum":
            errors.append(f"  Hint: Value must be >= {error.validator_value}")
        else:
            errors.append(f"  Hint: Value must be <= {error.validator_value}")

    # Add field-specific suggestions
    field_name = str(error.path[-1]) if error.path else ""

    if field_name == "schema_version":
        errors.append("  Hint: schema_version must be the integer 1 (not a string)")
        errors.append("  Correct:   schema_version: 1")
        errors.append('  Incorrect: schema_version: "1"')

    elif field_name == "workflow_name":
        errors.append("  Hint: Use snake_case naming (lowercase with underscores)")
        errors.append("  Correct:   workflow_name: provision_dev_vm")
        errors.append("  Incorrect: workflow_name: Provision-Dev-VM")

    elif field_name == "type":
        errors.append("  Hint: type must be one of: powercli, vrealize, custom")
        errors.append("  Example: type: powercli")

    elif field_name == "cpu_count" or field_name == "memory_gb":
        errors.append(f"  Hint: {field_name} must be a positive integer")
        errors.append(f"  Example: {field_name}: 4")

    elif field_name == "required":
        errors.append("  Hint: required must be a boolean (true or false)")
        errors.append("  Correct:   required: true")
        errors.append("  Incorrect: required: yes")

    elif "inputs" in str(error.path):
        errors.append("  Hint: Each input must have name, type, and required fields")
        errors.append("  Example:")
        errors.append("    inputs:")
        errors.append("      - name: vm_name")
        errors.append("        type: string")
        errors.append("        required: true")

    return errors


def validate_artifacts(workspace) -> tuple[bool, list]:
    """
    Validate generated artifacts.

    Returns:
        tuple: (is_valid, messages)
    """
    messages = []
    all_valid = True

    # Check KubeVirt YAML
    kubevirt_file = workspace.root / "output/kubevirt/vm.yaml"
    if kubevirt_file.exists():
        try:
            yaml.safe_load(kubevirt_file.read_text())
            messages.append("[green]✓ KubeVirt YAML is valid[/green]")
        except yaml.YAMLError as e:
            messages.append(f"[red]✗ KubeVirt YAML invalid: {e}[/red]")
            all_valid = False
    else:
        messages.append("[yellow]- KubeVirt YAML not found[/yellow]")

    # Check Ansible playbook
    ansible_file = workspace.root / "output/ansible/site.yml"
    if ansible_file.exists():
        try:
            yaml.safe_load(ansible_file.read_text())
            messages.append("[green]✓ Ansible playbook YAML is valid[/green]")
        except yaml.YAMLError as e:
            messages.append(f"[red]✗ Ansible playbook invalid: {e}[/red]")
            all_valid = False
    else:
        messages.append("[yellow]- Ansible playbook not found[/yellow]")

    return (all_valid, messages)
