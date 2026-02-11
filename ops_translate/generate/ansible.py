"""
Ansible playbook and role generation.
"""

from pathlib import Path
from typing import Any

import yaml

from ops_translate.report.loaders import ReportDataLoader, ReportFileLocator
from ops_translate.util.files import ensure_dir, write_text
from ops_translate.workspace import Workspace


def generate(
    workspace: Workspace, profile: str, use_ai: bool = False, assume_existing_vms: bool = False
):
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

    Args:
        workspace: Workspace instance
        profile: Profile name
        use_ai: Whether to use AI generation (currently unused)
        assume_existing_vms: If True, generate validation tasks instead of VM creation
    """
    output_dir = workspace.root / "output/ansible"
    ensure_dir(output_dir)

    config = workspace.load_config()
    profile_config = config["profiles"][profile]

    # Load gap analysis data if available (using decoupled components)
    locator = ReportFileLocator(workspace)
    loader = ReportDataLoader()

    gaps_data = None
    if gaps_file := locator.gaps_file():
        gaps_data = loader.load_json(gaps_file)

    recommendations_data = None
    if recs_file := locator.recommendations_file():
        recommendations_data = loader.load_json(recs_file)

    # Generate site.yml playbook
    playbook_content = generate_playbook(profile, gaps_data)
    write_text(output_dir / "site.yml", playbook_content)

    # Generate role
    role_dir = output_dir / "roles/provision_vm"
    ensure_dir(role_dir / "tasks")
    ensure_dir(role_dir / "defaults")

    tasks_content = generate_tasks(
        profile_config, use_ai, gaps_data, recommendations_data, assume_existing_vms
    )
    write_text(role_dir / "tasks/main.yml", tasks_content)

    defaults_content = generate_defaults(profile_config)
    write_text(role_dir / "defaults/main.yml", defaults_content)

    # Generate role stubs for MANUAL/BLOCKED components
    if gaps_data:
        for component in gaps_data.get("components", []):
            if component.get("level") in ["BLOCKED", "MANUAL"]:
                _create_manual_role_stub(output_dir, component, workspace, recommendations_data)

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
    profile_config: dict,
    use_ai: bool,
    gaps_data: dict[str, Any] | None = None,
    recommendations_data: dict[str, Any] | None = None,
    assume_existing_vms: bool = False,
) -> str:
    """
    Generate Ansible tasks.

    If gaps_data is provided, injects TODO tasks for PARTIAL/BLOCKED/MANUAL
    components before the main provisioning tasks. If recommendations_data is
    provided, includes detailed implementation guidance in TODO comments.

    If assume_existing_vms is True, generates validation tasks instead of VM creation.
    """
    namespace = profile_config["default_namespace"]

    if assume_existing_vms:
        # MTV mode: Validate existing VM instead of creating it
        tasks: list[dict[str, Any]] = [
            {
                "_comment": "# MTV Mode: Validate existing VM (migrated by MTV)",
                "name": "Verify VM exists",
                "kubernetes.core.k8s_info": {
                    "api_version": "kubevirt.io/v1",
                    "kind": "VirtualMachine",
                    "name": "{{ vm_name }}",
                    "namespace": namespace,
                },
                "register": "vm_info",
                "failed_when": "vm_info.resources | length == 0",
            },
            {
                "name": "Validate VM CPU configuration",
                "ansible.builtin.assert": {
                    "that": [
                        "vm_info.resources | length > 0",
                        "vm_info.resources[0].spec.template.spec.domain.cpu.cores == cpu_cores",
                    ],
                    "fail_msg": (
                        "VM CPU configuration doesn't match intent "
                        "(expected {{ cpu_cores }} cores)"
                    ),
                },
            },
            {
                "name": "Validate VM memory configuration",
                "ansible.builtin.assert": {
                    "that": [
                        (
                            "vm_info.resources[0].spec.template.spec.domain."
                            "resources.requests.memory == memory"
                        ),
                    ],
                    "fail_msg": (
                        "VM memory configuration doesn't match intent "
                        "(expected {{ memory }})"
                    ),
                },
            },
            {
                "name": "Apply operational labels to VM",
                "kubernetes.core.k8s": {
                    "api_version": "kubevirt.io/v1",
                    "kind": "VirtualMachine",
                    "name": "{{ vm_name }}",
                    "namespace": namespace,
                    "state": "patched",
                    "definition": {
                        "metadata": {
                            "labels": {
                                "managed-by": "ops-translate",
                                "environment": "{{ environment | default('unknown') }}",
                            }
                        }
                    },
                },
            },
        ]
    else:
        # Greenfield mode: Create VM from YAML
        tasks: list[dict[str, Any]] = [
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
                    "vm_info.resources | length > 0 and "
                    "vm_info.resources[0].status.ready is defined"
                ),
                "retries": 30,
                "delay": 10,
            },
        ]

    # Inject gap analysis TODOs if available
    if gaps_data:
        tasks, _ = _inject_gap_todos(tasks, gaps_data, recommendations_data)

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


def _inject_gap_todos(
    tasks: list[dict],
    gaps_data: dict[str, Any],
    recommendations_data: dict[str, Any] | None = None,
) -> tuple[list[dict], str]:
    """
    Inject TODO tasks for gap analysis findings.

    Adds TODO comment tasks for PARTIAL/BLOCKED/MANUAL components before
    the main provisioning tasks. Each TODO includes classification, OpenShift
    equivalent, migration path, and recommendations.

    If recommendations_data is provided, uses detailed implementation guidance
    from expert recommendations instead of basic gap analysis recommendations.

    Args:
        tasks: Existing Ansible tasks list
        gaps_data: Gap analysis data from gaps.json
        recommendations_data: Optional recommendations data from recommendations.json

    Returns:
        Tuple of (updated_tasks, summary_comment)

    Example:
        >>> tasks = [{"name": "Create VM", ...}]
        >>> gaps_data = {"components": [...], "summary": {...}}
        >>> updated_tasks, summary = _inject_gap_todos(tasks, gaps_data, recs_data)
    """
    if not gaps_data or not gaps_data.get("components"):
        return tasks, ""

    components = gaps_data["components"]
    summary = gaps_data["summary"]

    # Build recommendation lookup by component type and name
    rec_lookup = {}
    if recommendations_data and recommendations_data.get("recommendations"):
        for rec in recommendations_data["recommendations"]:
            key = (rec.get("component_type"), rec.get("component_name"))
            rec_lookup[key] = rec

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

        # Check if we have a detailed recommendation for this component
        rec_key = (comp_type, comp_name)
        recommendation = rec_lookup.get(rec_key)

        if recommendation:
            # Use detailed recommendation guidance
            comment_lines.append("#")
            comment_lines.append(f"# Owner: {recommendation.get('owner', 'Unknown')}")
            comment_lines.append("#")
            comment_lines.append("# Recommended Ansible Approach:")
            comment_lines.append(
                f"#   {recommendation.get('ansible_approach', 'See recommendations.md')}"
            )
            comment_lines.append("#")
            if recommendation.get("openshift_primitives"):
                comment_lines.append("# OpenShift/Kubernetes Primitives:")
                for primitive in recommendation["openshift_primitives"]:
                    comment_lines.append(f"#   - {primitive}")
                comment_lines.append("#")
            comment_lines.append(
                "# See: intent/recommendations.md for detailed implementation steps"
            )
        else:
            # Fall back to basic gap analysis info
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
    output_dir: Path,
    component: dict[str, Any],
    workspace: Workspace,
    recommendations_data: dict[str, Any] | None = None,
) -> None:
    """
    Create Ansible role stub for MANUAL/BLOCKED components.

    Generates a role directory structure with README, tasks, and defaults
    for components that require manual implementation. If recommendations_data
    is provided, includes detailed implementation guidance in the README.

    Args:
        output_dir: Base output directory (e.g., workspace.root/output/ansible)
        component: Component data dict from gaps.json
        workspace: Workspace instance
        recommendations_data: Optional recommendations data from recommendations.json

    Example:
        >>> _create_manual_role_stub(
        ...     Path("output/ansible"),
        ...     {"name": "web-sg", "component_type": "nsx_security_groups", ...},
        ...     workspace,
        ...     recs_data
        ... )
        # Creates: output/ansible/roles/nsx_security_groups/
    """
    # Sanitize role name
    component_type = component.get("component_type", "manual_component")
    component_name = component.get("name", "unnamed")

    # Find matching recommendation
    recommendation = None
    if recommendations_data and recommendations_data.get("recommendations"):
        for rec in recommendations_data["recommendations"]:
            # Match on both component_type and component_name
            # Handle plural/singular variations (e.g., nsx_security_groups vs nsx_security_group)
            rec_type = rec.get("component_type", "").rstrip("s")  # Remove trailing 's' for matching
            comp_type_normalized = component_type.rstrip("s")

            if rec_type == comp_type_normalized and rec.get("component_name") == component_name:
                recommendation = rec
                break

    # Use role stub name from recommendation if available, otherwise sanitize component type
    if recommendation and recommendation.get("ansible_role_stub"):
        role_name = recommendation["ansible_role_stub"]
    else:
        role_name = component_type.replace("-", "_").lower()

    role_dir = output_dir / "roles" / role_name

    # Skip if role already exists
    if role_dir.exists():
        return

    # Create directory structure
    ensure_dir(role_dir / "tasks")
    ensure_dir(role_dir / "defaults")

    # Generate README with detailed guidance if recommendation is available
    if recommendation:
        readme_content = f"""# {role_name.replace('_', ' ').title()} Role

