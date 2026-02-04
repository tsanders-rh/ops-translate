"""
Intent and artifact validation.
"""
from pathlib import Path
import yaml
import json


def validate_intent(intent_file: Path) -> tuple[bool, list]:
    """
    Validate intent YAML against schema.

    Returns:
        tuple: (is_valid, error_messages)
    """
    try:
        intent = yaml.safe_load(intent_file.read_text())

        errors = []

        # Basic schema validation
        if 'schema_version' not in intent:
            errors.append("Missing required field: schema_version")

        if 'intent' not in intent:
            errors.append("Missing required field: intent")
        else:
            intent_section = intent['intent']
            if 'workflow_name' not in intent_section:
                errors.append("Missing required field: intent.workflow_name")
            if 'workload_type' not in intent_section:
                errors.append("Missing required field: intent.workload_type")

        return (len(errors) == 0, errors)

    except yaml.YAMLError as e:
        return (False, [f"YAML parse error: {e}"])


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
