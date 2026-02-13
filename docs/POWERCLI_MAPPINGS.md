# PowerCLI Cmdlet Mappings Guide

This guide explains how ops-translate translates PowerCLI cmdlets to Ansible tasks using the deterministic mapping system.

## Overview

The PowerCLI translation system uses **mapping-based translation** to convert VMware PowerCLI cmdlets to Kubernetes/KubeVirt Ansible tasks. This provides:

- **Deterministic output** - Same input always produces identical output
- **No LLM required** - Fast, offline translation for common patterns
- **Profile-driven** - Adapts to target environment configuration
- **Transparent** - Clear mapping files, easy to understand and extend

## How It Works

### Translation Pipeline

```
PowerCLI Script
     │
     ├─ PowerCLIScriptParser
     │  └─ Parses .ps1 file line-by-line
     │  └─ Extracts cmdlets, parameters, variables
     │  └─ Categorizes statements (context, lookup, mutation, integration, gate)
     │
     ├─ PowerShellToAnsibleTranslator
     │  └─ Loads powercli_cmdlet_mappings.yaml
     │  └─ Matches cmdlets to Ansible modules
     │  └─ Substitutes parameters
     │  └─ Generates profile-driven adapters or BLOCKED stubs
     │
     └─ AnsibleTask objects
        └─ YAML generator
        └─ tasks/main.yml
```

### Statement Categories

PowerCLI statements are categorized to determine how they should be translated:

| Category | PowerCLI Examples | Ansible Translation |
|----------|-------------------|---------------------|
| **context** | `$Network = "dev-network"` | `ansible.builtin.set_fact` |
| **lookup** | `Get-VM -Name MyVM` | `kubernetes.core.k8s_info` |
| **mutation** | `New-VM`, `Start-VM`, `Set-VM` | `kubevirt.core.kubevirt_vm` |
| **integration** | `New-TagAssignment`, `New-Snapshot` | Labels, VolumeSnapshot |
| **gate** | `if ($x -gt 16) { throw "..." }` | `ansible.builtin.assert` |

## Cmdlet Mapping File

The cmdlet mappings are defined in `ops_translate/translate/powercli_cmdlet_mappings.yaml`.

### Mapping Structure

Each mapping contains:

```yaml
category_name:
  mapping_name:
    match:
      cmdlet: <PowerCLI cmdlet name>
    ansible:
      module: <Ansible module>
      params:
        <param_name>: <value or template>
    category: <statement category>
    tags: [tag1, tag2]
    requires_profile: [profile.path.to.config]  # Optional
```

### Example: New-VM Cmdlet

```yaml
vm_operations:
  new_vm:
    match:
      cmdlet: New-VM
    ansible:
      module: kubevirt.core.kubevirt_vm
      params:
        state: present
        name: "{Name}"
        namespace: "{{ target_namespace }}"
        cpu_cores: "{NumCpu}"
        memory: "{MemoryGB}Gi"
    category: mutation
    tags: [mutation, vm]
```

**PowerCLI Input:**
```powershell
New-VM -Name "test-vm" -NumCpu 4 -MemoryGB 8
```

**Ansible Output:**
```yaml
- name: Create VM test-vm
  kubevirt.core.kubevirt_vm:
    state: present
    name: "test-vm"
    namespace: "{{ target_namespace }}"
    cpu_cores: "4"
    memory: "8Gi"
  tags: [mutation, vm]
```

## Parameter Substitution

The mapping system supports flexible parameter substitution:

### Simple Substitution

Template: `{ParamName}`
- Replaced with the cmdlet parameter value
- Example: `{Name}` → `"test-vm"`

### Substitution with Suffix

Template: `{ParamName}Gi`
- Preserves suffix after substitution
- Example: `{MemoryGB}Gi` → `"8Gi"`

### PowerShell Variables to Jinja2

PowerShell variables are automatically converted to Jinja2 templates:
- `$VMName` → `{{ vmname }}` (lowercased)
- `$NumCPU` → `{{ numcpu }}`

## Integration Translations

### Tagging → Kubernetes Labels

**PowerCLI:**
```powershell
New-TagAssignment -Entity MyVM -Tag "Environment:Dev"
```

