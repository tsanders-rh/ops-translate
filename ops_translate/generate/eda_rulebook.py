"""
Event-Driven Ansible rulebook generator from vRO event subscriptions.
"""

import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from rich.console import Console

from ops_translate.summarize.vrealize_events import (
    EventSubscription,
    parse_event_subscriptions,
)
from ops_translate.util.files import ensure_dir, write_text
from ops_translate.workspace import Workspace

console = Console()
logger = logging.getLogger(__name__)

# Get project root to find mappings
PROJECT_ROOT = Path(__file__).parent.parent.parent


def generate_eda_rulebook(
    workspace: Workspace,
    policy_file: Path,
    output_file: Path | None = None,
    use_job_templates: bool = False,
):
    """
    Generate Event-Driven Ansible rulebook from vRO event subscription policy.

    Args:
        workspace: Workspace instance
        policy_file: Path to vRO policy XML file
        output_file: Optional path to output rulebook (defaults to output/eda/rulebook.yml)
        use_job_templates: If True, use run_job_template (AAP). If False, use run_playbook.
    """
    # Parse event subscriptions
    try:
        subscriptions = parse_event_subscriptions(policy_file)
    except ValueError as e:
        console.print(f"[red]Error parsing policy file: {e}[/red]")
        return

    if not subscriptions:
        console.print("[yellow]No event subscriptions found in policy file[/yellow]")
        return

    # Load event mappings
    mappings_file = PROJECT_ROOT / "ops_translate/generate/vcenter_event_mappings.yaml"
    try:
        with open(mappings_file) as f:
            event_mappings = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]Error loading event mappings: {e}[/red]")
        return

    # Generate rulebook structure
    rulebook = _generate_rulebook(subscriptions, event_mappings, use_job_templates)

    # Write output
    if output_file is None:
        output_file = workspace.root / "output/eda/rulebook.yml"

    ensure_dir(output_file.parent)
    write_text(output_file, yaml.dump(rulebook, default_flow_style=False, sort_keys=False))

    console.print(
        f"[green]✓ Generated EDA rulebook: {output_file.relative_to(workspace.root)}[/green]"
    )


def generate_eda_artifacts(
    workspace: Workspace,
    policy_files: list[Path],
    use_job_templates: bool = True,
    categorize: bool = True,
):
    """
    Generate complete EDA artifacts including rulebooks, requirements, and deployment files.

    Args:
        workspace: Workspace instance
        policy_files: List of vRO policy XML files
        use_job_templates: If True, use AAP job templates. If False, use playbooks.
        categorize: If True, split into multiple rulebooks by category
    """
    # Parse all subscriptions
    all_subscriptions = []
    for policy_file in policy_files:
        try:
            subscriptions = parse_event_subscriptions(policy_file)
            all_subscriptions.extend(subscriptions)
        except ValueError as e:
            console.print(f"[yellow]Warning: Could not parse {policy_file}: {e}[/yellow]")

    if not all_subscriptions:
        console.print("[yellow]No event subscriptions found in any policy files[/yellow]")
        return

    # Load event mappings
    mappings_file = PROJECT_ROOT / "ops_translate/generate/vcenter_event_mappings.yaml"
    with open(mappings_file) as f:
        event_mappings = yaml.safe_load(f)

    output_dir = workspace.root / "output/eda"
    ensure_dir(output_dir)
    ensure_dir(output_dir / "rulebooks")
    ensure_dir(output_dir / "deployment")

    # Generate rulebooks (categorized or single)
    if categorize:
        categorized = _categorize_subscriptions(all_subscriptions, event_mappings)
        for category, subs in categorized.items():
            rulebook = _generate_rulebook(subs, event_mappings, use_job_templates)
            output_file = output_dir / "rulebooks" / f"{category}.yml"
            write_text(output_file, yaml.dump(rulebook, default_flow_style=False, sort_keys=False))
            console.print(f"[green]✓ Generated: {output_file.relative_to(workspace.root)}[/green]")
    else:
        rulebook = _generate_rulebook(all_subscriptions, event_mappings, use_job_templates)
        output_file = output_dir / "rulebooks" / "all_events.yml"
        write_text(output_file, yaml.dump(rulebook, default_flow_style=False, sort_keys=False))
        console.print(f"[green]✓ Generated: {output_file.relative_to(workspace.root)}[/green]")

    # Generate requirements.yml
    _generate_requirements(output_dir)
    req_file = (output_dir / "requirements.yml").relative_to(workspace.root)
    console.print(f"[green]✓ Generated: {req_file}[/green]")

    # Generate deployment files
    _generate_deployment_files(output_dir, use_job_templates)
    deploy_file = (output_dir / "deployment/deployment.yml").relative_to(workspace.root)
    inv_file = (output_dir / "deployment/inventory.yml").relative_to(workspace.root)
    console.print(f"[green]✓ Generated: {deploy_file}[/green]")
    console.print(f"[green]✓ Generated: {inv_file}[/green]")


