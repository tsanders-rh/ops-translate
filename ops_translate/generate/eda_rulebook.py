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


def generate_eda_rulebook(workspace: Workspace, policy_file: Path, output_file: Path | None = None):
    """
    Generate Event-Driven Ansible rulebook from vRO event subscription policy.

    Args:
        workspace: Workspace instance
        policy_file: Path to vRO policy XML file
        output_file: Optional path to output rulebook (defaults to output/eda/rulebook.yml)
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
    rulebook = _generate_rulebook(subscriptions, event_mappings)

    # Write output
    if output_file is None:
        output_file = workspace.root / "output/eda/rulebook.yml"

    ensure_dir(output_file.parent)
    write_text(output_file, yaml.dump(rulebook, default_flow_style=False, sort_keys=False))

    console.print(
        f"[green]✓ Generated EDA rulebook: {output_file.relative_to(workspace.root)}[/green]"
    )


def _generate_rulebook(
    subscriptions: list[EventSubscription], event_mappings: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Generate EDA rulebook structure from subscriptions and mappings.

    Args:
        subscriptions: List of parsed event subscriptions
        event_mappings: Event mapping configuration

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
        rule = _generate_rule(sub, event_mappings)
        if rule:
            rules.append(rule)

    return rulebook


def _generate_rule(sub: EventSubscription, event_mappings: dict[str, Any]) -> dict[str, Any] | None:
    """
    Generate a single EDA rule from an event subscription.

    Args:
        sub: Event subscription
        event_mappings: Event mapping configuration

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
    action = _build_action(sub, event_info)

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


def _build_action(sub: EventSubscription, event_info: dict[str, Any]) -> dict[str, Any]:
    """
    Build EDA action from event subscription.

    Args:
        sub: Event subscription
        event_info: Event mapping info

    Returns:
        Action dict
    """
    # Build variable mappings from bindings
    set_facts = {}
    for binding in sub.bindings:
        # Convert event paths to EDA payload paths
        fact_value = _convert_event_path(binding.value)
        set_facts[binding.name] = fact_value

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
