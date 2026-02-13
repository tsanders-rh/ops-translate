"""Ansible project structure generator with profile-driven adapters.

This module generates complete Ansible project scaffolding including:
- Full directory structure (roles/, inventories/, adapters/, docs/)
- site.yml playbook with role includes
- Multi-environment inventories from profile
- Adapter stubs rendered from templates based on profile configuration
- Documentation (README, profile guide, adapter guide)
"""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ops_translate.models.profile import ProfileSchema

# Get project root for template loading
PROJECT_ROOT = Path(__file__).parent.parent.parent


def generate_ansible_project(
    workflows: list[dict[str, Any]],
    profile: ProfileSchema,
    output_dir: Path,
) -> Path:
    """
    Generate complete Ansible project structure with profile-driven adapters.

    Args:
        workflows: List of workflow definitions to include in project
        profile: ProfileSchema driving adapter generation
        output_dir: Target directory for Ansible project

    Returns:
        Path to generated ansible-project directory
    """
    project_dir = output_dir / "ansible-project"

    # Create directory structure
    _create_project_structure(project_dir)

    # Generate project files
    _generate_site_playbook(workflows, project_dir)
    _generate_inventories(profile, project_dir)
    _generate_ansible_cfg(project_dir)
    _generate_adapters(profile, project_dir)
    _generate_workflow_roles(workflows, output_dir, project_dir, profile)
    _generate_documentation(profile, workflows, project_dir)

    return project_dir


