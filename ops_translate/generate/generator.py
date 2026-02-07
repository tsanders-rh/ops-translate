"""
Unified artifact generation using LLM or templates.
"""

import re
from pathlib import Path

from rich.console import Console

from ops_translate.llm import get_provider
from ops_translate.util.files import ensure_dir, write_text
from ops_translate.workspace import Workspace

console = Console()

# Get project root to find prompts
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _generate_role_stubs_from_gaps(workspace: Workspace):
    """
    Generate role stubs for MANUAL/BLOCKED components from gap analysis.

    This is called after AI generation to add role stubs that AI can't create.
    """
    from ops_translate.generate.ansible import (
        _create_manual_role_stub,
        _load_gaps_data,
        _load_recommendations_data,
    )

    output_dir = workspace.root / "output/ansible"

    # Load gap analysis and recommendations data
    gaps_data = _load_gaps_data(workspace)
    recommendations_data = _load_recommendations_data(workspace)

    if not gaps_data:
        return

    # Generate role stubs for MANUAL/BLOCKED components
    for component in gaps_data.get("components", []):
        if component.get("level") in ["BLOCKED", "MANUAL"]:
            _create_manual_role_stub(output_dir, component, workspace, recommendations_data)
            comp_name = component.get("name", "unknown")
            console.print(f"[dim]  Generated role stub for: {comp_name}[/dim]")


def generate_all(
    workspace: Workspace,
    profile: str,
    use_ai: bool = False,
    output_format: str = "yaml",
):
    """
    Generate all artifacts (KubeVirt + Ansible) using AI or templates.

    Args:
        workspace: Workspace instance
        profile: Profile name (lab/prod)
        use_ai: If True, use LLM. If False, use templates.
        output_format: Output format (yaml, json, kustomize, argocd)
    """
    if use_ai:
        generate_with_ai(workspace, profile, output_format)
    else:
        generate_with_templates(workspace, profile, output_format)


def generate_with_ai(workspace: Workspace, profile: str, output_format: str = "yaml"):
    """
    Generate artifacts using LLM.

    Reads intent/intent.yaml and calls LLM to generate all artifacts.
    """
    # Load config and initialize LLM
    config = workspace.load_config()
    llm = get_provider(config)

    if not llm.is_available():
        console.print("[yellow]Warning: LLM not available. Falling back to templates.[/yellow]")
        generate_with_templates(workspace, profile, output_format)
        return

    # Load intent
    intent_file = workspace.root / "intent/intent.yaml"
    if not intent_file.exists():
        console.print("[red]Error: intent/intent.yaml not found. Run 'intent extract' first.[/red]")
        return

    intent_yaml = intent_file.read_text()

    # Load profile config
    profile_config = config["profiles"][profile]

    # Load prompt template
    prompt_file = PROJECT_ROOT / "prompts/generate_artifacts.md"
    prompt_template = prompt_file.read_text()

    # Format profile config as YAML
    profile_yaml = f"""profile_name: {profile}
default_namespace: {profile_config["default_namespace"]}
default_network: {profile_config["default_network"]}
default_storage_class: {profile_config["default_storage_class"]}"""

    # Fill in prompt
    prompt = prompt_template.replace("{intent_yaml}", intent_yaml)
    prompt = prompt.replace("{profile_config}", profile_yaml)

    console.print("[dim]Calling LLM to generate artifacts (this may take a moment)...[/dim]")

    # Call LLM
    try:
        response = llm.generate(
            prompt,
            max_tokens=8192,
            temperature=0.0,  # Larger for multiple files
        )

        # Parse multi-file response
        files = parse_multifile_response(response)

        # Write each file
        for file_path, content in files.items():
            full_path = workspace.root / file_path
            ensure_dir(full_path.parent)
            write_text(full_path, content)
            console.print(f"[dim]  Generated: {file_path}[/dim]")

        if not files:
            console.print(
                "[yellow]Warning: No files extracted from LLM response. "
                "Falling back to templates.[/yellow]"
            )
            generate_with_templates(workspace, profile, output_format)
        else:
            # After AI generation, also generate role stubs for MANUAL/BLOCKED components
            _generate_role_stubs_from_gaps(workspace)

    except Exception as e:
        console.print(f"[red]Error calling LLM: {e}[/red]")
        console.print("[yellow]Falling back to template-based generation[/yellow]")
        generate_with_templates(workspace, profile, output_format)


def parse_multifile_response(response: str) -> dict:
    """
    Parse LLM response with multiple files.

    Expected format:
    FILE: path/to/file.yaml
    ---
    content here
    ---

    FILE: path/to/another.yaml
    ---
    more content
    ---

    Returns:
        dict: {file_path: content}
    """
    files = {}

    # Split by FILE: markers
    file_pattern = r"FILE:\s*([^\n]+)\n---\n(.*?)\n---"
    matches = re.findall(file_pattern, response, re.DOTALL)

    for file_path, content in matches:
        file_path = file_path.strip()
        content = content.strip()
        files[file_path] = content

    return files


