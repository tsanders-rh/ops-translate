# ops-translate

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

```bash
# Install
pip install ops-translate

# Initialize workspace
ops-translate init demo && cd demo

# Import your VMware automation
ops-translate import --source powercli --file provision-vm.ps1
ops-translate import --source vrealize --file workflow.xml

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

Create `ops-translate.yaml` in your workspace:

```yaml
llm:
  provider: anthropic              # or openai, mock
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

- [SPEC.md](SPEC.md) - Complete specification and design
- [examples/](examples/) - Sample PowerCLI and vRealize inputs
- [schema/](schema/) - Operational intent schema definition

## Contributing

This is an early-stage prototype. Contributions welcome:

- Try it with your own PowerCLI/vRealize automation
- Report issues and edge cases
- Suggest improvements to the intent schema
- Add support for additional VMware automation patterns

## License

Apache-2.0 - See [LICENSE](LICENSE)

## Project Status

**v1 Prototype** - Demonstrating core workflow. Not for production use.

Built for ops and infra engineers evaluating migration paths from VMware to OpenShift Virtualization.
