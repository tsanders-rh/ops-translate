# Migration Field Guide

A comprehensive guide to common migration patterns when translating VMware/vRealize workflows to OpenShift Virtualization and Ansible.

## Table of Contents

1. [Introduction](#introduction)
2. [NSX Migration Patterns](#nsx-migration-patterns)
3. [Approval & Governance Workflows](#approval--governance-workflows)
4. [Storage & Datastore Management](#storage--datastore-management)
5. [Network Configuration](#network-configuration)
6. [Day 2 Operations](#day-2-operations)
7. [Custom Logic & Integrations](#custom-logic--integrations)
8. [Best Practices](#best-practices)

---

## Introduction

This field guide provides expert-backed patterns for migrating common VMware automation workflows to OpenShift-native equivalents. Each pattern includes:

- **Why it's challenging**: Understanding the fundamental differences
- **Recommended approach**: Proven strategies that work
- **Implementation steps**: Actionable guidance
- **Testing strategy**: How to validate the migration
- **Common pitfalls**: What to avoid

**Key Principle**: These patterns prioritize safety, reviewability, and maintainability over feature parity. The goal is sustainable cloud-native automation, not pixel-perfect replication.

---

## NSX Migration Patterns

### Pattern: NSX Distributed Firewall → NetworkPolicy

**Challenge**: NSX DFW provides L7 filtering, stateful inspection, and micro-segmentation that NetworkPolicy cannot replicate.

**Recommended Approach**: Allow-list NetworkPolicy with Calico for advanced features

```yaml
# Step 1: Design label taxonomy
# Define security zones as labels
# security.zone: dmz | internal | external
# app.tier: web | app | data
# team.owner: platform | security

# Step 2: Create baseline NetworkPolicy (deny-all default)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

# Step 3: Create allow-list policies
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-to-app
  namespace: production
spec:
  podSelector:
    matchLabels:
      app.tier: app
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app.tier: web
    ports:
    - protocol: TCP
      port: 8080
```

**Implementation Steps**:

1. **Inventory NSX rules**: Export all DFW rules and document their purpose
2. **Design label taxonomy**: Create security.zone, app.tier labels that map to your security zones
3. **Create deny-all default**: Start with a default-deny NetworkPolicy in each namespace
4. **Build allow-list incrementally**: Add NetworkPolicy rules for legitimate traffic patterns
5. **Test with real traffic**: Deploy to dev, monitor denied connections, iterate
6. **Document gaps**: Clearly document L7/stateful features that cannot be replicated
7. **Plan compensating controls**: Consider Calico, service mesh, or keeping NSX hybrid

**Testing Strategy**:

```bash
# Test connectivity between pods
kubectl run test-web --image=busybox --labels="app.tier=web" -- sleep 3600
kubectl run test-app --image=busybox --labels="app.tier=app" -- sleep 3600

# Test allowed connection
kubectl exec test-web -- wget -O- test-app:8080

# Test denied connection (should fail)
kubectl exec test-web -- wget -O- test-db:5432
```

**Common Pitfalls**:

- ❌ **Trying to replicate all NSX features**: NetworkPolicy is intentionally simpler - accept the gaps
- ❌ **Starting with allow-all**: Begin restrictive and open up based on actual traffic patterns
- ❌ **Ignoring egress**: Egress rules are just as important as ingress for zero-trust
- ❌ **Not testing blocked traffic**: Verify that unwanted traffic is actually denied

---

### Pattern: NSX Security Groups → Label Selectors

**Challenge**: NSX Security Groups support dynamic membership based on tags, network properties, and complex criteria. Kubernetes labels are static.

**Recommended Approach**: Kubernetes label taxonomy + automation to apply labels

```python
# Example: Ansible task to auto-label pods based on NSX group criteria
- name: Apply security zone labels based on namespace
  kubernetes.core.k8s:
    state: patched
    kind: Pod
    namespace: "{{ item.namespace }}"
    name: "{{ item.name }}"
    definition:
      metadata:
        labels:
          security.zone: "{% if item.namespace == 'production' %}dmz{% elif item.namespace == 'internal' %}internal{% else %}external{% endif %}"
  loop: "{{ pods }}"
```

**Implementation Steps**:

1. **Document NSX group membership rules**: Export all security group definitions
2. **Map to label criteria**: Design label schema that approximates NSX group logic
3. **Implement label automation**: Use Ansible, admission webhooks, or policy agents to auto-label
4. **Reference in NetworkPolicy**: Use label selectors in podSelector and namespaceSelector
5. **Audit label assignments**: Regularly verify labels match intended security posture
6. **Require SecOps sign-off**: Security boundary changes need security team approval

**Testing Strategy**:

```bash
# Verify label assignments
kubectl get pods --all-namespaces --show-labels

# Verify NetworkPolicy uses correct selectors
kubectl describe networkpolicy -n production | grep -A5 "Pod Selector"

# Test policy enforcement
kubectl exec test-pod -- curl -m 5 other-pod.svc
```

**Common Pitfalls**:

- ❌ **Manual labeling**: Labels drift without automation - use admission controllers or operators
- ❌ **Complex label logic**: Keep taxonomy simple - security.zone, app.tier, team.owner
- ❌ **Not documenting mappings**: Document how NSX groups map to label combinations
- ❌ **Ignoring namespace boundaries**: Namespaces provide hard isolation - use them strategically

---

## Approval & Governance Workflows

### Pattern: vRealize Approval → AAP Workflow with Approval Node

**Challenge**: Approval workflows involve human decision-making, SLAs, and organizational processes that vary by company.

**Recommended Approach**: Ansible Automation Platform workflow templates with approval nodes

```yaml
# AAP Workflow Template Structure:
# 1. Pre-approval validation
# 2. Approval node (waits for human decision)
# 3. Post-approval provisioning
# 4. Notification

# Example approval node configuration (via AAP UI/API):
approval_node:
  name: "Production VM Approval"
  timeout: 86400  # 24 hours
  description: "Approve provisioning of {{ vm_name }} in production"
  approvers:
    - role: "Production Approvers"
    - email: "ops-lead@example.com"
```

**Implementation Steps**:

1. **Map approval decision points**: Identify where approvals are needed (environment, cost, etc.)
2. **Design AAP workflow**: Create workflow template with approval nodes
3. **Configure notifications**: Set up email/Slack notifications for approvers
4. **Implement fallback logic**: Define what happens on timeout (auto-reject or escalate)
5. **Integrate ticketing**: Connect to ServiceNow/Jira for audit trail
6. **Test approval scenarios**: Test approve, reject, timeout, escalation paths
7. **Document SLAs**: Clear SLAs for approval response times

**Testing Strategy**:

```bash
# Launch workflow and test approval
awx-cli job_template launch --name="VM Provisioning" --extra_vars="..."

# Check approval status
awx-cli workflow_approval list

# Approve/reject via CLI
awx-cli workflow_approval approve <approval-id>
awx-cli workflow_approval deny <approval-id>
```

**Common Pitfalls**:

- ❌ **No timeout handling**: Always define what happens when approval times out
- ❌ **Skipping audit trail**: Integrate with ticketing for compliance
- ❌ **Hardcoding approvers**: Use roles/groups, not individual emails
- ❌ **Not testing rejection**: Ensure rejected requests don't provision anything

---

### Pattern: Cost Center Validation → Pre-Task Validation

**Challenge**: vRealize often validates cost centers against external systems before provisioning.

**Recommended Approach**: Ansible pre-flight validation tasks with external API calls

```yaml
---
- name: Validate cost center before provisioning
  block:
    - name: Call cost center validation API
      ansible.builtin.uri:
        url: "https://finance-api.example.com/validate-cost-center"
        method: POST
        body_format: json
        body:
          cost_center: "{{ cost_center }}"
          amount: "{{ estimated_cost }}"
        headers:
          Authorization: "Bearer {{ finance_api_token }}"
        status_code: [200, 201]
      register: validation_result

    - name: Fail if cost center invalid
      ansible.builtin.fail:
        msg: "Invalid cost center: {{ validation_result.json.error }}"
      when: not validation_result.json.valid

    - name: Proceed with provisioning
      # ... rest of playbook
```

**Implementation Steps**:

1. **Identify validation requirements**: What needs validation? Cost center, budget, quota?
2. **Map to external systems**: Which APIs provide validation? Finance, CMDB, ITSM?
3. **Implement pre-flight tasks**: Add validation tasks at start of playbook
4. **Handle errors gracefully**: Clear error messages when validation fails
5. **Add retries for transient failures**: Use `retries` and `until` for API calls
6. **Test failure scenarios**: Verify playbook stops when validation fails

**Common Pitfalls**:

- ❌ **Continuing on validation failure**: Always `fail` task when validation fails
- ❌ **No retries for API calls**: External APIs can have transient failures
- ❌ **Not caching validation results**: Cache results to avoid repeated API calls
- ❌ **Hardcoding API endpoints**: Use variables for environment-specific endpoints

---

## Storage & Datastore Management

### Pattern: Datastore Selection → StorageClass Selection

**Challenge**: vRealize selects datastores based on capacity, performance tier, and availability.

**Recommended Approach**: StorageClass with performance tiers + dynamic provisioning

```yaml
# Define StorageClasses for different performance tiers
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nvme-performance
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: kubernetes.io/cinder
parameters:
  type: nvme-ssd
  replication: "3"
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ssd-balanced
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: kubernetes.io/cinder
parameters:
  type: ssd
  replication: "2"
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: hdd-capacity
provisioner: kubernetes.io/cinder
parameters:
  type: hdd
  replication: "1"
```

**Ansible Selection Logic**:

```yaml
- name: Select StorageClass based on environment
  ansible.builtin.set_fact:
    storage_class: "{% if environment == 'prod' %}nvme-performance{% elif environment == 'uat' %}ssd-balanced{% else %}hdd-capacity{% endif %}"

- name: Create PVC with selected StorageClass
  kubernetes.core.k8s:
    definition:
      apiVersion: v1
      kind: PersistentVolumeClaim
      metadata:
        name: "{{ vm_name }}-disk"
        namespace: "{{ namespace }}"
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: "{{ disk_size_gb }}Gi"
        storageClassName: "{{ storage_class }}"
```

**Implementation Steps**:

1. **Define performance tiers**: Map VMware datastore tiers to StorageClass tiers
2. **Create StorageClasses**: Define StorageClass for each performance/cost tier
3. **Implement selection logic**: Use Ansible variables to select appropriate StorageClass
4. **Test dynamic provisioning**: Verify PVCs are provisioned with correct StorageClass
5. **Monitor capacity**: Set up alerts for storage capacity thresholds
6. **Document tier criteria**: Clear criteria for when to use each tier

**Common Pitfalls**:

- ❌ **Too many StorageClasses**: Keep it simple - 3-4 tiers max (performance, balanced, capacity)
- ❌ **Not setting default**: Always have a sensible default StorageClass
- ❌ **Ignoring access modes**: Use ReadWriteOnce for VMs, not ReadWriteMany
- ❌ **Not monitoring capacity**: StorageClass capacity should be monitored

---

## Network Configuration

### Pattern: Environment-Based Network Assignment → Multus NetworkAttachmentDefinition

**Challenge**: vRealize assigns VMs to different networks based on environment (dev/staging/prod).

**Recommended Approach**: Multus with per-environment NetworkAttachmentDefinitions

```yaml
# Production network definition
---
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: prod-network
  namespace: virt-prod
spec:
  config: |
    {
      "cniVersion": "0.3.1",
      "type": "bridge",
      "bridge": "br-prod",
      "vlan": 100,
      "ipam": {
        "type": "whereabouts",
        "range": "10.100.0.0/16"
      }
    }
```

**Ansible Network Selection**:

```yaml
- name: Select network based on environment
  ansible.builtin.set_fact:
    network_name: "{% if environment == 'prod' %}prod-network{% elif environment == 'staging' %}staging-network{% else %}dev-network{% endif %}"

- name: Create VM with selected network
  kubernetes.core.k8s:
    definition:
      apiVersion: kubevirt.io/v1
      kind: VirtualMachine
      metadata:
        name: "{{ vm_name }}"
      spec:
        template:
          spec:
            domain:
              devices:
                interfaces:
                - name: default
                  masquerade: {}
                - name: secondary
                  bridge: {}
            networks:
            - name: default
              pod: {}
            - name: secondary
              multus:
                networkName: "{{ network_name }}"
```

**Implementation Steps**:

1. **Define network requirements**: What networks exist? VLANs? IP ranges?
2. **Create NetworkAttachmentDefinitions**: One per network/environment
3. **Implement selection logic**: Map environment to network name
4. **Test connectivity**: Verify VMs can communicate on assigned networks
5. **Document network topology**: Clear documentation of network assignments
6. **Plan IP management**: Use Whereabouts or external IPAM

**Common Pitfalls**:

- ❌ **Hardcoding network names**: Use variables for environment-based selection
- ❌ **Not testing cross-network**: Test connectivity between networks
- ❌ **Ignoring IP conflicts**: Use proper IPAM solution (Whereabouts, Infoblox)
- ❌ **No network policy**: Apply NetworkPolicy even with Multus networks

---

## Day 2 Operations

### Pattern: VM Lifecycle Operations → KubeVirt virtctl Commands

**Challenge**: vRealize provides start/stop/restart operations for VMs.

**Recommended Approach**: Ansible tasks using `virtctl` or Kubernetes API

```yaml
---
- name: Start VM
  kubernetes.core.k8s:
    api_version: kubevirt.io/v1
    kind: VirtualMachine
    name: "{{ vm_name }}"
    namespace: "{{ namespace }}"
    state: patched
    definition:
      spec:
        running: true

- name: Stop VM
  kubernetes.core.k8s:
    api_version: kubevirt.io/v1
    kind: VirtualMachine
    name: "{{ vm_name }}"
    namespace: "{{ namespace }}"
    state: patched
    definition:
      spec:
        running: false

- name: Restart VM
  block:
    - name: Stop VM
      kubernetes.core.k8s:
        api_version: kubevirt.io/v1
        kind: VirtualMachine
        name: "{{ vm_name }}"
        namespace: "{{ namespace }}"
        state: patched
        definition:
          spec:
            running: false

    - name: Wait for VM to stop
      kubernetes.core.k8s_info:
        api_version: kubevirt.io/v1
        kind: VirtualMachineInstance
        name: "{{ vm_name }}"
        namespace: "{{ namespace }}"
      register: vmi
      until: vmi.resources | length == 0
      retries: 30
      delay: 10

    - name: Start VM
      kubernetes.core.k8s:
        api_version: kubevirt.io/v1
        kind: VirtualMachine
        name: "{{ vm_name }}"
        namespace: "{{ namespace }}"
        state: patched
        definition:
          spec:
            running: true
```

**Implementation Steps**:

1. **Map vRealize operations**: List all Day 2 operations (start, stop, snapshot, etc.)
2. **Find KubeVirt equivalents**: Map each operation to KubeVirt API or virtctl
3. **Create Ansible tasks**: Implement each operation as Ansible task
4. **Add idempotency checks**: Ensure tasks are idempotent (can run multiple times)
5. **Test each operation**: Verify start, stop, restart work correctly
6. **Add error handling**: Handle cases where VM doesn't exist, is already running, etc.

**Common Pitfalls**:

- ❌ **Not waiting for state changes**: Always wait for VM/VMI to reach desired state
- ❌ **Not handling edge cases**: What if VM is already running when you try to start?
- ❌ **Using virtctl in automation**: Prefer Kubernetes API over CLI tools in automation
- ❌ **No timeout handling**: Always set retries and timeout for wait tasks

---

## Custom Logic & Integrations

### Pattern: REST API Calls → ansible.builtin.uri Module

**Challenge**: vRealize workflows often call external REST APIs for CMDB, ITSM, or custom systems.

**Recommended Approach**: Ansible `uri` module with proper auth and error handling

```yaml
---
- name: Call CMDB to register VM
  ansible.builtin.uri:
    url: "https://cmdb.example.com/api/v1/servers"
    method: POST
    body_format: json
    body:
      name: "{{ vm_name }}"
      environment: "{{ environment }}"
      owner: "{{ owner_email }}"
      cost_center: "{{ cost_center }}"
    headers:
      Authorization: "Bearer {{ cmdb_api_token }}"
      Content-Type: "application/json"
    status_code: [200, 201]
    return_content: true
  register: cmdb_result
  retries: 3
  delay: 5
  until: cmdb_result.status in [200, 201]

- name: Store CMDB ID as VM annotation
  kubernetes.core.k8s:
    api_version: kubevirt.io/v1
    kind: VirtualMachine
    name: "{{ vm_name }}"
    namespace: "{{ namespace }}"
    state: patched
    definition:
      metadata:
        annotations:
          cmdb.id: "{{ cmdb_result.json.id }}"
```

**Implementation Steps**:

1. **Document API requirements**: Endpoint, method, auth, payload format
2. **Implement authentication**: Bearer token, basic auth, OAuth, API key
3. **Add retry logic**: Use `retries`, `delay`, `until` for transient failures
4. **Handle errors**: Check status codes, parse error messages
5. **Add idempotency check**: GET before POST to check if resource exists
6. **Test failure scenarios**: Test 404, 401, 500 responses
7. **Store results**: Save API response IDs as VM annotations for tracking

**Common Pitfalls**:

- ❌ **No retries**: External APIs can be flaky - always add retries
- ❌ **Not checking status codes**: Always validate `status_code` is in expected range
- ❌ **Hardcoding credentials**: Use Ansible Vault or AAP credentials
- ❌ **Not testing error paths**: Test what happens when API returns errors

---

## Best Practices

### General Migration Principles

1. **Start with deny-all**: Begin restrictive and open up based on actual needs
2. **Use label taxonomy**: Design labels early - they're the foundation of Kubernetes policy
3. **Separate concerns**: Provisioning, networking, storage, security are separate playbooks
4. **Document gaps**: Be honest about what can't be migrated - compensating controls are valid
5. **Test incrementally**: Migrate one workflow at a time, test thoroughly
6. **Keep it simple**: Don't over-engineer - Kubernetes is simpler than vRealize by design

### Ansible Best Practices

1. **Use roles for reusability**: Common patterns (networking, storage) belong in roles
2. **Idempotency is critical**: All tasks should be safe to run multiple times
3. **Error handling**: Use `block`/`rescue` for graceful failures
4. **Variables over hardcoding**: Environment-specific values in group_vars
5. **Retries for external calls**: APIs, Kubernetes operations can be transient
6. **Meaningful names**: Task names should describe what and why, not how

### Security Considerations

1. **Default deny NetworkPolicy**: Start with deny-all, allow incrementally
2. **Namespace isolation**: Use namespaces as hard security boundaries
3. **RBAC for automation**: Service accounts with minimal permissions
4. **Secrets management**: Vault, Sealed Secrets, or AAP credentials
5. **Audit trails**: Log all provisioning, changes, approvals
6. **SecOps approval**: Security boundary changes need security team sign-off

### Testing Strategy

1. **Dev environment first**: Test all workflows in dev before staging/prod
2. **Synthetic traffic**: Generate realistic traffic patterns for testing
3. **Negative testing**: Test what happens when things fail (validation, API errors)
4. **Load testing**: Verify automation works under load
5. **Rollback plan**: Document how to rollback if migration fails
6. **Monitoring**: Prometheus metrics, alerts for automation failures

---

## Conclusion

Migration is a journey, not a destination. These patterns provide proven approaches, but every organization has unique requirements. The key is to:

- **Embrace the differences**: Kubernetes is not vRealize - that's a feature, not a bug
- **Start small**: Migrate simple workflows first, learn, then tackle complex ones
- **Iterate**: Continuous improvement based on operational feedback
- **Document everything**: Future you (and your team) will thank you

**Need help?** Consult the generated `intent/recommendations.md` file for workflow-specific guidance based on your actual vRealize/PowerCLI scripts.

---

*Generated by ops-translate - Expert-guided VMware to OpenShift migration*
