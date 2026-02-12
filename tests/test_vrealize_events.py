"""Tests for vRealize event subscription parser."""

from pathlib import Path

import pytest

from ops_translate.summarize.vrealize_events import (
    EventBinding,
    EventCondition,
    EventSubscription,
    parse_event_subscriptions,
    summarize_event_subscriptions,
)


@pytest.fixture
def example_policy_file():
    """Path to example policy XML."""
    return Path(__file__).parent.parent / "examples/vrealize/vm-lifecycle-policy.xml"


def test_parse_event_subscriptions(example_policy_file):
    """Test parsing event subscriptions from policy XML."""
    subscriptions = parse_event_subscriptions(example_policy_file)

    assert len(subscriptions) == 4
    assert all(isinstance(sub, EventSubscription) for sub in subscriptions)


def test_vm_powered_on_subscription(example_policy_file):
    """Test parsing VmPoweredOnEvent subscription."""
    subscriptions = parse_event_subscriptions(example_policy_file)

    # Find the VM powered on subscription
    powered_on_sub = next(
        (sub for sub in subscriptions if sub.event_type == "VmPoweredOnEvent"), None
    )

    assert powered_on_sub is not None
    assert powered_on_sub.name == "VM Powered On - Compliance Check"
    assert powered_on_sub.workflow_id == "compliance-check-workflow"
    assert powered_on_sub.workflow_name == "VM Compliance Check"
    assert "production vm" in powered_on_sub.description.lower()

    # Check conditions
    assert len(powered_on_sub.conditions) == 1
    condition = powered_on_sub.conditions[0]
    assert "Production-Cluster" in condition.script
    assert "numCPU" in condition.script

    # Check bindings
    assert len(powered_on_sub.bindings) == 4
    binding_names = {b.name for b in powered_on_sub.bindings}
    assert binding_names == {"vmName", "vmId", "cluster", "poweredOnTime"}

    # Verify specific binding
    vm_name_binding = next((b for b in powered_on_sub.bindings if b.name == "vmName"), None)
    assert vm_name_binding is not None
    assert vm_name_binding.value == "event.vm.name"


def test_vm_powered_off_subscription(example_policy_file):
    """Test parsing VmPoweredOffEvent subscription."""
    subscriptions = parse_event_subscriptions(example_policy_file)

    powered_off_sub = next(
        (sub for sub in subscriptions if sub.event_type == "VmPoweredOffEvent"), None
    )

    assert powered_off_sub is not None
    assert powered_off_sub.name == "VM Powered Off - Cleanup"
    assert powered_off_sub.workflow_id == "vm-cleanup-workflow"

    # Should have unconditional trigger (true condition)
    assert len(powered_off_sub.conditions) == 1
    assert "true" in powered_off_sub.conditions[0].script.lower()

    # Should have basic bindings
    assert len(powered_off_sub.bindings) == 2


def test_vm_created_subscription(example_policy_file):
    """Test parsing VmCreatedEvent subscription."""
    subscriptions = parse_event_subscriptions(example_policy_file)

    created_sub = next((sub for sub in subscriptions if sub.event_type == "VmCreatedEvent"), None)

    assert created_sub is not None
    assert "CMDB" in created_sub.name
    assert created_sub.workflow_id == "cmdb-register-vm"

    # Check template exclusion condition
    assert len(created_sub.conditions) == 1
    assert "template" in created_sub.conditions[0].script.lower()

    # Should have template in bindings
    template_binding = next((b for b in created_sub.bindings if b.name == "template"), None)
    assert template_binding is not None


def test_alarm_status_changed_subscription(example_policy_file):
    """Test parsing AlarmStatusChangedEvent subscription."""
    subscriptions = parse_event_subscriptions(example_policy_file)

    alarm_sub = next(
        (sub for sub in subscriptions if sub.event_type == "AlarmStatusChangedEvent"), None
    )

    assert alarm_sub is not None
    assert "Critical" in alarm_sub.name
    assert "Incident" in alarm_sub.name

    # Check critical alarm condition
    assert len(alarm_sub.conditions) == 1
    condition = alarm_sub.conditions[0]
    assert "red" in condition.script
    assert "Test Alarm" in condition.script  # Excludes test alarms

    # Check alarm-specific bindings
    binding_names = {b.name for b in alarm_sub.bindings}
    assert "alarmName" in binding_names
    assert "entityName" in binding_names
    assert "alarmStatus" in binding_names


def test_condition_dataclass():
    """Test EventCondition dataclass."""
    condition = EventCondition(script='event.vm.name == "prod-vm"')

    assert condition.script == 'event.vm.name == "prod-vm"'