def _generate_rulebook(
    subscriptions: list[EventSubscription],
    event_mappings: dict[str, Any],
    use_job_templates: bool = False,
) -> list[dict[str, Any]]:
    """
    Generate EDA rulebook structure from subscriptions and mappings.

    Args:
        subscriptions: List of parsed event subscriptions
        event_mappings: Event mapping configuration
        use_job_templates: If True, use AAP job templates. If False, use playbooks.

    Returns:
        List of rulebook entries (one per rulebook name)
    """
    # Get event source configuration
    webhook_config = event_mappings.get("event_sources", {}).get("webhook", {})
    source_type = webhook_config.get("type", "ansible.eda.webhook")
    source_config = webhook_config.get("default_config", {})

    # Build rulebook with explicit type annotation
    rules: list[dict[str, Any]] = []
    rulebook: list[dict[str, Any]] = [
        {
            "name": "vCenter Event-Driven Automation",
            "hosts": "localhost",
            "sources": [
                {
                    source_type: source_config,
                }
            ],
            "rules": rules,
        }
    ]

    # Generate rules from subscriptions
    for sub in subscriptions:
        rule = _generate_rule(sub, event_mappings, use_job_templates)
        if rule:
            rules.append(rule)

    return rulebook


def _generate_rule(
    sub: EventSubscription, event_mappings: dict[str, Any], use_job_templates: bool = False
) -> dict[str, Any] | None:
    """
    Generate a single EDA rule from an event subscription.

    Args:
        sub: Event subscription
        event_mappings: Event mapping configuration
        use_job_templates: If True, use AAP job templates. If False, use playbooks.

    Returns:
        Rule dict or None if event type not mapped
    """
    # Find event mapping
    event_info = _find_event_mapping(sub.event_type, event_mappings)

    if not event_info:
        logger.warning(f"No mapping found for event type: {sub.event_type}")
        return None

    eda_event_type = event_info.get("eda_event_type", sub.event_type.lower())

    # Build condition
    conditions = _build_eda_conditions(sub, eda_event_type)

    # Build action
    action = _build_action(sub, event_info, use_job_templates)

    rule = {
        "name": sub.name,
        "condition": conditions,
        "action": action,
    }

    return rule


def _find_event_mapping(event_type: str, event_mappings: dict[str, Any]) -> dict[str, Any] | None:
    """Find event mapping for a given event type."""
    # Search through all categories
    for category, events in event_mappings.items():
        if category == "event_sources":
            continue
        if isinstance(events, dict) and event_type in events:
            mapping: dict[str, Any] = events[event_type]
            return mapping
    return None


def _build_eda_conditions(sub: EventSubscription, eda_event_type: str) -> str:
    """
    Build EDA condition from event subscription.

    Args:
        sub: Event subscription
        eda_event_type: EDA event type name

    Returns:
        EDA condition expression
    """
    # Start with event type match
    conditions = [f'event.type == "{eda_event_type}"']

    # Add JavaScript conditions (translated to Python/Jinja2)
    for condition in sub.conditions:
        translated = _translate_js_condition(condition.script)
        if translated:
            conditions.append(translated)

    # Combine with AND
    if len(conditions) == 1:
        return conditions[0]
    else:
        return " and ".join(f"({c})" for c in conditions)


