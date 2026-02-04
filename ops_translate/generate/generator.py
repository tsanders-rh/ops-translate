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


def generate_all(workspace: Workspace, profile: str, use_ai: bool = False):
    """
    Generate all artifacts (KubeVirt + Ansible) using AI or templates.

    Args:
        workspace: Workspace instance
        profile: Profile name (lab/prod)
        use_ai: If True, use LLM. If False, use templates.
    """
    if use_ai:
        generate_with_ai(workspace, profile)
    else:
        generate_with_templates(workspace, profile)


def generate_with_ai(workspace: Workspace, profile: str):
    """
    Generate artifacts using LLM.

    Reads intent/intent.yaml and calls LLM to generate all artifacts.
    """
    # Load config and initialize LLM
    config = workspace.load_config()
    llm = get_provider(config)

    if not llm.is_available():
        console.print("[yellow]Warning: LLM not available. Falling back to templates.[/yellow]")
        generate_with_templates(workspace, profile)
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
            generate_with_templates(workspace, profile)

    except Exception as e:
        console.print(f"[red]Error calling LLM: {e}[/red]")
        console.print("[yellow]Falling back to template-based generation[/yellow]")
        generate_with_templates(workspace, profile)


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


def generate_with_templates(workspace: Workspace, profile: str):
    """
    Generate artifacts using static templates (fallback).
    """
    from ops_translate.generate import ansible, kubevirt

    # Generate using template functions
    kubevirt.generate(workspace, profile, use_ai=False)
    ansible.generate(workspace, profile, use_ai=False)