def generate_with_templates(workspace: Workspace, profile: str, output_format: str = "yaml"):
    """
    Generate artifacts using Jinja2 templates or direct generation.

    For standard YAML format, calls ansible.py and kubevirt.py directly to enable
    gap analysis integration. For other formats, uses Jinja2 templates.
    """
    import yaml

    from ops_translate.generate import ansible, kubevirt
    from ops_translate.generate.formats import get_format_handler
    from ops_translate.util.templates import TemplateLoader, create_template_context

    # Load config and intent
    config = workspace.load_config()
    intent_file = workspace.root / "intent/intent.yaml"
    gaps_file = workspace.root / "intent/gaps.json"

    # Check if we can work with gaps.json instead of merged intent
    has_merged_intent = intent_file.exists()
    has_gaps_data = gaps_file.exists()

    # For YAML format, check if custom templates exist
    loader = TemplateLoader(workspace.root)
    has_custom_templates = loader.has_custom_templates()

    if output_format == "yaml" and not has_custom_templates:
        # Use direct generation to support gap analysis (only if no custom templates)
        # This path works without merged intent.yaml if gaps.json exists
        try:
            ansible.generate(workspace, profile, use_ai=False)
            kubevirt.generate(workspace, profile, use_ai=False)
            console.print("[green]✓ KubeVirt manifest: output/kubevirt/vm.yaml[/green]")
            console.print("[green]✓ Ansible playbook: output/ansible/site.yml[/green]")
            console.print("[green]✓ Ansible role: output/ansible/roles/provision_vm/[/green]")
            console.print("[green]✓ README: output/README.md[/green]")
        except Exception as e:
            console.print(f"[red]Error generating artifacts: {e}[/red]")
        return

    # For other formats, we need merged intent.yaml
    if not has_merged_intent:
        console.print("[red]Error: intent/intent.yaml not found. Run 'intent merge' first.[/red]")
        console.print("[dim]Tip: For YAML format, you can skip merge if gaps.json exists[/dim]")
        return

    intent_data = yaml.safe_load(intent_file.read_text())
    profile_config = config["profiles"][profile]

    # Initialize template loader
    loader = TemplateLoader(workspace.root)

    # Show whether using custom or default templates
    if loader.has_custom_templates():
        console.print("[dim]Using custom templates from workspace[/dim]")
    else:
        console.print("[dim]Using default templates[/dim]")

    # Create template context
    context = create_template_context(intent_data, profile_config, profile)

    # Generate base YAML content
    content = {}

    # Generate KubeVirt manifest
    try:
        kubevirt_output = workspace.root / "output/kubevirt/vm.yaml"
        loader.render_template("kubevirt/vm.yaml.j2", context, kubevirt_output)
        content["kubevirt/vm.yaml"] = kubevirt_output.read_text()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not generate KubeVirt manifest: {e}[/yellow]")

    # Generate Ansible playbook
    try:
        playbook_output = workspace.root / "output/ansible/site.yml"
        loader.render_template("ansible/playbook.yml.j2", context, playbook_output)
        content["ansible/site.yml"] = playbook_output.read_text()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not generate Ansible playbook: {e}[/yellow]")

    # Generate Ansible role tasks
    try:
        role_tasks_output = workspace.root / "output/ansible/roles/provision_vm/tasks/main.yml"
        loader.render_template("ansible/role_tasks.yml.j2", context, role_tasks_output)
        content["ansible/roles/provision_vm/tasks/main.yml"] = role_tasks_output.read_text()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not generate Ansible role: {e}[/yellow]")

    # Apply output format
    if output_format != "yaml":
        try:
            format_handler = get_format_handler(output_format, workspace.root)
            format_handler.write(content, profile, context)
        except Exception as e:
            console.print(f"[yellow]⚠ Could not apply format {output_format}: {e}[/yellow]")

    # Generate README
    generate_readme(workspace, profile, context)


def generate_readme(workspace: Workspace, profile: str, context: dict):
    """Generate README.md for output artifacts."""
    readme_content = f"""# Generated Artifacts

Generated by ops-translate from workflow: {context['intent'].get('workflow_name', 'unknown')}

## Profile: {profile}

Configuration:
- Namespace: {context['profile'].get('default_namespace', 'default')}
- Network: {context['profile'].get('default_network', 'pod-network')}
- Storage Class: {context['profile'].get('default_storage_class', 'standard')}

## Files

- `kubevirt/vm.yaml` - KubeVirt VirtualMachine manifest
- `ansible/site.yml` - Ansible playbook
- `ansible/roles/provision_vm/tasks/main.yml` - Ansible role tasks

## Usage

### Apply KubeVirt Manifest

```bash
kubectl apply -f output/kubevirt/vm.yaml
```

### Run Ansible Playbook

```bash
cd output/ansible
ansible-playbook site.yml
```

## Customization

To customize the generated artifacts, initialize your workspace with templates:

```bash
ops-translate init my-workspace --with-templates
```

Then edit the templates in `templates/` directory before running `generate`.
"""

    readme_file = workspace.root / "output/README.md"
    write_text(readme_file, readme_content)
    console.print(f"[dim]  Generated: {readme_file.relative_to(workspace.root)}[/dim]")
