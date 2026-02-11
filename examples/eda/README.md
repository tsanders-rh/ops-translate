# Event-Driven Ansible Rulebook Generation

This directory contains an example Event-Driven Ansible (EDA) rulebook generated from a vRealize Orchestrator event subscription policy.

## Overview

The EDA rulebook generator translates vRealize Orchestrator reactive automation patterns into Event-Driven Ansible rulebooks. This preserves the event-driven behavior when migrating from vRO to Ansible Automation Platform.

## Files

- **rulebook.yml** - Generated EDA rulebook with 4 rules
- **../vrealize/vm-lifecycle-policy.xml** - Source vRO event subscription policy

## Generated Rulebook Structure

The generated rulebook includes:

### Event Sources

```yaml
sources:
  - ansible.eda.webhook:
      host: 0.0.0.0
      port: 5000
      token: '{{ webhook_token }}'
```

Configured to receive events via webhook from vCenter Event Broker Appliance (VEBA) or similar event router.

### Rules

Each vRO event subscription becomes an EDA rule with:

1. **Name**: From the subscription name
2. **Condition**: Translated from JavaScript to Python/Jinja2
3. **Action**: Calls an Ansible playbook with event data

#### Example Rule

From this vRO subscription:

```xml
<event-subscription>
  <name>VM Powered On - Compliance Check</name>
  <event-type>VmPoweredOnEvent</event-type>
  <workflow-id>compliance-check-workflow</workflow-id>
  <conditions>
    <condition>
      <script><![CDATA[
        event.vm.runtime.host.parent.name == "Production-Cluster" &&
        event.vm.config.hardware.numCPU > 4
      ]]></script>
    </condition>
  </conditions>
  <bindings>
    <binding>
      <name>vmName</name>
      <value>event.vm.name</value>
    </binding>
  </bindings>
</event-subscription>
```

To this EDA rule:

```yaml
- name: VM Powered On - Compliance Check
  condition: (event.type == "vm_powered_on") and (event.payload.cluster == "Production-Cluster" and event.payload.cpu_count > 4)
  action:
    run_playbook:
      name: playbooks/compliance-check-workflow.yml
      extra_vars:
        vmName: '{{ event.payload.vm_name }}'
        vmId: '{{ event.payload.vm_id }}'
        cluster: '{{ event.payload.cluster }}'
        poweredOnTime: '{{ event.payload.created_time }}'
```

## JavaScript to Python Translation

The generator automatically translates JavaScript conditions to Python/EDA format:

| JavaScript | Python/EDA |
|-----------|-----------|
| `&&` | `and` |
| `||` | `or` |
| `!` | `not` |
| `!=` | `!=` |
| `==` | `==` |
| `true` | `True` |
| `false` | `False` |
| `event.vm.name` | `event.payload.vm_name` |
| `event.vm.config.hardware.numCPU` | `event.payload.cpu_count` |

## Event Payload Mapping

vCenter event properties are mapped to EDA payload fields using the mappings in `vcenter_event_mappings.yaml`.

Common mappings:

- `event.vm.name` → `event.payload.vm_name`
- `event.vm.id` → `event.payload.vm_id`
- `event.createdTime` → `event.payload.created_time`
- `event.alarm.name` → `event.payload.alarm_name`

## Usage

### 1. Generate Rulebook from vRO Policy

```bash
ops-translate generate --format eda --policy examples/vrealize/vm-lifecycle-policy.xml
```

### 2. Create Playbooks

Create playbooks referenced by the rules (e.g., `playbooks/compliance-check-workflow.yml`):

```yaml
---
- name: VM Compliance Check
  hosts: localhost
  tasks:
    - name: Run compliance check for {{ vmName }}
      ansible.builtin.debug:
        msg: "Checking compliance for VM {{ vmName }} ({{ vmId }}) in cluster {{ cluster }}"

    # Add your compliance check tasks here
```

### 3. Run with ansible-rulebook

```bash
ansible-rulebook --rulebook examples/eda/rulebook.yml --inventory inventory.yml --vars webhook_token=your_secret_token
```

### 4. Configure Event Source

Set up vCenter Event Broker Appliance (VEBA) or another event router to forward vCenter events to the webhook endpoint:

```yaml
# VEBA function configuration
event_source:
  type: vcenter
  vcenter:
    address: vcenter.example.com
    username: svc-veba@vsphere.local
    password: "{{ vcenter_password }}"

event_processor:
  type: webhook
  webhook:
    url: http://eda-controller:5000
    headers:
      Authorization: "Bearer your_secret_token"
```

## Supported vCenter Events

The generator supports all vCenter event types defined in `vcenter_event_mappings.yaml`:

- **VM Lifecycle**: VmPoweredOnEvent, VmPoweredOffEvent, VmCreatedEvent, VmRemovedEvent, VmClonedEvent, VmMigratedEvent
- **VM Configuration**: VmReconfiguredEvent, VmRenamedEvent
- **Alarms**: AlarmStatusChangedEvent, AlarmCreatedEvent
- **Host Lifecycle**: HostConnectedEvent, HostDisconnectedEvent, EnteredMaintenanceModeEvent, ExitMaintenanceModeEvent
- **Datastore**: DatastoreFileUploadedEvent, DatastoreFileDeletedEvent
- **Network**: DvsCreatedEvent, DvsPortConnectedEvent
- **Resource Pool**: ResourcePoolCreatedEvent, ResourcePoolMovedEvent
- **Tasks**: TaskTimeoutEvent
- **Licensing**: LicenseExpiredEvent
- **User Management**: UserLoginSessionEvent, UserLogoutSessionEvent

## Limitations

### Current Limitations

1. **Simple Condition Translation**: Complex JavaScript expressions may need manual review
2. **Event Field Mapping**: Custom event properties may need manual mapping additions
3. **Nested Logic**: Deeply nested conditionals should be verified
4. **String Methods**: JavaScript string methods like `.startsWith()` are not yet translated

### Not Translated

- JavaScript functions and methods beyond basic operators
- Complex object manipulation
- Custom vRO plugin calls (these need workflow translation instead)

## Next Steps

After generating the rulebook:

1. Review translated conditions for correctness
2. Create the referenced Ansible playbooks
3. Set up event routing from vCenter to EDA
4. Test each rule with sample events
5. Monitor and tune event filters as needed

## References

- [Event-Driven Ansible Documentation](https://access.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.4/html/event-driven_ansible_controller_user_guide/index)
- [vCenter Event Broker Appliance (VEBA)](https://vmweventbroker.io/)
- [Ansible Rulebook Reference](https://ansible.readthedocs.io/projects/rulebook/en/latest/)