def _translate_js_condition(js_script: str) -> str | None:
    """
    Translate JavaScript condition to EDA/Jinja2 condition.

    This is a basic translation - more complex logic should use a dedicated translator.

    Args:
        js_script: JavaScript condition script

    Returns:
        Translated condition or None if cannot translate
    """
    # Remove comments and whitespace
    script = "\n".join(line for line in js_script.split("\n") if not line.strip().startswith("//"))
    script = script.strip()

    # Simple translations (use placeholders to avoid conflicts)
    # First pass: replace operators that contain other operators
    script = script.replace("!=", "__NE__")  # Placeholder for !=
    script = script.replace("==", "__EQ__")  # Placeholder for ==
    script = script.replace("&&", "__AND__")  # Placeholder for &&
    script = script.replace("||", "__OR__")  # Placeholder for ||

    # Second pass: replace simple operators
    script = script.replace("!", "not ")

    # Third pass: restore placeholders
    script = script.replace("__NE__", "!=")
    script = script.replace("__EQ__", "==")
    script = script.replace("__AND__", " and ")
    script = script.replace("__OR__", " or ")

    # Replace boolean literals
    script = script.replace("true", "True")
    script = script.replace("false", "False")

    # Convert event.vm.name to event.payload.vm_name (basic dot notation)
    # This is simplified - a full translator would handle more cases
    script = script.replace("event.vm.name", "event.payload.vm_name")
    script = script.replace("event.vm.id", "event.payload.vm_id")
    script = script.replace("event.vm.config.template", "event.payload.template")
    script = script.replace("event.vm.config.hardware.numCPU", "event.payload.cpu_count")
    script = script.replace("event.vm.runtime.host.parent.name", "event.payload.cluster")
    script = script.replace("event.alarm.name", "event.payload.alarm_name")
    script = script.replace("event.entity.name", "event.payload.entity_name")
    script = script.replace("event.to", "event.payload.to_status")
    script = script.replace("event.from", "event.payload.from_status")

    # Handle string literals with .startsWith(), .contains(), etc.
    # For now, return the translated script as-is
    # A more sophisticated translator would parse the AST

    if not script or script == "True":
        return None  # Skip trivial conditions

    return script


def _build_action(
    sub: EventSubscription, event_info: dict[str, Any], use_job_templates: bool = False
) -> dict[str, Any]:
    """
    Build EDA action from event subscription.

    Args:
        sub: Event subscription
        event_info: Event mapping info
        use_job_templates: If True, use AAP job templates. If False, use playbooks.

    Returns:
        Action dict
    """
    # Build variable mappings from bindings
    set_facts = {}
    for binding in sub.bindings:
        # Convert event paths to EDA payload paths
        fact_value = _convert_event_path(binding.value)
        set_facts[binding.name] = fact_value

    if use_job_templates:
        # AAP Job Template mode
        action = {
            "run_job_template": {
                "name": sub.workflow_name,
                "organization": "Default",
                "job_args": {"extra_vars": set_facts},
            }
        }
    else:
        # Playbook mode
        action = {
            "run_playbook": {
                "name": f"playbooks/{sub.workflow_id}.yml",
                "extra_vars": set_facts,
            }
        }

    return action


def _convert_event_path(event_path: str) -> str:
    """
    Convert vCenter event path to EDA event payload path.

    Args:
        event_path: vCenter event path (e.g., "event.vm.name")

    Returns:
        EDA payload path (e.g., "{{ event.payload.vm_name }}")
    """
    # Simple path conversions
    conversions = {
        "event.vm.name": "{{ event.payload.vm_name }}",
        "event.vm.id": "{{ event.payload.vm_id }}",
        "event.vm.uuid": "{{ event.payload.vm_uuid }}",
        "event.vm.cluster": "{{ event.payload.cluster }}",
        "event.host.name": "{{ event.payload.host }}",
        "event.datacenter.name": "{{ event.payload.datacenter }}",
        "event.createdTime": "{{ event.payload.created_time }}",
        "event.template.name": "{{ event.payload.template }}",
        "event.vm.folder": "{{ event.payload.folder }}",
        "event.alarm.name": "{{ event.payload.alarm_name }}",
        "event.entity.name": "{{ event.payload.entity_name }}",
        "event.to": "{{ event.payload.to_status }}",
        "event.from": "{{ event.payload.from_status }}",
        "event.vm.runtime.host.parent.name": "{{ event.payload.cluster }}",
    }

    return conversions.get(event_path, f"{{{{ event.payload.{event_path} }}}}")


