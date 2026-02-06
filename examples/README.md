# ops-translate Examples

This directory contains example PowerCLI scripts and vRealize workflows to help you get started with ops-translate.

## Directory Structure

```
examples/
├── powercli/              # PowerCLI script examples
│   ├── simple-vm.ps1                  # Basic VM provisioning
│   ├── environment-aware.ps1          # Environment branching (dev/prod)
│   ├── provision-vm.ps1               # Comprehensive example with documentation
│   ├── with-governance.ps1            # Governance and quotas
│   └── multi-nic-storage.ps1          # Advanced networking and storage
│
└── vrealize/              # vRealize Orchestrator workflow examples
    ├── simple-provision.workflow.xml          # Basic workflow
    ├── environment-branching.workflow.xml     # Environment-based configuration
    ├── provision.workflow.xml                 # Full governance workflow
    └── with-approval.workflow.xml             # Approval and governance
```

## PowerCLI Examples

### 1. simple-vm.ps1

**What it demonstrates:**
- Basic VM provisioning
- Required parameters
- Minimal configuration

**Parameters:**
- `VMName` (string, required) - Name of the VM
- `CPUCount` (int, required) - Number of CPU cores
- `MemoryGB` (int, required) - Memory in GB

**Use case:** Simple VM creation without environment-specific logic.

---

### 2. environment-aware.ps1

**What it demonstrates:**
- Environment branching (dev vs prod)
- Conditional resource allocation
- Environment-specific networking and storage
- Tag application

**Parameters:**
- `VMName` (string, required) - Name of the VM
- `Environment` (string, required) - "dev" or "prod"
- `OwnerEmail` (string, required) - Email of the VM owner

**Use case:** Different configurations for development and production environments.

**Key features:**
- Production: 4 CPU, 16 GB RAM, gold storage, prod network
- Development: 2 CPU, 8 GB RAM, standard storage, dev network
- Automatic tagging with environment, owner, and management metadata

---

### 3. with-governance.ps1

**What it demonstrates:**
- Governance policies and approval requirements
- Resource quotas and validation
- Comprehensive metadata tagging
- Cost tracking

**Parameters:**
- `VMName` (string, required) - Name of the VM
- `Environment` (string, required) - "dev" or "prod"
- `CPUCount` (int, 1-32, required) - Number of CPU cores
- `MemoryGB` (int, 1-256, required) - Memory in GB
- `DiskGB` (int, 20-2000, required) - Disk size in GB
- `OwnerEmail` (string, required) - Email of the VM owner
- `CostCenter` (string, optional) - Cost center code
- `ApprovalTicket` (string, required for prod) - Approval ticket number

**Use case:** Enterprise environments requiring approval workflows and quota enforcement.

**Key features:**
- Production deployments require approval ticket
- Quota validation (max 16 CPU, max 128 GB RAM)
- Comprehensive tagging including cost center and approval tracking
- Environment-specific resource profiles

---

### 4. multi-nic-storage.ps1

**What it demonstrates:**
- Multiple network adapters
- Multiple storage volumes
- High availability configuration
- Advanced network and storage profiles

**Parameters:**
- `VMName` (string, required) - Name of the VM
- `Environment` (string, required) - "dev" or "prod"
- `CPUCount` (int, required) - Number of CPU cores
- `MemoryGB` (int, required) - Memory in GB
- `HighAvailability` (switch, optional) - Enable HA features

**Use case:** VMs requiring multiple network interfaces and storage volumes.

**Key features:**
- Primary network adapter (environment-specific)
- Management network adapter (all VMs)
- Storage network adapter (prod HA only)
- Multiple data disks
- HA-specific storage classes

---

## vRealize Workflow Examples

### 1. simple-provision.workflow.xml

**What it demonstrates:**
- Basic workflow structure
- Input parameters and validation
- Simple task execution
- Output parameters

**Inputs:**
- `vmName` (string) - Name of the VM
- `cpuCount` (number, 1-32) - Number of CPU cores
- `memoryGB` (number, 1-256) - Memory in GB

