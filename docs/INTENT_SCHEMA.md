# Intent Schema Reference

Complete reference documentation for the ops-translate Operational Intent Schema (v1).

## Table of Contents

1. [Overview](#overview)
2. [Schema Structure](#schema-structure)
3. [Field Reference](#field-reference)
4. [Examples](#examples)
5. [Common Mistakes](#common-mistakes)
6. [Validation Tips](#validation-tips)

## Overview

The intent schema is a normalized, platform-agnostic representation of operational workflows. It captures **what** should happen (intent) rather than **how** it happens (implementation).

### Purpose

- **Normalization**: Convert various automation formats (PowerCLI, vRealize) into a common structure
- **Validation**: Ensure extracted intent is complete and correct
- **Portability**: Enable generation to multiple target formats (Ansible, KubeVirt, etc.)
- **Transparency**: Make operational logic explicit and reviewable

### Schema Version

Current version: **1**

All intent files must include `schema_version: 1` at the root level.

---

## Schema Structure

```yaml
schema_version: 1              # Required: Always 1
sources: []                    # Optional: Source file metadata
intent:                        # Required: Core intent data
  workflow_name: ...           # Required: Workflow identifier
  workload_type: ...           # Required: Type of workload
  inputs: {}                   # Optional: Input parameters
  governance: {}               # Optional: Approval/policy rules
  compute: {}                  # Optional: Resource specifications
  profiles: {}                 # Optional: Environment profiles
  metadata: {}                 # Optional: Tags and labels
  day2_operations: {}          # Optional: Lifecycle operations
assumptions: []                # Optional: Documented inferences
```

---

## Field Reference

### schema_version

**Type**: `integer`
**Required**: Yes
**Value**: Must be `1`

**Description**: Version number of the intent schema. Used for compatibility checks.

**Example**:
```yaml
schema_version: 1
```

**Common Mistakes**:
- ❌ Using a string: `schema_version: "1"` (must be integer)
- ❌ Omitting the field entirely
- ✅ Correct: `schema_version: 1`

---

### sources

**Type**: `array of objects`
**Required**: No
**Description**: Metadata about source files that contributed to this intent.

**Structure**:
```yaml
sources:
  - type: powercli | vrealize       # Required: Source type
    file: string                    # Required: Path to source file
    sha256: string                  # Optional: File hash
```

**Example**:
```yaml
sources:
  - type: powercli
    file: input/powercli/provision-vm.ps1
    sha256: a1b2c3d4...
  - type: vrealize
    file: input/vrealize/approval-workflow.xml
```

---

### intent

**Type**: `object`
**Required**: Yes
**Description**: The core intent section containing all operational specifications.

---

#### intent.workflow_name

**Type**: `string`
**Required**: Yes
**Pattern**: `^[a-z][a-z0-9_]*$` (snake_case)

**Description**: Unique identifier for the workflow. Used to generate artifact names.

**Examples**:
- ✅ `provision_vm`
- ✅ `deploy_dev_environment`
- ✅ `backup_database`
- ❌ `Provision-VM` (not snake_case)
- ❌ `Provision VM` (contains spaces)
- ❌ `1st_workflow` (doesn't start with letter)

**Conversion Guide**:
| Original | Correct |
|----------|---------|
| `Provision-VM` | `provision_vm` |
| `Deploy Dev Environment` | `deploy_dev_environment` |
| `BackupDatabase` | `backup_database` |

---

#### intent.workload_type

**Type**: `string`
**Required**: Yes
**Allowed Values**: `virtual_machine`, `container`, `mixed`

**Description**: Type of workload being provisioned or managed.

**Values**:
- `virtual_machine`: VMware VMs → KubeVirt VirtualMachines
- `container`: Container workloads
- `mixed`: Workflows that provision both VMs and containers

**Example**:
```yaml
intent:
  workflow_name: provision_vm
  workload_type: virtual_machine
```

---

#### intent.inputs

**Type**: `object`
**Required**: No
**Description**: Input parameters for the workflow. Keys are parameter names in snake_case.

**Parameter Structure**:
```yaml
inputs:
  param_name:                  # Parameter name (snake_case)
    type: string | integer | boolean | enum | array
    required: true | false     # Is this parameter required?
    default: value             # Default value (optional)
    description: string        # Human-readable description (optional)

    # For integer types:
    min: integer               # Minimum value (optional)
    max: integer               # Maximum value (optional)

    # For enum types:
    values: [option1, option2] # List of allowed values (required for enum)
```

**Example**:
```yaml
inputs:
  vm_name:
    type: string
    required: true
    description: Name of the virtual machine

  environment:
    type: enum
    values: [dev, staging, prod]
    required: true
    default: dev
    description: Target environment

  cpu_count:
    type: integer
    required: false
    default: 2
    min: 1
    max: 32
    description: Number of CPU cores

  enable_monitoring:
    type: boolean
    required: false
    default: false
    description: Enable monitoring integration
```

**Common Mistakes**:
- ❌ `required: yes` (must be boolean: `true` or `false`)
- ❌ Enum without `values` array
- ❌ Integer with string default: `default: "4"` (must be `default: 4`)

---

#### intent.governance

**Type**: `object`
**Required**: No
**Description**: Governance policies, approval requirements, and constraints.

**Structure**:
```yaml
governance:
  approval:
    required_when: {condition}  # Conditions that require approval
    approvers: [list]           # List of approver emails/groups

  quotas:
    max_instances: integer      # Maximum instances allowed
    max_cpu: integer            # Maximum total CPUs
    max_memory_gb: integer      # Maximum total memory
```

**Example**:
```yaml
governance:
  approval:
    required_when:
      environment: prod          # Require approval for prod
    approvers:
      - ops-team@example.com
      - manager@example.com

  quotas:
    max_instances: 10
    max_cpu: 64
    max_memory_gb: 256
```

---

#### intent.compute

**Type**: `object`
**Required**: No
**Description**: Compute resource specifications (CPU, memory, storage).

**Structure**:
```yaml
compute:
  cpu_count: integer            # Number of CPUs
  memory_gb: integer            # Memory in GB
  disk_gb: integer              # Disk size in GB
```

**Example**:
```yaml
compute:
  cpu_count: 4
  memory_gb: 16
  disk_gb: 100
```

---

#### intent.profiles

**Type**: `object`
**Required**: No
**Description**: Environment-specific configuration profiles (dev, staging, prod).

**Structure**:
```yaml
profiles:
  resource_name:               # Network, storage, etc.
    when: {condition}          # When to use this value
    value: string              # Value to use
  resource_name_else: string   # Fallback value
```

**Example**:
```yaml
profiles:
  network:
    when: { environment: prod }
    value: prod-network
  network_else: dev-network

  storage:
    when: { environment: prod }
    value: ceph-rbd
  storage_else: nfs
```

**Notes**:
- `when` conditions are checked in order
- `_else` suffix denotes the fallback value
- Conditions can reference input parameters

---

#### intent.metadata

**Type**: `object`
**Required**: No
**Description**: Tags, labels, and custom metadata to apply to resources.

**Structure**:
```yaml
metadata:
  tags:
    - key: string              # Tag key
      value: string            # Static value
      # OR
      value_from: param_name   # Dynamic value from input parameter

  labels:
    key: value                 # Static labels

  annotations:
    key: value                 # Kubernetes annotations
```

**Example**:
```yaml
metadata:
  tags:
    - key: environment
      value_from: environment   # Use value from input parameter

    - key: cost-center
      value_from: cost_center

    - key: managed-by
      value: ops-translate     # Static value

  labels:
    team: platform
    project: migration

  annotations:
    contact: ops-team@example.com
```

---

#### intent.day2_operations

**Type**: `object`
**Required**: No
**Description**: Supported Day 2 lifecycle operations beyond initial provisioning.

**Structure**:
```yaml
day2_operations:
  supported: [operation1, operation2, ...]
```

**Common Operations**:
- `start`: Start/power on the workload
- `stop`: Stop/power off the workload
- `restart`: Restart the workload
- `reconfigure`: Modify resource allocation
- `backup`: Create backup/snapshot
- `restore`: Restore from backup
- `scale`: Scale resources up/down
- `migrate`: Move to different host/cluster
- `delete`: Remove the workload

**Example**:
```yaml
day2_operations:
  supported:
    - start
    - stop
    - restart
    - reconfigure
    - backup
```

---

### assumptions

**Type**: `array of strings`
**Required**: No
**Description**: Documented assumptions made during intent extraction.

**Purpose**: Transparency and auditability. Lists what was inferred vs. explicit.

**Example**:
```yaml
assumptions:
  - Inferred day2_operations from New-VM command (start/stop are standard)
  - No explicit approval workflow detected in source
  - CPU and memory limits set based on common VMware constraints
  - Network profile derived from environment-based branching logic
```

---

## Examples

### Minimal Valid Intent

```yaml
schema_version: 1
intent:
  workflow_name: minimal_example
  workload_type: virtual_machine
```

### Simple VM Provisioning

```yaml
schema_version: 1
sources:
  - type: powercli
    file: input/powercli/simple-vm.ps1

intent:
  workflow_name: provision_simple_vm
  workload_type: virtual_machine

  inputs:
    vm_name:
      type: string
      required: true
      description: Name for the new VM

    cpu_count:
      type: integer
      required: false
      default: 2
      min: 1
      max: 16

    memory_gb:
      type: integer
      required: false
      default: 4
      min: 1
      max: 64

  compute:
    cpu_count: 2
    memory_gb: 4
    disk_gb: 50

  day2_operations:
    supported: [start, stop]
```

### Environment-Aware Workflow

```yaml
schema_version: 1
sources:
  - type: powercli
    file: input/powercli/env-aware.ps1

intent:
  workflow_name: provision_vm_with_profiles
  workload_type: virtual_machine

  inputs:
    vm_name:
      type: string
      required: true

    environment:
      type: enum
      values: [dev, staging, prod]
      required: true
      default: dev

    owner_email:
      type: string
      required: true

  governance:
    approval:
      required_when:
        environment: prod
      approvers:
        - ops-manager@example.com

  profiles:
    network:
      when: { environment: prod }
      value: prod-network
    network:
      when: { environment: staging }
      value: staging-network
    network_else: dev-network

    storage:
      when: { environment: prod }
      value: ceph-rbd
    storage_else: nfs

  metadata:
    tags:
      - key: environment
        value_from: environment
      - key: owner
        value_from: owner_email
      - key: managed-by
        value: ops-translate

  day2_operations:
    supported: [start, stop, restart, backup]

assumptions:
  - Approval requirement inferred from environment checks in source
  - Network and storage profiles derived from conditional logic
  - Day 2 operations based on standard VM lifecycle
```

---

## Common Mistakes

### 1. Wrong Type for schema_version

❌ **Incorrect**:
```yaml
schema_version: "1"    # String instead of integer
```

✅ **Correct**:
```yaml
schema_version: 1      # Integer
```

### 2. workflow_name Not in snake_case

❌ **Incorrect**:
```yaml
workflow_name: "Provision-VM"      # Kebab-case
workflow_name: "Provision VM"      # Spaces
workflow_name: "ProvisionVM"       # CamelCase
```

✅ **Correct**:
```yaml
workflow_name: provision_vm         # snake_case
```

### 3. required Field as String

❌ **Incorrect**:
```yaml
inputs:
  vm_name:
    type: string
    required: "true"    # String instead of boolean
```

✅ **Correct**:
```yaml
inputs:
  vm_name:
    type: string
    required: true      # Boolean
```

### 4. enum Type Without values

❌ **Incorrect**:
```yaml
inputs:
  environment:
    type: enum
    required: true
    # Missing: values array!
```

✅ **Correct**:
```yaml
inputs:
  environment:
    type: enum
    values: [dev, prod]  # Required for enum type
    required: true
```

### 5. Integer with String Default

❌ **Incorrect**:
```yaml
inputs:
  cpu_count:
    type: integer
    default: "4"        # String instead of integer
```

✅ **Correct**:
```yaml
inputs:
  cpu_count:
    type: integer
    default: 4          # Integer
```

### 6. Missing Required Fields

❌ **Incorrect**:
```yaml
schema_version: 1
intent:
  # Missing workflow_name!
  workload_type: virtual_machine
```

✅ **Correct**:
```yaml
schema_version: 1
intent:
  workflow_name: my_workflow
  workload_type: virtual_machine
```

---

## Validation Tips

### Running Validation

```bash
# Validate during extraction
ops-translate intent extract

# Validate merged intent
ops-translate intent merge

# Run comprehensive validation
ops-translate dry-run
```

### Reading Validation Errors

Validation errors follow this format:

```
Validation error at 'intent.workflow_name': 'Provision-VM' does not match '^[a-z][a-z0-9_]*$'
  Expected pattern: ^[a-z][a-z0-9_]*$
  Got: Provision-VM
  Hint: Use snake_case naming (lowercase with underscores)
  Example: Provision-VM → provision_vm
```

Parts of the error:
1. **Location**: `intent.workflow_name` - where the error is
2. **Message**: What's wrong
3. **Expected**: What was expected
4. **Got**: What was actually found
5. **Hint**: How to fix it
6. **Example**: Concrete fix

### Quick Fix Checklist

- [ ] `schema_version` is integer `1` (not string `"1"`)
- [ ] `workflow_name` is snake_case (lowercase_with_underscores)
- [ ] `workload_type` is one of: `virtual_machine`, `container`, `mixed`
- [ ] All `required` fields are boolean (`true`/`false`, not `yes`/`no`)
- [ ] All `enum` type inputs have `values` array
- [ ] Integer fields have integer values (not strings)
- [ ] Input parameter names are valid identifiers (no spaces, special chars)

---

## Schema File Location

The authoritative JSON schema is located at:
```
schema/intent.schema.json
```

For programmatic validation:
```python
from ops_translate.intent.validate import validate_intent
from pathlib import Path

is_valid, errors = validate_intent(Path("intent/my-intent.yaml"))
if not is_valid:
    for error in errors:
        print(error)
```

---

## Next Steps

- **See examples**: Check `examples/` directory for sample intent files
- **Read architecture**: See `docs/ARCHITECTURE.md` for system design
- **Tutorial**: Follow `docs/TUTORIAL.md` for step-by-step guide
- **API reference**: See `docs/API_REFERENCE.md` for programmatic usage

---

## Support

- **Schema issues**: https://github.com/tsanders-rh/ops-translate/issues
- **Documentation**: https://github.com/tsanders-rh/ops-translate/tree/main/docs
- **Examples**: https://github.com/tsanders-rh/ops-translate/tree/main/examples
