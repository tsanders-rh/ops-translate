"""
Intent and artifact validation.
"""

from pathlib import Path
import yaml
import json
from jsonschema import validate, ValidationError, Draft7Validator
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
    Format jsonschema ValidationError into user-friendly messages.

    Args:
        error: ValidationError from jsonschema

    Returns:
        list: List of formatted error messages
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

    elif error.validator == "type":
        errors.append(f"  Expected type: {error.validator_value}")
        errors.append(f"  Got: {type(error.instance).__name__}")

    elif error.validator == "enum":
        errors.append(f"  Allowed values: {error.validator_value}")
        errors.append(f"  Got: {error.instance}")

    elif error.validator == "pattern":
        errors.append(f"  Expected pattern: {error.validator_value}")
        errors.append(f"  Got: {error.instance}")

    elif error.validator == "minimum" or error.validator == "maximum":
        errors.append(f"  Constraint: {error.validator} = {error.validator_value}")
        errors.append(f"  Got: {error.instance}")

    # Add suggestion for common errors
    if "schema_version" in str(error.path):
        errors.append("  Hint: schema_version must be the integer 1")
    elif "workflow_name" in str(error.path):
        errors.append("  Hint: workflow_name must be snake_case (lowercase with underscores)")
    elif "workload_type" in str(error.path):
        errors.append(
            "  Hint: workload_type must be one of: virtual_machine, container, baremetal, other"
        )

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
