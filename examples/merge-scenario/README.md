# Multi-Source Merge Example

This example demonstrates how ops-translate merges **multiple automation sources** into a **single unified intent**.

## Scenario

Your organization has separate automation for different environments:

1. **`dev-provision.ps1`** - Quick, simple provisioning for development VMs
2. **`prod-provision.ps1`** - Governed provisioning for production VMs with strict requirements
3. **`approval.workflow.xml`** - vRealize approval workflow for production requests

Instead of translating each separately, you can **merge them** into one unified workflow that handles both dev and prod.

---

## The Source Files

### 1. Development Provisioning (`dev-provision.ps1`)

**Purpose**: Fast, lightweight provisioning for developers

**Key Characteristics**:
- Simple parameters: `VMName`, `NumCPU`, `MemoryGB`
- No approval required
- Lower resource limits (max 8 CPU, 32GB RAM)
- Auto-starts VMs
- Basic tagging

**Use Case**: Developers need quick VMs for testing/development

---

### 2. Production Provisioning (`prod-provision.ps1`)

**Purpose**: Governed provisioning for production workloads

**Key Characteristics**:
- Additional required parameters: `OwnerEmail`, `CostCenter`
- Stricter validation (min 2 CPU, max 16 CPU)
- Higher resource limits (up to 64GB RAM)
- **Does NOT auto-start** - requires approval
- Comprehensive tagging (owner, cost center, compliance)
- Enables HA and creates baseline snapshot

**Use Case**: Production deployments requiring accountability and governance

---

### 3. Approval Workflow (`approval.workflow.xml`)

**Purpose**: Automated approval routing for production requests

**Key Characteristics**:
- Checks environment (prod requires approval, dev auto-approves)
- Validates against quotas
- Routes to approvers: `ops-manager@example.com`, `infrastructure-lead@example.com`
- 24-hour approval timeout
- Email notifications to requester

**Use Case**: Ensuring production changes have proper oversight

---

## How to Merge These Sources

### Step 1: Initialize Workspace

```bash
ops-translate init merge-demo
cd merge-demo
```

### Step 2: Import All Sources

```bash
# Import development script
ops-translate import --source powercli --file ../examples/merge-scenario/dev-provision.ps1

# Import production script
ops-translate import --source powercli --file ../examples/merge-scenario/prod-provision.ps1

# Import approval workflow
ops-translate import --source vrealize --file ../examples/merge-scenario/approval.workflow.xml
```

**Result**: Three files copied to your workspace:
- `input/powercli/dev-provision.ps1`
- `input/powercli/prod-provision.ps1`
- `input/vrealize/approval.workflow.xml`

### Step 3: Extract Intent from Each Source

```bash
ops-translate intent extract
```

**Result**: Three intent files created:
- `intent/dev-provision.intent.yaml`
- `intent/prod-provision.intent.yaml`
- `intent/approval.intent.yaml`

### Step 4: Merge All Intents

```bash
ops-translate intent merge
```

**What happens during merge**:

1. **Inputs**: Union of all parameters from all sources
   - From dev: `vm_name`, `cpu`, `memory_gb`
   - From prod: `owner_email`, `cost_center`
   - **Merged**: All parameters available, constraints reconciled

2. **Governance**: Most restrictive policy wins
   - Dev has no approval requirement
   - Prod requires approval for `environment: prod`
   - **Merged**: Approval required for prod (safer)

3. **Compute**: Maximum values to satisfy all requirements
   - Dev: 2 CPU, 4GB RAM, 50GB disk
   - Prod: 4 CPU, 16GB RAM, 200GB disk
   - **Merged**: 4 CPU, 16GB RAM, 200GB disk (max of all)

4. **Profiles**: Union of all environment configs
   - Dev network: `dev-network`
   - Prod network: `prod-network`
   - **Merged**: Both environments supported with conditional profiles

5. **Day 2 Operations**: Union of all supported operations
   - Dev: `start`, `stop`
   - Prod: `start`, `stop`, `reconfigure`, `snapshot`
   - **Merged**: All operations available

**Result**: Single merged intent file: `intent/intent.yaml`

### Step 5: Review Merged Intent

```bash
cat intent/intent.yaml
```

Expected structure:

