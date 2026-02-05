# ops-translate Tutorial

Step-by-step tutorial for migrating VMware automation to OpenShift Virtualization using ops-translate.

## Table of Contents

1. [Tutorial Overview](#tutorial-overview)
2. [Prerequisites](#prerequisites)
3. [Scenario: Dev/Prod VM Provisioning](#scenario-devprod-vm-provisioning)
4. [Part 1: Setup and Import](#part-1-setup-and-import)
5. [Part 2: Analysis and Summarization](#part-2-analysis-and-summarization)
6. [Part 3: Intent Extraction](#part-3-intent-extraction)
7. [Part 4: Multi-Source Merging](#part-4-multi-source-merging)
8. [Part 5: Artifact Generation](#part-5-artifact-generation)
9. [Part 6: Testing and Deployment](#part-6-testing-and-deployment)
10. [Advanced Tutorial: Governance Workflow](#advanced-tutorial-governance-workflow)

## Tutorial Overview

### What You'll Learn

In this tutorial, you'll migrate a complete VMware automation workflow to OpenShift:

- Import PowerCLI scripts and vRealize workflows
- Extract operational intent using AI
- Merge multiple automation sources
- Generate Ansible playbooks and KubeVirt manifests
- Validate and test the output

### Time Required

- Basic tutorial: 30-45 minutes
- Advanced tutorial: 60-90 minutes

### What You'll Build

By the end, you'll have:
- A complete OpenShift VM provisioning workflow
- Ansible playbooks with environment awareness
- KubeVirt manifests for dev and prod
- Validation and testing setup

## Prerequisites

### Required Software

```bash
# Python 3.10+
python --version  # Should be 3.10 or higher

# ops-translate
pip install ops-translate

# Optional: OpenShift CLI (for testing)
oc version
```

### API Keys (Choose One)

**Option 1: Anthropic Claude** (Recommended)
```bash
# Get key from https://console.anthropic.com
export OPS_TRANSLATE_LLM_API_KEY="sk-ant-your-key"
```

**Option 2: OpenAI**
```bash
# Get key from https://platform.openai.com
export OPS_TRANSLATE_LLM_API_KEY="sk-your-key"
```

**Option 3: No API Key** (Mock mode)
```bash
# No setup needed - will use mock provider
# Good for learning the workflow
```

### Verify Installation

```bash
ops-translate --help
```

You should see the CLI help text.

## Scenario: Dev/Prod VM Provisioning

### Business Context

Your organization uses VMware for VM provisioning with:
- **PowerCLI scripts** for basic provisioning
- **vRealize workflows** for approval and governance
- **Environment branching** (dev uses lower resources than prod)
- **Tag-based tracking** for cost allocation

You need to migrate to OpenShift Virtualization while preserving all operational patterns.

### Source Automation

**PowerCLI Script** (`provision-vm.ps1`):
- Takes VM name and environment (dev/prod)
- Provisions VMs with environment-specific resources
- Applies tags for tracking

**vRealize Workflow** (`approval-workflow.xml`):
- Requires approval for prod VMs
- Validates against quotas
- Sends notifications

### Target Output

- **KubeVirt manifests** for VM definitions
- **Ansible playbooks** with approval hooks
- **Environment-aware** resource allocation
- **Quota enforcement** in Ansible

## Part 1: Setup and Import

### Step 1: Create Workspace

Create a new workspace for the migration:

```bash
ops-translate init vmware-migration
cd vmware-migration
```

**What happened?**
```
vmware-migration/
├── ops-translate.yaml   # Configuration file
├── input/              # For source files
│   ├── powercli/
│   └── vrealize/
├── intent/             # Extracted intent (created later)
├── mapping/            # Mappings (created later)
└── output/             # Generated artifacts (created later)
```

### Step 2: Review Configuration

Open and review `ops-translate.yaml`:

```bash
cat ops-translate.yaml
```

You'll see:
```yaml
llm:
  provider: anthropic  # or openai, mock
  model: claude-sonnet-4-5
  api_key_env: OPS_TRANSLATE_LLM_API_KEY

profiles:
  lab:
    default_namespace: virt-lab
    default_network: lab-network
    default_storage_class: nfs

  prod:
    default_namespace: virt-prod
    default_network: prod-network
    default_storage_class: ceph-rbd
```

**Configure for your environment**:
```bash
# Edit configuration
$EDITOR ops-translate.yaml

# Set API key
export OPS_TRANSLATE_LLM_API_KEY="your-key-here"
```

### Step 3: Get Example Files

We'll use example files from the ops-translate repository:

```bash
# Clone the repository if you haven't
git clone https://github.com/tsanders-rh/ops-translate
cd ops-translate

# Copy example files
cp examples/powercli/environment-aware.ps1 ~/vmware-migration/
cp examples/vrealize/with-approval.workflow.xml ~/vmware-migration/

cd ~/vmware-migration
```

Alternatively, create your own files:

**provision-vm.ps1**:
```powershell
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "prod")]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [string]$OwnerEmail
)

# Environment-specific resource allocation
if ($Environment -eq "prod") {
    $CPUCount = 4
    $MemoryGB = 16
    $Network = "prod-network"
    $Storage = "storage-gold"
} else {
    $CPUCount = 2
    $MemoryGB = 8
    $Network = "dev-network"
    $Storage = "storage-standard"
}

# Provision VM
New-VM -Name $VMName `
    -NumCpu $CPUCount `
    -MemoryGB $MemoryGB `
    -NetworkName $Network `
    -Datastore $Storage

# Apply tags
New-TagAssignment -Entity $VMName -Tag "env:$Environment"
New-TagAssignment -Entity $VMName -Tag "owner:$OwnerEmail"
```

### Step 4: Import Files

Import the PowerCLI script:

```bash
ops-translate import --source powercli --file provision-vm.ps1
```

**Output**:
```
✓ Imported provision-vm.ps1 to input/powercli/
  SHA-256: abc123...
```

Import the vRealize workflow:

```bash
ops-translate import --source vrealize --file approval-workflow.xml
```

**Output**:
```
✓ Imported approval-workflow.xml to input/vrealize/
  SHA-256: def456...
```

### Step 5: Verify Imports

Check that files were imported:

```bash
ls -R input/
```

**Output**:
```
input/powercli:
provision-vm.ps1

input/vrealize:
approval-workflow.xml
```

**Checkpoint**: You now have a workspace with imported source files.

## Part 2: Analysis and Summarization

### Step 6: Run Summarize

Analyze the imported files without AI:

```bash
ops-translate summarize
```

**Output**:
```
Analyzing PowerCLI scripts...
Analyzing vRealize workflows...

✓ Summary written to intent/summary.md
```

### Step 7: Review Summary

Read the generated summary:

```bash
cat intent/summary.md
```

**Output Example**:
```markdown
# Automation Summary

## PowerCLI Scripts

### File: provision-vm.ps1

**Parameters**:
- Environment (string, required) - ValidateSet: dev, prod
- VMName (string, required)
- OwnerEmail (string, required)

**Environment Branching**: ✓ Detected
- Uses ValidateSet for environment selection
- Different CPU/memory for dev vs prod
- Different network selection
- Different storage tier

**Tagging/Metadata**: ✓ Detected
- Tags VMs with environment
- Tags VMs with owner email

**Network/Storage Selection**: ✓ Detected
- Environment-specific network: prod-network vs dev-network
- Environment-specific storage: storage-gold vs storage-standard

**Compute Resources**:
- Prod: 4 vCPU, 16 GB RAM
- Dev: 2 vCPU, 8 GB RAM

## vRealize Workflows

### File: approval-workflow.xml

**Inputs**:
- vmName (string)
- environment (string)
- requester (string)

**Approval Requirements**: ✓ Detected
- Approval required for prod environment
- Approver: ops-team
- Timeout: 168 hours (7 days)

**Governance**: ✓ Detected
- Quota validation before provisioning
- Max 16 vCPU, 128 GB RAM per VM

**Environment Branching**: ✓ Detected
- Conditional approval based on environment
```

**Analysis**: The summary shows:
- Both sources handle dev/prod environments
- vRealize adds approval workflow
- Resource limits are defined
- Tagging for compliance

## Part 3: Intent Extraction

### Step 8: Extract Intent with AI

Extract operational intent from both sources:

```bash
ops-translate intent extract
```

**Output**:
```
Extracting intent from PowerCLI...
  ✓ provision-vm.ps1 → intent/powercli.intent.yaml

Extracting intent from vRealize...
  ✓ approval-workflow.xml → intent/vrealize.intent.yaml

✓ Assumptions written to intent/assumptions.md
```

**What happened?**
- AI read each source file
- Extracted structured operational intent
- Logged assumptions it made

### Step 9: Review PowerCLI Intent

```bash
cat intent/powercli.intent.yaml
```

**Output**:
```yaml
schema_version: 1
type: powercli
workflow_name: provision_environment_aware_vm

inputs:
  - name: environment
    type: string
    required: true
    allowed_values:
      - dev
      - prod
    description: Target environment (dev or prod)

  - name: vm_name
    type: string
    required: true
    description: Name of the VM to create

  - name: owner_email
    type: string
    required: true
    description: Email of VM owner for cost allocation

compute:
  cpu_count: 2  # Default for dev
  memory_gb: 8  # Default for dev

environment_branching:
  enabled: true
  conditions:
    - if: environment == "prod"
      then:
        compute:
          cpu_count: 4
          memory_gb: 16
        networking:
          network: prod-network
        storage:
          storage_class: storage-gold
    - if: environment == "dev"
      then:
        compute:
          cpu_count: 2
          memory_gb: 8
        networking:
          network: dev-network
        storage:
          storage_class: storage-standard

metadata:
  tags:
    - key: env
      value: "{{ environment }}"
    - key: owner
      value: "{{ owner_email }}"

assumptions:
  - description: Inferred default compute resources from dev path
    confidence: high
  - description: Network names extracted from variable assignments
    confidence: high
  - description: Storage class names inferred from datastore names
    confidence: medium
```

### Step 10: Review vRealize Intent

```bash
cat intent/vrealize.intent.yaml
```

**Output**:
```yaml
schema_version: 1
type: vrealize
workflow_name: vm_provision_with_approval

inputs:
  - name: vm_name
    type: string
    required: true
  - name: environment
    type: string
    required: true
  - name: requester
    type: string
    required: true

governance:
  approval_required: true
  approval_conditions:
    - if: environment == "prod"
      then:
        approval_required: true
        approvers:
          - ops-team
        approval_timeout_hours: 168  # 7 days

  quotas:
    max_cpu: 16
    max_memory_gb: 128
    enforcement: pre_provision

validation:
  pre_checks:
    - validate_quota
    - check_naming_convention
    - verify_network_availability

assumptions:
  - description: Approval timeout extracted from workflow timer element
    confidence: high
  - description: Quota values extracted from validation scriptlet
    confidence: high
  - description: Approval only required for prod based on decision node
    confidence: high
```

### Step 11: Review Assumptions

```bash
cat intent/assumptions.md
```

**Output**:
```markdown
# AI Assumptions Log

## PowerCLI: provision-vm.ps1

### Extracted Intent

**Inputs**:
- Preserved all parameter definitions
- Detected ValidateSet constraint for environment
- Identified required vs optional parameters

**Compute Resources**:
- Default values (2 CPU, 8GB) inferred from dev branch
- Prod values (4 CPU, 16GB) explicitly from prod branch
- Confidence: HIGH - directly from if/else logic

**Networking**:
- Network names extracted from variable assignments
- Confidence: HIGH - explicit variable values

**Storage**:
- Mapped datastore names to storage classes
- Assumed "storage-gold" → "gold" storage class
- Assumed "storage-standard" → "standard" storage class
- Confidence: MEDIUM - naming convention inference

**Tagging**:
- Detected New-TagAssignment cmdlets
- Extracted tag key:value patterns
- Confidence: HIGH - explicit cmdlet calls

### Assumptions Made

1. **Default Environment**: Assumed "dev" as default since it's first in ValidateSet
2. **Storage Mapping**: Inferred OpenShift storage class names from VMware datastore names
3. **Network Type**: Assumed bridge networking (no explicit type in script)

## vRealize: approval-workflow.xml

### Extracted Intent

**Approval Workflow**:
- Detected decision node for environment check
- Approval only required when environment == "prod"
- Approver group "ops-team" from workflow metadata
- Timeout 168 hours from timer element
- Confidence: HIGH - explicit workflow structure

**Quota Enforcement**:
- Max 16 CPU, 128GB RAM from validation scriptlet
- Enforcement happens before provisioning (pre_provision)
- Confidence: HIGH - explicit validation code

### Assumptions Made

1. **Notification**: Assumed email notification on approval (standard vRO pattern)
2. **Timeout Behavior**: Assumed auto-reject on timeout (not explicit in workflow)
3. **Retry Logic**: No retry logic detected, assumed single-attempt provisioning
```

**Analysis**: The AI assumptions are well-documented and mostly high confidence.

### Step 12: Edit Intent (Optional)

If you notice any errors, edit the intent:

```bash
ops-translate intent edit --file intent/powercli.intent.yaml
```

Make corrections, save, and exit.

## Part 4: Multi-Source Merging

### Step 13: Merge Intents

Combine PowerCLI and vRealize intents:

```bash
ops-translate intent merge
```

**Possible outcomes**:

**Scenario A: No Conflicts**
```
Merging intents...
  ✓ Merged compute resources (using maximum values)
  ✓ Merged inputs (union of all inputs)
  ✓ Merged governance policies
  ✓ Merged environment branching

✓ Merged intent written to intent/intent.yaml
```

**Scenario B: Conflicts Detected**
```
Merging intents...
  ✓ Merged compute resources
  ⚠ Conflict detected: Network naming differs
  ⚠ Conflict detected: Approval timeout mismatch

✗ Conflicts detected during merge
  See intent/conflicts.md for details
  Use --force to merge anyway
```

### Step 14: Review Merged Intent

```bash
cat intent/intent.yaml
```

**Output**:
```yaml
schema_version: 1
workflow_name: provision_vm_unified
type: merged

inputs:
  # Union of all unique inputs
  - name: environment
    type: string
    required: true
    allowed_values: [dev, prod]
  - name: vm_name
    type: string
    required: true
  - name: owner_email
    type: string
    required: true
  - name: requester
    type: string
    required: true

compute:
  # Maximum values across sources
  cpu_count: 4
  memory_gb: 16

environment_branching:
  enabled: true
  conditions:
    - if: environment == "prod"
      then:
        compute:
          cpu_count: 4
          memory_gb: 16
        networking:
          network: prod-network
        storage:
          storage_class: gold
        governance:
          approval_required: true
          approvers: [ops-team]
          approval_timeout_hours: 168

    - if: environment == "dev"
      then:
        compute:
          cpu_count: 2
          memory_gb: 8
        networking:
          network: dev-network
        storage:
          storage_class: standard
        governance:
          approval_required: false

governance:
  quotas:
    max_cpu: 16
    max_memory_gb: 128
  validation:
    pre_checks:
      - validate_quota
      - check_naming_convention

metadata:
  tags:
    - key: env
      value: "{{ environment }}"
    - key: owner
      value: "{{ owner_email }}"
    - key: requester
      value: "{{ requester }}"
```

**Analysis**: The merge combined:
- All inputs from both sources
- Maximum compute values (4 CPU, 16GB)
- Governance from vRealize
- Environment branching from PowerCLI
- Tagging from both sources

### Step 15: Handle Conflicts (If Any)

If conflicts were detected:

```bash
cat intent/conflicts.md
```

**Example conflicts**:
```markdown
# Intent Merge Conflicts

## 1. Network Naming Convention

**PowerCLI**: Uses "prod-network", "dev-network"
**vRealize**: Uses "production-net", "development-net"

**Impact**: Generated manifests will have inconsistent network references

**Recommendation**: Standardize on one naming convention
- Option A: Use PowerCLI names (shorter)
- Option B: Use vRealize names (more descriptive)

**Resolution**: Edit `intent/powercli.intent.yaml` or `intent/vrealize.intent.yaml`

## 2. Approval Timeout

**PowerCLI**: No timeout specified
**vRealize**: 168 hours (7 days)

**Impact**: Unclear timeout behavior

**Recommendation**: Use vRealize timeout (7 days) as it's explicit

**Resolution**: Already resolved in favor of vRealize (explicit wins)
```

**Resolve conflicts**:
```bash
# Edit source intents to fix issues
ops-translate intent edit --file intent/powercli.intent.yaml
# Fix network names to match vRealize

# Re-merge
ops-translate intent merge

# Or force merge if conflicts are acceptable
ops-translate intent merge --force
```

## Part 5: Artifact Generation

### Step 16: Generate for Lab

Generate Ansible and KubeVirt artifacts for lab environment:

```bash
ops-translate generate --profile lab
```

**Output**:
```
Generating artifacts for profile: lab

Generating KubeVirt manifest...
  ✓ output/kubevirt/vm.yaml

Generating Ansible playbook...
  ✓ output/ansible/site.yml
  ✓ output/ansible/roles/provision_vm/tasks/main.yml
  ✓ output/ansible/roles/provision_vm/defaults/main.yml

Generating README...
  ✓ output/README.md

✓ Generation complete
```

### Step 17: Review KubeVirt Manifest

```bash
cat output/kubevirt/vm.yaml
```

**Output**:
```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: "{{ vm_name }}"
  namespace: virt-lab
  labels:
    app: provision-vm
    env: "{{ environment }}"
    owner: "{{ owner_email }}"
spec:
  running: false
  template:
    metadata:
      labels:
        app: provision-vm
        env: "{{ environment }}"
    spec:
      domain:
        cpu:
          cores: "{{ cpu_count }}"
        resources:
          requests:
            memory: "{{ memory_gb }}Gi"
        devices:
          disks:
            - name: rootdisk
              disk:
                bus: virtio
          interfaces:
            - name: default
              masquerade: {}
      networks:
        - name: default
          pod: {}
      volumes:
        - name: rootdisk
          dataVolume:
            name: "{{ vm_name }}-rootdisk"
---
apiVersion: cdi.kubevirt.io/v1beta1
kind: DataVolume
metadata:
  name: "{{ vm_name }}-rootdisk"
  namespace: virt-lab
spec:
  source:
    pvc:
      namespace: openshift-virtualization-os-images
      name: rhel9
  storage:
    resources:
      requests:
        storage: 30Gi
    storageClassName: nfs
```

**Key Points**:
- Uses lab profile (namespace: virt-lab, storage: nfs)
- Includes Jinja2 variables for Ansible
- Creates both VM and DataVolume
- Preserves tagging as labels

### Step 18: Review Ansible Playbook

```bash
cat output/ansible/site.yml
```

**Output**:
```yaml
---
- name: Provision VM with environment awareness
  hosts: localhost
  gather_facts: false
  vars_prompt:
    - name: environment
      prompt: "Environment (dev or prod)"
      private: false

    - name: vm_name
      prompt: "VM Name"
      private: false

    - name: owner_email
      prompt: "Owner Email"
      private: false

    - name: requester
      prompt: "Requester Email"
      private: false

  tasks:
    - name: Validate environment value
      assert:
        that:
          - environment in ['dev', 'prod']
        fail_msg: "Environment must be 'dev' or 'prod'"

    - name: Set environment-specific variables
      set_fact:
        cpu_count: "{{ '4' if environment == 'prod' else '2' }}"
        memory_gb: "{{ '16' if environment == 'prod' else '8' }}"
        network: "{{ 'prod-network' if environment == 'prod' else 'dev-network' }}"
        storage_class: "{{ 'gold' if environment == 'prod' else 'standard' }}"
        approval_required: "{{ environment == 'prod' }}"

    - name: Request approval for prod
      pause:
        prompt: "Approval required for prod VM. Notify ops-team and press ENTER when approved"
      when: approval_required

    - name: Validate against quotas
      assert:
        that:
          - cpu_count | int <= 16
          - memory_gb | int <= 128
        fail_msg: "VM exceeds quota limits (max 16 CPU, 128 GB RAM)"

    - name: Create KubeVirt VM
      kubernetes.core.k8s:
        state: present
        template: "{{ lookup('file', 'kubevirt/vm.yaml') }}"
        namespace: virt-lab

    - name: Wait for VM to be ready
      kubernetes.core.k8s_info:
        api_version: kubevirt.io/v1
        kind: VirtualMachine
        name: "{{ vm_name }}"
        namespace: virt-lab
      register: vm_status
      until: vm_status.resources | length > 0
      retries: 30
      delay: 10

    - name: Start VM
      kubernetes.core.k8s:
        state: present
        definition:
          apiVersion: kubevirt.io/v1
          kind: VirtualMachine
          metadata:
            name: "{{ vm_name }}"
            namespace: virt-lab
          spec:
            running: true

    - name: Display VM information
      debug:
        msg:
          - "VM created successfully"
          - "Name: {{ vm_name }}"
          - "Environment: {{ environment }}"
          - "CPU: {{ cpu_count }}"
          - "Memory: {{ memory_gb }}Gi"
          - "Owner: {{ owner_email }}"
```

**Key Points**:
- Implements environment branching
- Includes approval gate for prod
- Validates quotas
- Creates KubeVirt VM
- Uses kubernetes.core collection

### Step 19: Review Ansible Role

```bash
cat output/ansible/roles/provision_vm/tasks/main.yml
```

See role structure:
```bash
tree output/ansible/
```

**Output**:
```
output/ansible/
├── site.yml
└── roles
    └── provision_vm
        ├── defaults
        │   └── main.yml
        └── tasks
            └── main.yml
```

### Step 20: Review Generation README

```bash
cat output/README.md
```

**Output**: Instructions for using the generated artifacts (how to run Ansible, apply KubeVirt manifests, etc.)

## Part 6: Testing and Deployment

### Step 21: Validate Artifacts

Run dry-run validation:

```bash
ops-translate dry-run
```

**Output**:
```
Validating intent/intent.yaml...
  ✓ Schema version valid: 1
  ✓ Required fields present
  ✓ Environment branching valid
  ✓ Governance policies valid
  ✓ Compute resources within limits

Validating output/kubevirt/vm.yaml...
  ✓ Valid YAML syntax
  ✓ KubeVirt API version correct
  ✓ Required fields present

Validating output/ansible/site.yml...
  ✓ Valid YAML syntax
  ✓ Ansible playbook structure valid
  ✓ kubernetes.core collection referenced

✓ All validations passed
```

### Step 22: Test Ansible Playbook (Syntax)

```bash
cd output/ansible
ansible-playbook site.yml --syntax-check
```

**Output**:
```
playbook: site.yml
```

### Step 23: Test Ansible Playbook (Check Mode)

```bash
ansible-playbook site.yml --check --extra-vars "environment=dev vm_name=test-vm owner_email=user@example.com requester=user@example.com"
```

**Note**: This does a dry run without creating resources.

### Step 24: Deploy to Lab (Dev VM)

**Prerequisites**:
- Access to OpenShift cluster
- kubectl/oc configured
- kubernetes.core Ansible collection installed

```bash
# Install Ansible collection
ansible-galaxy collection install kubernetes.core

# Run playbook for dev VM
ansible-playbook site.yml

# When prompted:
# Environment: dev
# VM Name: my-test-vm
# Owner Email: you@example.com
# Requester: you@example.com
```

**Output**:
```
PLAY [Provision VM with environment awareness] ***

TASK [Validate environment value] ***
ok: [localhost]

TASK [Set environment-specific variables] ***
ok: [localhost]

TASK [Validate against quotas] ***
ok: [localhost]

TASK [Create KubeVirt VM] ***
changed: [localhost]

TASK [Wait for VM to be ready] ***
ok: [localhost]

TASK [Start VM] ***
changed: [localhost]

TASK [Display VM information] ***
ok: [localhost] => {
    "msg": [
        "VM created successfully",
        "Name: my-test-vm",
        "Environment: dev",
        "CPU: 2",
        "Memory: 8Gi",
        "Owner: you@example.com"
    ]
}

PLAY RECAP ***
localhost: ok=7 changed=2
```

### Step 25: Verify VM in OpenShift

```bash
# Check VM status
oc get vms -n virt-lab

# Output:
# NAME          AGE    STATUS    READY
# my-test-vm    2m     Running   True

# Check VM details
oc describe vm my-test-vm -n virt-lab
```

### Step 26: Test Prod Workflow

Test prod provisioning with approval:

```bash
ansible-playbook site.yml

# When prompted:
# Environment: prod
# VM Name: prod-vm-001
# Owner Email: admin@example.com
# Requester: admin@example.com

# You'll see approval prompt:
# "Approval required for prod VM. Notify ops-team and press ENTER when approved"
# [pause]

# Press ENTER after getting approval
# VM will be created with 4 CPU, 16 GB RAM
```

### Step 27: Generate for Production

Generate production-ready artifacts:

```bash
cd ~/vmware-migration

ops-translate generate --profile prod
```

Review production differences:
```bash
# Different namespace, network, storage class
diff output/kubevirt/vm.yaml <(ops-translate generate --profile prod && cat output/kubevirt/vm.yaml)
```

**Checkpoint**: You've successfully completed the basic migration!

## Advanced Tutorial: Governance Workflow

### Scenario: Enhanced Approval Process

Add multi-level approval and quota management.

### Step 28: Create Enhanced Workflow

Create `governance-enhanced.ps1`:

```powershell
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "test", "staging", "prod")]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [string]$ProjectCode,

    [Parameter(Mandatory=$false)]
    [ValidateSet("low", "medium", "high")]
    [string]$Priority = "medium",

    [Parameter(Mandatory=$false)]
    [int]$CPUCount,

    [Parameter(Mandatory=$false)]
    [int]$MemoryGB
)

# Multi-tier resource allocation
$Tiers = @{
    dev     = @{ CPU = 2;  Memory = 8;   Approval = "none";       Budget = 100 }
    test    = @{ CPU = 2;  Memory = 8;   Approval = "team-lead";  Budget = 200 }
    staging = @{ CPU = 4;  Memory = 16;  Approval = "manager";    Budget = 500 }
    prod    = @{ CPU = 8;  Memory = 32;  Approval = "director";   Budget = 1000 }
}

$Tier = $Tiers[$Environment]

# Override if specified
if ($CPUCount) { $Tier.CPU = $CPUCount }
if ($MemoryGB) { $Tier.Memory = $MemoryGB }

# Validation
if ($Tier.CPU -gt 16 -or $Tier.Memory -gt 128) {
    throw "Resource request exceeds maximum quota"
}

# Tagging for comprehensive tracking
$Tags = @(
    "env:$Environment",
    "project:$ProjectCode",
    "priority:$Priority",
    "approved-by:$($Tier.Approval)",
    "monthly-budget:$($Tier.Budget)"
)

# Provision
New-VM -Name $VMName `
    -NumCpu $Tier.CPU `
    -MemoryGB $Tier.Memory

# Apply all tags
foreach ($Tag in $Tags) {
    New-TagAssignment -Entity $VMName -Tag $Tag
}
```

### Step 29: Import Enhanced Script

```bash
ops-translate import --source powercli --file governance-enhanced.ps1
```

### Step 30: Re-extract and Merge

```bash
# Extract new intent
ops-translate intent extract

# Review new intent
cat intent/powercli.intent.yaml

# Merge all sources
ops-translate intent merge --force
```

### Step 31: Review Enhanced Intent

The merged intent now includes:
- Multi-tier environments (dev/test/staging/prod)
- Approval levels (team-lead, manager, director)
- Budget tracking
- Priority levels
- Enhanced tagging

### Step 32: Generate Enhanced Artifacts

```bash
ops-translate generate --profile prod
```

The generated Ansible will include:
- Multi-level approval gates
- Budget validation
- Priority-based scheduling
- Comprehensive tagging

## Summary

### What You Accomplished

✅ Created an ops-translate workspace
✅ Imported PowerCLI and vRealize automation
✅ Analyzed source files without AI
✅ Extracted operational intent with AI
✅ Merged multiple sources intelligently
✅ Generated Ansible playbooks and KubeVirt manifests
✅ Validated and tested artifacts
✅ Deployed to OpenShift
✅ Enhanced with governance workflow

### Key Takeaways

1. **Workspace Organization**: Everything in one place, version-controllable
2. **AI Assumptions**: Always review assumptions.md for accuracy
3. **Conflict Resolution**: Merge conflicts highlight design decisions
4. **Profile-Based**: Same intent, different environments
5. **Transparent**: Every step creates inspectable artifacts

### Next Steps

- **Production Deployment**: Use prod profile for real workloads
- **CI/CD Integration**: Automate with GitHub Actions
- **Team Collaboration**: Share workspace in git
- **Custom Extensions**: Add custom LLM providers or generators
- **Advanced Patterns**: Explore multi-network, multi-disk scenarios

## Additional Resources

- [User Guide](USER_GUIDE.md) - Complete reference
- [Architecture](ARCHITECTURE.md) - System design
- [API Reference](API_REFERENCE.md) - Programmatic usage
- [Examples](../examples/) - More sample workflows

## Troubleshooting

### Common Issues During Tutorial

**Issue**: "Not in a workspace"
```bash
# Solution: Make sure you're in the workspace directory
cd vmware-migration
```

**Issue**: "LLM API key not found"
```bash
# Solution: Set the environment variable
export OPS_TRANSLATE_LLM_API_KEY="your-key"
```

**Issue**: "Merge conflicts detected"
```bash
# Solution: Review conflicts and decide resolution
cat intent/conflicts.md
ops-translate intent merge --force  # If conflicts acceptable
```

**Issue**: "kubernetes.core collection not found"
```bash
# Solution: Install Ansible collection
ansible-galaxy collection install kubernetes.core
```

**Issue**: "Permission denied on kubectl"
```bash
# Solution: Login to OpenShift
oc login https://your-cluster:6443
```

## Feedback

Found an issue or have suggestions? Please open an issue:
https://github.com/tsanders-rh/ops-translate/issues