def _categorize_subscriptions(
    subscriptions: list[EventSubscription], event_mappings: dict[str, Any]
) -> dict[str, list[EventSubscription]]:
    """
    Categorize subscriptions by event type for separate rulebooks.

    Args:
        subscriptions: List of all subscriptions
        event_mappings: Event mapping configuration

    Returns:
        Dict mapping category names to subscription lists
    """
    categories: dict[str, list[EventSubscription]] = {
        "vm_lifecycle": [],
        "network_events": [],
        "storage_events": [],
        "alarm_events": [],
    }

    for sub in subscriptions:
        # Find category from event mappings
        for category, events in event_mappings.items():
            if category == "event_sources":
                continue
            if isinstance(events, dict) and sub.event_type in events:
                # Map categories
                if category in ["vm_lifecycle", "vm_configuration"]:
                    categories["vm_lifecycle"].append(sub)
                elif category in ["network", "datastore"]:
                    categories["network_events"].append(sub)
                elif category == "alarms":
                    categories["alarm_events"].append(sub)
                elif category in ["host_lifecycle", "resource_pool"]:
                    categories["storage_events"].append(sub)
                break

    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def _generate_requirements(output_dir: Path):
    """Generate requirements.yml for EDA collections."""
    requirements = {
        "collections": [
            {"name": "ansible.eda", "version": ">=1.4.0"},
            {"name": "ansible.controller", "version": ">=4.5.0"},
        ]
    }

    requirements_file = output_dir / "requirements.yml"
    write_text(
        requirements_file, yaml.dump(requirements, default_flow_style=False, sort_keys=False)
    )


def _generate_deployment_files(output_dir: Path, use_job_templates: bool):
    """Generate deployment playbook and inventory."""
    # Generate deployment playbook
    deployment_playbook = [
        {
            "name": "Deploy EDA Rulebooks to Controller",
            "hosts": "eda_controller",
            "gather_facts": False,
            "tasks": [
                {
                    "name": "Ensure EDA collections are installed",
                    "ansible.builtin.command": (
                        "ansible-galaxy collection install -r requirements.yml"
                    ),
                    "args": {"chdir": "{{ playbook_dir }}/.."},
                    "delegate_to": "localhost",
                    "run_once": True,
                },
                {
                    "name": "Copy rulebooks to EDA controller",
                    "ansible.builtin.copy": {
                        "src": "{{ playbook_dir }}/../rulebooks/",
                        "dest": "/var/lib/awx/projects/eda-rulebooks/",
                        "mode": "0644",
                    },
                },
                {
                    "name": "Restart EDA services",
                    "ansible.builtin.systemd": {
                        "name": "ansible-rulebook",
                        "state": "restarted",
                    },
                    "when": "restart_eda_services | default(false)",
                },
            ],
        }
    ]

    deployment_file = output_dir / "deployment" / "deployment.yml"
    write_text(
        deployment_file, yaml.dump(deployment_playbook, default_flow_style=False, sort_keys=False)
    )

    # Generate inventory
    inventory = {
        "all": {
            "children": {
                "eda_controller": {
                    "hosts": {
                        "eda-controller.example.com": {
                            "ansible_host": "{{ eda_controller_host }}",
                            "ansible_user": "{{ eda_controller_user | default('root') }}",
                            "ansible_connection": "ssh",
                        }
                    }
                }
            }
        }
    }

    inventory_file = output_dir / "deployment" / "inventory.yml"
    write_text(inventory_file, yaml.dump(inventory, default_flow_style=False, sort_keys=False))
