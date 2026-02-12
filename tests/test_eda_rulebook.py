"""Tests for EDA rulebook generator."""

from pathlib import Path

import pytest
import yaml

from ops_translate.generate.eda_rulebook import (
    _build_action,
    _build_eda_conditions,
    _convert_event_path,
    _find_event_mapping,
    _generate_rule,
    _generate_rulebook,
    _translate_js_condition,
    generate_eda_rulebook,
)
from ops_translate.summarize.vrealize_events import (
    EventBinding,
    EventCondition,
    EventSubscription,
    parse_event_subscriptions,
)
from ops_translate.workspace import Workspace


@pytest.fixture
def example_policy_file():
    """Path to example policy XML."""
    return Path(__file__).parent.parent / "examples/vrealize/vm-lifecycle-policy.xml"


@pytest.fixture
def event_mappings():
    """Load event mappings."""
    mappings_file = (
        Path(__file__).parent.parent / "ops_translate/generate/vcenter_event_mappings.yaml"
    )
    with open(mappings_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def sample_subscription():
    """Create a sample event subscription."""
    return EventSubscription(
        id="sub1",
        name="VM Powered On - Compliance Check",
        description="Run compliance check when VM is powered on",
        event_type="VmPoweredOnEvent",
        workflow_id="compliance-check-workflow",
        workflow_name="VM Compliance Check",
        conditions=[
            EventCondition(
                script=(
                    'event.vm.runtime.host.parent.name == "Production-Cluster" '
                    "&& event.vm.config.hardware.numCPU > 4"
                )
            )
        ],
        bindings=[
            EventBinding(name="vmName", value="event.vm.name"),
            EventBinding(name="vmId", value="event.vm.id"),
        ],
    )


def test_find_event_mapping(event_mappings):
    """Test finding event mapping by type."""
    # VM lifecycle event
    mapping = _find_event_mapping("VmPoweredOnEvent", event_mappings)
    assert mapping is not None
    assert mapping["eda_event_type"] == "vm_powered_on"

    # Alarm event
    mapping = _find_event_mapping("AlarmStatusChangedEvent", event_mappings)
    assert mapping is not None
    assert mapping["eda_event_type"] == "alarm_status_changed"

    # Unknown event
    mapping = _find_event_mapping("UnknownEvent", event_mappings)
    assert mapping is None


def test_convert_event_path():
    """Test converting vCenter event paths to EDA payload paths."""
    assert _convert_event_path("event.vm.name") == "{{ event.payload.vm_name }}"
    assert _convert_event_path("event.vm.id") == "{{ event.payload.vm_id }}"
    assert _convert_event_path("event.alarm.name") == "{{ event.payload.alarm_name }}"
    assert _convert_event_path("event.createdTime") == "{{ event.payload.created_time }}"


def test_translate_simple_js_condition():
    """Test translating simple JavaScript conditions."""
    # Boolean operators
    result = _translate_js_condition("true")
    assert result is None  # Trivial condition

    result = _translate_js_condition('event.vm.name == "test"')
    assert result == 'event.payload.vm_name == "test"'

    # Logical operators
    result = _translate_js_condition("event.vm.id != 123 && event.to == 'red'")
    assert "and" in result
    assert "event.payload.vm_id" in result


def test_translate_js_condition_with_comments():
    """Test translating JS with comments."""
    script = """// Only production VMs
event.vm.runtime.host.parent.name == "Production-Cluster" &&
event.vm.config.hardware.numCPU > 4"""

    result = _translate_js_condition(script)
    assert result is not None
    assert "Production-Cluster" in result
    assert "and" in result


def test_build_action(sample_subscription):
    """Test building EDA action from subscription."""
    action = _build_action(sample_subscription, {})

    assert "run_playbook" in action
    assert action["run_playbook"]["name"] == "playbooks/compliance-check-workflow.yml"
    assert "extra_vars" in action["run_playbook"]

    extra_vars = action["run_playbook"]["extra_vars"]
    assert "vmName" in extra_vars
    assert extra_vars["vmName"] == "{{ event.payload.vm_name }}"


def test_build_eda_conditions_simple(sample_subscription):
    """Test building EDA conditions."""
    conditions = _build_eda_conditions(sample_subscription, "vm_powered_on")

    assert 'event.type == "vm_powered_on"' in conditions
    assert "and" in conditions  # Multiple conditions combined
    assert "event.payload.cluster" in conditions


def test_build_eda_conditions_no_filters():
    """Test building conditions with no filters (only event type)."""
    sub = EventSubscription(
        id="sub1",
        name="Test",
        description="",
        event_type="VmPoweredOffEvent",
        workflow_id="wf1",
        workflow_name="Workflow",
        conditions=[],
        bindings=[],
    )

    conditions = _build_eda_conditions(sub, "vm_powered_off")
    assert conditions == 'event.type == "vm_powered_off"'


def test_generate_rule(sample_subscription, event_mappings):
    """Test generating a complete rule."""
    rule = _generate_rule(sample_subscription, event_mappings)

    assert rule is not None
    assert rule["name"] == "VM Powered On - Compliance Check"
    assert "condition" in rule
    assert "action" in rule
    assert "run_playbook" in rule["action"]


def test_generate_rule_unknown_event(event_mappings):
    """Test generating rule for unknown event type."""
    sub = EventSubscription(
        id="sub1",
        name="Unknown Event",
        description="",
        event_type="UnknownEventType",
        workflow_id="wf1",
        workflow_name="Workflow",
    )

    rule = _generate_rule(sub, event_mappings)
    assert rule is None  # Should skip unknown events


def test_generate_rulebook(example_policy_file, event_mappings):
    """Test generating complete rulebook structure."""
    subscriptions = parse_event_subscriptions(example_policy_file)
    rulebook = _generate_rulebook(subscriptions, event_mappings)

    assert len(rulebook) == 1
    assert rulebook[0]["name"] == "vCenter Event-Driven Automation"
    assert "sources" in rulebook[0]
    assert "rules" in rulebook[0]

    # Should have 4 rules from example policy
    assert len(rulebook[0]["rules"]) == 4


def test_rulebook_sources(example_policy_file, event_mappings):
    """Test rulebook event sources are configured."""
    subscriptions = parse_event_subscriptions(example_policy_file)
    rulebook = _generate_rulebook(subscriptions, event_mappings)

    sources = rulebook[0]["sources"]
    assert len(sources) == 1
    assert "ansible.eda.webhook" in sources[0]

    webhook_config = sources[0]["ansible.eda.webhook"]
    assert "host" in webhook_config
    assert "port" in webhook_config


def test_rulebook_rules_have_required_fields(example_policy_file, event_mappings):
    """Test all generated rules have required fields."""
    subscriptions = parse_event_subscriptions(example_policy_file)
    rulebook = _generate_rulebook(subscriptions, event_mappings)

    for rule in rulebook[0]["rules"]:
        assert "name" in rule
        assert "condition" in rule
        assert "action" in rule
        assert "run_playbook" in rule["action"]


def test_full_integration(tmp_path, example_policy_file):
    """Test full EDA generation workflow."""
    workspace = Workspace(tmp_path)

    # Generate rulebook
    output_file = tmp_path / "output/eda/rulebook.yml"
    generate_eda_rulebook(workspace, example_policy_file, output_file)

    # Verify output file exists
    assert output_file.exists()

    # Load and verify structure
    with open(output_file) as f:
        rulebook = yaml.safe_load(f)

    assert isinstance(rulebook, list)
    assert len(rulebook) == 1
    assert rulebook[0]["name"] == "vCenter Event-Driven Automation"
    assert len(rulebook[0]["rules"]) == 4


def test_vm_powered_on_rule_details(example_policy_file, event_mappings):
    """Test specific details of VM powered on rule."""
    subscriptions = parse_event_subscriptions(example_policy_file)
    rulebook = _generate_rulebook(subscriptions, event_mappings)

    # Find the powered on rule
    powered_on_rule = next(
        (r for r in rulebook[0]["rules"] if "Compliance Check" in r["name"]), None
    )

    assert powered_on_rule is not None
    assert "vm_powered_on" in powered_on_rule["condition"]

    # Check playbook action
    action = powered_on_rule["action"]["run_playbook"]
    assert action["name"] == "playbooks/compliance-check-workflow.yml"

    # Check extra vars from bindings
    extra_vars = action["extra_vars"]
    assert "vmName" in extra_vars
    assert "vmId" in extra_vars
    assert "cluster" in extra_vars
    assert "poweredOnTime" in extra_vars


def test_alarm_status_changed_rule_details(example_policy_file, event_mappings):
    """Test alarm status changed rule details."""
    subscriptions = parse_event_subscriptions(example_policy_file)
    rulebook = _generate_rulebook(subscriptions, event_mappings)

    # Find the alarm rule
    alarm_rule = next((r for r in rulebook[0]["rules"] if "Critical Alarm" in r["name"]), None)

    assert alarm_rule is not None
    assert "alarm_status_changed" in alarm_rule["condition"]

    # Check that condition includes the red status check
    assert "red" in alarm_rule["condition"]

    # Check action
    action = alarm_rule["action"]["run_playbook"]
    assert "create-incident-from-alarm" in action["name"]


def test_error_handling_invalid_policy(tmp_path):
    """Test handling of invalid policy file."""
    workspace = Workspace(tmp_path)
    invalid_file = tmp_path / "invalid.xml"
    invalid_file.write_text("not valid xml")

    # Should handle error gracefully (no exception)
    generate_eda_rulebook(workspace, invalid_file)


def test_error_handling_empty_policy(tmp_path):
    """Test handling of policy with no subscriptions."""
    workspace = Workspace(tmp_path)
    empty_file = tmp_path / "empty.xml"
    empty_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<dunes-policy xmlns="http://vmware.com/vco/policy">
  <id>empty</id>
  <name>Empty Policy</name>
</dunes-policy>""")

    output_file = tmp_path / "output/eda/rulebook.yml"
    generate_eda_rulebook(workspace, empty_file, output_file)

    # Should not create output file for empty policy
    assert not output_file.exists()
