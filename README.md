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
pip install -e .

# Initialize workspace
ops-translate init demo && cd demo

# Try with a provided example
ops-translate import --source powercli --file ../examples/powercli/environment-aware.ps1

# Extract and view operational intent
ops-translate summarize
ops-translate intent extract

# Validate before generating
ops-translate dry-run

# Generate OpenShift artifacts (try different formats!)
ops-translate generate --profile lab                    # YAML (default)
ops-translate generate --profile lab --format kustomize # GitOps
ops-translate generate --profile lab --format argocd    # ArgoCD

# Review generated files
tree output/
```

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

## Key Features

- Parse PowerCLI parameters, environment branching, and resource profiles
- Extract vRealize workflow logic including approvals and governance
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

## Example Output

After running `ops-translate generate`, you'll have:

```
output/
├── kubevirt/
│   └── vm.yaml                    # KubeVirt VirtualMachine manifest
├── ansible/
│   ├── site.yml                   # Main playbook
│   └── roles/
│       └── provision_vm/
│           ├── tasks/main.yml
│           └── defaults/main.yml
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
- NSX network policy conversion
- Full Ansible Automation Platform workflow import
- Production-grade correctness guarantees

See [SPEC.md](SPEC.md) for complete design details.

## Installation

> **Note**: ops-translate is not yet published to PyPI. Install from source for now.

```bash
# Clone the repository
git clone https://github.com/tsanders-rh/ops-translate.git
cd ops-translate

# Install in development mode (recommended)
pip install -e .

# Or install normally
pip install .
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

# Install with dev dependencies
pip install -e ".[dev]"
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