**Ansible:**
```yaml
- name: Apply environment label to MyVM
  kubernetes.core.k8s:
    state: patched
    kind: VirtualMachine
    name: "MyVM"
    namespace: "{{ target_namespace }}"
    definition:
      metadata:
        labels:
          environment: "dev"
  tags: [integration, tagging]
```

**Mapping:**
```yaml
tagging:
  new_tag_assignment:
    match:
      cmdlet: New-TagAssignment
    ansible:
      module: kubernetes.core.k8s
      params:
        state: patched
        kind: VirtualMachine
        name: "{Entity}"
        definition:
          metadata:
            labels:
              "{tag_key}": "{tag_value}"
    category: integration
    integration_type: tagging
```

### Snapshots → VolumeSnapshot

**PowerCLI:**
```powershell
New-Snapshot -VM MyVM -Name snap1
```

**Ansible:**
```yaml
- name: Create snapshot snap1 for VM MyVM
  kubevirt.core.kubevirt_vm_snapshot:
    state: present
    name: "snap1"
    vm_name: "MyVM"
    namespace: "{{ target_namespace }}"
  tags: [integration, snapshot]
```

## Profile-Driven Translation

Some translations depend on profile configuration. When required profile sections are missing, ops-translate generates **BLOCKED stubs** with guidance.

### Network Adapters

**PowerCLI:**
```powershell
New-NetworkAdapter -VM MyVM -NetworkName "prod-network"
```

**With profile.network_security configured:**
```yaml
- name: Create network adapter for MyVM
  ansible.builtin.include_role:
    name: adapters/nsx/create_segment
  vars:
    vm_name: "MyVM"
    network_name: "prod-network"
  tags: [integration, network]
```

**Without profile.network_security:**
```yaml
- name: BLOCKED - Network adapter creation requires configuration
  ansible.builtin.fail:
    msg: |
      BLOCKED: Network Adapter Creation

      This script requires network adapter creation.
      Configure profile.network_security to proceed.

      Evidence: New-NetworkAdapter -NetworkName "prod-network"

      TO FIX: Add to profile.yml:
        network_security:
          model: networkpolicy

      Then re-run: ops-translate generate --profile <profile>
  tags: [blocked, network]
```

### Mapping with Profile Requirement

```yaml
network:
  new_network_adapter:
    match:
      cmdlet: New-NetworkAdapter
    ansible:
      module: ansible.builtin.include_role
      params:
        name: "adapters/nsx/create_segment"
    category: integration
    integration_type: network
    requires_profile:
      - profile.network_security.model
```

## Adding New Cmdlet Mappings

To add support for a new PowerCLI cmdlet:

### 1. Identify the Cmdlet Category

Determine which category fits:
- **context**: Environment setup, variable assignments
- **lookup**: Read-only operations (Get-* cmdlets)
- **mutation**: State-changing operations (New-*, Set-*, Start-*, Stop-*, Remove-*)
- **integration**: External system interactions

### 2. Add Mapping to YAML

Edit `ops_translate/translate/powercli_cmdlet_mappings.yaml`:

```yaml
category_name:
  mapping_name:
    match:
      cmdlet: <Cmdlet-Name>
    ansible:
      module: <ansible.module.name>
      params:
        param1: "{PowerCLIParam1}"
        param2: "static_value"
    category: <category>
    tags: [tag1, tag2]
```

### 3. Test the Mapping

Create a test PowerCLI script:

```powershell
# test.ps1
<Cmdlet-Name> -Param1 "value1" -Param2 "value2"
```

Import and generate:

```bash
ops-translate import --source powercli --file test.ps1
ops-translate generate --profile lab
```

Verify the generated `output/ansible/roles/*/tasks/main.yml` contains the expected Ansible task.

### 4. Add Test Coverage

Add a test in `tests/test_powershell_to_ansible_translator.py`:

```python
def test_translate_new_cmdlet(self):
    """Test translation of New-Cmdlet to ansible_module."""
    stmt = PowerCLIStatement(
        line_number=1,
        raw_text="New-Cmdlet -Param1 Value1 -Param2 Value2",
        statement_type="cmdlet",
        category="mutation",
        cmdlet="New-Cmdlet",
        parameters={"Param1": "Value1", "Param2": "Value2"},
    )

    translator = PowerShellToAnsibleTranslator()
    task = translator._translate_cmdlet(stmt)

    assert task is not None
    assert task.module == "ansible.module.name"
    assert task.module_args["param1"] == "Value1"
    assert task.module_args["param2"] == "Value2"
```