def test_binding_dataclass():
    """Test EventBinding dataclass."""
    binding = EventBinding(name="vmName", value="event.vm.name")

    assert binding.name == "vmName"
    assert binding.value == "event.vm.name"


def test_subscription_dataclass():
    """Test EventSubscription dataclass with defaults."""
    subscription = EventSubscription(
        id="sub1",
        name="Test Subscription",
        description="Test description",
        event_type="VmPoweredOnEvent",
        workflow_id="test-workflow",
        workflow_name="Test Workflow",
    )

    assert subscription.id == "sub1"
    assert subscription.conditions == []
    assert subscription.bindings == []


def test_subscription_with_conditions_and_bindings():
    """Test EventSubscription with conditions and bindings."""
    condition = EventCondition(script="true")
    binding = EventBinding(name="vmName", value="event.vm.name")

    subscription = EventSubscription(
        id="sub1",
        name="Test",
        description="",
        event_type="VmPoweredOnEvent",
        workflow_id="wf1",
        workflow_name="Workflow",
        conditions=[condition],
        bindings=[binding],
    )

    assert len(subscription.conditions) == 1
    assert len(subscription.bindings) == 1


def test_summarize_event_subscriptions(example_policy_file):
    """Test summarize function produces markdown output."""
    subscriptions = parse_event_subscriptions(example_policy_file)
    summary = summarize_event_subscriptions(subscriptions)

    assert "**Event Subscriptions:**" in summary
    assert "VmPoweredOnEvent" in summary
    assert "VmPoweredOffEvent" in summary
    assert "VmCreatedEvent" in summary
    assert "AlarmStatusChangedEvent" in summary
    assert "Workflow:" in summary
    assert "Conditions:" in summary
    assert "Bindings:" in summary


def test_summarize_empty_subscriptions():
    """Test summarize with no subscriptions."""
    summary = summarize_event_subscriptions([])
    assert summary == "No event subscriptions found"


def test_parse_invalid_xml(tmp_path):
    """Test parsing invalid XML raises error."""
    invalid_file = tmp_path / "invalid.xml"
    invalid_file.write_text("not valid xml <<>>")

    with pytest.raises(ValueError, match="Unable to parse"):
        parse_event_subscriptions(invalid_file)


def test_parse_empty_xml(tmp_path):
    """Test parsing empty XML raises error."""
    empty_file = tmp_path / "empty.xml"
    empty_file.write_text("")

    with pytest.raises(ValueError):
        parse_event_subscriptions(empty_file)


def test_parse_xml_with_no_subscriptions(tmp_path):
    """Test parsing XML with no event subscriptions."""
    no_subs_file = tmp_path / "no-subs.xml"
    no_subs_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<dunes-policy xmlns="http://vmware.com/vco/policy">
  <id>test-policy</id>
  <name>Empty Policy</name>
</dunes-policy>""")

    subscriptions = parse_event_subscriptions(no_subs_file)
    assert subscriptions == []


def test_parse_incomplete_subscription(tmp_path):
    """Test parsing subscription with missing required fields."""
    incomplete_file = tmp_path / "incomplete.xml"
    incomplete_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<dunes-policy xmlns="http://vmware.com/vco/policy">
  <event-subscription>
    <id>sub1</id>
    <name>Incomplete Subscription</name>
    <!-- Missing event-type and workflow-id -->
  </event-subscription>
</dunes-policy>""")

    subscriptions = parse_event_subscriptions(incomplete_file)
    assert subscriptions == []  # Should skip incomplete subscription


def test_multiple_conditions(tmp_path):
    """Test parsing subscription with multiple conditions."""
    multi_cond_file = tmp_path / "multi-cond.xml"
    multi_cond_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<dunes-policy xmlns="http://vmware.com/vco/policy">
  <event-subscription>
    <id>sub1</id>
    <name>Multi Condition</name>
    <event-type>VmPoweredOnEvent</event-type>
    <workflow-id>wf1</workflow-id>
    <conditions>
      <condition>
        <script><![CDATA[event.vm.name.startsWith("prod")]]></script>
      </condition>
      <condition>
        <script><![CDATA[event.vm.config.hardware.numCPU > 2]]></script>
      </condition>
    </conditions>
  </event-subscription>
</dunes-policy>""")

    subscriptions = parse_event_subscriptions(multi_cond_file)
    assert len(subscriptions) == 1
    assert len(subscriptions[0].conditions) == 2
    assert "startsWith" in subscriptions[0].conditions[0].script
    assert "numCPU" in subscriptions[0].conditions[1].script