**Outputs:**
- `vmId` (string) - ID of created VM

**Use case:** Simple linear workflow without branching logic.

---

### 2. environment-branching.workflow.xml

**What it demonstrates:**
- Environment-based configuration
- Decision logic in workflows
- Attribute usage for intermediate values
- Tag application

**Inputs:**
- `vmName` (string) - Name of the VM
- `environment` (string) - "dev" or "prod"
- `ownerEmail` (string) - Email of the VM owner

**Outputs:**
- `vmId` (string) - ID of created VM

**Use case:** Workflows that need different behavior for different environments.

**Workflow steps:**
1. Determine environment configuration (CPU, RAM, network, storage)
2. Create VM with environment-specific settings
3. Apply metadata tags

---

### 3. with-approval.workflow.xml

**What it demonstrates:**
- Governance and approval workflows
- Decision elements for conditional execution
- Quota validation
- Approval requirement based on environment

**Inputs:**
- `vmName` (string) - Name of the VM
- `environment` (string) - "dev" or "prod"
- `cpuCount` (number, 1-32) - Number of CPU cores
- `memoryGB` (number, 1-256) - Memory in GB
- `ownerEmail` (string) - Email of the VM owner
- `costCenter` (string, optional) - Cost center code

**Outputs:**
- `vmId` (string) - ID of created VM
- `approved` (boolean) - Whether request was approved

**Use case:** Enterprise environments requiring approval for production deployments.

**Workflow steps:**
1. Check governance requirements and quotas
2. Decision: requires approval?
   - Yes (prod): Request approval
   - No (dev): Auto-approve
3. Provision VM if approved

---

## Getting Started

### Quick Start Guide

1. **Initialize a workspace:**
   ```bash
   ops-translate init my-project
   cd my-project
   ```

2. **Import an example:**
   ```bash
   # Import PowerCLI example
   ops-translate import --source powercli --file ../examples/powercli/environment-aware.ps1

   # Or import vRealize example
   ops-translate import --source vrealize --file ../examples/vrealize/environment-branching.workflow.xml
   ```

3. **Generate summary (no AI required):**
   ```bash
   ops-translate summarize
   cat intent/summary.md
   ```

4. **Extract intent (requires LLM):**
   ```bash
   # Configure your LLM provider first
   export OPS_TRANSLATE_LLM_API_KEY=your-api-key-here

   ops-translate intent extract
   ```

5. **Review migration readiness:**
   ```bash
   ops-translate report --format html --profile lab
   open output/report/index.html  # Review gaps and blockers
   ```

6. **Generate Ansible + KubeVirt artifacts:**
   ```bash
   # Using AI assistance
   ops-translate generate --profile lab

   # Or template-based (no AI)
   ops-translate generate --profile lab --no-ai
   ```

7. **Validate the output:**
   ```bash
   ops-translate dry-run
   ```

8. **Review generated files:**
   ```bash
   tree output/
   # output/
   # ├── ansible/
   # │   ├── site.yml
   # │   └── roles/provision_vm/
   # ├── kubevirt/
   # │   └── vm.yaml
   # └── README.md
   ```

---

## Example Workflow: Environment-Aware Provisioning

This example shows the complete workflow using `environment-aware.ps1`:

```bash
# 1. Initialize workspace
ops-translate init env-demo
cd env-demo

# 2. Import the PowerCLI script
ops-translate import \
  --source powercli \
  --file ../examples/powercli/environment-aware.ps1

# 3. Generate summary (no AI)
ops-translate summarize

# Output shows:
# - Parameters detected: VMName, Environment, OwnerEmail
# - Environment branching detected (dev/prod)
# - Tagging detected

# 4. Configure LLM (if using AI-assisted generation)
export OPS_TRANSLATE_LLM_API_KEY=sk-ant-...

# 5. Extract intent
ops-translate intent extract

# Review extracted intent
cat intent/environment-aware.ps1.intent.yaml

# 6. Review migration readiness
ops-translate report --format html --profile lab
open output/report/index.html

# 7. Generate artifacts for lab environment
ops-translate generate --profile lab

# 8. Review generated Ansible playbook
cat output/ansible/site.yml

# 9. Review generated KubeVirt manifest
cat output/kubevirt/vm.yaml

# 10. Validate everything
ops-translate dry-run
```

