"""
Ansible playbook and role generation.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from ops_translate.util.files import ensure_dir, write_text
from ops_translate.workspace import Workspace


def generate(workspace: Workspace, profile: str, use_ai: bool = False):
    """
    Generate Ansible playbook and role.

    Outputs:
    - output/ansible/site.yml
    - output/ansible/roles/provision_vm/tasks/main.yml
    - output/ansible/roles/provision_vm/defaults/main.yml
    - output/README.md

    If gap analysis data exists (intent/gaps.json):
    - Injects TODO tasks for PARTIAL/BLOCKED/MANUAL components
    - Creates role stubs for MANUAL components
    - Adds gap summary to playbook
    """
    output_dir = workspace.root / "output/ansible"
    ensure_dir(output_dir)

    config = workspace.load_config()
    profile_config = config["profiles"][profile]

    # Load gap analysis data if available
    gaps_data = _load_gaps_data(workspace)

    # Generate site.yml playbook
    playbook_content = generate_playbook(profile, gaps_data)
    write_text(output_dir / "site.yml", playbook_content)

    # Generate role
    role_dir = output_dir / "roles/provision_vm"
    ensure_dir(role_dir / "tasks")
    ensure_dir(role_dir / "defaults")

    tasks_content = generate_tasks(profile_config, use_ai, gaps_data)
    write_text(role_dir / "tasks/main.yml", tasks_content)

    defaults_content = generate_defaults(profile_config)
    write_text(role_dir / "defaults/main.yml", defaults_content)

    # Generate role stubs for MANUAL components
    if gaps_data:
        for component in gaps_data.get("components", []):
            if component.get("level") in ["BLOCKED", "MANUAL"]:
                _create_manual_role_stub(output_dir, component, workspace)

    # Generate README
    readme_content = generate_readme(profile)
    write_text(workspace.root / "output/README.md", readme_content)


def generate_playbook(profile: str, gaps_data: dict[str, Any] | None = None) -> str:
    """
    Generate Ansible playbook.

    If gaps_data is provided, adds a gap analysis summary comment at the top.
    """
    playbook = [
        {
            "name": "Provision KubeVirt VM",
            "hosts": "localhost",
            "gather_facts": False,
            "roles": ["provision_vm"],
        }
    ]

    playbook_yaml = yaml.dump(playbook, default_flow_style=False, sort_keys=False)

    # Prepend gap analysis summary if available
    if gaps_data and gaps_data.get("components"):
        summary = gaps_data["summary"]
        summary_comment = f"""---
# ============================================================================
# GAP ANALYSIS SUMMARY
# ============================================================================
# Overall Assessment: {summary.get('overall_assessment', 'UNKNOWN')}
# Total Components: {summary.get('total_components', 0)}
# - SUPPORTED: {summary['counts'].get('SUPPORTED', 0)}
# - PARTIAL: {summary['counts'].get('PARTIAL', 0)} (manual configuration needed)
# - BLOCKED: {summary['counts'].get('BLOCKED', 0)} (no direct equivalent)
# - MANUAL: {summary['counts'].get('MANUAL', 0)} (specialist work required)
#
# For detailed migration guidance, see: intent/gaps.md
#
# To skip manual tasks during testing:
#   ansible-playbook site.yml --skip-tags manual_implementation_required
# ============================================================================

"""
        return summary_comment + playbook_yaml

    return "---\n" + playbook_yaml


def generate_tasks(
    profile_config: dict, use_ai: bool, gaps_data: dict[str, Any] | None = None
) -> str:
    """
    Generate Ansible tasks.

    If gaps_data is provided, injects TODO tasks for PARTIAL/BLOCKED/MANUAL
    components before the main provisioning tasks.
    """
    namespace = profile_config["default_namespace"]

    tasks = [
        {
            "name": "Create KubeVirt VirtualMachine",
            "kubernetes.core.k8s": {
                "state": "present",
                "definition": "{{ lookup('file', 'kubevirt/vm.yaml') | from_yaml }}",
            },
        },
        {
            "name": "Wait for VM to be ready",
            "kubernetes.core.k8s_info": {
                "api_version": "kubevirt.io/v1",
                "kind": "VirtualMachine",
                "name": "{{ vm_name }}",
                "namespace": namespace,
            },
            "register": "vm_info",
            "until": (
                "vm_info.resources | length > 0 and vm_info.resources[0].status.ready is defined"
            ),
            "retries": 30,
            "delay": 10,
        },
    ]

    # Inject gap analysis TODOs if available
    if gaps_data:
        tasks, _ = _inject_gap_todos(tasks, gaps_data)

    # Convert to YAML with custom handling for comments
    tasks_yaml = "---\n"

    for task in tasks:
        # Handle special _comment key
        if "_comment" in task:
            tasks_yaml += task.pop("_comment") + "\n"

        # Add the task itself
        task_yaml = yaml.dump([task], default_flow_style=False, sort_keys=False)
        # Remove the leading '---\n' and '- ' from yaml.dump output
        task_yaml = task_yaml.replace("---\n", "").replace("- name:", "- name:", 1)
        tasks_yaml += task_yaml

    return tasks_yaml.rstrip() + "\n"


def generate_defaults(profile_config: dict) -> str:
    """Generate Ansible role defaults."""
    defaults = {
        "vm_name": "example-vm",
        "namespace": profile_config["default_namespace"],
        "cpu_cores": 2,
        "memory": "4Gi",
        "storage_class": profile_config["default_storage_class"],
    }

    return yaml.dump(defaults, default_flow_style=False, sort_keys=False)


def generate_readme(profile: str) -> str:
    """Generate README for output artifacts."""
    return f"""# Generated Artifacts