def _create_project_structure(project_dir: Path) -> None:
    """
    Create Ansible project directory structure.

    Args:
        project_dir: Root project directory
    """
    # Create base directories
    directories = [
        project_dir,
        project_dir / "roles",
        project_dir / "adapters" / "nsx",
        project_dir / "adapters" / "servicenow",
        project_dir / "adapters" / "dns",
        project_dir / "adapters" / "ipam",
        project_dir / "docs",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def _generate_site_playbook(workflows: list[dict[str, Any]], project_dir: Path) -> None:
    """
    Generate site.yml playbook that includes all roles.

    Args:
        workflows: Workflow definitions
        project_dir: Project root directory
    """
    playbook = [
        {
            "name": "ops-translate generated playbook",
            "hosts": "all",
            "gather_facts": True,
            "roles": [workflow["name"] for workflow in workflows],
        }
    ]

    site_file = project_dir / "site.yml"
    site_file.write_text(yaml.dump(playbook, default_flow_style=False, sort_keys=False))


def _generate_inventories(profile: ProfileSchema, project_dir: Path) -> None:
    """
    Generate inventory files for each environment in profile.

    Args:
        profile: ProfileSchema with environment configurations
        project_dir: Project root directory
    """
    inventories_dir = project_dir / "inventories"

    for env_name, env_config in profile.environments.items():
        env_dir = inventories_dir / env_name
        env_dir.mkdir(parents=True, exist_ok=True)

        # Create hosts file
        hosts_content = f"""[all]
localhost ansible_connection=local

[openshift]
openshift_cluster ansible_host={env_config.openshift_api_url}
"""
        (env_dir / "hosts").write_text(hosts_content)

        # Create group_vars/all.yml
        group_vars_dir = env_dir / "group_vars"
        group_vars_dir.mkdir(parents=True, exist_ok=True)

        group_vars: dict[str, Any] = {
            "target_namespace": env_config.namespace or f"{profile.name}-{env_name}",
            "openshift_api_url": env_config.openshift_api_url,
        }

        if env_config.node_selectors:
            group_vars["node_selectors"] = env_config.node_selectors

        (group_vars_dir / "all.yml").write_text(
            yaml.dump(group_vars, default_flow_style=False, sort_keys=False)
        )


def _generate_ansible_cfg(project_dir: Path) -> None:
    """
    Generate ansible.cfg with project defaults.

    Args:
        project_dir: Project root directory
    """
    ansible_cfg = """[defaults]
inventory = inventories/dev
roles_path = roles
host_key_checking = False
retry_files_enabled = False
stdout_callback = yaml
callbacks_enabled = timer, profile_tasks

[inventory]
enable_plugins = host_list, yaml, ini

[privilege_escalation]
become = False
"""
    (project_dir / "ansible.cfg").write_text(ansible_cfg)


def _generate_adapters(profile: ProfileSchema, project_dir: Path) -> None:
    """
    Generate adapter stubs from templates based on profile configuration.

    Args:
        profile: ProfileSchema driving conditional template rendering
        project_dir: Project root directory
    """
    # Setup Jinja2 environment
    template_dir = PROJECT_ROOT / "templates" / "ansible" / "adapters"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Render each adapter template
    adapters = [
        ("nsx/create_segment.yml.j2", "adapters/nsx/create_segment.yml"),
        ("nsx/create_firewall_rule.yml.j2", "adapters/nsx/create_firewall_rule.yml"),
        ("servicenow/create_change.yml.j2", "adapters/servicenow/create_change.yml"),
        ("servicenow/create_incident.yml.j2", "adapters/servicenow/create_incident.yml"),
        ("dns/create_record.yml.j2", "adapters/dns/create_record.yml"),
        ("ipam/reserve_ip.yml.j2", "adapters/ipam/reserve_ip.yml"),
    ]

    for template_path, output_path in adapters:
        template = env.get_template(template_path)
        rendered = template.render(profile=profile)

        output_file = project_dir / output_path
        output_file.write_text(rendered)


def _generate_workflow_roles(
    workflows: list[dict[str, Any]],
    output_dir: Path,
    project_dir: Path,
    profile: ProfileSchema,
) -> None:
    """
    Generate role skeletons for all workflows.

    Args:
        workflows: List of workflow definitions
        output_dir: Output directory (parent of project_dir)
        project_dir: Ansible project root directory
        profile: ProfileSchema for profile-driven translation
    """
    workspace_root = output_dir.parent

    for workflow in workflows:
        try:
            # Skip template placeholders - they don't have real source files
            if workflow["source"] == "template":
                continue

            source_file = workspace_root / workflow["source_file"]

            if workflow["source"] == "vrealize":
                _generate_vrealize_role(workflow, source_file, project_dir)
            elif workflow["source"] == "powercli":
                _generate_powercli_role(workflow, source_file, project_dir, profile)
        except Exception as e:
            # Log but continue - graceful degradation
            print(f"Warning: Failed to generate role {workflow['name']}: {e}")
            _create_fallback_role(workflow["name"], project_dir)


def _generate_vrealize_role(
    workflow: dict,
    source_file: Path,
    project_dir: Path,
) -> None:
    """
    Generate role for vRealize workflow.

    Args:
        workflow: Workflow definition dict
        source_file: Path to workflow XML file
        project_dir: Ansible project root directory
    """
    metadata = _extract_vrealize_metadata(source_file)
    _create_role_structure(workflow["name"], project_dir, metadata, workflow)


def _generate_powercli_role(
    workflow: dict,
    source_file: Path,
    project_dir: Path,
    profile: ProfileSchema | None = None,
) -> None:
    """
    Generate role for PowerCLI script with translated tasks.

    Args:
        workflow: Workflow definition dict
        source_file: Path to PowerCLI script file
        project_dir: Ansible project root directory
        profile: ProfileSchema for profile-driven translation
    """
    from ops_translate.generate.workflow_to_ansible import generate_ansible_yaml
    from ops_translate.translate.powercli_script import (
        PowerCLIScriptParser,
        PowerShellToAnsibleTranslator,
    )

    # Extract metadata for role structure
    metadata = _extract_powercli_metadata(source_file)

    # Create role structure (tasks/, defaults/, meta/, README.md)
    _create_role_structure(workflow["name"], project_dir, metadata, workflow)

    # Parse PowerCLI script
    parser = PowerCLIScriptParser()
    statements = parser.parse_file(source_file)

    # Translate to Ansible tasks
    translator = PowerShellToAnsibleTranslator(profile=profile)
    tasks = translator.translate_statements(statements)

    # Generate YAML from tasks
    tasks_yaml = generate_ansible_yaml(tasks)

    # Override tasks/main.yml with translated content
    role_dir = project_dir / "roles" / workflow["name"]
    tasks_file = role_dir / "tasks" / "main.yml"
    tasks_file.write_text(tasks_yaml)


def _extract_vrealize_metadata(workflow_file: Path) -> dict:
    """
    Extract inputs/outputs from vRealize workflow XML.

    Args:
        workflow_file: Path to vRealize workflow XML file

    Returns:
        Metadata dict with display_name, description, inputs, source_type
    """
    from xml.etree import ElementTree

    from ops_translate.summarize.vrealize import extract_inputs

    tree = ElementTree.parse(workflow_file)
    root = tree.getroot()

    ns = {"vco": "http://vmware.com/vco/workflow"}
    display_name = root.findtext(".//vco:display-name", namespaces=ns)
    description = root.findtext(".//vco:description", namespaces=ns)

    inputs = extract_inputs(root)

    return {
        "display_name": display_name or workflow_file.stem,
        "description": description or "",
        "inputs": inputs,
        "source_type": "vRealize Orchestrator Workflow",
    }


def _extract_powercli_metadata(script_file: Path) -> dict:
    """
    Extract parameters from PowerCLI script.

    Args:
        script_file: Path to PowerCLI script file

    Returns:
        Metadata dict with display_name, description, parameters, source_type
    """
    from ops_translate.summarize.powercli import extract_parameters

    content = script_file.read_text()
    parameters = extract_parameters(content)

    # Extract header comments as description
    description_lines = []
    for line in content.split("\n"):
        if line.strip().startswith("#"):
            description_lines.append(line.strip("# ").strip())
        elif line.strip() and not line.strip().startswith("#"):
            break

    return {
        "display_name": script_file.stem,
        "description": "\n".join(description_lines),
        "parameters": parameters,
        "source_type": "PowerCLI Script",
    }


def _create_role_structure(
    role_name: str,
    project_dir: Path,
    metadata: dict,
    workflow: dict,
) -> None:
    """
    Create physical role directory with files.

    Args:
        role_name: Role name (normalized)
        project_dir: Ansible project root directory
        metadata: Metadata extracted from source file
        workflow: Workflow definition dict
    """
    import shutil

    role_dir = project_dir / "roles" / role_name

    # Recreate directory (idempotent, overwrite existing)
    if role_dir.exists():
        shutil.rmtree(role_dir)

    # Create structure
    role_dir.mkdir(parents=True)
    (role_dir / "tasks").mkdir()
    (role_dir / "defaults").mkdir()
    (role_dir / "meta").mkdir()

    # Generate tasks/main.yml
    _generate_tasks_main(role_dir, role_name, metadata, workflow)

    # Generate defaults/main.yml
    _generate_defaults_main(role_dir, role_name, metadata)

    # Generate README.md
    _generate_role_readme(role_dir, role_name, metadata, workflow)

    # Generate meta/main.yml
    _generate_role_meta(role_dir, role_name, metadata)


def _generate_tasks_main(
    role_dir: Path,
    role_name: str,
    metadata: dict,
    workflow: dict,
) -> None:
    """
    Generate tasks/main.yml with metadata header.

    Args:
        role_dir: Role directory path
        role_name: Role name
        metadata: Metadata dict
        workflow: Workflow definition dict
    """
    # Build inputs section
    inputs_section = ""
    if "inputs" in metadata:  # vRealize
        for inp in metadata["inputs"]:
            inputs_section += f"#   - {inp['name']}: {inp['type']}\n"
    elif "parameters" in metadata:  # PowerCLI
        for param in metadata["parameters"]:
            req = "[required]" if param.get("required") else "[optional]"
            inputs_section += f"#   - {param['name']}: {param['type']} {req}\n"

    content = f"""---
# Ansible role: {role_name}
# Source: {metadata['source_type']}
# Original: {workflow['source_file']}
#
# This role skeleton was auto-generated by ops-translate.
# Business logic translation will be implemented in future issues.

# Inputs:
{inputs_section if inputs_section else "# (none)"}

# TODO: Implement workflow logic
# This role currently contains placeholder tasks only.

- name: Placeholder for {role_name}
  ansible.builtin.debug:
    msg: "Role skeleton - awaiting business logic translation (Issue #59/#60)"
  tags:
    - todo
    - {role_name}
"""

    (role_dir / "tasks" / "main.yml").write_text(content)


def _generate_defaults_main(
    role_dir: Path,
    role_name: str,
    metadata: dict,
) -> None:
    """
    Generate defaults/main.yml from inputs/parameters.

    Args:
        role_dir: Role directory path
        role_name: Role name
        metadata: Metadata dict
    """
    lines = [
        "---",
        f"# Default variables for {role_name}",
        "# Auto-generated from workflow inputs/parameters",
        "",
    ]

    if "inputs" in metadata:
        for inp in metadata["inputs"]:
            lines.append(f"# {inp['name']}: {inp['type']}")
            lines.append(f"{inp['name']}: \"\"  # TODO: Set default")
            lines.append("")
    elif "parameters" in metadata:
        for param in metadata["parameters"]:
            lines.append(f"# {param['name']}: {param['type']}")
            default = '""' if param["type"] == "string" else "null"
            lines.append(f"{param['name']}: {default}")
            lines.append("")

    (role_dir / "defaults" / "main.yml").write_text("\n".join(lines))


def _generate_role_readme(
    role_dir: Path,
    role_name: str,
    metadata: dict,
    workflow: dict,
) -> None:
    """
    Generate role README.md.

    Args:
        role_dir: Role directory path
        role_name: Role name
        metadata: Metadata dict
        workflow: Workflow definition dict
    """
    # Build inputs table
    inputs_table = "| Name | Type | Required |\n|------|------|----------|\n"

    if "inputs" in metadata:
        for inp in metadata["inputs"]:
            inputs_table += f"| {inp['name']} | {inp['type']} | - |\n"
    elif "parameters" in metadata:
        for param in metadata["parameters"]:
            req = "Yes" if param.get("required") else "No"
            inputs_table += f"| {param['name']} | {param['type']} | {req} |\n"

    content = f"""# Role: {role_name}

## Description

{metadata['description'] or 'No description available'}

## Source

- **Type:** {metadata['source_type']}
- **Original File:** `{workflow['source_file']}`

## Inputs

{inputs_table}

## Implementation Status

**Status:** Skeleton Only

This role was auto-generated by ops-translate. It contains:
- ✅ Role directory structure
- ✅ Documented inputs/parameters
- ✅ Placeholder tasks
- ❌ Business logic (to be implemented in Issue #59/#60)

## Usage

```bash
ansible-playbook -i inventories/dev site.yml --tags {role_name}
```

## Next Steps

1. Review inputs in `defaults/main.yml` and set appropriate defaults
2. Implement business logic in `tasks/main.yml`
3. Add integration adapter calls (see `adapters/` directory)
4. Test independently before integration

---

*Auto-generated by [ops-translate](https://github.com/tsanders-rh/ops-translate)*
"""

    (role_dir / "README.md").write_text(content)


def _generate_role_meta(
    role_dir: Path,
    role_name: str,
    metadata: dict,
) -> None:
    """
    Generate Ansible Galaxy metadata.

    Args:
        role_dir: Role directory path
        role_name: Role name
        metadata: Metadata dict
    """
    description = metadata.get("description", "Auto-generated role")
    # Truncate description to 100 chars for Galaxy compatibility
    if len(description) > 100:
        description = description[:97] + "..."

    content = f"""---
galaxy_info:
  role_name: {role_name}
  author: ops-translate
  description: {description}
  license: MIT
  min_ansible_version: "2.9"

dependencies: []
"""
    (role_dir / "meta" / "main.yml").write_text(content)


def _create_fallback_role(role_name: str, project_dir: Path) -> None:
    """
    Create minimal role when metadata extraction fails.

    Args:
        role_name: Role name
        project_dir: Ansible project root directory
    """
    role_dir = project_dir / "roles" / role_name
    role_dir.mkdir(parents=True, exist_ok=True)
    (role_dir / "tasks").mkdir(exist_ok=True)

    tasks_file = role_dir / "tasks" / "main.yml"
    tasks_file.write_text("""---
# Role generation failed - placeholder created
- name: Placeholder
  ansible.builtin.debug:
    msg: "Role skeleton generation incomplete"
""")


def _generate_documentation(
    profile: ProfileSchema,
    workflows: list[dict[str, Any]],
    project_dir: Path,
) -> None:
    """
    Generate project documentation.

    Args:
        profile: ProfileSchema used for generation
        workflows: Workflow definitions
        project_dir: Project root directory
    """
    docs_dir = project_dir / "docs"

    # Pre-compute joined strings for f-string usage
    workflow_list = "\n".join(f"- {wf['name']}" for wf in workflows)

    # Pre-compute profile config strings to avoid long lines
    approval_str = profile.approval.model if profile.approval else "Not configured"
    network_sec_str = (
        profile.network_security.model if profile.network_security else "Not configured"
    )
    itsm_str = profile.itsm.provider if profile.itsm else "Not configured"
    dns_str = profile.dns.provider if profile.dns else "Not configured"
    ipam_str = profile.ipam.provider if profile.ipam else "Not configured"

    # Generate README.md
    readme = f"""# Ansible Project: {profile.name}

{profile.description or 'Generated by ops-translate from vRealize workflows'}

## Project Structure

```
ansible-project/
├── site.yml              # Main playbook
├── ansible.cfg           # Ansible configuration
├── inventories/          # Environment-specific inventories
│   ├── dev/             # Development environment
│   └── prod/            # Production environment
├── roles/               # Workflow roles
├── adapters/            # Integration adapter stubs
│   ├── nsx/            # NSX-T adapters
│   ├── servicenow/     # ServiceNow adapters
│   ├── dns/            # DNS provider adapters
│   └── ipam/           # IPAM provider adapters
└── docs/               # Documentation
```

## Usage

### Run playbook for dev environment:
```bash
ansible-playbook -i inventories/dev site.yml
```

### Run playbook for prod environment:
```bash
ansible-playbook -i inventories/prod site.yml
```

### Run specific role:
```bash
ansible-playbook -i inventories/dev site.yml --tags role_name
```

## Workflows

This project includes {len(workflows)} workflow(s):

{workflow_list}

## Profile Configuration

- Profile: {profile.name}
- Environments: {', '.join(profile.environments.keys())}
- Approval: {approval_str}
- Network Security: {network_sec_str}
- ITSM: {itsm_str}
- DNS: {dns_str}
- IPAM: {ipam_str}

## Adapter Stubs

Adapter stubs in the `adapters/` directory provide integration points for external
systems. Profile-driven generation ensures adapters are functional when profile
sections are configured, or BLOCKED with guidance when missing.

See [Adapter Guide](adapters.md) for details on each adapter type.

## Next Steps

1. Review generated roles in `roles/` directory
2. Configure credentials in inventory group_vars
3. Test adapters with dry-run mode
4. Execute playbooks in dev environment first

Generated by [ops-translate](https://github.com/tsanders-rh/ops-translate)
"""
    (docs_dir / "README.md").write_text(readme)

    # Pre-compute environment and storage tier sections for profile.md
    env_sections = "\n".join(f"""#### {env_name}
- OpenShift API: {env_cfg.openshift_api_url}
- Namespace: {env_cfg.namespace or f'{profile.name}-{env_name}'}
- Node Selectors: {env_cfg.node_selectors or 'None'}
""" for env_name, env_cfg in profile.environments.items())

    storage_tiers_section = (
        "\n".join(
            f"- {tier.vmware_tier} → {tier.openshift_storage_class}"
            for tier in profile.storage_tiers
        )
        if profile.storage_tiers
        else "**Not configured** - storage tiers will use default storage class"
    )

    # Pre-compute profile doc config strings to avoid long lines
    approval_doc = (
        f"**Model:** {profile.approval.model}"
        if profile.approval
        else "**Not configured** - approval workflows will generate BLOCKED stubs"
    )
    network_sec_doc = (
        f"**Model:** {profile.network_security.model}"
        if profile.network_security
        else "**Not configured** - NSX network adapters will generate BLOCKED stubs"
    )
    itsm_doc = (
        f"**Provider:** {profile.itsm.provider}"
        if profile.itsm
        else "**Not configured** - ITSM ticket adapters will generate BLOCKED stubs"
    )
    dns_doc = (
        f"**Provider:** {profile.dns.provider}"
        if profile.dns
        else "**Not configured** - DNS record adapters will generate BLOCKED stubs"
    )
    ipam_doc = (
        f"**Provider:** {profile.ipam.provider}"
        if profile.ipam
        else "**Not configured** - IPAM allocation adapters will generate BLOCKED stubs"
    )

    # Pre-compute completeness check strings
    approval_check = "Configured" if profile.approval else "Missing"
    network_sec_check = "Configured" if profile.network_security else "Missing"
    itsm_check = "Configured" if profile.itsm else "Missing"
    dns_check = "Configured" if profile.dns else "Missing"
    ipam_check = "Configured" if profile.ipam else "Missing"
    storage_tiers_check = (
        f"{len(profile.storage_tiers)} mappings" if profile.storage_tiers else "Missing"
    )

    # Generate profile.md
    profile_doc = f"""# Profile Guide: {profile.name}

## Overview

This Ansible project was generated using the **{profile.name}** profile.
Profiles drive deterministic translation by providing explicit configuration
for external integrations and platform-specific components.

## Profile Schema

### Environments

{env_sections}

### Approval Configuration

{approval_doc}

### Network Security Configuration

{network_sec_doc}

### ITSM Configuration

{itsm_doc}

### DNS Configuration

{dns_doc}

### IPAM Configuration

{ipam_doc}

### Storage Tier Mappings

{storage_tiers_section}

## Updating Profile

To update the profile configuration:

1. Edit your `profile.yml` file
2. Re-run `ops-translate generate ansible --profile profile.yml`
3. Review updated adapter stubs in `adapters/` directory

## Profile Completeness

Missing profile sections result in BLOCKED adapter stubs with guidance.
Configure all relevant sections for fully functional adapters:

- ✓ Environments: {len(profile.environments)} configured
- {'✓' if profile.approval else '✗'} Approval: {approval_check}
- {'✓' if profile.network_security else '✗'} Network Security: {network_sec_check}
- {'✓' if profile.itsm else '✗'} ITSM: {itsm_check}
- {'✓' if profile.dns else '✗'} DNS: {dns_check}
- {'✓' if profile.ipam else '✗'} IPAM: {ipam_check}
- {'✓' if profile.storage_tiers else '✗'} Storage Tiers: {storage_tiers_check}
"""
    (docs_dir / "profile.md").write_text(profile_doc)

    # Generate adapters.md
    adapters_doc = """# Adapter Guide

## Overview

Adapters provide integration points for external systems and platform-specific
components. Each adapter is profile-driven:

- **Configured:** Profile section exists → functional adapter with provider-specific tasks
- **BLOCKED:** Profile section missing → BLOCKED stub with configuration guidance

## Adapter Types

### NSX Adapters

**Location:** `adapters/nsx/`

#### create_segment.yml
Translates NSX-T segment creation to Kubernetes NetworkAttachmentDefinition.

**Profile requirement:** `network_security` section
**Supports:** calico, networkpolicy, cilium, istio

#### create_firewall_rule.yml
Translates NSX-T distributed firewall rules to Kubernetes NetworkPolicy.

**Profile requirement:** `network_security` section
**Supports:** calico, cilium, networkpolicy, istio

### ServiceNow Adapters

**Location:** `adapters/servicenow/`

#### create_change.yml
Creates ServiceNow change request for approval workflows.

**Profile requirement:** `approval` section with model=servicenow_change
**Alternative models:** aap_workflow, gitops_pr, manual_pause

#### create_incident.yml
Creates ServiceNow incident/ticket for operational events.

**Profile requirement:** `itsm` section with provider=servicenow
**Alternative providers:** jira, manual

### DNS Adapters

**Location:** `adapters/dns/`

#### create_record.yml
Creates DNS A records via configured DNS provider.

**Profile requirement:** `dns` section
**Supports:** infoblox, externaldns, coredns, manual

### IPAM Adapters

**Location:** `adapters/ipam/`

#### reserve_ip.yml
Allocates IP addresses via configured IPAM provider.

**Profile requirement:** `ipam` section
**Supports:** infoblox, whereabouts, static

## Using Adapters

Adapters are included in role tasks via `include_tasks`:

```yaml
- name: Create NSX segment
  include_tasks: ../../adapters/nsx/create_segment.yml
  vars:
    segment_name: "{{ vm_network }}"
    segment_subnet: "10.1.0.0/24"
```

## BLOCKED Stubs

When profile sections are missing, adapters generate BLOCKED stubs that fail
with detailed guidance:

```
BLOCKED: NSX Segment Creation
══════════════════════════════════════════════════════════

This workflow requires NSX-T segment creation, which translates to
NetworkAttachmentDefinition in Kubernetes. However, your profile does not
have network_security configured.

TO FIX THIS:
Add network_security configuration to your profile.yml:

  network_security:
    model: networkpolicy
    default_isolation: namespace
```

## Deterministic Generation

Adapters are deterministically generated from profile configuration:
- Same profile + same workflow = identical adapter stubs
- No AI guessing for external integrations
- Re-running with complete profile fills in BLOCKED stubs

## Next Steps

1. Review profile.md for current configuration
2. Configure missing profile sections
3. Re-generate to produce functional adapters
4. Test adapters with dry-run mode before production use
"""
    (docs_dir / "adapters.md").write_text(adapters_doc)