## Component

**Name:** {component_name}
**Type:** {component_type}
**Classification:** {component.get('level', 'MANUAL')}
**Owner:** {recommendation.get('owner', 'Unknown')}

## Why Not Auto-Translatable

{recommendation.get('reason_not_auto_translatable', 'No reason provided.')}

## Recommended Ansible Approach

{recommendation.get('ansible_approach', 'See intent/recommendations.md')}

## OpenShift/Kubernetes Primitives

"""
        if recommendation.get("openshift_primitives"):
            for primitive in recommendation["openshift_primitives"]:
                readme_content += f"- `{primitive}`\n"
        else:
            readme_content += "- None specified\n"

        readme_content += """
## Implementation Steps

"""
        if recommendation.get("implementation_steps"):
            for i, step in enumerate(recommendation["implementation_steps"], 1):
                readme_content += f"{i}. {step}\n"
        else:
            readme_content += (
                "1. Review the component requirements in `intent/recommendations.md`\n"
            )
            readme_content += "2. Design an OpenShift-native solution or hybrid approach\n"
            readme_content += "3. Implement tasks in `tasks/main.yml`\n"

        readme_content += """
## Required Inputs

"""
        if recommendation.get("required_inputs"):
            for var_name, description in recommendation["required_inputs"].items():
                readme_content += f"- `{var_name}`: {description}\n"
        else:
            readme_content += "_No specific inputs documented_\n"

        readme_content += """