## Currently Supported Cmdlets

### VM Operations

| PowerCLI Cmdlet | Ansible Module | Description |
|-----------------|----------------|-------------|
| `New-VM` | `kubevirt.core.kubevirt_vm` | Create virtual machine |
| `Start-VM` | `kubevirt.core.kubevirt_vm` | Start VM (state: running) |
| `Stop-VM` | `kubevirt.core.kubevirt_vm` | Stop VM (state: stopped) |
| `Set-VM` | `kubevirt.core.kubevirt_vm` | Update VM configuration |
| `Remove-VM` | `kubevirt.core.kubevirt_vm` | Delete VM (state: absent) |

### Lookup Operations

| PowerCLI Cmdlet | Ansible Module | Description |
|-----------------|----------------|-------------|
| `Get-VM` | `kubernetes.core.k8s_info` | Query VM information |

### Integration Operations

| PowerCLI Cmdlet | Ansible Module | Description |
|-----------------|----------------|-------------|
| `New-TagAssignment` | `kubernetes.core.k8s` | Apply labels to VMs |
| `New-Snapshot` | `kubevirt.core.kubevirt_vm_snapshot` | Create VM snapshot |
| `New-NetworkAdapter` | Profile-driven | Create network adapter (requires profile.network_security) |

### Control Flow

| PowerCLI Pattern | Ansible Module | Description |
|------------------|----------------|-------------|
| `if ($x -gt N) { throw }` | `ansible.builtin.assert` | Validation gate |
| `$Var = "value"` | `ansible.builtin.set_fact` | Variable assignment |

## Limitations

### Not Translated

The following PowerCLI features are **not translated** by the mapping system:

1. **Complex PowerShell syntax**:
   - Classes, DSC, remoting
   - Custom functions and modules
   - Advanced scripting constructs

2. **Interactive cmdlets**:
   - `Read-Host`, `Get-Credential`, `Write-Host` with prompts

3. **GUI-specific cmdlets**:
   - No equivalent in Kubernetes/CLI environments

4. **Custom cmdlet libraries**:
   - Non-VMware PowerCLI modules

For these scenarios, use the **Intent Extraction** path instead:

```bash
ops-translate intent extract --profile lab
ops-translate generate --profile lab
```

This uses LLM to understand the semantic intent and generate appropriate Ansible tasks.

## Troubleshooting

### Cmdlet Not Recognized

**Symptom**: PowerCLI cmdlet is skipped in translation

**Solution**: Check if cmdlet is in `powercli_cmdlet_mappings.yaml`. If not, add a mapping or use intent extraction.

### BLOCKED Stub Generated

**Symptom**: Task shows "BLOCKED - ... requires configuration"

**Solution**: Add the required profile section. The BLOCKED message includes specific guidance:

```yaml
# profile.yml
network_security:
  model: networkpolicy
  default_isolation: namespace
```

### Parameter Not Substituted

**Symptom**: `{ParamName}` appears in output instead of value

**Solution**: Check parameter name matches exactly (case-sensitive). PowerCLI parameter names are case-insensitive, but mapping substitution is exact.

### Variable Not Converted

**Symptom**: `$VMName` appears instead of `{{ vmname }}`

**Solution**: Ensure variable is parsed correctly. Check `_parse_cmdlet_parameters()` regex handles the variable pattern.

## Best Practices

1. **Test incrementally**: Add one cmdlet mapping at a time and test immediately
2. **Use clear names**: Mapping names should reflect the cmdlet purpose
3. **Document requirements**: Use `requires_profile` to document dependencies
4. **Add test coverage**: Every new mapping should have a test case
5. **Follow conventions**: Match existing mapping structure and naming

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md#translate-module) - Translate Module architecture
- [USER_GUIDE.md](USER_GUIDE.md) - User guide for ops-translate commands
- [TUTORIAL.md](TUTORIAL.md) - Step-by-step tutorial with examples

## Contributing

To contribute new cmdlet mappings:

1. Fork the repository
2. Add mapping to `ops_translate/translate/powercli_cmdlet_mappings.yaml`
3. Add test coverage in `tests/test_powershell_to_ansible_translator.py`
4. Submit pull request with example PowerCLI script and expected output

For questions or suggestions, open an issue at https://github.com/tsanders-rh/ops-translate/issues
