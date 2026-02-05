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
# Install
pip install ops-translate

# Initialize workspace
ops-translate init demo && cd demo

# Try with a provided example
ops-translate import --source powercli --file ../examples/powercli/environment-aware.ps1

# Extract and view operational intent
ops-translate summarize
ops-translate intent extract

# Generate OpenShift artifacts
ops-translate generate --profile lab

# Review generated files
tree output/
```

See [examples/](examples/) for more sample PowerCLI scripts and vRealize workflows.

### Using Your Own Scripts

```bash
# Initialize workspace
ops-translate init my-project && cd my-project

# Import your VMware automation
ops-translate import --source powercli --file /path/to/your-script.ps1
ops-translate import --source vrealize --file /path/to/workflow.xml

# Extract and merge operational intent
ops-translate summarize
ops-translate intent extract
ops-translate intent merge

# Generate OpenShift artifacts
ops-translate generate --profile lab
```

**Result**: Ansible roles, KubeVirt VM manifests, and a clear migration path.

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

## Requirements

- Python 3.10+
- Optional: OpenAI or Anthropic API key (for AI-assisted extraction)

## Installation

```bash
# From PyPI (once published)
pip install ops-translate

# From source
git clone https://github.com/tsanders-rh/ops-translate
cd ops-translate
pip install -e .
```

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
