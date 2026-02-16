# ops-translate Quick Reference Guide

## One-Page Overview

**What**: AI-assisted tool that converts VMware PowerCLI and vRealize Orchestrator automation to Ansible + OpenShift Virtualization

**Why**: Preserve operational logic during VMware to OpenShift migration, accelerate conversion by 95%, reduce costs by 40-60%

**How**: Import scripts → AI extracts intent → Generate Ansible/KubeVirt artifacts → Deploy to OpenShift

**Cost**: $0.10-$0.30 per script (LLM API) + internal team time

**Time**: 30-60 minutes per script vs. 2-4 weeks manual

---

## Quick Start (5 Minutes)

```bash
# 1. Install
pip install ops-translate

# 2. Initialize workspace
ops-translate init my-migration && cd my-migration

# 3. Import a PowerCLI script
ops-translate import --source powercli --file ../my-script.ps1

# 4. Analyze (no AI, no cost)
ops-translate summarize

# 5. Extract intent (uses mock provider by default, no API cost)
ops-translate intent extract

# 6. Generate Ansible + KubeVirt
ops-translate generate --profile lab

# 7. Review output
ls -R output/
```

**Result**: Ready-to-deploy Ansible playbooks and KubeVirt manifests in `output/` directory

---

## Essential Commands

### Workspace Setup
```bash
ops-translate init <workspace-name>           # Create new workspace
cd <workspace-name>                           # Enter workspace
```

### Import Automation
```bash
# Single PowerCLI file
ops-translate import --source powercli --file script.ps1

# Single vRealize workflow
ops-translate import --source vrealize --file workflow.xml

# Entire directory (auto-detect)
ops-translate import --source powercli --dir /path/to/scripts

# vRealize package bundle
ops-translate import --source vrealize --file bundle.package
```

### Analysis
```bash
# Static analysis (fast, free)
ops-translate summarize

# AI intent extraction (requires LLM API key)
export OPS_TRANSLATE_LLM_API_KEY="your-key"
ops-translate intent extract

# Merge multiple intent files
ops-translate intent merge

# Validate schemas
ops-translate dry-run
```

### Reporting
```bash
# Generate migration readiness report
ops-translate report

# Open report in browser
open report/index.html
```

### Generation
```bash
# Basic generation (YAML format)
ops-translate generate --profile lab

# Multiple formats
ops-translate generate --format json          # JSON output
ops-translate generate --format kustomize     # GitOps multi-env
ops-translate generate --format argocd        # ArgoCD apps

# Advanced options
ops-translate generate --no-ai                # Template-only
ops-translate generate --assume-existing-vms  # MTV mode
ops-translate generate --eda                  # Include EDA rulebooks
ops-translate generate --lint                 # Run ansible-lint
ops-translate generate --lint-strict          # Fail on lint warnings
```

### Decision Interview (for PARTIAL/BLOCKED components)
```bash
# Generate interview questions
ops-translate intent interview-generate

# Answer questions interactively
ops-translate intent interview-apply

# Regenerate with answers
ops-translate generate --profile lab
```

---

## Configuration File (`ops-translate.yaml`)

```yaml
# LLM Provider
llm:
  provider: anthropic           # anthropic, openai, or mock
  model: claude-sonnet-4-5      # Recommended model
  api_key_env: OPS_TRANSLATE_LLM_API_KEY
  rate_limit_delay: 1.0         # Seconds between API calls

# Environment Profiles
profiles:
  lab:
    default_namespace: virt-lab
    default_network: lab-network
    default_storage_class: nfs
    template_mappings:
      "RHEL8-Golden": "registry:quay.io/containerdisks/centos:8"
      "Windows-2022": "pvc:os-images/windows-server-2022"

  prod:
    default_namespace: virt-prod
    default_network: prod-network
    default_storage_class: ceph-rbd
    locking:
      backend: redis              # redis, consul, or file
    template_mappings:
      "RHEL8-Golden": "registry:quay.io/containerdisks/centos:8"

# Global settings
assume_existing_vms: false        # Default MTV mode for all profiles
```

---

## Output Structure

```
output/
├── kubevirt/
│   └── vm.yaml                   # KubeVirt VirtualMachine manifest
├── ansible/
│   ├── site.yml                  # Main playbook
│   ├── requirements.yml          # Ansible collections
│   ├── LOCKING_SETUP.md          # Distributed locking docs
│   └── roles/
│       └── provision_vm/
│           ├── tasks/main.yml    # Provisioning tasks
│           └── defaults/main.yml # Variables
├── report/
│   └── index.html                # Migration readiness report
└── README.md                     # Deployment instructions
```

---

## Classification System

| Class | Meaning | Example | Action Required |
|-------|---------|---------|-----------------|
| **SUPPORTED** | Fully automatic | New-VM, Set-VM, tagging | None - deploy as-is |
| **PARTIAL** | Needs configuration | Multi-NIC, NSX basic | Configure resources (NetworkAttachmentDefinition, etc.) |
| **BLOCKED** | Needs decisions | Environment-specific choices | Complete decision interview |
| **MANUAL** | Custom development | Complex JavaScript, custom plugins | Manual playbook development |