```yaml
schema_version: 1
sources:
  - type: powercli
    file: input/powercli/dev-provision.ps1
  - type: powercli
    file: input/powercli/prod-provision.ps1
  - type: vrealize
    file: input/vrealize/approval.workflow.xml

intent:
  workflow_name: provision_vm  # Unified name
  workload_type: virtual_machine

  inputs:
    vm_name: { type: string, required: true }
    owner_email: { type: string, required: true }  # From prod
    cost_center: { type: string, required: true }  # From prod
    cpu: { type: integer, min: 1, max: 16 }        # Merged constraints
    memory_gb: { type: integer, min: 2, max: 64 }  # Merged constraints

  governance:
    approval:
      required_when: { environment: prod }  # From vRealize
      approvers:
        - ops-manager@example.com
        - infrastructure-lead@example.com

  compute:
    cpu_cores: 4      # max(2, 4) from sources
    memory_gb: 16     # max(4, 16) from sources
    disk_gb: 200      # max(50, 200) from sources

  profiles:
    network:
      when: { environment: dev }
      value: dev-network
    network:
      when: { environment: prod }
      value: prod-network

  metadata:
    tags:
      - key: environment
        value_from: environment
      - key: owner
        value_from: owner_email
      - key: cost-center
        value_from: cost_center
      - key: managed-by
        value: ops-translate

  day2_operations:
    supported: [start, stop, reconfigure, snapshot]  # Union
```

---

## What You Get

After merging, you have **one unified workflow** that:

✅ **Handles both dev and prod** via environment profiles
✅ **Requires approval only for prod** via governance rules
✅ **Supports all operations** from both sources
✅ **Includes all metadata** for tracking and compliance
✅ **Uses maximum resources** to satisfy strictest requirements

### Step 6: Generate Unified Artifacts

```bash
# Generate for dev environment
ops-translate generate --profile lab --format yaml

# Generate for prod environment
ops-translate generate --profile prod --format yaml
```

**Result**: Single Ansible playbook and KubeVirt manifest that work for both dev and prod, with environment-specific behavior controlled by input parameters.

---

## Key Insights

### Why Merge Instead of Separate Workflows?

**Without merging** (3 separate workflows):
- ❌ Duplicate code for common logic
- ❌ Inconsistent behavior between environments
- ❌ Hard to maintain (change in 3 places)
- ❌ No unified governance view

**With merging** (1 unified workflow):
- ✅ Single source of truth
- ✅ Consistent logic across environments
- ✅ Easy to maintain (change once)
- ✅ Unified governance and auditing
- ✅ Environment-specific behavior via profiles

### Merge Strategies Applied

| Element | Strategy | Example |
|---------|----------|---------|
| **Inputs** | Union + reconcile | Combined all params, merged min/max |
| **Governance** | Most restrictive | Prod approval requirement preserved |
| **Compute** | Maximum values | Highest CPU/RAM from any source |
| **Profiles** | Union | Both dev and prod network configs |
| **Tags** | Union | All tags from all sources combined |
| **Day 2 Ops** | Union | All operations from any source |

---

## Handling Conflicts

If sources have **incompatible** requirements, conflicts are reported:

```bash
# After merge, check for conflicts
cat intent/conflicts.md
```

**Example conflicts**:
- Type mismatches (one source says `cpu` is string, another says integer)
- Incompatible network naming (can't reconcile different conventions)
- Conflicting resource limits

**Resolution**:
1. Review conflicts in `intent/conflicts.md`
2. Edit source scripts to align
3. Re-extract and re-merge
4. OR: Use `--force` to merge anyway with warnings

---

## Try It Yourself

```bash
# Full workflow in one go:
ops-translate init merge-demo && cd merge-demo
ops-translate import --source powercli --file ../examples/merge-scenario/dev-provision.ps1
ops-translate import --source powercli --file ../examples/merge-scenario/prod-provision.ps1
ops-translate import --source vrealize --file ../examples/merge-scenario/approval.workflow.xml
ops-translate intent extract
ops-translate intent merge
cat intent/intent.yaml  # Review merged result
ops-translate generate --profile lab
```

---

## Learn More

- **[ARCHITECTURE.md](../../docs/ARCHITECTURE.md#core-concepts)**: Conceptual explanation of intent and merging
- **[INTENT_SCHEMA.md](../../docs/INTENT_SCHEMA.md)**: Complete schema reference
- **[TUTORIAL.md](../../docs/TUTORIAL.md)**: Step-by-step walkthrough with more examples