---

## Multi-Source Example

You can import multiple sources and merge them:

```bash
# Initialize workspace
ops-translate init multi-source-demo
cd multi-source-demo

# Import PowerCLI script
ops-translate import \
  --source powercli \
  --file ../examples/powercli/with-governance.ps1

# Import vRealize workflow
ops-translate import \
  --source vrealize \
  --file ../examples/vrealize/with-approval.workflow.xml

# Generate summaries
ops-translate summarize

# Extract intents from both sources
ops-translate intent extract

# Merge intents
ops-translate intent merge

# Review conflicts (if any)
cat intent/conflicts.md

# Review migration readiness before generating
ops-translate report --format html --profile prod
open output/report/index.html

# Generate combined artifacts
ops-translate generate --profile prod
```

---

## Tips and Best Practices

### Choosing Examples

- **Start simple:** Begin with `simple-vm.ps1` or `simple-provision.workflow.xml`
- **Add complexity:** Progress to environment-aware examples
- **Enterprise features:** Use governance examples for production scenarios

### LLM Configuration

For best results with AI-assisted generation:

1. **Anthropic Claude (recommended):**
   ```yaml
   llm:
     provider: anthropic
     model: claude-sonnet-4-5
     api_key_env: OPS_TRANSLATE_LLM_API_KEY
   ```

2. **OpenAI:**
   ```yaml
   llm:
     provider: openai
     model: gpt-4
     api_key_env: OPENAI_API_KEY
   ```

3. **Testing without API calls:**
   ```yaml
   llm:
     provider: mock
   ```

### Profile Configuration

Customize profiles in `ops-translate.yaml`:

```yaml
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

---

## Understanding the Translation

### What ops-translate Does

1. **Import:** Copies source files to `input/` directory
2. **Summarize:** Analyzes scripts without AI to detect patterns
3. **Extract:** Uses LLM to convert imperative code to declarative intent
4. **Merge:** Combines multiple intents, detecting conflicts
5. **Generate:** Produces Ansible playbooks and KubeVirt manifests

### Generated Outputs

- **Ansible Playbook** (`output/ansible/site.yml`): Automation to create VMs
- **Ansible Role** (`output/ansible/roles/provision_vm/`): Reusable VM provisioning logic
- **KubeVirt Manifest** (`output/kubevirt/vm.yaml`): VM definition for OpenShift
- **README** (`output/README.md`): Instructions for using the generated artifacts

---

## Troubleshooting

### No parameters detected

**Symptom:** Summary shows "No detectable features"

**Solution:** Check that your script uses PowerShell `param()` blocks or vRealize `<input>` elements.

### Intent extraction fails

**Symptom:** Error during `ops-translate intent extract`

**Solution:**
- Verify LLM API key is set correctly
- Check that the LLM provider is accessible
- Review `intent/assumptions.md` for extraction notes

### Validation errors

**Symptom:** `ops-translate dry-run` reports schema errors

**Solution:**
- Review the error messages in output
- Edit `intent/intent.yaml` to fix schema issues
- Re-run generation after fixing intent

---

## Next Steps

- **Customize generated artifacts:** Edit templates in `output/`
- **Add more sources:** Import additional scripts and workflows
- **Extend profiles:** Add environment-specific configurations
- **Contribute examples:** Share your own examples with the community

---

## Support

For questions and issues:
- GitHub Issues: https://github.com/tsanders-rh/ops-translate/issues
- Documentation: https://github.com/tsanders-rh/ops-translate/blob/main/README.md