**Typical Distribution**: 70% SUPPORTED, 20% PARTIAL, 5% BLOCKED, 5% MANUAL

---

## Common Workflows

### Workflow 1: Simple Migration (Lab Environment)
```bash
# Setup
ops-translate init lab-migration && cd lab-migration

# Import
ops-translate import --source powercli --file ../simple-vm.ps1

# Analyze
ops-translate summarize
ops-translate intent extract

# Generate
ops-translate generate --profile lab

# Deploy
cd output/ansible
ansible-playbook site.yml
```
**Time**: 15 minutes

---

### Workflow 2: Production Migration with Governance
```bash
# Setup
ops-translate init prod-migration && cd prod-migration

# Import multiple sources
ops-translate import --source powercli --dir ../powercli-scripts
ops-translate import --source vrealize --file ../workflows.package

# Analyze
ops-translate summarize
ops-translate intent extract

# Merge and review
ops-translate intent merge
ops-translate report
open report/index.html

# Handle gaps
ops-translate intent interview-generate
ops-translate intent interview-apply

# Generate with validation
ops-translate generate --profile prod --lint
ops-translate dry-run

# Deploy via GitOps
cd output
git add . && git commit -m "Migration artifacts for prod"
git push origin main
```
**Time**: 2-3 hours

---

### Workflow 3: MTV Validation Mode
```bash
# Setup (VMs already migrated via MTV)
ops-translate init mtv-validation && cd mtv-validation

# Import original automation
ops-translate import --source powercli --dir ../original-scripts

# Extract and generate validation playbooks
ops-translate intent extract
ops-translate generate --assume-existing-vms --profile prod

# Run validation
cd output/ansible
ansible-playbook site.yml  # Validates VMs, applies governance
```
**Time**: 30 minutes

---

## LLM Provider Setup

### Anthropic Claude (Recommended)
```bash
# Get API key from https://console.anthropic.com/
export OPS_TRANSLATE_LLM_API_KEY="sk-ant-..."

# In ops-translate.yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-5  # Best balance of cost and quality
```
**Cost**: ~$0.15 per typical script

### OpenAI GPT (Alternative)
```bash
# Get API key from https://platform.openai.com/
export OPS_TRANSLATE_LLM_API_KEY="sk-..."

# In ops-translate.yaml
llm:
  provider: openai
  model: gpt-4-turbo-preview
```
**Cost**: ~$0.20 per typical script

### Mock Provider (Testing)
```bash
# No API key needed
# In ops-translate.yaml
llm:
  provider: mock
```
**Cost**: $0 (uses templates only, limited intelligence)

---

## Template Mappings

Map VMware template names to KubeVirt image sources:

### Registry (Container Disk)
```yaml
template_mappings:
  "RHEL8-Golden": "registry:quay.io/containerdisks/centos:8"
```

### PVC (Pre-loaded Image)
```yaml
template_mappings:
  "Windows-2022": "pvc:os-images/windows-server-2022"
  "Ubuntu-20.04": "pvc:default/ubuntu-20-04-image"
```

### HTTP/HTTPS URL
```yaml
template_mappings:
  "Custom-App": "http:https://images.example.com/custom-app.qcow2"
```

### Blank Disk
```yaml
template_mappings:
  "Empty": "blank"
```

---

## Troubleshooting Quick Fixes

### "LLM API key not found"
```bash
export OPS_TRANSLATE_LLM_API_KEY="your-key"
```

### "Conflict detected during merge"
```bash
# Review conflicts
cat intent/conflicts.md

# Force merge (use last value)
ops-translate intent merge --force

# OR manually edit intent/intent.yaml
```

### "Schema validation failed"
```bash
# Check error details
ops-translate dry-run

# Review schema docs
cat docs/INTENT_SCHEMA.md

# Fix intent/intent.yaml manually
```

### Generated playbooks fail lint
```bash
# Review issues
ops-translate generate --lint

# Fix common issues in generated files or create custom templates
```

### VMs fail to start
```bash
# Check logs
oc logs -n <namespace> virt-launcher-<vm-name>-xxxxx

# Verify template mapping
oc get pvc -n <namespace>  # For PVC-based images

# Check storage class
oc get storageclass
```

---

## Key Files Reference

