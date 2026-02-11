"""
vRealize Orchestrator event subscription parser.
Parses policy/event subscription XML exports to extract reactive automation patterns.
"""

from dataclasses import dataclass, field
from pathlib import Path

from defusedxml import ElementTree  # type: ignore[import-untyped]


@dataclass
class EventBinding:
    """Represents a parameter binding from event to workflow."""

    name: str
    value: str  # Event property path (e.g., "event.vm.name")


@dataclass
class EventCondition:
    """Represents a JavaScript condition for event filtering."""

    script: str


@dataclass
class EventSubscription:
    """Represents a vRO event subscription/policy."""

    id: str
    name: str
    description: str
    event_type: str  # e.g., "VmPoweredOnEvent"
    workflow_id: str
    workflow_name: str
    conditions: list[EventCondition] = field(default_factory=list)
    bindings: list[EventBinding] = field(default_factory=list)


def parse_event_subscriptions(policy_file: Path) -> list[EventSubscription]:
    """
    Parse vRO policy/event subscription XML files.

    Args:
        policy_file: Path to vRO policy XML file

    Returns:
        List of event subscription definitions
    """
    try:
        tree = ElementTree.parse(policy_file)
        root = tree.getroot()
    except ElementTree.ParseError as e:
        raise ValueError(f"Unable to parse policy XML: {e}") from e

    if root is None:
        raise ValueError("Empty XML document")

    subscriptions = []

    # Find all event-subscription elements (iterate to handle namespaces)
    for elem in root.iter():
        # Check if tag ends with 'event-subscription' to handle namespaces
        if elem.tag.endswith("event-subscription"):
            subscription = _parse_subscription(elem)
            if subscription:
                subscriptions.append(subscription)

    return subscriptions


def _parse_subscription(sub_elem) -> EventSubscription | None:
    """Parse a single event-subscription element."""

    # Helper function to find child element by tag suffix (namespace-aware)
    def find_child(parent, tag_suffix):
        for child in parent:
            if child.tag.endswith(tag_suffix):
                return child.text
        return None

    # Extract basic fields
    sub_id = find_child(sub_elem, "id")
    name = find_child(sub_elem, "name")
    description = find_child(sub_elem, "description") or ""
    event_type = find_child(sub_elem, "event-type")
    workflow_id = find_child(sub_elem, "workflow-id")
    workflow_name = find_child(sub_elem, "workflow-name")

    if not all([sub_id, name, event_type, workflow_id]):
        # Skip incomplete subscriptions
        return None

    # Parse conditions
    conditions = []
    for elem in sub_elem.iter():
        if elem.tag.endswith("condition"):
            # Find script element
            for child in elem:
                if child.tag.endswith("script") and child.text:
                    script = child.text.strip()
                    conditions.append(EventCondition(script=script))

    # Parse bindings
    bindings = []
    for elem in sub_elem.iter():
        if elem.tag.endswith("binding"):
            bind_name = find_child(elem, "name")
            bind_value = find_child(elem, "value")

            if bind_name and bind_value:
                bindings.append(EventBinding(name=bind_name, value=bind_value))

    return EventSubscription(
        id=sub_id,
        name=name,
        description=description,
        event_type=event_type,
        workflow_id=workflow_id,
        workflow_name=workflow_name or workflow_id,
        conditions=conditions,
        bindings=bindings,
    )


def summarize_event_subscriptions(subscriptions: list[EventSubscription]) -> str:
    """
    Generate a markdown summary of event subscriptions.

    Args:
        subscriptions: List of parsed event subscriptions

    Returns:
        Markdown-formatted summary
    """
    if not subscriptions:
        return "No event subscriptions found"

    summary = ["**Event Subscriptions:**\n"]

    for sub in subscriptions:
        summary.append(f"- **{sub.name}** ({sub.event_type})")
        summary.append(f"  - Workflow: `{sub.workflow_name}`")

        if sub.conditions:
            summary.append(f"  - Conditions: {len(sub.conditions)} filter(s)")

        if sub.bindings:
            summary.append(f"  - Bindings: {len(sub.bindings)} parameter(s)")

        summary.append("")

    return "\n".join(summary)
