# ops-translate User Guide

Complete guide to using ops-translate for migrating VMware automation to OpenShift Virtualization.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Core Concepts](#core-concepts)
4. [Getting Started](#getting-started)
5. [Workflow Commands](#workflow-commands)
6. [Configuration](#configuration)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

## Introduction

### What is ops-translate?

ops-translate is a CLI tool that helps you migrate from VMware automation (PowerCLI scripts and vRealize Orchestrator workflows) to cloud-native infrastructure on OpenShift Virtualization. Instead of manually rewriting your automation, ops-translate:

1. **Analyzes** your existing PowerCLI and vRealize automation
2. **Extracts** the operational intent using AI
3. **Merges** multiple automation sources into a unified intent model
4. **Generates** production-ready Ansible playbooks and KubeVirt manifests

### Key Benefits

- **Accelerated Migration**: Convert weeks of manual work into hours
- **Preserves Intent**: Captures operational patterns, not just configurations
- **Transparent**: Every assumption and inference is documented
- **Safe**: Read-only operations with no live system access
- **Flexible**: Works with or without AI assistance

### Do I Need an LLM?

**TL;DR**: Only for intent extraction. Everything else is LLM-free.

ops-translate separates "understanding" (needs AI) from "translation" (doesn't need AI):

| Command | LLM Required? | Why |
|---------|---------------|-----|
| `import` | ❌ No | Just copies files |
| `summarize` | ❌ No | Static pattern matching |
| `intent extract` | ✅ **YES** | Understands semantic meaning of code |
| `intent merge` | ❌ No | Deterministic YAML reconciliation |
| `dry-run` | ❌ No | Schema validation |
| `generate` | ❌ No | Template-based (Jinja2) |

**The only step that needs LLM is intent extraction**, which converts imperative PowerCLI/vRealize code into declarative intent YAML.

**Three ways to use ops-translate:**

1. **With AI** (Recommended for legacy automation)
   ```bash
   ops-translate intent extract  # Uses LLM
   ops-translate generate        # Uses templates (no LLM)
   ```
   - Best for complex scripts
   - Requires API key
   - One-time cost per file

2. **Without AI** (Manual intent creation)
   ```bash
   # Write intent.yaml yourself using schema
   vim intent/intent.yaml

   ops-translate generate --no-ai  # Templates only
   ```
   - 100% deterministic
   - Works offline
   - Free

3. **Mock Provider** (Testing/Demos)
   ```bash
   # No API key configured
   ops-translate intent extract  # Uses mock responses
   ops-translate generate        # Uses templates
   ```
   - No API costs
   - Good for testing workflow
   - Not real AI understanding

**Important**: Even if you use AI for extraction, **generation always uses templates** by default. This is by design:
- ✅ Faster (no API call)
- ✅ Deterministic (same input → same output)
- ✅ Schema-validated
- ✅ Works offline

**Cost estimate**: Extracting intent from a typical PowerCLI script costs $0.01-0.10 per file. Generation is free.

### Who Should Use This?

- Infrastructure engineers migrating from VMware to OpenShift
- Operations teams modernizing VM automation
- Architects evaluating migration paths
- DevOps teams adopting Infrastructure as Code

## Installation

### Prerequisites

- **Python 3.10 or higher**
- **pip** (Python package installer)
- **Optional**: API key for OpenAI or Anthropic (for AI-assisted extraction)

### Install from PyPI

```bash
pip install ops-translate
```

### Install from Source

```bash
git clone https://github.com/tsanders-rh/ops-translate
cd ops-translate
pip install -e .
```

### Verify Installation

```bash
ops-translate --help
```

You should see the command-line interface help text listing all available commands.

## Core Concepts

### Workspace

A workspace is a directory structure that holds all inputs, intermediate artifacts, and outputs for a translation project. Each workspace contains:

```
my-workspace/
├── ops-translate.yaml      # Configuration file
├── input/                  # Source automation files
│   ├── powercli/          # PowerCLI scripts (.ps1)
│   └── vrealize/          # vRealize workflows (.xml)
├── intent/                # Extracted operational intent
│   ├── powercli.intent.yaml
│   ├── vrealize.intent.yaml
│   ├── intent.yaml        # Merged intent
│   ├── assumptions.md     # AI assumptions log
│   └── conflicts.md       # Merge conflicts (if any)
├── mapping/               # VMware → OpenShift mappings
│   └── preview.md
└── output/                # Generated artifacts
    ├── kubevirt/
    │   └── vm.yaml
    └── ansible/
        ├── site.yml
        └── roles/
```

### Operational Intent Model

The core of ops-translate is the **Operational Intent Model** - a normalized YAML schema that captures:

- **What** resources to provision (VMs, networks, storage)
- **How** to configure them (CPU, memory, networking)
- **When** to apply governance (approvals, quotas)
- **Why** decisions are made (environment branching, tagging)

Example intent:

```yaml
schema_version: 1
type: powercli
workflow_name: provision_dev_vm
inputs:
  - name: vm_name
    type: string
    required: true
  - name: environment
    type: string
    required: true
    allowed_values: [dev, prod]
compute:
  cpu_count: 2
  memory_gb: 8
environment_branching:
  enabled: true
  conditions:
    - if: environment == "prod"
      then:
        cpu_count: 4
        memory_gb: 16
```

### Translation Workflow

The ops-translate workflow has five main phases:

1. **Import**: Copy source files into workspace
2. **Summarize**: Quick analysis without AI (optional)
3. **Extract**: AI-powered intent extraction
4. **Merge**: Combine multiple sources into unified intent
5. **Generate**: Create Ansible and KubeVirt artifacts

## Getting Started

### Quick Start with Examples

The fastest way to learn ops-translate is to use the provided examples:

```bash
# 1. Initialize workspace
ops-translate init demo-workspace
cd demo-workspace

# 2. Import example PowerCLI script
ops-translate import --source powercli --file ../examples/powercli/environment-aware.ps1

# 3. Summarize (no AI required)
ops-translate summarize
cat intent/summary.md

# 4. Extract intent (requires LLM API key or uses mock)
ops-translate intent extract
cat intent/powercli.intent.yaml

# 5. Review migration readiness BEFORE generating
ops-translate report
open output/report/index.html  # Interactive report with recommendations

# 6. Generate artifacts
ops-translate generate --profile lab

# 7. Review output
ls -R output/
cat output/README.md
```

### Your First Real Migration

Let's migrate a real PowerCLI script:

#### Step 1: Create Workspace

```bash
ops-translate init my-migration
cd my-migration
```

This creates the directory structure and default configuration.

#### Step 2: Import Your Automation

```bash
# Import PowerCLI scripts
ops-translate import --source powercli --file /path/to/provision-vm.ps1
ops-translate import --source powercli --file /path/to/configure-network.ps1

# Import vRealize workflows (if you have them)
ops-translate import --source vrealize --file /path/to/workflow.xml
```

Files are copied into `input/powercli/` and `input/vrealize/` respectively.

#### Step 3: Configure LLM Provider

Edit `ops-translate.yaml` and configure your LLM provider:

```yaml
llm:
  provider: anthropic  # or openai
  model: claude-sonnet-4-5
  api_key_env: OPS_TRANSLATE_LLM_API_KEY
```

Set the API key:

```bash
export OPS_TRANSLATE_LLM_API_KEY="your-api-key-here"
```

#### Step 4: Summarize Inputs

```bash
ops-translate summarize
```

Review `intent/summary.md` to understand what was detected:
- Input parameters
- Environment branching logic
- Governance requirements
- Network/storage patterns

#### Step 5: Extract Intent

```bash
ops-translate intent extract
```

This creates:
- `intent/powercli.intent.yaml` - Intent from PowerCLI scripts
- `intent/vrealize.intent.yaml` - Intent from vRealize workflows (if any)
- `intent/assumptions.md` - AI assumptions and inferences

**Review these files carefully** - check that the AI correctly understood your automation.

#### Step 6: Edit Intent (if needed)

If the AI misunderstood something, edit the intent manually:

```bash
ops-translate intent edit
# Opens intent/powercli.intent.yaml in your $EDITOR
```

#### Step 7: Merge Multiple Sources

If you imported both PowerCLI and vRealize:

```bash
ops-translate intent merge
```

This creates `intent/intent.yaml` by combining sources. If there are conflicts:
- Conflicts are written to `intent/conflicts.md`
- Command exits with error unless you use `--force`

Example conflict:

```markdown
## Conflict: Approval Required

- PowerCLI script: No approval requirement
- vRealize workflow: Requires approval for prod environment

**Resolution needed**: Decide which behavior to preserve
```

#### Step 8: Preview Mapping

See how VMware concepts map to OpenShift:

```bash
ops-translate map preview --target openshift
cat mapping/preview.md
```

#### Step 9: Review Migration Readiness

Before generating artifacts, review the interactive migration readiness report:

```bash
ops-translate report
open output/report/index.html
```

This interactive HTML report shows:
- **3-layer progressive disclosure**: Executive summary, architecture planning, implementation details
- **Translation status**: Supported, Partial, Expert-Guided, Custom classifications
- **Expert recommendations**: Production-grade patterns organized by team
- **Migration paths**: PATH A/B/C guidance with OpenShift equivalents
- **Interactive features**: Filters, collapsible sections, CSV export

#### Step 10: Generate Artifacts

After reviewing the report, generate artifacts:

```bash
ops-translate generate --profile lab
```

This creates:
- `output/kubevirt/vm.yaml` - KubeVirt VirtualMachine manifest
- `output/ansible/site.yml` - Main Ansible playbook
- `output/ansible/roles/provision_vm/` - Ansible role structure
- `output/README.md` - How to use the generated artifacts

#### Step 11: Validate Output

```bash
# Dry-run validation
ops-translate dry-run

# Review generated files
cat output/kubevirt/vm.yaml
cat output/ansible/site.yml
cat output/README.md
```

## Workflow Commands

### ops-translate init

**Purpose**: Initialize a new workspace.

```bash
ops-translate init <workspace_dir>
```

**Example**:
```bash
ops-translate init my-project
cd my-project
```

**What it creates**:
- Directory structure (input/, intent/, output/, etc.)
- Default `ops-translate.yaml` configuration
- README with next steps

### ops-translate import

**Purpose**: Import PowerCLI scripts or vRealize workflows into workspace.

```bash
ops-translate import --source <powercli|vrealize> --file <path>
```

**Options**:
- `--source`: Source type (`powercli` or `vrealize`)
- `--file`: Path to file to import

**Examples**:
```bash
# Import single PowerCLI script
ops-translate import --source powercli --file provision.ps1

# Import multiple scripts
ops-translate import --source powercli --file script1.ps1
ops-translate import --source powercli --file script2.ps1

# Import vRealize workflow
ops-translate import --source vrealize --file workflow.xml
```

**Notes**:
- Files are copied, not moved
- Original files remain unchanged
- Import metadata is logged in workspace

### ops-translate summarize

**Purpose**: Analyze inputs and generate summary without AI.

```bash
ops-translate summarize
```

**Output**: `intent/summary.md`

**What it detects**:
- Input parameters (name, type, required/optional)
- Environment branching (dev/prod/staging patterns)
- Approval requirements
- Tagging and metadata operations
- Network and storage selection logic

**When to use**:
- Before running expensive AI extraction
- To verify files were imported correctly
- To understand automation complexity

**Example output** (`intent/summary.md`):

```markdown
# Automation Summary

## PowerCLI Scripts

### File: provision-vm.ps1

**Parameters**:
- `VMName` (string, required)
- `Environment` (string, required)
- `CPUCount` (int, optional)

**Environment Branching**: Detected
- Uses ValidateSet for environment selection
- Different resource profiles for dev/prod

**Tagging/Metadata**: Detected
- Tags VMs with environment
- Owner email tracking

**Network/Storage Selection**: Detected
- Environment-specific network selection
- Storage profile varies by environment
```

### ops-translate intent extract

**Purpose**: Use AI to extract operational intent from source files.

```bash
ops-translate intent extract [--no-ai]
```

**Options**:
- `--no-ai`: Use template-based extraction instead of AI

**Output**:
- `intent/powercli.intent.yaml` - Intent from PowerCLI
- `intent/vrealize.intent.yaml` - Intent from vRealize
- `intent/assumptions.md` - AI assumptions log

**Example workflow**:

```bash
# Extract with AI (default)
ops-translate intent extract

# Review extracted intent
cat intent/powercli.intent.yaml

# Check AI assumptions
cat intent/assumptions.md
```

**AI Assumptions Log Example**:

```markdown
# Assumptions Made During Intent Extraction

## PowerCLI: provision-vm.ps1

1. **CPU/Memory Defaults**: Assumed dev environment uses 2 vCPU / 8GB RAM based on script logic
2. **Network Selection**: Inferred network names from variable assignments
3. **Storage Profile**: Assumed "gold" storage for prod, "standard" for dev
4. **Approval**: No approval workflow detected in script

**Confidence**: High

## vRealize: approval-workflow.xml

1. **Approval Gate**: Detected approval decision node before VM creation
2. **Approvers**: Extracted from workflow metadata
3. **Timeout**: 7 days based on workflow timer configuration

**Confidence**: High
```

**Automatic Gap Analysis (vRealize Only)**:

When extracting intent from vRealize workflows, ops-translate automatically analyzes them for translatability issues:

```bash
ops-translate intent extract
```

Output includes:
```
Running gap analysis on vRealize workflows...
  Analyzing: nsx-provisioning.xml
    ⚠ Found 3 blocking issue(s)
  ✓ Gap analysis reports written to intent/gaps.md and intent/gaps.json

⚠ Warning: Found 3 component(s) that cannot be automatically translated.
  Review intent/gaps.md for migration guidance.
```

**Gap analysis output files**:
- `intent/gaps.md` - Human-readable report with migration paths and recommendations
- `intent/gaps.json` - Machine-readable data for tooling integration

**What gets analyzed**:
- NSX-T operations (segments, firewall rules, load balancers, security groups, etc.)
- Custom vRO plugins (ServiceNow, Infoblox, Active Directory, etc.)
- REST API calls to external systems
- vRealize-specific constructs

**Classification levels**:
- ✅ **SUPPORTED** - Fully automatic translation to OpenShift-native equivalent
- ⚠️ **PARTIAL** - Can translate but requires manual configuration
- 🎯 **EXPERT-GUIDED** - Production-grade patterns available from Red Hat experts
- 🔧 **CUSTOM** - Complex custom logic requiring specialist review

**Example gap report** (`intent/gaps.md`):
```markdown
# Gap Analysis Report: nsx-provisioning.xml

## Executive Summary

**Overall Assessment**: REQUIRES_MANUAL_WORK

- Total Components: 5
- ✅ SUPPORTED: 2
- ⚠️ PARTIAL: 2
- 🎯 EXPERT-GUIDED: 1

## Detailed Component Analysis

### NSX Firewall Rule

**Type**: `nsx_firewall_rule`
**Classification**: ⚠️ PARTIAL
**OpenShift Equivalent**: NetworkPolicy
**Migration Path**: PATH_A - OpenShift-native replacement

**Why this classification**:
NSX distributed firewall rules can be replaced with Kubernetes NetworkPolicy,
but require manual translation of rule syntax and testing.

**Recommendations**:
1. Create NetworkPolicy manifest with equivalent rules
2. Test pod-to-pod connectivity in dev environment
3. Consider Calico for advanced features (egress rules, logging)
4. Review default-deny policies

**Evidence**: `nsxClient.createFirewallRule()` at line 45

**Example NetworkPolicy**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-to-app-allow
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: app-tier
    ports:
    - protocol: TCP
      port: 8080
```
```

When you run `ops-translate generate`, these gaps are automatically incorporated into the Ansible playbooks as TODO tasks and role stubs. See [ops-translate generate](#ops-translate-generate) for details.

### ops-translate intent edit

**Purpose**: Manually edit extracted intent.

```bash
ops-translate intent edit [--file <intent_file>]
```

**Options**:
- `--file`: Specific intent file to edit (default: `intent/intent.yaml`)

**Examples**:
```bash
# Edit merged intent
ops-translate intent edit

# Edit specific source intent
ops-translate intent edit --file intent/powercli.intent.yaml
```

**Tip**: Set your preferred editor:
```bash
export EDITOR=vim  # or nano, emacs, code, etc.
```

### ops-translate intent merge

**Purpose**: Merge multiple source intents into unified intent.

```bash
ops-translate intent merge [--force]
```

**Options**:
- `--force`: Proceed even if conflicts detected

**Output**:
- `intent/intent.yaml` - Merged intent
- `intent/conflicts.md` - Conflicts (if any)

**Conflict Resolution**:

If conflicts are detected, review `intent/conflicts.md`:

```markdown
# Intent Merge Conflicts

## 1. Approval Requirement Mismatch

**PowerCLI**: No approval required
**vRealize**: Requires approval for prod environment

**Recommendation**: Include approval requirement to match vRealize governance

## 2. Network Mapping Difference

**PowerCLI**: Uses "prod-network" for prod
**vRealize**: Uses "production-net" for prod

**Recommendation**: Standardize on one network name
```

Options:
1. **Resolve manually**: Edit intent files to resolve conflicts
2. **Force merge**: Use `--force` to merge with conflicts logged
3. **Choose one source**: Remove conflicting intent file

### ops-translate map preview

**Purpose**: Generate VMware → OpenShift concept mapping.

```bash
ops-translate map preview --target openshift
```

**Output**: `mapping/preview.md`

**Example output**:

```markdown
# VMware → OpenShift Mapping Preview

## Compute Mappings

| VMware Concept | OpenShift Equivalent | Notes |
|----------------|---------------------|-------|
| New-VM cmdlet | KubeVirt VirtualMachine | Creates VM custom resource |
| CPU cores | spec.template.spec.domain.cpu.cores | Direct mapping |
| Memory GB | spec.template.spec.domain.resources.requests.memory | Convert to Mi/Gi |

## Network Mappings

| VMware Concept | OpenShift Equivalent | Notes |
|----------------|---------------------|-------|
| PortGroup | NetworkAttachmentDefinition | Requires Multus CNI |
| Get-NetworkAdapter | spec.template.spec.domain.devices.interfaces | Network interface config |

## Storage Mappings

| VMware Concept | OpenShift Equivalent | Notes |
|----------------|---------------------|-------|
| Datastore | StorageClass | Abstract storage backend |
| New-HardDisk | DataVolume | Persistent volume claim |
```

### ops-translate report

**Purpose**: Generate interactive HTML migration readiness report.

```bash
ops-translate report
```

**Output**: `output/report/index.html` (self-contained HTML with embedded CSS/JS)

**When to use**: After `intent extract` and BEFORE `generate` to review migration complexity, gaps, and expert recommendations.

#### What the Report Shows

The HTML report provides a comprehensive migration analysis organized in **3 progressive disclosure layers**:

**Layer 1: Executive Summary**
- Translation status cards (Supported, Partial, Expert-Guided, Custom)
- Real-world migration story with actual component counts
- Target architecture snapshot showing end-state
- How to read this report guide for different audiences
- Overall migration assessment

**Layer 2: Architecture & Planning**
- Expert recommendations by team (Platform, Network, Security)
- Migration path quick reference (PATH A/B/C)
- Consolidated SUPPORTED patterns (reduced repetition)
- Detailed gap analysis with OpenShift equivalents

**Layer 3: Implementation Details** (collapsible)
- Intent overview (workflow info, inputs, outputs, integrations)
- Generated artifacts preview
- Source code evidence with line numbers

#### Interactive Features

- **Click to filter**: Click summary cards to filter gaps by severity level
- **Team-based filters**: Filter expert recommendations by Platform/Network/Security teams
- **Collapsible sections**: Layer 3 sections expand on demand
- **SUPPORTED toggle**: Hide/show fully-supported patterns (hidden by default)
- **Export options**: PDF (print) and CSV (migration tasks)

#### Multi-Audience Design

The report serves different stakeholders:

| Audience | Recommended Path |
|----------|-----------------|
| **Executives** | Executive Summary → Migration Story → Target Architecture |
| **Platform Teams** | Architecture Snapshot → Expert Recommendations → Implementation Details |
| **NetOps / SecOps** | NSX Migration Findings → Expert-Guided Security & Governance Patterns |

#### Understanding Migration Classifications

| Label | Meaning | Example |
|-------|---------|---------|
| **Supported** | Auto-translatable to OpenShift | VM provisioning, CPU/memory config |
| **Partial Translation** | Core intent detected, manual mapping needed | Custom network policies, advanced storage |
| **Expert-Guided** | Production-grade patterns available from Red Hat | NSX firewall rules, approval workflows |
| **Custom** | Complex custom logic requiring specialist review | Custom plugins, JavaScript scriptable tasks |

#### Example Workflow

```bash
# Extract intent
ops-translate intent extract

# Generate and review report
ops-translate report
open output/report/index.html

# Review the report to:
# 1. Understand what will auto-translate (SUPPORTED)
# 2. Identify components needing manual work (PARTIAL/CUSTOM)
# 3. Access expert recommendations for complex patterns (EXPERT-GUIDED)
# 4. Plan migration based on PATH A/B/C guidance

# After reviewing, generate artifacts
ops-translate generate --profile lab
```

#### Report Sections Explained

**Migration Story**
- Shows actual counts from your workspace analysis
- Demonstrates proven automation for standard patterns
- Highlights availability of expert patterns for complex scenarios
- Not a research project - production-grade guidance

**Target Architecture Snapshot**
- Explicit end-state showing what runs where
- OpenShift Virtualization for VM workloads
- Ansible Automation Platform for orchestration
- OpenShift Networking (OVN-Kubernetes, NetworkPolicy, Ingress)
- Clarifies virt-first migration journey

**Expert Recommendations**
- Production-grade patterns from successful customer migrations
- Organized by team responsibility (Platform, Network, Security)
- Includes implementation guidance and OpenShift equivalents
- Emphasizes supported automation stack (not DIY)

**Gap Analysis**
- Component-by-component analysis with severity levels
- Migration path assignments (PATH A/B/C)
- Evidence from source code with file locations and line numbers
- Specific recommendations for each component

**Consolidated SUPPORTED Patterns**
- Groups repeated SUPPORTED components by type
- Shows "VM Provisioning (5 instances across 2 files)" instead of listing each
- Reduces report length while preserving full detail
- Hidden by default (toggle to show)

#### Tips

- **Review BEFORE generating**: Understand migration complexity before creating artifacts
- **Share with stakeholders**: Report is self-contained HTML (no server required)
- **Use filters**: Focus on specific severity levels or teams
- **Export to CSV**: Create migration task tracking in your project management tool
- **Print to PDF**: Create offline documentation or presentations

### ops-translate generate

**Purpose**: Generate Ansible playbooks and KubeVirt manifests.

**⚠️ Best Practice**: Review the migration readiness report BEFORE generating:
```bash
ops-translate report
open output/report/index.html
```
The interactive report shows translation status, expert recommendations, and migration paths to help you understand what will be automated vs. what needs manual work.

```bash
ops-translate generate --profile <profile_name> [--no-ai]
```

**Options**:
- `--profile`: Target environment profile (lab, prod, etc.)
- `--no-ai`: Use templates instead of AI for generation

**Output**:
- `output/kubevirt/vm.yaml`
- `output/ansible/site.yml`
- `output/ansible/roles/provision_vm/tasks/main.yml`
- `output/ansible/roles/provision_vm/defaults/main.yml`
- `output/README.md`

**Examples**:
```bash
# Generate for lab environment
ops-translate generate --profile lab

# Generate for production
ops-translate generate --profile prod

# Generate without AI (template-based)
ops-translate generate --profile lab --no-ai
```

**Gap Analysis Integration**:

When vRealize workflows have been analyzed (via `intent extract`), the generated Ansible playbooks automatically include:

1. **TODO tasks** for components requiring manual work
2. **Role stubs** for EXPERT-GUIDED/CUSTOM components
3. **Migration guidance** as embedded comments

**Example: Generated playbook with gaps** (`output/ansible/site.yml`):
```yaml
---
- name: Provision VM with NSX networking
  hosts: localhost
  tasks:
    # Gap Analysis Summary:
    # - 2 PARTIAL components require manual configuration
    # - 1 EXPERT-GUIDED component has production patterns available
    # Review intent/gaps.md for detailed migration guidance

    - name: "TODO: Review NSX segment migration (PARTIAL)"
      debug:
        msg: |
          CLASSIFICATION: PARTIAL
          COMPONENT: NSX Segment
          OPENSHIFT EQUIVALENT: NetworkAttachmentDefinition (Multus CNI)
          MIGRATION PATH: PATH_A - OpenShift-native replacement

          RECOMMENDATIONS:
          - Create NetworkAttachmentDefinition manifest
          - Configure Multus CNI on target cluster
          - Test network connectivity
          - Update VM spec to reference NAD

          EVIDENCE: nsxClient.createSegment() detected at line 23
      tags: [manual_review_required]

    - name: "TODO: Implement NSX firewall rule migration (PARTIAL)"
      debug:
        msg: |
          CLASSIFICATION: PARTIAL
          COMPONENT: NSX Firewall Rule
          OPENSHIFT EQUIVALENT: NetworkPolicy
          MIGRATION PATH: PATH_A - OpenShift-native replacement

          RECOMMENDATIONS:
          - Create NetworkPolicy manifest with equivalent rules
          - Test pod-to-pod connectivity
          - Consider Calico for advanced features
      tags: [manual_review_required]

    # Normal automation tasks follow...
    - name: Create KubeVirt VM
      kubernetes.core.k8s:
        state: present
        definition: "{{ lookup('file', 'kubevirt/vm.yaml') }}"
```

**Auto-generated role stubs** (`output/ansible/roles/nsx_segment_migration/`):

For EXPERT-GUIDED/CUSTOM components, ops-translate generates role scaffolding:

```
output/ansible/roles/
└── nsx_segment_migration/
    ├── README.md                 # Migration guidance
    ├── tasks/main.yml            # TODO placeholders
    └── defaults/main.yml         # Discovered parameters
```

**Role README** (`roles/nsx_segment_migration/README.md`):
```markdown
# NSX Segment Migration Role

**Classification**: PARTIAL
**OpenShift Equivalent**: NetworkAttachmentDefinition (Multus CNI)
**Migration Path**: PATH_A - OpenShift-native replacement

## Overview

This role was auto-generated because NSX segment operations were detected
in the source vRealize workflow that cannot be fully automatically translated.

## What Needs Implementation

1. Create NetworkAttachmentDefinition manifest
2. Configure Multus CNI on target cluster
3. Test network connectivity
4. Update VM spec to reference NAD

## Discovered Parameters

The following parameters were extracted from the source workflow:
- segment_name: "web-tier-segment"
- vlan_ids: [100]
- gateway_address: "192.168.1.1/24"

## Implementation Steps

[Detailed steps based on migration path...]

## Testing

[Testing checklist...]
```

**Role tasks** (`roles/nsx_segment_migration/tasks/main.yml`):
```yaml
---
# TODO: Implement NSX segment migration
# Classification: PARTIAL
# OpenShift Equivalent: NetworkAttachmentDefinition

- name: TODO - Create NetworkAttachmentDefinition
  fail:
    msg: |
      This task is a placeholder. Implement NAD creation here.
      See README.md for guidance.
  tags: [manual_implementation_required]

- name: TODO - Verify Multus CNI configuration
  fail:
    msg: |
      This task is a placeholder. Add CNI verification logic.
  tags: [manual_implementation_required]
```

This gives you a clear starting point for manual work instead of starting from scratch.

### ops-translate dry-run

**Purpose**: Validate intent and generated artifacts without execution.

```bash
ops-translate dry-run
```

**What it checks**:
- Intent YAML schema validation
- Required fields presence
- YAML syntax of generated artifacts
- Ansible playbook structure
- KubeVirt manifest validity

**Example output**:

```
Validating intent/intent.yaml...
✓ Schema version valid: 1
✓ Required fields present
✓ Environment branching valid
✓ Compute resources valid

Validating generated artifacts...
✓ output/kubevirt/vm.yaml is valid YAML
✓ output/ansible/site.yml is valid YAML
✓ Ansible role structure valid

All validations passed ✓
```

## Configuration

### ops-translate.yaml Structure

The workspace configuration file controls all aspects of ops-translate:

```yaml
# LLM Provider Configuration
llm:
  provider: anthropic  # anthropic, openai, or mock
  model: claude-sonnet-4-5
  api_key_env: OPS_TRANSLATE_LLM_API_KEY
  max_tokens: 4096
  temperature: 0.0

# Environment Profiles
profiles:
  lab:
    default_namespace: virt-lab
    default_network: lab-network
    default_storage_class: nfs
    compute_limits:
      max_cpu: 8
      max_memory_gb: 32

  prod:
    default_namespace: virt-prod
    default_network: prod-network
    default_storage_class: ceph-rbd
    compute_limits:
      max_cpu: 16
      max_memory_gb: 64

# Feature Flags
features:
  enable_approval_workflows: true
  enable_quota_enforcement: true
  enable_tagging: true
```

### LLM Provider Configuration

#### Anthropic Claude (Recommended)

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-5  # Best balance of cost/quality
  # model: claude-opus-4     # Use for complex workflows
  api_key_env: OPS_TRANSLATE_LLM_API_KEY
```

**Get API Key**: https://console.anthropic.com

**Set Environment Variable**:
```bash
export OPS_TRANSLATE_LLM_API_KEY="sk-ant-..."
```

**Model Selection**:
- `claude-sonnet-4-5`: Recommended for most workflows (fast, cost-effective)
- `claude-opus-4`: Use for complex vRealize workflows with intricate logic
- `claude-sonnet-3-5`: Previous generation, still supported

#### OpenAI

```yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
  api_key_env: OPS_TRANSLATE_LLM_API_KEY
```

**Get API Key**: https://platform.openai.com

**Model Selection**:
- `gpt-4-turbo-preview`: Best quality
- `gpt-4`: Stable version
- `gpt-3.5-turbo`: Faster, lower cost

#### Mock Provider (Testing)

```yaml
llm:
  provider: mock
  model: mock-model
```

**Use cases**:
- Testing CLI workflow
- CI/CD pipelines
- Demos without API costs

### Profile Configuration

Profiles define target OpenShift environments:

```yaml
profiles:
  lab:
    default_namespace: virt-lab
    default_network: lab-network
    default_storage_class: nfs
    compute_limits:
      max_cpu: 8
      max_memory_gb: 32
    enable_node_selector: false

  staging:
    default_namespace: virt-staging
    default_network: staging-network
    default_storage_class: ceph-rbd
    compute_limits:
      max_cpu: 16
      max_memory_gb: 64
    enable_node_selector: true
    node_selector:
      workload: virtualization

  prod:
    default_namespace: virt-prod
    default_network: prod-network
    default_storage_class: ceph-rbd
    compute_limits:
      max_cpu: 32
      max_memory_gb: 128
    enable_node_selector: true
    node_selector:
      workload: virtualization
      tier: production
```

## Advanced Usage

### Multi-Source Merging

When migrating complex automation with multiple PowerCLI scripts and vRealize workflows:

```bash
# Import all sources
ops-translate import --source powercli --file vm-provision.ps1
ops-translate import --source powercli --file network-config.ps1
ops-translate import --source powercli --file storage-setup.ps1
ops-translate import --source vrealize --file approval-workflow.xml
ops-translate import --source vrealize --file notification-workflow.xml

# Extract intent from each
ops-translate intent extract

# Review each intent file
ls -l intent/*.intent.yaml

# Merge with conflict detection
ops-translate intent merge

# If conflicts, review and resolve
if [ -f intent/conflicts.md ]; then
  cat intent/conflicts.md
  # Edit intent files as needed
  ops-translate intent merge --force
fi

# Generate unified output
ops-translate generate --profile prod
```

### Template-Based Workflow (No AI)

For environments without LLM API access:

```bash
# Extract using templates
ops-translate intent extract --no-ai

# Generate using templates
ops-translate generate --profile lab --no-ai
```

**Note**: Template-based extraction is less accurate than AI but requires no API keys.

### Custom Intent Schema

You can manually create intent YAML if you prefer not to use extraction:

```bash
# Skip extraction, create intent manually
cat > intent/intent.yaml <<EOF
schema_version: 1
type: custom
workflow_name: my_vm_provision

inputs:
  - name: vm_name
    type: string
    required: true

compute:
  cpu_count: 4
  memory_gb: 16

networking:
  interfaces:
    - name: eth0
      network: prod-network

storage:
  volumes:
    - name: root
      size_gb: 100
      storage_class: ceph-rbd
EOF

# Generate from custom intent
ops-translate generate --profile prod
```

### Incremental Migration

Migrate automation incrementally:

**Week 1**: Start with simple provisioning
```bash
ops-translate import --source powercli --file provision-basic.ps1
ops-translate intent extract
ops-translate generate --profile lab
# Test in lab
```

**Week 2**: Add networking complexity
```bash
ops-translate import --source powercli --file provision-networking.ps1
ops-translate intent extract
ops-translate intent merge
ops-translate generate --profile lab
# Test networking
```

**Week 3**: Add governance
```bash
ops-translate import --source vrealize --file approval-workflow.xml
ops-translate intent extract
ops-translate intent merge
ops-translate generate --profile staging
# Test approval flow
```

## Troubleshooting

### Common Issues

#### API Key Not Found

**Symptom**:
```
Warning: LLM API key not found. Falling back to mock provider.
```

**Solution**:
```bash
export OPS_TRANSLATE_LLM_API_KEY="your-api-key"
# Or edit ops-translate.yaml and set api_key_env correctly
```

#### Import File Not Found

**Symptom**:
```
Error: File not found: /path/to/script.ps1
```

**Solution**:
- Verify file path is correct
- Use absolute paths or paths relative to current directory
- Check file permissions

#### Merge Conflicts

**Symptom**:
```
Error: Conflicts detected during merge. See intent/conflicts.md
```

**Solution**:
1. Review `intent/conflicts.md`
2. Edit intent files to resolve conflicts
3. Re-run merge, or use `--force` to proceed

#### Invalid Intent Schema

**Symptom**:
```
Error: Intent schema validation failed
```

**Solution**:
- Run `ops-translate dry-run` to see specific errors
- Check intent YAML syntax
- Verify required fields are present
- Compare with schema in `schema/` directory

#### Not in Workspace

**Symptom**:
```
Error: Not in a workspace. Run 'ops-translate init <dir>' first.
```

**Solution**:
```bash
# Either cd into workspace
cd my-workspace

# Or initialize new workspace
ops-translate init my-workspace
cd my-workspace
```

### Debug Mode

Enable verbose logging:

```bash
export OPS_TRANSLATE_DEBUG=1
ops-translate intent extract
```

### Getting Help

```bash
# General help
ops-translate --help

# Command-specific help
ops-translate intent extract --help
ops-translate generate --help
```

## Best Practices

### 1. Version Control Your Workspace

```bash
cd my-workspace
git init
git add ops-translate.yaml intent/ output/
git commit -m "Initial migration setup"
```

**What to commit**:
- `ops-translate.yaml`
- `intent/*.yaml`
- `intent/*.md`
- `output/`

**What not to commit**:
- `input/` (contains original source files)
- API keys (use environment variables)

### 2. Review Before Generate

Always review extracted intent before generation:

```bash
ops-translate intent extract
# Review intent files
cat intent/powercli.intent.yaml
cat intent/assumptions.md
# Make corrections if needed
ops-translate intent edit
# Then generate
ops-translate generate --profile lab
```

### 3. Test in Lab First

Never generate directly to production:

```bash
# Generate for lab
ops-translate generate --profile lab

# Test in lab environment
kubectl apply -f output/kubevirt/vm.yaml --dry-run=client
ansible-playbook output/ansible/site.yml --check

# After validation, generate for prod
ops-translate generate --profile prod
```

### 4. Document Assumptions

Keep the AI assumptions log in version control:

```bash
git add intent/assumptions.md
git commit -m "Document AI assumptions for VM provisioning"
```

This helps team members understand AI decisions.

### 5. Incremental Complexity

Start simple, add complexity incrementally:

1. Basic VM provisioning
2. Add networking
3. Add storage
4. Add governance
5. Add approval workflows

### 6. Validate Generated Artifacts

Always validate before deployment:

```bash
# Validate YAML syntax
yamllint output/kubevirt/vm.yaml
yamllint output/ansible/site.yml

# Validate Ansible playbook
ansible-playbook output/ansible/site.yml --syntax-check

# Validate KubeVirt manifest
kubectl apply -f output/kubevirt/vm.yaml --dry-run=server

# Run full validation
ops-translate dry-run
```

### 7. Keep Originals Safe

ops-translate copies files during import. Keep originals:

```bash
# Backup originals before import
cp /original/location/*.ps1 ~/backups/
cp /original/location/*.xml ~/backups/

# Then import
ops-translate import --source powercli --file /original/location/script.ps1
```

### 8. Use Profiles Consistently

Define profiles once, use everywhere:

```yaml
# ops-translate.yaml
profiles:
  lab: { namespace: virt-lab, ... }
  staging: { namespace: virt-staging, ... }
  prod: { namespace: virt-prod, ... }
```

```bash
# Always specify profile
ops-translate generate --profile lab
ops-translate generate --profile staging
ops-translate generate --profile prod
```

### 9. Monitor Costs

If using paid LLM APIs:

```bash
# Use mock for testing
ops-translate intent extract --no-ai

# Use cheaper models for simple scripts
# Edit ops-translate.yaml:
llm:
  model: claude-sonnet-4-5  # Cheaper than opus

# Use AI only when needed
ops-translate summarize  # No AI
ops-translate intent extract  # AI only here
ops-translate generate --no-ai  # Templates
```

### 10. Collaborate with Team

Share workspace configuration:

```bash
# Share ops-translate.yaml (without API keys!)
git add ops-translate.yaml
git commit -m "Add team workspace configuration"
git push

# Team members clone and set their own API keys
git clone <repo>
cd <workspace>
export OPS_TRANSLATE_LLM_API_KEY="their-key"
```

## Next Steps

- Read the [Architecture Documentation](ARCHITECTURE.md) to understand how ops-translate works
- Follow the [Tutorial](TUTORIAL.md) for a hands-on walkthrough
- Check the [API Reference](API_REFERENCE.md) for programmatic usage
- Review [examples/](../examples/) for sample workflows