| File | Purpose | When Created |
|------|---------|--------------|
| `ops-translate.yaml` | Configuration | `ops-translate init` |
| `manifest.json` | Imported files index | `ops-translate import` |
| `intent/summary.md` | Static analysis | `ops-translate summarize` |
| `intent/*.intent.yaml` | Per-file extracted intent | `ops-translate intent extract` |
| `intent/intent.yaml` | Merged consolidated intent | `ops-translate intent merge` |
| `intent/assumptions.md` | AI assumptions log | `ops-translate intent extract` |
| `intent/gaps.json` | Gap analysis | `ops-translate intent extract` (vRealize) |
| `intent/recommendations.json` | Expert guidance | `ops-translate intent extract` |
| `intent/conflicts.md` | Merge conflicts | `ops-translate intent merge` (if conflicts) |
| `report/index.html` | Migration readiness report | `ops-translate report` |
| `output/ansible/site.yml` | Main Ansible playbook | `ops-translate generate` |
| `output/kubevirt/vm.yaml` | KubeVirt manifest | `ops-translate generate` |

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `OPS_TRANSLATE_LLM_API_KEY` | LLM provider API key | For AI extraction |
| `KUBECONFIG` | OpenShift cluster config | For deployment |

---

## Deployment Quick Check

### Before deploying generated artifacts:

1. **Validate schemas**
   ```bash
   ops-translate dry-run
   ```

2. **Lint Ansible playbooks**
   ```bash
   cd output/ansible
   ansible-lint
   ```

3. **Check cluster prerequisites**
   ```bash
   # KubeVirt installed?
   oc get pods -n openshift-cnv

   # Storage class exists?
   oc get storageclass

   # Network attachments exist? (if multi-NIC)
   oc get network-attachment-definitions
   ```

4. **Test in lab first**
   ```bash
   # Deploy to lab namespace
   cd output/ansible
   ansible-playbook site.yml -e namespace=virt-lab
   ```

5. **Review assumptions**
   ```bash
   # Check what AI inferred
   cat intent/assumptions.md
   ```

---

## Presentation Talking Points

### For Executives
- **95% faster**: Hours instead of weeks per script
- **40-60% cost reduction**: Typical mid-size migration saves $200-300K
- **Risk mitigation**: Read-only analysis, comprehensive validation, expert guidance
- **Timeline**: Weeks to months vs. months to years for manual

### For Technical Teams
- **70-90% automation**: Most scripts fully or partially automated
- **GitOps ready**: Kustomize and ArgoCD output formats
- **Validation built-in**: Dry-run, lint, schema validation
- **Transparent**: All AI assumptions logged for review

### For Security/Compliance
- **Read-only**: No access to live systems required
- **Audit trail**: Complete logging of assumptions and decisions
- **No hardcoded secrets**: Follows Ansible best practices
- **Gap analysis**: Clear visibility into security control changes

---

## Success Metrics to Track

### Technical
- % of scripts SUPPORTED vs. PARTIAL/BLOCKED/MANUAL
- Time from source files to deployable artifacts
- % of generated artifacts that deploy successfully
- Number of manual fixes required

### Business
- Total cost (tool + LLM + internal effort)
- Timeline vs. estimated manual timeline
- Team satisfaction score
- Knowledge retention (% of operational logic preserved)

---

## Getting Help

| Resource | Location |
|----------|----------|
| **Quick Start** | README.md |
| **Full User Guide** | docs/USER_GUIDE.md |
| **User Stories** | USER_STORIES.md |
| **FAQ** | FAQ.md |
| **Tutorial** | docs/TUTORIAL.md |
| **Architecture** | docs/ARCHITECTURE.md |
| **Intent Schema** | docs/INTENT_SCHEMA.md |
| **Issues/Support** | Project repository |

---

## Demo Script

```bash
# 5-minute demo walkthrough
./demo.sh

# Fast mode (minimal delays)
./demo.sh --fast

# Keep workspace for exploration
./demo.sh --no-cleanup
```

---

## Common Customizations

### Custom Namespace per Environment
```yaml
profiles:
  dev:
    default_namespace: virt-dev
  prod:
    default_namespace: virt-prod
```

### Custom Network Mappings
```yaml
profiles:
  prod:
    network_mappings:
      "Production-VLAN-100": "prod-network-nad"
      "Management-VLAN-10": "mgmt-network-nad"
```

### Custom Storage Classes per Use Case
```yaml
profiles:
  prod:
    storage_class_mappings:
      performance: "ceph-rbd"
      capacity: "nfs-slow"
      archive: "s3-backed"
```

---

## Cheat Sheet: Command Summary

```bash
# Workspace
ops-translate init <name>

# Import
ops-translate import --source [powercli|vrealize] --file <file>
ops-translate import --source [powercli|vrealize] --dir <dir>

# Analysis
ops-translate summarize
ops-translate intent extract
ops-translate intent merge [--force]

# Reporting
ops-translate report

# Decision Interview
ops-translate intent interview-generate
ops-translate intent interview-apply

# Validation
ops-translate dry-run

# Generation
ops-translate generate [--profile <prof>] [--format <fmt>]
  --format: yaml|json|kustomize|argocd
  --no-ai: Template-only
  --assume-existing-vms: MTV mode
  --eda: Event-Driven Ansible
  --lint: Run ansible-lint
  --lint-strict: Fail on warnings

# Global Options
--log-level: ERROR|WARN|INFO|DEBUG
--help: Command help
```

---

**Print this page for quick reference during demos and migrations!**

**Version**: 1.0 | **Updated**: 2026-02-16