This directory contains the generated Ansible and KubeVirt artifacts.

## Profile: {profile}

## Files

- `ansible/site.yml` - Main Ansible playbook
- `ansible/roles/provision_vm/` - Ansible role for VM provisioning
- `kubevirt/vm.yaml` - KubeVirt VirtualMachine manifest

## Usage

### Apply KubeVirt manifest directly:

```bash
kubectl apply -f kubevirt/vm.yaml
```

### Run Ansible playbook:

```bash
ansible-playbook ansible/site.yml -e vm_name=my-vm
```

## Requirements

- Ansible 2.9+
- kubernetes.core collection (`ansible-galaxy collection install kubernetes.core`)
- community.kubevirt collection (`ansible-galaxy collection install community.kubevirt`)
- kubectl configured with cluster access
- KubeVirt installed on target cluster

## Variables

See `ansible/roles/provision_vm/defaults/main.yml` for configurable variables.
"""


def _load_gaps_data(workspace: Workspace) -> dict[str, Any] | None:
    """
    Load gap analysis data from intent/gaps.json if it exists.

    Args:
        workspace: Workspace instance

    Returns:
        Gap analysis data dict, or None if gaps.json doesn't exist

    Example:
        >>> gaps = _load_gaps_data(workspace)
        >>> if gaps:
        ...     print(f"Found {len(gaps['components'])} gap components")
    """
    gaps_file = workspace.root / "intent/gaps.json"
    if not gaps_file.exists():
        return None

    try:
        with open(gaps_file) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        # Gracefully handle corrupted/unreadable gaps file
        return None


def _inject_gap_todos(tasks: list[dict], gaps_data: dict[str, Any]) -> tuple[list[dict], str]:
    """
    Inject TODO tasks for gap analysis findings.

    Adds TODO comment tasks for PARTIAL/BLOCKED/MANUAL components before
    the main provisioning tasks. Each TODO includes classification, OpenShift
    equivalent, migration path, and recommendations.

    Args:
        tasks: Existing Ansible tasks list
        gaps_data: Gap analysis data from gaps.json

    Returns:
        Tuple of (updated_tasks, summary_comment)

    Example:
        >>> tasks = [{"name": "Create VM", ...}]
        >>> gaps_data = {"components": [...], "summary": {...}}
        >>> updated_tasks, summary = _inject_gap_todos(tasks, gaps_data)
    """
    if not gaps_data or not gaps_data.get("components"):
        return tasks, ""

    components = gaps_data["components"]
    summary = gaps_data["summary"]

    # Build summary comment for top of playbook
    summary_lines = [
        "",
        "# ============================================================================",
        "# GAP ANALYSIS SUMMARY",
        "# ============================================================================",
        f"# Overall Assessment: {summary.get('overall_assessment', 'UNKNOWN')}",
        f"# Total Components: {summary.get('total_components', 0)}",
        f"# - SUPPORTED: {summary['counts'].get('SUPPORTED', 0)}",
        f"# - PARTIAL: {summary['counts'].get('PARTIAL', 0)} (manual configuration needed)",
        f"# - BLOCKED: {summary['counts'].get('BLOCKED', 0)} (no direct equivalent)",
        f"# - MANUAL: {summary['counts'].get('MANUAL', 0)} (specialist work required)",
        "#",
        "# For detailed migration guidance, see: intent/gaps.md",
        "# ============================================================================",
        "",
    ]
    summary_comment = "\n".join(summary_lines)

    # Create TODO tasks for components requiring manual work
    todo_tasks = []
    for comp in components:
        level = comp.get("level")
        if level not in ["PARTIAL", "BLOCKED", "MANUAL"]:
            continue  # Skip SUPPORTED components

        # Determine tag based on level
        if level == "PARTIAL":
            tag = "manual_review_required"
            emoji = "⚠️"
        else:  # BLOCKED or MANUAL
            tag = "manual_implementation_required"
            emoji = "🚫"

        # Build TODO comment lines
        comp_type = comp.get("component_type", "unknown")
        comp_name = comp.get("name", "unnamed")
        comment_lines = [f"# TODO: {level} - {comp_type} '{comp_name}'"]

        if comp.get("openshift_equivalent"):
            comment_lines.append(f"# OpenShift Equivalent: {comp['openshift_equivalent']}")
        else:
            comment_lines.append("# OpenShift Equivalent: None (requires custom solution)")

        if comp.get("migration_path"):
            comment_lines.append(f"# Migration Path: {comp['migration_path']}")

        if comp.get("recommendations"):
            comment_lines.append("# Recommendations:")
            for rec in comp["recommendations"]:
                comment_lines.append(f"#   - {rec}")

        comment_lines.append("# See: intent/gaps.md for details")

        # Create task with comment header
        task = {
            "_comment": "\n".join(comment_lines),
            "name": f"TODO: {emoji} Manual work required - {comp.get('name', 'unnamed')}",
            "ansible.builtin.debug": {
                "msg": f"{level} component detected - see gap analysis for migration guidance"
            },
            "tags": [tag, "gap_analysis"],
        }

        todo_tasks.append(task)

    # Prepend TODO tasks before main tasks
    return todo_tasks + tasks, summary_comment


def _create_manual_role_stub(
    output_dir: Path, component: dict[str, Any], workspace: Workspace
) -> None:
    """
    Create Ansible role stub for MANUAL components.

    Generates a role directory structure with README, tasks, and defaults
    for components that require manual implementation.

    Args:
        output_dir: Base output directory (e.g., workspace.root/output/ansible)
        component: Component data dict from gaps.json
        workspace: Workspace instance

    Example:
        >>> _create_manual_role_stub(
        ...     Path("output/ansible"),
        ...     {"name": "web-sg", "component_type": "nsx_security_groups", ...},
        ...     workspace
        ... )
        # Creates: output/ansible/roles/nsx_security_groups/
    """
    # Sanitize role name
    component_type = component.get("component_type", "manual_component")
    role_name = component_type.replace("-", "_").lower()
    role_dir = output_dir / "roles" / role_name

    # Skip if role already exists
    if role_dir.exists():
        return

    # Create directory structure
    ensure_dir(role_dir / "tasks")
    ensure_dir(role_dir / "defaults")

    # Generate README
    readme_content = f"""# {role_name.replace('_', ' ').title()} Role

