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

        group_vars = {
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
- Approval: {profile.approval.model if profile.approval else 'Not configured'}
- Network Security: {profile.network_security.model if profile.network_security else 'Not configured'}
- ITSM: {profile.itsm.provider if profile.itsm else 'Not configured'}
- DNS: {profile.dns.provider if profile.dns else 'Not configured'}
- IPAM: {profile.ipam.provider if profile.ipam else 'Not configured'}

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
    env_sections = "\n".join(
        f"""#### {env_name}
- OpenShift API: {env_cfg.openshift_api_url}
- Namespace: {env_cfg.namespace or f'{profile.name}-{env_name}'}
- Node Selectors: {env_cfg.node_selectors or 'None'}
"""
        for env_name, env_cfg in profile.environments.items()
    )

    storage_tiers_section = (
        "\n".join(f"- {tier.vmware_tier} → {tier.openshift_storage_class}" for tier in profile.storage_tiers)
        if profile.storage_tiers
        else "**Not configured** - storage tiers will use default storage class"
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

{f"**Model:** {profile.approval.model}" if profile.approval else "**Not configured** - approval workflows will generate BLOCKED stubs"}

### Network Security Configuration

{f"**Model:** {profile.network_security.model}" if profile.network_security else "**Not configured** - NSX network adapters will generate BLOCKED stubs"}

### ITSM Configuration

{f"**Provider:** {profile.itsm.provider}" if profile.itsm else "**Not configured** - ITSM ticket adapters will generate BLOCKED stubs"}

### DNS Configuration

{f"**Provider:** {profile.dns.provider}" if profile.dns else "**Not configured** - DNS record adapters will generate BLOCKED stubs"}

### IPAM Configuration

{f"**Provider:** {profile.ipam.provider}" if profile.ipam else "**Not configured** - IPAM allocation adapters will generate BLOCKED stubs"}

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
- {'✓' if profile.approval else '✗'} Approval: {'Configured' if profile.approval else 'Missing'}
- {'✓' if profile.network_security else '✗'} Network Security: {'Configured' if profile.network_security else 'Missing'}
- {'✓' if profile.itsm else '✗'} ITSM: {'Configured' if profile.itsm else 'Missing'}
- {'✓' if profile.dns else '✗'} DNS: {'Configured' if profile.dns else 'Missing'}
- {'✓' if profile.ipam else '✗'} IPAM: {'Configured' if profile.ipam else 'Missing'}
- {'✓' if profile.storage_tiers else '✗'} Storage Tiers: {f'{len(profile.storage_tiers)} mappings' if profile.storage_tiers else 'Missing'}
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