## Testing & Validation

"""
        readme_content += recommendation.get(
            "testing_guidance", "Test thoroughly in dev environment before production use."
        )

        readme_content += """

## References

"""
        if recommendation.get("references"):
            for ref in recommendation["references"]:
                readme_content += f"- {ref}\n"
        else:
            readme_content += "- [Gap Analysis Report](../../../intent/gaps.md)\n"
            readme_content += "- [Migration Recommendations](../../../intent/recommendations.md)\n"

    else:
        # Fall back to basic README without detailed recommendation
        readme_content = f"""# {role_name.replace('_', ' ').title()} Role

## Component

**Name:** {component_name}
**Type:** {component_type}
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

## References

- [Gap Analysis Report](../../../intent/gaps.md)
- [OpenShift Documentation](https://docs.openshift.com/)
- [KubeVirt Documentation](https://kubevirt.io/user-guide/)
"""

    # Add evidence section
    readme_content += """
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
    if recommendation and recommendation.get("ansible_todo_task"):
        # Use the detailed TODO from recommendation
        todo_comment = recommendation["ansible_todo_task"]
    else:
        # Use basic TODO
        todo_comment = f"""# TODO: Implement {component_name} migration
# Classification: {component.get('level', 'MANUAL')}
# See README.md for guidance"""

    tasks_content = f"""---
# Tasks for {role_name}
# This is a STUB - manual implementation required

{todo_comment}

- name: "TODO: Implement {component_name} migration"
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

# Component information
component_name: "{component_name}"
component_type: "{component_type}"

"""

    # Add required inputs from recommendation if available
    if recommendation and recommendation.get("required_inputs"):
        defaults_content += "# Required inputs (see README.md for descriptions)\n"
        for var_name, description in recommendation["required_inputs"].items():
            # Add comment describing the variable
            defaults_content += f"# {description}\n"
            # Add placeholder variable
            defaults_content += f'{var_name}: "TODO: Define {var_name}"\n'
            defaults_content += "\n"
    else:
        defaults_content += "# TODO: Define required variables based on component requirements\n"
        defaults_content += "# See README.md for guidance\n"

    write_text(role_dir / "defaults/main.yml", defaults_content)