## Component

**Name:** {component.get('name', 'unnamed')}
**Type:** {component.get('component_type', 'unknown')}
**Classification:** {component.get('level', 'MANUAL')}

## Migration Guidance

{component.get('reason', 'No reason provided.')}

"""

    if component.get("openshift_equivalent"):
        readme_content += f"""**OpenShift Equivalent:** {component['openshift_equivalent']}

"""
    else:
        readme_content += """**OpenShift Equivalent:** None - requires custom solution

"""

    readme_content += f"""**Migration Path:** {component.get('migration_path', 'Unknown')}

## Recommendations

"""

    if component.get("recommendations"):
        for rec in component["recommendations"]:
            readme_content += f"- {rec}\n"
    else:
        readme_content += "- No specific recommendations provided\n"

    readme_content += """
## Implementation

This role stub has been created because this component requires manual
implementation. You will need to:

1. Review the component requirements in `intent/gaps.md`
2. Design an OpenShift-native solution or hybrid approach
3. Implement tasks in `tasks/main.yml`
4. Define variables in `defaults/main.yml`
5. Test thoroughly in a non-production environment

## Evidence

"""

    if component.get("evidence"):
        readme_content += f"""Source detection:
```
{component['evidence']}
```

"""

    if component.get("location"):
        readme_content += f"""**Location:** {component['location']}

"""

    readme_content += """## References

- [Gap Analysis Report](../../../intent/gaps.md)
- [OpenShift Documentation](https://docs.openshift.com/)
- [KubeVirt Documentation](https://kubevirt.io/user-guide/)
"""

    write_text(role_dir / "README.md", readme_content)

    # Generate tasks/main.yml with TODO placeholders
    tasks_content = f"""---
# Tasks for {role_name}
# This is a STUB - manual implementation required

# TODO: Implement {component.get('name', 'component')} migration
# Classification: {component.get('level', 'MANUAL')}
# See README.md for guidance

- name: "TODO: Implement {component.get('name', 'component')} migration"
  ansible.builtin.debug:
    msg: "Manual implementation required - see role README.md"
  tags:
    - manual_implementation_required
    - stub
"""

    write_text(role_dir / "tasks/main.yml", tasks_content)

    # Generate defaults/main.yml with discovered parameters
    defaults_content = f"""---
# Default variables for {role_name}
# TODO: Define required variables based on component requirements

# Component information
component_name: "{component.get('name', 'unnamed')}"
component_type: "{component.get('component_type', 'unknown')}"

# Add your implementation-specific variables here
"""

    write_text(role_dir / "defaults/main.yml", defaults_content)
