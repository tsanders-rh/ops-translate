# Architecture Patterns Guide

This guide documents architectural patterns and alternative approaches for vRealize Orchestrator (vRO) capabilities that don't have direct Ansible Automation Platform (AAP) equivalents.

## Table of Contents

- [Pattern 1: Long-Running Stateful Workflows](#pattern-1-long-running-stateful-workflows)
- [Pattern 2: Complex Interactive Forms](#pattern-2-complex-interactive-forms)
- [Pattern 3: Dynamic Workflow Generation](#pattern-3-dynamic-workflow-generation)
- [Pattern 4: State Management](#pattern-4-state-management)
- [Pattern 5: NSX Security Components](#pattern-5-nsx-security-components)
- [Migration Decision Tree](#migration-decision-tree)

---

## Pattern 1: Long-Running Stateful Workflows

### vRO Capability

vRO workflows can run for extended periods (days or weeks) with built-in state persistence:

```javascript
// Workflow runs for days/weeks with state persistence
provisionVM();
System.sleep(86400000); // Sleep 24 hours
checkQuota();
if (quotaExceeded()) {
    System.sleep(604800000); // Sleep 7 days
    checkQuotaAgain();
}
completeProvisioning();
```

### Alternative Patterns

#### Option A: AAP Scheduled Jobs (Simple)

**When to use:** Predictable delays, simple state requirements

```yaml
# Job 1: Initial provisioning
- name: Provision VM
  # ... provisioning tasks ...

- name: Schedule quota check for tomorrow
  ansible.builtin.uri:
    url: "{{ aap_url }}/api/v2/job_templates/{{ quota_check_template_id }}/launch/"
    method: POST
    headers:
      Authorization: "Bearer {{ aap_token }}"
    body_format: json
    body:
      extra_vars:
        vm_id: "{{ vm_result.id }}"
        check_type: "quota"
```

**Trade-offs:**
- ✅ Simple to implement
- ✅ Uses native AAP features
- ✅ No additional infrastructure
- ❌ No complex state persistence
- ❌ Limited to scheduled intervals
- ❌ Difficult to track multi-step workflows

#### Option B: External Workflow Engine (Advanced)

**When to use:** Complex state, long delays, conditional logic, multi-step orchestration

Use **Temporal.io**, **Conductor**, or **Apache Airflow**:

```python
# Temporal workflow example
from temporalio import workflow
from datetime import timedelta
import asyncio

@workflow.defn
class VMProvisioningWorkflow:
    @workflow.run
    async def run(self, vm_params):
        # Provision VM
        vm = await workflow.execute_activity(
            provision_vm,
            vm_params,
            start_to_close_timeout=timedelta(minutes=30)
        )

        # Sleep 24 hours (Temporal handles state persistence)
        await asyncio.sleep(86400)

        # Check quota
        quota = await workflow.execute_activity(
            check_quota,
            vm.id,
            start_to_close_timeout=timedelta(minutes=5)
        )

        if quota.exceeded:
            # Sleep 7 days
            await asyncio.sleep(604800)
            quota = await workflow.execute_activity(check_quota_again, vm.id)

        # Complete provisioning via Ansible
        await workflow.execute_activity(
            run_ansible_playbook,
            {"playbook": "complete_provisioning.yml", "vm_id": vm.id}
        )
```

**Trade-offs:**
- ✅ Full state persistence across arbitrary delays
- ✅ Complex conditional logic
- ✅ Automatic retry handling
- ✅ Workflow versioning
- ❌ Additional infrastructure (Temporal cluster)
- ❌ More operational complexity
- ❌ Team needs to learn new tooling

#### Option C: Event-Driven Ansible (Reactive)

**When to use:** Event-triggered continuations, not time-based delays

```yaml
# EDA rulebook waits for external event
- name: VM Provisioning Continuation
  sources:
    - ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000

  rules:
    - name: Continue provisioning when quota available
      condition: event.type == "quota_available" and event.vm_id == vm_id
      action:
        run_job_template:
          name: Complete VM Provisioning
          organization: Default
          extra_vars:
            vm_id: "{{ event.vm_id }}"
```

**Trade-offs:**
- ✅ True reactive automation
- ✅ No polling or sleeping
- ✅ Scales well for event-driven architectures
- ❌ Requires external event source
- ❌ Not suitable for pure time-based delays
- ❌ Event delivery must be reliable

### Decision Tree

```
Is the delay predictable and short (< 1 hour)?
├─ YES → Use AAP scheduled jobs
└─ NO → Is the workflow event-driven or time-driven?
    ├─ EVENT-DRIVEN → Use Event-Driven Ansible
    └─ TIME-DRIVEN → Need complex state management?
        ├─ YES → Use external workflow engine (Temporal/Conductor)
        └─ NO → Chain AAP scheduled jobs with simple state
```

---

## Pattern 2: Complex Interactive Forms

### vRO Capability

vRO supports complex forms with conditional visibility, dynamic choices, and complex validation:

```xml
<!-- Conditional fields: show approvers only if environment == "prod" -->
<form>
  <field name="environment" type="dropdown">
    <choices>dev,staging,prod</choices>
  </field>

  <field name="approvers" type="multiselect"
         visible-when="environment == 'prod'">
    <choices dynamic="true" source="getApproverList()"/>
  </field>

  <field name="cpu_count" type="integer" min="1" max="16"
         default-when="environment == 'dev': 2,
                      environment == 'staging': 4,
                      environment == 'prod': 8"/>

  <field name="compliance_required" type="boolean"
         readonly-when="environment == 'prod'"
         default-when="environment == 'prod': true"/>
</form>
```

### Alternative Patterns

#### Option A: AAP Surveys (Limited)

**When to use:** Simple forms with no conditional logic

```yaml
survey_spec:
  - question_name: Environment
    variable: environment
    type: multiplechoice
    choices:
      - dev
      - staging
      - prod
    required: true

  - question_name: Approvers (required for prod)
    variable: approvers
    type: text
    required: false  # Cannot conditionally require

  - question_name: CPU Count
    variable: cpu_count
    type: integer
    min: 1
    max: 16
    default: 2
    required: true
```

**Trade-offs:**
- ✅ Native AAP feature
- ✅ Simple to configure
- ✅ No development required
- ❌ No conditional visibility
- ❌ No dynamic choice population
- ❌ Limited validation rules
- ❌ Cannot compute defaults based on other fields

#### Option B: Service Catalog Integration

**When to use:** Complex forms, enterprise ITSM already in place

Integrate with **ServiceNow Service Catalog** or **Red Hat Service Catalog**:

```javascript
// ServiceNow catalog item with full conditional logic
var CatalogItem = Class.create();
CatalogItem.prototype = {
    initialize: function() {},

    onLoad: function() {
        // Hide approvers field initially
        g_form.setDisplay('approvers', false);
        g_form.setDisplay('compliance_required', false);
    },

    onChangeEnvironment: function() {
        var env = g_form.getValue('environment');

        // Show approvers for prod
        g_form.setDisplay('approvers', env == 'prod');
        g_form.setMandatory('approvers', env == 'prod');

        // Set CPU defaults
        var cpuDefaults = {
            'dev': 2,
            'staging': 4,
            'prod': 8
        };
        g_form.setValue('cpu_count', cpuDefaults[env]);

        // Compliance required for prod
        if (env == 'prod') {
            g_form.setValue('compliance_required', true);
            g_form.setReadOnly('compliance_required', true);
        }
    },

    onSubmit: function() {
        // Call AAP API to launch job
        var r = new sn_ws.RESTMessageV2();
        r.setEndpoint(g_form.getValue('aap_url') + '/api/v2/job_templates/provision_vm/launch/');
        r.setHttpMethod('POST');
        r.setRequestBody(JSON.stringify({
            extra_vars: {
                environment: g_form.getValue('environment'),
                approvers: g_form.getValue('approvers'),
                cpu_count: g_form.getValue('cpu_count')
            }
        }));
        var response = r.execute();
    }
};
```

**Trade-offs:**
- ✅ Full conditional logic
- ✅ Dynamic choice loading
- ✅ Complex validation
- ✅ Approval workflows built-in
- ✅ Audit trail and CMDB integration
- ❌ Requires ServiceNow or similar ITSM platform
- ❌ Additional licensing cost
- ❌ ServiceNow-specific development

#### Option C: Custom Web Portal

**When to use:** Unique requirements, full control needed, modern UX desired

Build a React/Vue app that calls AAP API:

```javascript
// React component with conditional form logic
import React, { useState, useEffect } from 'react';
import { launchAAP Job } from './api/aap';

function VMProvisionForm() {
  const [environment, setEnvironment] = useState('dev');
  const [approvers, setApprovers] = useState([]);
  const [cpuCount, setCpuCount] = useState(2);
  const [complianceRequired, setComplianceRequired] = useState(false);
  const [approverList, setApproverList] = useState([]);

  // Load approvers from AD/LDAP when environment changes
  useEffect(() => {
    if (environment === 'prod') {
      fetch('/api/approvers')
        .then(res => res.json())
        .then(data => setApproverList(data));
    }
  }, [environment]);

  // Update defaults when environment changes
  useEffect(() => {
    const cpuDefaults = { dev: 2, staging: 4, prod: 8 };
    setCpuCount(cpuDefaults[environment]);
    setComplianceRequired(environment === 'prod');
  }, [environment]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (environment === 'prod' && approvers.length === 0) {
      alert('Approvers required for production');
      return;
    }

    // Launch AAP job
    await launchAAPJob('provision_vm', {
      environment,
      approvers,
      cpu_count: cpuCount,
      compliance_required: complianceRequired
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Environment</label>
        <select value={environment} onChange={(e) => setEnvironment(e.target.value)}>
          <option value="dev">Development</option>
          <option value="staging">Staging</option>
          <option value="prod">Production</option>
        </select>
      </div>

      {/* Conditionally show approvers for prod */}
      {environment === 'prod' && (
        <div className="form-group">
          <label>Approvers *</label>
          <MultiSelect
            options={approverList}
            value={approvers}
            onChange={setApprovers}
            placeholder="Select approvers..."
          />
        </div>
      )}

      <div className="form-group">
        <label>CPU Count</label>
        <input
          type="number"
          min="1"
          max="16"
          value={cpuCount}
          onChange={(e) => setCpuCount(parseInt(e.target.value))}
        />
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={complianceRequired}
            disabled={environment === 'prod'}
            onChange={(e) => setComplianceRequired(e.target.checked)}
          />
          Compliance Required
        </label>
      </div>

      <button type="submit">Provision VM</button>
    </form>
  );
}
```

**Trade-offs:**
- ✅ Full flexibility and control
- ✅ Modern, responsive UX
- ✅ Complex conditional logic
- ✅ Can integrate with any backend
- ✅ Progressive web app capabilities
- ❌ Requires front-end development
- ❌ Maintenance and security updates
- ❌ Need to build authentication/authorization

### Decision Tree

```
Do you need conditional field visibility or dynamic choices?
├─ NO → Use AAP surveys
└─ YES → Do you have ServiceNow or enterprise ITSM?
    ├─ YES → Use Service Catalog integration (lowest friction)
    └─ NO → Do you have front-end development resources?
        ├─ YES → Build custom web portal
        └─ NO → Simplify requirements or use AAP surveys
```

---

## Pattern 3: Dynamic Workflow Generation

### vRO Capability

vRO can generate workflow steps dynamically at runtime based on data:

```javascript
// Generate workflow steps dynamically based on data
var steps = getRequiredSteps(environment, vmType, complianceLevel);
for each (step in steps) {
    executeStep(step);
}

// Or: build workflow graph at runtime
if (needsCompliance) {
    workflow.addStep(complianceCheck);
}
if (needsBackup) {
    workflow.addStep(configureBackup);
}
if (vmType == "database") {
    workflow.addStep(tuneDatabase);
    workflow.addStep(configureReplication);
}
```

### Alternative Patterns

#### Option A: Dynamic Includes (Ansible Native)

**When to use:** Simple conditional step inclusion

```yaml
---
- name: Dynamic VM Provisioning
  hosts: localhost
  vars:
    required_steps: "{{ lookup('template', 'step_selector.j2') | from_yaml }}"

  tasks:
    - name: Execute dynamic steps
      ansible.builtin.include_tasks: "{{ item }}"
      loop: "{{ required_steps }}"

# templates/step_selector.j2
{% if environment == 'prod' %}
  - compliance_check.yml
  - security_hardening.yml
{% endif %}

{% if vm_type == 'database' %}
  - configure_backup.yml
  - tune_performance.yml
  - setup_replication.yml
{% endif %}

{% if needs_monitoring %}
  - install_agents.yml
{% endif %}

  - finalize.yml
```

**Trade-offs:**
- ✅ Native Ansible feature
- ✅ No external dependencies
- ✅ Easy to maintain
- ❌ Limited to task-level inclusion
- ❌ Cannot generate AAP workflow graph dynamically
- ❌ Logic is evaluated at runtime (not visible in AAP UI)

#### Option B: AAP Workflow Templates with Branching

**When to use:** Need visual workflow in AAP, moderate complexity

```python
# Create AAP workflow template with conditional branches
from ansible.controller import WorkflowJobTemplate, WorkflowNode

# Define workflow structure
workflow = WorkflowJobTemplate(
    name="VM Provisioning",
    organization="Default"
)

# Always run provision
provision_node = WorkflowNode(
    workflow=workflow,
    unified_job_template="Provision VM",
    identifier="provision"
)

# Conditional: compliance check for prod
compliance_node = WorkflowNode(
    workflow=workflow,
    unified_job_template="Compliance Check",
    identifier="compliance",
    success_nodes=["finalize"],
    # Only run if environment == prod
    extra_data={"_prompt": {"environment": "prod"}}
)
provision_node.success_nodes = ["compliance", "finalize"]

# Conditional: backup for database VMs
backup_node = WorkflowNode(
    workflow=workflow,
    unified_job_template="Configure Backup",
    identifier="backup",
    # Only run if vm_type == database
    extra_data={"_prompt": {"vm_type": "database"}}
)

# All paths lead to finalize
finalize_node = WorkflowNode(
    workflow=workflow,
    unified_job_template="Finalize",
    identifier="finalize"
)
```

**Trade-offs:**
- ✅ Visible in AAP workflow visualizer
- ✅ Built-in approval gates
- ✅ Conditional branching support
- ❌ Workflow structure is static (defined at design time)
- ❌ Limited conditional logic (based on success/failure/always)
- ❌ Cannot dynamically add nodes at runtime

#### Option C: AAP API Programmatic Workflow Generation

**When to use:** Truly dynamic workflows, templates generated per request

```python
import requests
from typing import List, Dict

def generate_dynamic_workflow(
    vm_id: str,
    environment: str,
    vm_type: str,
    compliance_needed: bool
) -> str:
    """Generate AAP workflow template on-the-fly."""

    nodes = []
    node_id = 1

    # Always start with provisioning
    nodes.append({
        "id": node_id,
        "unified_job_template": get_template_id("provision_vm"),
        "identifier": "provision",
        "extra_data": {"vm_id": vm_id, "environment": environment}
    })
    prev_node = node_id
    node_id += 1

    # Add compliance check for prod
    if environment == "prod" and compliance_needed:
        nodes.append({
            "id": node_id,
            "unified_job_template": get_template_id("compliance_check"),
            "identifier": "compliance",
            "success_nodes": [prev_node]
        })
        prev_node = node_id
        node_id += 1

    # Add database-specific tasks
    if vm_type == "database":
        for task in ["configure_backup", "tune_performance", "setup_replication"]:
            nodes.append({
                "id": node_id,
                "unified_job_template": get_template_id(task),
                "identifier": task,
                "success_nodes": [prev_node]
            })
            prev_node = node_id
            node_id += 1

    # Create workflow template via API
    workflow_name = f"VM Provisioning - {vm_id}"
    response = requests.post(
        f"{AAP_URL}/api/v2/workflow_job_templates/",
        headers={"Authorization": f"Bearer {AAP_TOKEN}"},
        json={
            "name": workflow_name,
            "organization": get_org_id("Default"),
            "workflow_nodes": nodes
        }
    )

    # Launch the workflow
    workflow_id = response.json()["id"]
    launch_response = requests.post(
        f"{AAP_URL}/api/v2/workflow_job_templates/{workflow_id}/launch/"
    )

    return launch_response.json()["id"]
```

**Trade-offs:**
- ✅ Truly dynamic workflow generation
- ✅ Full flexibility
- ✅ Can create complex conditional logic
- ❌ Workflow templates proliferate (cleanup needed)
- ❌ Requires API scripting
- ❌ Not visible in AAP until generated

### Decision Tree

```
Is the dynamic logic simple conditional task inclusion?
├─ YES → Use Ansible dynamic includes
└─ NO → Is the workflow structure moderately complex?
    ├─ YES → Use AAP workflow templates with branching
    └─ NO (very complex) → Use AAP API to generate workflows programmatically
```

---

## Pattern 4: State Management

### vRO Capability

vRO workflows maintain persistent state across runs and can resume from checkpoints:

```javascript
// Workflow attributes persist across runs
workflow.state = "provisioning";
provisionVM();

workflow.state = "configuring";
configureVM();

workflow.state = "completed";

// Resume from last state on retry
if (workflow.state == "provisioning") {
    // Skip provisioning, go to configuring
    configureVM();
} else if (workflow.state == "configuring") {
    // Retry configuration
    configureVM();
}
```

### Alternative Patterns

#### Option A: Ansible Facts (Simple)

**When to use:** Single-host state, simple workflows

```yaml
---
- name: Stateful VM Provisioning
  hosts: localhost

  tasks:
    - name: Check current state
      ansible.builtin.stat:
        path: "/var/lib/ansible/{{ vm_id }}_state.json"
      register: state_file

    - name: Load state
      ansible.builtin.slurp:
        path: "/var/lib/ansible/{{ vm_id }}_state.json"
      register: vm_state_raw
      when: state_file.stat.exists

    - name: Parse state
      ansible.builtin.set_fact:
        vm_state: "{{ vm_state_raw.content | b64decode | from_json }}"
      when: state_file.stat.exists

    - name: Initialize state
      ansible.builtin.set_fact:
        vm_state: {stage: "new", completed_steps: []}
      when: not state_file.stat.exists

    - name: Provision VM
      # ... provisioning tasks ...
      when: "'provisioning' not in vm_state.completed_steps"
      register: provision_result

    - name: Update state after provisioning
      ansible.builtin.copy:
        content: "{{ vm_state | combine({'completed_steps': vm_state.completed_steps + ['provisioning']}) | to_json }}"
        dest: "/var/lib/ansible/{{ vm_id }}_state.json"
      when: provision_result is changed

    - name: Configure VM
      # ... configuration tasks ...
      when: "'configuring' not in vm_state.completed_steps"
      register: configure_result

    - name: Update state after configuration
      ansible.builtin.copy:
        content: "{{ vm_state | combine({'completed_steps': vm_state.completed_steps + ['configuring']}) | to_json }}"
        dest: "/var/lib/ansible/{{ vm_id }}_state.json"
      when: configure_result is changed
```

**Trade-offs:**
- ✅ Simple, no external dependencies
- ✅ File-based, easy to inspect
- ❌ Single-host only (no distributed state)
- ❌ Manual cleanup required
- ❌ No expiration/TTL

#### Option B: External State Store (Redis/Database)

**When to use:** Multi-host workflows, complex state, need TTL

```yaml
---
- name: Stateful VM Provisioning with Redis
  hosts: localhost
  vars:
    redis_host: "{{ lookup('env', 'REDIS_HOST') }}"
    redis_port: 6379

  tasks:
    - name: Get current state from Redis
      community.general.redis_data:
        key: "vm:{{ vm_id }}:state"
        host: "{{ redis_host }}"
        port: "{{ redis_port }}"
      register: vm_state_redis

    - name: Parse state
      ansible.builtin.set_fact:
        vm_state: "{{ vm_state_redis.value | default('{}') | from_json }}"

    - name: Provision VM
      # ... provisioning tasks ...
      when: vm_state.stage | default('new') != 'provisioned'
      register: provision_result

    - name: Update state in Redis
      community.general.redis_data:
        key: "vm:{{ vm_id }}:state"
        host: "{{ redis_host }}"
        port: "{{ redis_port }}"
        value: "{{ {'stage': 'provisioned', 'timestamp': ansible_date_time.iso8601} | to_json }}"
        expiration: 604800  # 7 days TTL
      when: provision_result is changed

    - name: Configure VM
      # ... configuration tasks ...
      when: vm_state.stage | default('new') == 'provisioned'
      register: configure_result

    - name: Update state to completed
      community.general.redis_data:
        key: "vm:{{ vm_id }}:state"
        host: "{{ redis_host }}"
        port: "{{ redis_port }}"
        value: "{{ {'stage': 'completed', 'timestamp': ansible_date_time.iso8601} | to_json }}"
        expiration: 604800
      when: configure_result is changed
```

**Trade-offs:**
- ✅ Distributed state (accessible from any host)
- ✅ Automatic TTL/expiration
- ✅ Fast lookups
- ✅ Can store complex state
- ❌ Requires Redis infrastructure
- ❌ Additional operational complexity

#### Option C: CMDB Integration

**When to use:** State should be part of asset management, compliance tracking

```yaml
---
- name: Stateful VM Provisioning with ServiceNow CMDB
  hosts: localhost

  tasks:
    - name: Get VM record from CMDB
      servicenow.itsm.configuration_item_info:
        instance:
          host: "{{ snow_host }}"
          username: "{{ snow_user }}"
          password: "{{ snow_password }}"
        query:
          name: "{{ vm_name }}"
      register: vm_cmdb

    - name: Extract provisioning state
      ansible.builtin.set_fact:
        provision_state: "{{ vm_cmdb.records[0].u_provision_state | default('new') }}"
      when: vm_cmdb.records | length > 0

    - name: Provision VM
      # ... provisioning tasks ...
      when: provision_state != 'provisioned'
      register: provision_result

    - name: Update CMDB with provisioned state
      servicenow.itsm.configuration_item:
        instance:
          host: "{{ snow_host }}"
          username: "{{ snow_user }}"
          password: "{{ snow_password }}"
        name: "{{ vm_name }}"
        u_provision_state: "provisioned"
        u_last_provisioned: "{{ ansible_date_time.iso8601 }}"
      when: provision_result is changed
```

**Trade-offs:**
- ✅ State is part of CMDB (single source of truth)
- ✅ Audit trail built-in
- ✅ Compliance reporting
- ❌ Requires ServiceNow or similar CMDB
- ❌ Slower than Redis
- ❌ CMDB schema constraints

### Decision Tree

```
Do you need distributed state (multi-host)?
├─ NO → Use Ansible facts (file-based)
└─ YES → Is state part of asset management?
    ├─ YES → Use CMDB integration
    └─ NO → Use Redis/external state store
```

---

## Pattern 5: NSX Networking & Infrastructure Components

### Overview

vRO integrates with NSX-T for network virtualization, security, and infrastructure. This pattern covers migration strategies for NSX components that are classified as **BLOCKED** or **MANUAL** because OpenShift doesn't provide direct equivalents.

### 5.1 NSX Security Groups

#### vRO Capability

```javascript
// NSX Security Group with dynamic membership
var securityGroup = nsxManager.createSecurityGroup("WebTier");
securityGroup.addDynamicMember({
    "criteria": {
        "tag": "app:web",
        "environment": "prod"
    }
});

// NSX Distributed Firewall Rule
var firewallRule = nsxManager.createFirewallRule("Allow-Web-to-DB");
firewallRule.setSource(securityGroup("WebTier"));
firewallRule.setDestination(securityGroup("DBTier"));
firewallRule.setService("MySQL");
firewallRule.setAction("ALLOW");
```

#### Alternative Patterns

##### Option A: Kubernetes NetworkPolicy (Native)

**When to use:** Workloads running as containers/pods in OpenShift

```yaml
# Equivalent to NSX firewall rule: Web -> DB
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-db
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: web
    ports:
    - protocol: TCP
      port: 3306
```

**Trade-offs:**
- ✅ Native Kubernetes/OpenShift feature
- ✅ No additional infrastructure
- ✅ Works with pods/containers
- ❌ Limited to L3/L4 (no L7 filtering)
- ❌ Doesn't apply to VMs (only pods)
- ❌ No dynamic membership (labels are static)

##### Option B: Calico NetworkPolicy (Advanced)

**When to use:** Need L7 filtering, global policies, or VM integration

```yaml
# Calico supports L7 filtering and VM integration
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-web-to-db-advanced
  namespace: production
spec:
  selector: tier == 'database'
  types:
  - Ingress
  ingress:
  - action: Allow
    protocol: TCP
    source:
      selector: tier == 'web'
    destination:
      ports:
      - 3306
    http:
      methods: ['GET', 'POST']  # L7 filtering

---
# Calico Global NetworkPolicy applies to VMs and pods
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: deny-egress-to-internet
spec:
  selector: has(isolation)
  types:
  - Egress
  egress:
  - action: Deny
    destination:
      notNets:
      - 10.0.0.0/8
      - 192.168.0.0/16
```

**Trade-offs:**
- ✅ L7 filtering (HTTP methods, paths)
- ✅ Global policies across namespaces
- ✅ Can apply to VMs via KubeVirt
- ✅ More sophisticated selectors
- ❌ Requires Calico installation
- ❌ More complex than Kubernetes NetworkPolicy

##### Option C: Hybrid Architecture (NSX + OpenShift)

**When to use:** Gradual migration, need NSX features during transition

```yaml
# VMs stay in NSX, pods use NetworkPolicy
# Use NSX-T Container Plugin (NCP) for pod networking

# OpenShift pods get NSX security group tags
apiVersion: v1
kind: Pod
metadata:
  name: web-app
  annotations:
    nsx-t.vmware.com/security-groups: |
      ["WebTier", "ProdApps"]
spec:
  containers:
  - name: nginx
    image: nginx:latest

# NSX firewall rules apply to both VMs and pods
# Managed via NSX Manager or Terraform:
resource "nsxt_policy_group" "web_tier" {
  display_name = "WebTier"
  criteria {
    condition {
      member_type = "VirtualMachine"
      operator    = "CONTAINS"
      key         = "Tag"
      value       = "app:web"
    }
  }
  criteria {
    condition {
      member_type = "Pod"
      operator    = "CONTAINS"
      key         = "Tag"
      value       = "app:web"
    }
  }
}
```

**Trade-offs:**
- ✅ Consistent security policy across VMs and containers
- ✅ Gradual migration path
- ✅ Full NSX feature set
- ❌ Requires NSX-T Container Plugin
- ❌ Operational complexity
- ❌ Licensing costs

##### Option D: OpenShift Service Mesh (Istio)

**When to use:** Microservices architecture, need L7 features, service-to-service auth

```yaml
# Istio AuthorizationPolicy for L7 security
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-web-to-db
  namespace: production
spec:
  selector:
    matchLabels:
      tier: database
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/production/sa/web-app"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/users/*"]
    when:
    - key: request.headers[x-api-key]
      values: ["*"]  # Require API key

---
# Load balancing with traffic splitting (canary)
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: web-app
spec:
  hosts:
  - webapp.example.com
  http:
  - match:
    - headers:
        x-version:
          exact: "v2"
    route:
    - destination:
        host: webapp
        subset: v2
  - route:
    - destination:
        host: webapp
        subset: v1
      weight: 90
    - destination:
        host: webapp
        subset: v2
      weight: 10  # 10% canary traffic
```

**Trade-offs:**
- ✅ L7 security policies
- ✅ Mutual TLS between services
- ✅ Advanced traffic management (canary, A/B testing)
- ✅ Observability (distributed tracing)
- ❌ Requires OpenShift Service Mesh operator
- ❌ Adds latency (sidecar proxies)
- ❌ Increased operational complexity

#### Security Groups Decision Tree

```
What workloads are you migrating?
├─ VMs only → Are you migrating to KubeVirt?
│   ├─ YES → Use Calico NetworkPolicy (VM support)
│   └─ NO → Use Hybrid Architecture (NSX + VMs) or external firewall
│
└─ Containers/Pods → Do you need L7 security features?
    ├─ YES → Use OpenShift Service Mesh (Istio)
    └─ NO → Do you need advanced features (global policies, VM integration)?
        ├─ YES → Use Calico NetworkPolicy
        └─ NO → Use native Kubernetes NetworkPolicy
```

---

### 5.2 Tier Gateways (T0/T1)

#### The Problem

NSX-T Tier-0 and Tier-1 gateways provide critical networking functions:
- **North-south routing** (datacenter ↔ external networks)
- **East-west routing** between network segments
- **Dynamic routing** with BGP/OSPF
- **High availability** with active/standby failover
- **Stateful services** (firewall, load balancing, NAT)

**OpenShift has no equivalent for Tier gateways.**

#### Alternative Patterns

##### Option A: Hybrid Architecture (Keep NSX for Gateways)

**When to use:**
- Complex north-south routing requirements
- Need BGP/OSPF peering with physical network infrastructure
- Existing NSX investment and expertise
- Transitional migration (migrate workloads first, networking later)

**Architecture:**

```
┌─────────────────────────────────────────┐
│  External Network / Physical Datacenter │
└─────────────┬───────────────────────────┘
              │
      ┌───────▼────────┐
      │ NSX Tier-0 GW  │ ← Keep NSX for north-south
      │  (BGP/OSPF)    │
      └───────┬────────┘
              │
      ┌───────▼────────┐
      │ NSX Tier-1 GW  │ ← Keep NSX for tenant routing
      │ (per tenant)   │
      └───────┬────────┘
              │
    ┌─────────▼──────────┐
    │ OpenShift Cluster  │
    │                    │
    │  ┌──────────────┐  │
    │  │ Pods/VMs     │  │ ← Workloads in OpenShift
    │  │ (KubeVirt)   │  │
    │  └──────────────┘  │
    └────────────────────┘
```

**Ansible implementation:**

```yaml
# Configure OpenShift node network to use NSX segment
- name: Configure node interface for NSX segment
  community.general.nmcli:
    conn_name: nsx-overlay
    type: ethernet
    ifname: ens224
    ip4: "{{ node_ip }}/24"
    gw4: "{{ nsx_t1_gateway }}"  # NSX Tier-1 gateway IP
    state: present

# Add route to NSX-managed networks
- name: Add route to NSX networks
  ansible.builtin.command:
    cmd: ip route add 10.0.0.0/8 via {{ nsx_t1_gateway }}
  when: not ansible_check_mode
```

**Trade-offs:**
| Pros | Cons |
|------|------|
| ✅ Preserves all NSX gateway features | ❌ Ongoing NSX licensing costs |
| ✅ No redesign required | ❌ Dual network management platforms |
| ✅ Proven routing and HA capabilities | ❌ Delayed NSX decommissioning |
| ✅ Lower migration risk | ❌ Team needs skills for both platforms |

##### Option B: External Load Balancer (Replace NSX Gateway)

**When to use:**
- Simple north-south routing (ingress traffic only)
- Don't need BGP/OSPF dynamic routing
- Want to eliminate NSX completely
- Have budget for external load balancer (F5, HAProxy, MetalLB)

**Architecture:**

```
┌─────────────────────────────────────────┐
│  External Network                       │
└─────────────┬───────────────────────────┘
              │
      ┌───────▼────────┐
      │ F5 BIG-IP or   │ ← Replace NSX T0/T1
      │ MetalLB        │
      └───────┬────────┘
              │
    ┌─────────▼──────────┐
    │ OpenShift Cluster  │
    │                    │
    │  ┌──────────────┐  │
    │  │ OpenShift    │  │ ← Ingress Controller
    │  │ Router       │  │
    │  └──────┬───────┘  │
    │         │          │
    │  ┌──────▼───────┐  │
    │  │ Pods/VMs     │  │
    │  └──────────────┘  │
    └────────────────────┘
```

**MetalLB implementation:**

```yaml
# Install MetalLB operator
- name: Deploy MetalLB operator
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: v1
      kind: Namespace
      metadata:
        name: metallb-system

- name: Create MetalLB instance
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: metallb.io/v1beta1
      kind: MetalLB
      metadata:
        name: metallb
        namespace: metallb-system

- name: Configure MetalLB IP address pool
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: metallb.io/v1beta1
      kind: IPAddressPool
      metadata:
        name: external-pool
        namespace: metallb-system
      spec:
        addresses:
          - 192.168.1.240-192.168.1.250  # External IP range

- name: Configure L2 advertisement
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: metallb.io/v1beta1
      kind: L2Advertisement
      metadata:
        name: external-l2
        namespace: metallb-system
      spec:
        ipAddressPools:
          - external-pool
```

**Trade-offs:**
| Pros | Cons |
|------|------|
| ✅ Eliminates NSX dependency | ❌ Requires new product/expertise |
| ✅ Simplified management (single platform) | ❌ May lack NSX advanced features |
| ✅ Lower total cost (if using MetalLB) | ❌ No BGP/OSPF in MetalLB L2 mode |
| ✅ Cloud-native approach | ❌ MetalLB BGP mode has limitations vs NSX |

##### Option C: Cloud-Native Redesign (No Gateway)

**When to use:**
- Greenfield deployment on public cloud
- Simple connectivity requirements
- Pod-to-pod communication only
- Using cloud provider's load balancer

**Architecture:**

```
┌─────────────────────────────────────────┐
│  Cloud Provider Load Balancer (AWS ELB)│
└─────────────┬───────────────────────────┘
              │
    ┌─────────▼──────────┐
    │ OpenShift on AWS   │
    │                    │
    │  ┌──────────────┐  │
    │  │ Service      │  │ ← LoadBalancer type service
    │  │ (type: LB)   │  │
    │  └──────┬───────┘  │
    │         │          │
    │  ┌──────▼───────┐  │
    │  │ Pods         │  │
    │  └──────────────┘  │
    └────────────────────┘
```

**Implementation:**

```yaml
# Expose service with cloud load balancer
apiVersion: v1
kind: Service
metadata:
  name: web-frontend
  namespace: production
spec:
  type: LoadBalancer  # Cloud provider creates external LB
  ports:
    - port: 80
      targetPort: 8080
      protocol: TCP
  selector:
    app: web
```

**Trade-offs:**
| Pros | Cons |
|------|------|
| ✅ Fully cloud-native | ❌ Requires architecture redesign |
| ✅ No gateway infrastructure to manage | ❌ Cloud provider lock-in |
| ✅ Auto-scaling load balancer | ❌ Not suitable for on-premises |
| ✅ Integrated with cloud networking | ❌ Limited control vs dedicated gateway |

#### Tier Gateway Decision Matrix

| Requirement | Hybrid NSX | External LB | Cloud-Native |
|-------------|------------|-------------|--------------|
| BGP/OSPF routing | ✅ | ⚠️ F5 only | ❌ |
| Complex north-south | ✅ | ⚠️ Product-dependent | ❌ |
| HA failover | ✅ | ✅ | ✅ |
| Zero NSX cost | ❌ | ✅ | ✅ |
| On-premises support | ✅ | ✅ | ❌ |
| Quick migration | ✅ | ⚠️ Moderate | ❌ |

---

### 5.3 NAT Rules

#### The Problem

NSX-T provides NAT capabilities:
- **Source NAT (SNAT)** for outbound traffic
- **Destination NAT (DNAT)** for inbound traffic
- **1:1 NAT mappings** for specific VMs
- **Port-based NAT (PAT)** for address conservation

**OpenShift has no built-in NAT capability.**

#### Alternative Patterns

##### Option A: Keep NSX for NAT (Hybrid)

**When to use:**
- Complex NAT requirements (1:1 mappings, custom rules)
- Already using hybrid architecture for Tier Gateways
- Need centralized NAT management

This approach uses the same hybrid architecture as Tier Gateways (Section 5.2, Option A).

**NSX NAT configuration remains in place:**

```javascript
// vRO workflow configures NSX NAT (unchanged)
var nat = nsxManager.createNATRule("WebApp-SNAT");
nat.setAction("SNAT");
nat.setSourceNetwork("10.244.0.0/16");  // OpenShift pods
nat.setTranslatedNetwork("192.168.1.100");  // Public IP
```

**Trade-offs:**
- ✅ Preserves all NSX NAT features
- ✅ No redesign required
- ❌ Ongoing NSX costs
- ❌ Dual management platforms

##### Option B: External Router/Firewall NAT

**When to use:**
- Want to eliminate NSX but need NAT
- Have existing physical/virtual router
- Simple NAT requirements

**Products:**
- Cisco ASA
- Palo Alto Networks
- pfSense
- Linux gateway with iptables

**iptables NAT example:**

```yaml
# Configure Linux gateway for OpenShift NAT
- name: Configure SNAT for OpenShift egress traffic
  ansible.builtin.iptables:
    table: nat
    chain: POSTROUTING
    source: 10.244.0.0/16  # OpenShift pod network
    out_interface: eth0
    jump: MASQUERADE
    comment: "OpenShift egress SNAT"

- name: Configure DNAT for ingress
  ansible.builtin.iptables:
    table: nat
    chain: PREROUTING
    protocol: tcp
    destination_port: 443
    to_destination: 192.168.1.50:443  # OpenShift router
    jump: DNAT
    comment: "HTTPS ingress to OpenShift"

- name: Save iptables rules
  ansible.builtin.command:
    cmd: iptables-save > /etc/iptables/rules.v4
```

**Trade-offs:**
- ✅ Eliminates NSX dependency
- ✅ Uses existing network infrastructure
- ❌ Requires router/firewall management
- ❌ NAT rules separate from OpenShift

##### Option C: Cloud Provider NAT Gateway

**When to use:**
- Deploying on public cloud (AWS, Azure, GCP)
- Need egress NAT for outbound traffic
- Want cloud-native solution

**AWS NAT Gateway example:**

```yaml
# Ansible to provision AWS NAT Gateway
- name: Create NAT Gateway for OpenShift egress
  amazon.aws.ec2_vpc_nat_gateway:
    subnet_id: "{{ public_subnet_id }}"
    allocation_id: "{{ elastic_ip_allocation_id }}"
    region: us-east-1
    tags:
      Name: "openshift-nat-gateway"
  register: nat_gateway

- name: Update route table for private subnets
  amazon.aws.ec2_vpc_route_table:
    vpc_id: "{{ vpc_id }}"
    region: us-east-1
    subnets:
      - "{{ openshift_private_subnet_id }}"
    routes:
      - dest: 0.0.0.0/0
        gateway_id: "{{ nat_gateway.nat_gateway_id }}"
    tags:
      Name: "openshift-private-routes"
```

**Trade-offs:**
- ✅ Fully managed by cloud provider
- ✅ High availability built-in
- ✅ No NAT infrastructure to manage
- ❌ Cloud provider lock-in
- ❌ Not available for on-premises
- ❌ Ongoing cloud costs

##### Option D: Redesign to Eliminate NAT

**When to use:**
- Cloud-native deployment
- Can use LoadBalancer services for ingress
- Don't need address hiding/conservation

**Best practice for Kubernetes:**

```yaml
# Ingress: Use LoadBalancer services (no DNAT needed)
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  type: LoadBalancer
  ports:
    - port: 443
      targetPort: 8443
  selector:
    app: web

# Egress: Pods use direct routing or egress IPs
# OpenShift EgressIP for predictable source addressing
apiVersion: k8s.ovn.org/v1
kind: EgressIP
metadata:
  name: web-app-egress
spec:
  egressIPs:
    - 192.168.1.200
  namespaceSelector:
    matchLabels:
      name: production
  podSelector:
    matchLabels:
      app: web
```

**Trade-offs:**
- ✅ Cloud-native approach
- ✅ No NAT infrastructure
- ✅ Simplified networking
- ❌ Requires architecture changes
- ❌ May not meet compliance requirements (source IP hiding)

#### NAT Decision Tree

```
What is your deployment environment?
├─ On-premises → Do you have existing router/firewall?
│   ├─ YES → Use external router NAT
│   └─ NO → Already using hybrid NSX?
│       ├─ YES → Keep NSX for NAT
│       └─ NO → Consider redesign or add router/firewall
│
└─ Public cloud → Can you eliminate NAT requirement?
    ├─ YES → Redesign with LoadBalancer + EgressIP
    └─ NO → Use cloud provider NAT Gateway
```

---

### 5.4 VPN Services

#### The Problem

NSX-T provides VPN services:
- **IPSec site-to-site VPN** for datacenter connectivity
- **SSL VPN** for remote user access
- **L2 VPN** for stretched Layer 2 networks

**OpenShift has no built-in VPN service.**

#### Alternative Patterns

##### Option A: External VPN Appliance

**When to use:**
- Enterprise VPN requirements
- Need compliance/certification (FIPS, etc.)
- Already have VPN infrastructure
- Site-to-site connectivity critical

**Products:**
- Cisco ASA
- Palo Alto Networks
- Fortinet FortiGate
- pfSense/OPNsense

**Ansible configuration example (pfSense):**

```yaml
# Configure IPSec site-to-site VPN via pfSense API
- name: Create IPSec Phase 1 configuration
  ansible.builtin.uri:
    url: "https://{{ pfsense_host }}/api/v1/services/ipsec/phase1"
    method: POST
    headers:
      Authorization: "{{ pfsense_api_token }}"
    body_format: json
    body:
      iketype: ikev2
      protocol: inet
      interface: wan
      remote_gateway: "{{ remote_vpn_endpoint }}"
      authentication_method: pre_shared_key
      preshared_key: "{{ vpn_psk }}"
      encryption_algorithm: aes256
      hash_algorithm: sha256
      dhgroup: 14

- name: Create IPSec Phase 2 configuration
  ansible.builtin.uri:
    url: "https://{{ pfsense_host }}/api/v1/services/ipsec/phase2"
    method: POST
    headers:
      Authorization: "{{ pfsense_api_token }}"
    body_format: json
    body:
      mode: tunnel
      local_subnet: "10.244.0.0/16"  # OpenShift pod network
      remote_subnet: "{{ remote_network }}"
      protocol: esp
      encryption_algorithm: aes256
      hash_algorithm: sha256
```

**Trade-offs:**
- ✅ Enterprise-grade features
- ✅ Compliance certifications
- ✅ Centralized VPN management
- ✅ Proven reliability
- ❌ Additional hardware/licensing costs
- ❌ Separate VPN infrastructure to manage

##### Option B: Containerized VPN (Cloud-Native)

**When to use:**
- Simple VPN requirements
- Want Kubernetes-native solution
- Don't need enterprise VPN features
- Development/testing environments

**WireGuard in OpenShift:**

```yaml
# Deploy WireGuard VPN server as a pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wireguard-vpn
  namespace: vpn
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wireguard
  template:
    metadata:
      labels:
        app: wireguard
    spec:
      containers:
      - name: wireguard
        image: linuxserver/wireguard:latest
        securityContext:
          capabilities:
            add:
              - NET_ADMIN
              - SYS_MODULE
          privileged: true
        env:
        - name: PUID
          value: "1000"
        - name: PGID
          value: "1000"
        - name: TZ
          value: "America/New_York"
        - name: SERVERURL
          value: "vpn.example.com"
        - name: PEERS
          value: "10"  # Number of VPN clients
        - name: PEERDNS
          value: "auto"
        - name: INTERNAL_SUBNET
          value: "10.13.13.0/24"
        volumeMounts:
        - name: config
          mountPath: /config
        - name: modules
          mountPath: /lib/modules
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: wireguard-config
      - name: modules
        hostPath:
          path: /lib/modules

---
# Expose WireGuard with LoadBalancer
apiVersion: v1
kind: Service
metadata:
  name: wireguard-vpn
  namespace: vpn
spec:
  type: LoadBalancer
  ports:
    - port: 51820
      targetPort: 51820
      protocol: UDP
      name: wireguard
  selector:
    app: wireguard
```

**Trade-offs:**
- ✅ Kubernetes-native deployment
- ✅ No separate infrastructure
- ✅ Open source (no licensing)
- ✅ Modern WireGuard protocol
- ❌ Limited enterprise features
- ❌ Manual certificate management
- ❌ Not suitable for compliance-heavy environments

##### Option C: Redesign to Eliminate VPN

**When to use:**
- VPN was used for remote access → Replace with OAuth/SSO
- VPN was for site-to-site → Replace with direct routing/SD-WAN
- VPN was for L2 stretch → Redesign for L3 routing

**Remote access redesign:**

```yaml
# Replace SSL VPN with OpenShift OAuth + Identity Provider
apiVersion: config.openshift.io/v1
kind: OAuth
metadata:
  name: cluster
spec:
  identityProviders:
  - name: corporate_ldap
    type: LDAP
    ldap:
      attributes:
        id: ["dn"]
        email: ["mail"]
        name: ["cn"]
        preferredUsername: ["uid"]
      bindDN: "cn=admin,dc=example,dc=com"
      bindPassword:
        name: ldap-secret
      url: "ldaps://ldap.example.com:636/ou=users,dc=example,dc=com?uid"

---
# Users access via OpenShift Console (HTTPS) instead of VPN
# Multi-factor authentication via identity provider
# No VPN client needed
```

**Site-to-site connectivity redesign:**

```yaml
# Replace VPN with direct routing or SD-WAN
# Configure BGP peering between datacenters
- name: Configure BGP on OpenShift cluster
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: metallb.io/v1beta1
      kind: BGPAdvertisement
      metadata:
        name: datacenter-peering
        namespace: metallb-system
      spec:
        ipAddressPools:
          - openshift-services
        peers:
          - 192.168.100.1  # Remote datacenter router
        communities:
          - 65000:100

- name: Configure BGP peer
  kubernetes.core.k8s:
    state: present
    definition:
      apiVersion: metallb.io/v1beta2
      kind: BGPPeer
      metadata:
        name: remote-datacenter
        namespace: metallb-system
      spec:
        peerAddress: 192.168.100.1
        peerASN: 65001
        myASN: 65000
```

**Trade-offs:**
- ✅ No VPN infrastructure
- ✅ Modern authentication (OAuth/SSO)
- ✅ Better performance (no VPN overhead)
- ✅ Simplified architecture
- ❌ Requires network redesign
- ❌ May need routing changes
- ❌ Not always feasible (compliance, legacy systems)

#### VPN Decision Tree

```
Why was VPN needed in vRO workflows?
├─ Remote user access → Can you use OAuth/SSO instead?
│   ├─ YES → Redesign with OpenShift OAuth + identity provider
│   └─ NO (compliance requires VPN) → Use external VPN appliance
│
├─ Site-to-site connectivity → Can you use direct routing/SD-WAN?
│   ├─ YES → Redesign with BGP or SD-WAN
│   └─ NO → Use external VPN appliance
│
└─ L2 network stretch → Can you redesign for L3 routing?
    ├─ YES → Redesign for Layer 3 networking (better for cloud-native)
    └─ NO → Use external VPN appliance or keep NSX L2 VPN

Special case: Simple dev/test VPN → Use containerized WireGuard
```

---

### NSX Components: Overall Migration Decision Tree

```
What NSX component is your vRO workflow using?
├─ Security Groups → See Section 5.1 decision tree
├─ Tier Gateways (T0/T1) → See Section 5.2 decision matrix
├─ NAT Rules → See Section 5.3 decision tree
└─ VPN Services → See Section 5.4 decision tree
```

---

## Migration Decision Tree

Use this decision tree to determine the right migration approach for your vRO workflows:

```
Start: Evaluating vRO workflow for migration

├─ Does it use long-running delays (> 1 hour)?
│   ├─ YES → See Pattern 1 (Long-Running Workflows)
│   └─ NO → Continue
│
├─ Does it use complex conditional forms?
│   ├─ YES → See Pattern 2 (Complex Forms)
│   └─ NO → Continue
│
├─ Does it generate workflow structure dynamically?
│   ├─ YES → See Pattern 3 (Dynamic Workflows)
│   └─ NO → Continue
│
├─ Does it require persistent state across runs?
│   ├─ YES → See Pattern 4 (State Management)
│   └─ NO → Continue
│
├─ Does it integrate with NSX for networking/security?
│   ├─ YES → See Pattern 5 (NSX Security Components)
│   └─ NO → Continue
│
└─ Direct translation with ops-translate is likely feasible
    └─ Run: ops-translate analyze
```

---

## Additional Resources

- [Ansible Automation Platform Documentation](https://docs.ansible.com/automation-controller/)
- [Event-Driven Ansible Documentation](https://www.ansible.com/products/event-driven-ansible)
- [Temporal.io Documentation](https://docs.temporal.io/)
- [Calico NetworkPolicy Documentation](https://docs.tigera.io/calico/latest/network-policy/)
- [OpenShift Service Mesh Documentation](https://docs.openshift.com/container-platform/latest/service_mesh/)
- [KubeVirt Documentation](https://kubevirt.io/user-guide/)

---

## Getting Help

If you're unsure which pattern applies to your use case:

1. Run `ops-translate analyze` to get automated recommendations
2. Review the generated `intent/gaps.json` for component classifications
3. Check the HTML report for specific guidance on blocked components
4. Consult this patterns guide for architectural alternatives
5. Open an issue on [GitHub](https://github.com/tsanders-rh/ops-translate/issues) for complex scenarios

---

*This guide is generated as part of the ops-translate migration assessment. For the latest version, see the [GitHub repository](https://github.com/tsanders-rh/ops-translate).*
