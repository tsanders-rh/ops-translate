# ops-translate

[![CI](https://github.com/tsanders-rh/ops-translate/actions/workflows/ci.yml/badge.svg)](https://github.com/tsanders-rh/ops-translate/actions/workflows/ci.yml)
[![Lint](https://github.com/tsanders-rh/ops-translate/actions/workflows/lint.yml/badge.svg)](https://github.com/tsanders-rh/ops-translate/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/tsanders-rh/ops-translate/branch/main/graph/badge.svg)](https://codecov.io/gh/tsanders-rh/ops-translate)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> **AI-assisted migration from VMware automation to OpenShift Virtualization**

Stop manually rewriting your PowerCLI scripts and vRealize workflows. Let AI extract operational intent and generate production-ready Ansible + KubeVirt artifacts — safely, transparently, and locally.

## What It Does

`ops-translate` bridges the gap between VMware automation and cloud-native infrastructure:

1. **Import** your existing PowerCLI scripts and vRealize Orchestrator workflows
2. **Extract** a normalized operational intent model using AI
3. **Merge** multiple sources into a single unified intent
4. **Generate** Ansible playbooks and KubeVirt manifests ready for OpenShift

All processing happens locally. No execution by default. Full transparency at every step.

## Quick Start

### Try with Example Scripts

```bash
# Install from source
git clone https://github.com/tsanders-rh/ops-translate.git
cd ops-translate

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies and package
pip install -r requirements.txt
pip install -e .

# Initialize workspace
ops-translate init demo && cd demo

# Try with a provided example
ops-translate import --source powercli --file ../examples/powercli/environment-aware.ps1

# Extract and view operational intent
ops-translate summarize
ops-translate intent extract

# Review migration readiness BEFORE generating
ops-translate report
open output/report/index.html  # Interactive report with expert recommendations

# After reviewing the report, generate artifacts
ops-translate generate --profile lab                    # YAML (default)
ops-translate generate --profile lab --format kustomize # GitOps
ops-translate generate --profile lab --format argocd    # ArgoCD

# OR if VMs were already migrated via MTV, generate validation playbooks
ops-translate generate --profile lab --assume-existing-vms

# Review generated files
tree output/
```

**Preview the report**: See a [sample HTML report](examples/sample-report/) generated from real-world examples to understand what ops-translate produces.

See [examples/](examples/) for more sample PowerCLI scripts and vRealize workflows.

### Using Your Own Scripts

```bash
# Initialize workspace (optionally with custom templates)
ops-translate init my-project --with-templates && cd my-project

# Import your VMware automation
ops-translate import --source powercli --file /path/to/your-script.ps1
ops-translate import --source vrealize --file /path/to/workflow.xml

# Extract and merge operational intent
ops-translate summarize
ops-translate intent extract
ops-translate intent merge

# Validate the extracted intent
ops-translate dry-run

# Generate OpenShift artifacts in your preferred format
ops-translate generate --profile lab                    # YAML
ops-translate generate --profile lab --format kustomize # GitOps with Kustomize
ops-translate generate --profile prod --format argocd   # ArgoCD Applications
```

**Result**: Ansible roles, KubeVirt VM manifests, and a clear migration path in your choice of format.

## Why ops-translate?

- **Safe by design**: Read-only operations, no live system access in v1
- **Transparent**: Every assumption and inference is logged
- **Flexible**: Supports AI-assisted or template-based generation (`--no-ai`)
- **Conflict detection**: Identifies incompatibilities between source automations
- **Day 2 aware**: Captures operational patterns beyond just provisioning

## When Do You Need an LLM?

**Short answer**: Only for intent extraction. Everything else works without AI.

### LLM Required ✅ (One Step Only)

**`ops-translate intent extract`** - Convert PowerCLI/vRealize to normalized intent
- **Why**: Understands semantic meaning of imperative code
- **Alternative**: Write intent.yaml files manually (see [INTENT_SCHEMA.md](docs/INTENT_SCHEMA.md))
- **Options**: OpenAI, Anthropic, or mock provider (for testing)

### No LLM Needed ❌ (Everything Else)

All other commands are **deterministic** and **LLM-free**:
- `ops-translate import` - Copies files
- `ops-translate summarize` - Static pattern matching
- `ops-translate intent merge` - YAML reconciliation
- `ops-translate dry-run` - Schema validation
- `ops-translate generate` - Template-based (Jinja2)

**Visual breakdown:**
```
PowerCLI/vRealize  ──[LLM]──>  intent.yaml  ──[Templates]──>  Ansible + KubeVirt
   (legacy)         NEEDS AI    (normalized)   NO AI NEEDED    (cloud-native)
```

### Three Modes

1. **AI-Assisted Extraction** (Recommended)
   - Use LLM for extraction, templates for generation
   - Best accuracy for complex scripts

2. **Manual Intent Creation** (No LLM Required)
   - Write intent.yaml files yourself
   - 100% deterministic, works offline

3. **Mock Provider** (Testing/Demo)
   - No API key needed
   - Uses predefined templates

### Cost & Requirements

- **Extraction**: One-time LLM cost per source file (typically $0.01-0.10 per file)
- **Generation**: Free (template-based)
- **Offline use**: Possible after initial extraction (or with manual intent files)

**Bottom line**: LLM extracts *what* your automation does. Templates generate *how* to do it in OpenShift.

## Key Features

- Parse PowerCLI parameters, environment branching, and resource profiles
- Extract vRealize workflow logic including approvals and governance
- **Automatic gap analysis for vRealize workflows** - Detects NSX operations, custom plugins, and REST calls
- **Translatability assessment** - Classifies components as SUPPORTED, PARTIAL, EXPERT-GUIDED, or CUSTOM
- **Migration path guidance** - Provides specific recommendations with production-grade patterns
- **Smart Ansible scaffolding** - Generates TODO tasks and role stubs for manual work
- **MTV (Migration Toolkit for Virtualization) support** - Generate validation playbooks for already-migrated VMs
- Detect conflicts during intent merge (different approval requirements, network mappings, etc.)
- Generate KubeVirt VirtualMachine manifests
- Generate Ansible roles with proper structure and defaults
- Support multiple LLM providers (OpenAI, Anthropic, or mock for testing)

## Advanced Features

### Multiple Output Formats

ops-translate can generate artifacts in several formats to support different deployment strategies:

#### YAML (Default)
Standard Kubernetes manifests and Ansible playbooks:
```bash
ops-translate generate --profile lab --format yaml
```

Generates:
- `output/kubevirt/vm.yaml` - KubeVirt VirtualMachine manifest
- `output/ansible/site.yml` - Ansible playbook
- `output/ansible/roles/provision_vm/` - Ansible role structure

#### JSON Format
For API integration and programmatic consumption:
```bash
ops-translate generate --profile lab --format json
```

Generates JSON equivalents of all YAML manifests in `output/json/`. Perfect for:
- REST API payloads
- CI/CD pipeline integration
- Programmatic artifact manipulation

#### Kustomize/GitOps
Multi-environment GitOps structure with Kustomize:
```bash
ops-translate generate --profile lab --format kustomize
# or
ops-translate generate --profile lab --format gitops
```

Generates a full Kustomize directory structure:
```
output/
├── base/
│   ├── kustomization.yaml
│   └── vm.yaml
└── overlays/
    ├── dev/
    │   └── kustomization.yaml      # 2Gi memory, 1 CPU
    ├── staging/
    │   └── kustomization.yaml      # 4Gi memory, 2 CPUs
    └── prod/
        └── kustomization.yaml      # 8Gi memory, 4 CPUs
```

Each overlay automatically adjusts resources for its environment. Deploy with:
```bash
kubectl apply -k output/overlays/dev
kubectl apply -k output/overlays/prod
```

#### ArgoCD Applications
Full GitOps deployment with ArgoCD Application manifests:
```bash
ops-translate generate --profile lab --format argocd
```

Generates both Kustomize structure and ArgoCD resources:
```
output/
├── base/                          # Kustomize base
├── overlays/                      # Environment overlays
└── argocd/
    ├── project.yaml               # AppProject definition
    ├── dev-application.yaml       # Dev app (automated sync)
    ├── staging-application.yaml   # Staging app (partial automation)
    └── prod-application.yaml      # Prod app (manual sync)
```

Features:
- **dev**: Automated sync with prune and self-heal
- **staging**: Automated sync with prune only
- **prod**: Manual sync for safety

Apply to your cluster:
```bash
kubectl apply -f output/argocd/project.yaml
kubectl apply -f output/argocd/dev-application.yaml
```

### Template Customization

Customize generated artifacts to match your organization's standards:

```bash
# Initialize workspace with editable templates
ops-translate init my-project --with-templates
```

This copies all default templates to `templates/` in your workspace:
```
my-project/
├── templates/
│   ├── kubevirt/
│   │   └── vm.yaml.j2           # Jinja2 template for VMs
│   └── ansible/
│       ├── playbook.yml.j2      # Playbook template
│       └── role_tasks.yml.j2    # Role tasks template
└── ops-translate.yaml
```

**Edit templates** to add:
- Organization-specific labels and annotations
- Custom resource requests/limits
- Additional Ansible tasks or variables
- Company-specific naming conventions

When you run `generate`, ops-translate automatically uses your custom templates instead of defaults.

**Benefits:**
- Maintain consistency across migrations
- Encode organizational best practices
- No need to post-process generated artifacts

### MTV (Migration Toolkit for Virtualization) Mode

When VMs have already been migrated to OpenShift Virtualization using MTV, ops-translate can generate validation and day-2 operations playbooks instead of VM creation manifests:

```bash
# Generate validation playbooks for already-migrated VMs
ops-translate generate --profile lab --assume-existing-vms
```

**What changes in MTV mode:**

| Aspect | Greenfield Mode | MTV Mode |
|--------|----------------|----------|
| **VM YAML** | ✅ Generated (`output/kubevirt/vm.yaml`) | ❌ Skipped |
| **Ansible Tasks** | Create VM, wait for ready | Verify exists, validate config, apply labels |
| **Use Case** | New VM deployments | Post-migration validation |

**Generated Ansible tasks in MTV mode:**

1. **Verify VM exists** - Fails if VM not found
   ```yaml
   - name: Verify VM exists
     kubernetes.core.k8s_info:
       api_version: kubevirt.io/v1
       kind: VirtualMachine
       name: "{{ vm_name }}"
       namespace: virt-lab
     register: vm_info
     failed_when: vm_info.resources | length == 0
   ```

2. **Validate configurations** - Assert CPU/memory match intent
   ```yaml
   - name: Validate VM CPU configuration
     ansible.builtin.assert:
       that:
         - vm_info.resources[0].spec.template.spec.domain.cpu.cores == cpu_cores
       fail_msg: "CPU doesn't match intent"
   ```

3. **Apply operational labels** - Tag VMs with managed-by, environment
   ```yaml
   - name: Apply operational labels to VM
     kubernetes.core.k8s:
       state: patched
       definition:
         metadata:
           labels:
             managed-by: ops-translate
             environment: "{{ environment }}"
   ```

**Configure as default** (optional):
```yaml
# ops-translate.yaml
assume_existing_vms: true  # Always use MTV mode
```

**When to use MTV mode:**
- VMs were migrated using Migration Toolkit for Virtualization
- VMs already exist and need governance applied
- You want to validate existing VMs against operational intent
- Post-migration day-2 operations

### Enhanced Dry-Run Validation

Validate your intent and generated artifacts before execution:

```bash
ops-translate dry-run
```

Performs comprehensive checks:
- **Schema validation**: Intent YAML structure correctness
- **Resource validation**: Generated manifests are valid Kubernetes/Ansible
- **Consistency checks**: Metadata tags match intent specifications
- **Completeness**: All required inputs are defined with proper types

Output includes:
```
Dry-Run Validation Report
========================

✓ Schema validation passed
✓ 2 KubeVirt manifests validated
✓ 1 Ansible playbook validated

⚠ Review Items:
  - Input 'owner_email' has no default value
  - Consider adding min/max constraints to 'cpu' input

Execution Plan:
1. Validate inputs: vm_name, environment, cpu, memory_gb
2. Select profile based on environment
3. Generate KubeVirt manifest with tags
4. Generate Ansible playbook
5. Execute Ansible role tasks
6. Verify VM creation
7. Tag resources with metadata

Status: SAFE TO PROCEED (with 2 review items)
```

**Categories:**
- 🔴 **BLOCKING**: Must fix before execution
- 🟡 **REVIEW**: Should verify but not blocking
- 🟢 **SAFE**: No issues found

### Automatic Gap Analysis (vRealize Workflows)

When extracting intent from vRealize workflows, ops-translate automatically analyzes them for translatability issues and provides migration guidance:

```bash
ops-translate intent extract
```

**What gets analyzed:**
- NSX-T operations (segments, firewall rules, load balancers, security groups)
- Custom vRO plugins (ServiceNow, Infoblox, etc.)
- REST API calls to external systems
- vRealize-specific constructs

**Output:**

1. **Console warnings** - Immediate feedback during extraction:
```
Running gap analysis on vRealize workflows...
  Analyzing: nsx-provisioning.xml
    ⚠ Found 3 blocking issue(s)
  ✓ Gap analysis reports written to intent/gaps.md and intent/gaps.json

⚠ Warning: Found 3 component(s) that cannot be automatically translated.
  Review intent/gaps.md for migration guidance and manual implementation steps.
```

2. **Gap reports** - Detailed analysis in `intent/`:
   - `gaps.md` - Human-readable report with migration paths and recommendations
   - `gaps.json` - Machine-readable for tooling integration

3. **Smart scaffolding** - When you run `generate`, Ansible playbooks include:
   - **TODO tasks** for PARTIAL components (need configuration)
   - **Role stubs** for EXPERT-GUIDED/CUSTOM components (need implementation)
   - **Migration guidance** embedded as comments

**Classification levels:**
- ✅ **SUPPORTED** - Fully automatic translation to OpenShift-native
- ⚠️ **PARTIAL** - Can translate with manual configuration needed
- 🎯 **EXPERT-GUIDED** - Production-grade patterns available from Red Hat experts
- 🔧 **CUSTOM** - Complex custom logic requiring specialist review

**Migration paths:**
- **PATH_A**: OpenShift-native replacement available (e.g., NetworkPolicy for NSX firewall)
- **PATH_B**: Hybrid approach - keep existing system temporarily
- **PATH_C**: Custom specialist implementation required

**Example gap report snippet:**
```markdown
## NSX Firewall Rule

**Type**: `nsx_firewall_rule`
**Classification**: ⚠️ PARTIAL
**OpenShift Equivalent**: NetworkPolicy
**Migration Path**: PATH_A - OpenShift-native replacement

**Recommendations**:
- Create NetworkPolicy manifest with equivalent rules
- Test pod-to-pod connectivity
- Consider Calico for advanced features
- Review default-deny policies

**Evidence**:
nsxClient.createFirewallRule() at line 45
```

**Generated Ansible includes TODO tasks:**
```yaml
- name: "TODO: Implement NSX firewall rule migration"
  debug:
    msg: |
      CLASSIFICATION: PARTIAL
      OPENSHIFT EQUIVALENT: NetworkPolicy
      MIGRATION PATH: PATH_A - OpenShift-native replacement

      RECOMMENDATIONS:
      - Create NetworkPolicy manifest with equivalent rules
      - Test pod-to-pod connectivity
  tags: [manual_review_required]
```

This gives you a clear migration roadmap before writing any code.

## Example Output

After running `ops-translate generate`, you'll have:

```
output/
├── kubevirt/
│   └── vm.yaml                    # KubeVirt VirtualMachine manifest
├── ansible/
│   ├── site.yml                   # Main playbook with TODO tasks for gaps
│   └── roles/
│       ├── provision_vm/
│       │   ├── tasks/main.yml
│       │   └── defaults/main.yml
│       └── nsx_segment_migration/ # Auto-generated stub for manual work
│           ├── README.md          # Migration guidance
│           ├── tasks/main.yml     # TODO placeholders
│           └── defaults/main.yml  # Discovered parameters
├── intent/
│   ├── gaps.md                    # Human-readable gap analysis
│   └── gaps.json                  # Machine-readable gap data
└── README.md                      # How to run the artifacts
```

## Configuration

The `ops-translate init` command automatically creates `ops-translate.yaml` with default settings. You can customize it for your environment.

### LLM Provider Setup

ops-translate supports three LLM providers for intent extraction:

#### Option 1: Anthropic Claude (Recommended)

1. **Get an API key** from [https://console.anthropic.com](https://console.anthropic.com)
2. **Set the environment variable**:
   ```bash
   export OPS_TRANSLATE_LLM_API_KEY=sk-ant-your-key-here
   ```
3. **Configure in `ops-translate.yaml`**:
   ```yaml
   llm:
     provider: anthropic
     model: claude-sonnet-4-5        # Recommended for cost/quality balance
     # model: claude-opus-4           # Use for complex workflows
     api_key_env: OPS_TRANSLATE_LLM_API_KEY
   ```

**Supported models**: `claude-sonnet-4-5`, `claude-opus-4`, `claude-sonnet-3-5`

#### Option 2: OpenAI

1. **Get an API key** from [https://platform.openai.com](https://platform.openai.com)
2. **Set the environment variable**:
   ```bash
   export OPS_TRANSLATE_LLM_API_KEY=sk-your-openai-key-here
   ```
3. **Configure in `ops-translate.yaml`**:
   ```yaml
   llm:
     provider: openai
     model: gpt-4-turbo-preview
     api_key_env: OPS_TRANSLATE_LLM_API_KEY
   ```

**Supported models**: `gpt-4-turbo-preview`, `gpt-4`, `gpt-3.5-turbo`

#### Option 3: Mock Provider (Testing)

Use the mock provider to test without API calls or costs:

```yaml
llm:
  provider: mock
  model: mock-model
```

The mock provider returns pre-defined intent YAML based on file type. Perfect for:
- Testing the CLI workflow
- CI/CD pipelines
- Demos without API dependencies

**Note**: If no API key is found, ops-translate automatically falls back to the mock provider with a warning.

### Environment Profiles

Configure target OpenShift environments:

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

Use profiles with the `generate` command:
```bash
ops-translate generate --profile lab   # Uses lab settings
ops-translate generate --profile prod  # Uses prod settings
```

## Non-Goals (v1)

This is a v1 prototype focused on demonstrating the translation workflow. Not included:

- Live VMware/vCenter access
- Full Ansible Automation Platform workflow import
- Production-grade correctness guarantees

**Note**: NSX operations are now detected and analyzed via gap analysis, providing migration guidance even though automatic conversion is not always possible.

See [SPEC.md](SPEC.md) for complete design details.

## Installation

> **Note**: ops-translate is not yet published to PyPI. Install from source for now.

```bash
# Clone the repository
git clone https://github.com/tsanders-rh/ops-translate.git
cd ops-translate

# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development (includes testing/linting tools)
pip install -r requirements-dev.txt

# Install the package in editable mode
pip install -e .
```

**Requirements:**
- Python 3.10 or higher
- pip and virtualenv (recommended)
- Optional: OpenAI or Anthropic API key for AI-assisted extraction

## Documentation

### Getting Started

- **[Tutorial](docs/TUTORIAL.md)** - Step-by-step walkthrough of a complete migration
  - Hands-on tutorial with real examples
  - Dev/prod VM provisioning scenario
  - Advanced governance workflows
  - **Start here if you're new to ops-translate!**

- **[User Guide](docs/USER_GUIDE.md)** - Complete usage guide
  - Installation and setup
  - All CLI commands with examples
  - Configuration reference
  - Best practices and troubleshooting
  - **Your comprehensive reference**

### Technical Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design and internals
  - Component architecture
  - Data flow and state management
  - Intent schema specification
  - LLM integration patterns
  - **For understanding how it works**

- **[API Reference](docs/API_REFERENCE.md)** - Programmatic usage
  - Python API documentation
  - Extending ops-translate
  - Custom providers and generators
  - Type hints and examples
  - **For developers and integrators**

### Additional Resources

- [SPEC.md](SPEC.md) - Original design specification
- [examples/](examples/) - Sample PowerCLI and vRealize inputs with full walkthrough
- [schema/](schema/) - Operational intent schema definition

### Example Workflows

The [examples/](examples/) directory contains ready-to-use samples:

**PowerCLI Scripts:**
- `simple-vm.ps1` - Basic VM provisioning
- `environment-aware.ps1` - Environment branching (dev/prod)
- `with-governance.ps1` - Governance policies and approvals
- `multi-nic-storage.ps1` - Advanced networking and storage

**vRealize Workflows:**
- `simple-provision.workflow.xml` - Basic workflow
- `environment-branching.workflow.xml` - Environment-based logic
- `with-approval.workflow.xml` - Approval and governance

See [examples/README.md](examples/README.md) for detailed usage instructions.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/tsanders-rh/ops-translate
cd ops-translate

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .
```

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=ops_translate

# Run specific test file
pytest tests/test_integration.py -v

# Run with coverage report
pytest tests/ --cov=ops_translate --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Code Quality

```bash
# Format code with black
black ops_translate/ tests/

# Lint with ruff
ruff check ops_translate/ tests/

# Type check with mypy
mypy ops_translate/

# Run all checks (what CI runs)
black --check ops_translate/ tests/
ruff check ops_translate/ tests/
pytest tests/ -v --cov=ops_translate
```

### CI/CD

All PRs automatically run:
- Tests on Python 3.10, 3.11, 3.12, 3.13
- Code formatting checks (black)
- Linting (ruff)
- Type checking (mypy)
- Coverage reporting

## Contributing

This is an early-stage prototype. Contributions welcome:

- Try it with your own PowerCLI/vRealize automation
- Report issues and edge cases
- Suggest improvements to the intent schema
- Add support for additional VMware automation patterns
- Add tests for new features

## License

Apache-2.0 - See [LICENSE](LICENSE)

## Project Status

**v1 Prototype** - Demonstrating core workflow. Not for production use.

Built for ops and infra engineers evaluating migration paths from VMware to OpenShift Virtualization.
