"""
Intent extraction from source files using LLM.
"""

import re
import time
from pathlib import Path

from rich.console import Console

from ops_translate.llm import get_provider
from ops_translate.util.config import get_llm_rate_limit_delay
from ops_translate.workspace import Workspace

console = Console()

# Get project root to find prompts
PROJECT_ROOT = Path(__file__).parent.parent.parent


def extract_all(workspace: Workspace):
    """
    Extract operational intent from all imported source files using LLM.

    Processes all PowerCLI scripts (*.ps1) and vRealize workflows (*.xml)
    in the workspace's input directories, extracts operational intent using
    the configured LLM provider, and writes individual intent YAML files for
    each source. Also consolidates assumptions from all sources into a single
    markdown file.

    The extraction process:
    1. Loads workspace configuration and initializes LLM provider
    2. Falls back to mock provider if LLM is unavailable
    3. Processes each PowerCLI script in input/powercli/
    4. Processes each vRealize workflow in input/vrealize/
    5. Validates extracted intent against schema
    6. Writes individual intent files and combined assumptions

    Args:
        workspace: Workspace instance with loaded configuration and directory structure.
            Must have input/powercli/ and/or input/vrealize/ directories with source files.

    Outputs:
        Creates the following files in the workspace:
        - intent/{filename}.intent.yaml - One file per source file
        - intent/assumptions.md - Combined assumptions from all extractions

    Raises:
        LLMProviderNotAvailableError: If LLM provider configuration is invalid.
        FileNotFoundError: If workspace input directories don't exist.

    Side Effects:
        - Makes API calls to configured LLM provider (may incur costs)
        - Writes multiple YAML and markdown files to workspace
        - Displays progress messages to console
        - Adds rate-limiting delays between API calls

    Example:
        >>> from pathlib import Path
        >>> from ops_translate.workspace import Workspace
        >>> ws = Workspace(Path("my-workspace"))
        >>> extract_all(ws)  # Extracts intent from all input files
        Extracting intent from: provision-vm.ps1
          ✓ Schema validation passed
        ✓ Intent extracted to intent/*.intent.yaml
        ✓ Assumptions written to intent/assumptions.md

    Notes:
        - Rate limiting is applied between LLM calls (default: 1 second)
        - If intent validation fails, warnings are displayed but processing continues
        - Empty input directories are skipped silently
    """
    # Load config and initialize LLM provider
    config = workspace.load_config()
    llm = get_provider(config)

    if not llm.is_available():
        console.print("[yellow]Warning: LLM not available. Using mock provider.[/yellow]")
        from ops_translate.llm.mock import MockProvider

        llm = MockProvider(config.get("llm", {}))

    assumptions = []

    # Process PowerCLI files
    powercli_dir = workspace.root / "input/powercli"
    if powercli_dir.exists():
        ps_files = list(powercli_dir.glob("*.ps1"))
        for i, ps_file in enumerate(ps_files):
            console.print(f"  Extracting intent from: {ps_file.name}")
            intent_yaml, file_assumptions = extract_powercli_intent(llm, ps_file)

            output_file = workspace.root / "intent" / f"{ps_file.stem}.intent.yaml"
            output_file.write_text(intent_yaml)

            # Validate extracted intent
            from ops_translate.intent.validate import validate_intent

            is_valid, errors = validate_intent(output_file)
            if not is_valid:
                console.print(
                    f"[yellow]  Warning: Intent validation failed for {output_file.name}:[/yellow]"
                )
                for error in errors:
                    console.print(f"[yellow]    {error}[/yellow]")
            else:
                console.print("[dim]  ✓ Schema validation passed[/dim]")

            assumptions.append(f"## {ps_file.name}\n")
            assumptions.extend([f"- {a}" for a in file_assumptions])
            assumptions.append("")

            # Rate limiting: delay before next API call (except after last file)
            if i < len(ps_files) - 1:
                delay = get_llm_rate_limit_delay()
                time.sleep(delay)

    # Process vRealize files
    vrealize_dir = workspace.root / "input/vrealize"
    if vrealize_dir.exists():
        xml_files = list(vrealize_dir.glob("*.xml"))
        for i, xml_file in enumerate(xml_files):
            console.print(f"  Extracting intent from: {xml_file.name}")
            intent_yaml, file_assumptions = extract_vrealize_intent(llm, xml_file)

            output_file = workspace.root / "intent" / f"{xml_file.stem}.intent.yaml"
            output_file.write_text(intent_yaml)

            # Validate extracted intent
            from ops_translate.intent.validate import validate_intent

            is_valid, errors = validate_intent(output_file)
            if not is_valid:
                console.print(
                    f"[yellow]  Warning: Intent validation failed for {output_file.name}:[/yellow]"
                )
                for error in errors:
                    console.print(f"[yellow]    {error}[/yellow]")
            else:
                console.print("[dim]  ✓ Schema validation passed[/dim]")

            assumptions.append(f"## {xml_file.name}\n")
            assumptions.extend([f"- {a}" for a in file_assumptions])
            assumptions.append("")

            # Rate limiting: delay before next API call (except after last file)
            if i < len(xml_files) - 1:
                delay = get_llm_rate_limit_delay()
                time.sleep(delay)

    # Write assumptions
    assumptions_file = workspace.root / "intent/assumptions.md"
    assumptions_content = "# Assumptions and Inferences\n\n" + "\n".join(assumptions)
    assumptions_file.write_text(assumptions_content)


def extract_powercli_intent(llm, ps_file: Path) -> tuple[str, list]:
    """
    Extract intent from PowerCLI script using LLM.

    Args:
        llm: LLM provider instance
        ps_file: Path to PowerCLI script

    Returns:
        tuple: (intent_yaml, assumptions_list)
    """
    from jinja2 import Template

    # Load prompt template using Jinja2
    template_file = PROJECT_ROOT / "templates/prompts/extract_powercli.txt.j2"
    template = Template(template_file.read_text())

    # Load PowerCLI script content
    script_content = ps_file.read_text()

    # Render prompt template with Jinja2
    prompt = template.render(script_content=script_content)

    # Call LLM
    try:
        response = llm.generate(prompt, max_tokens=4096, temperature=0.0)

        # Clean up response (remove markdown fences if present)
        yaml_content = clean_llm_response(response)

        # Extract assumptions from YAML if present
        assumptions = extract_assumptions_from_yaml(yaml_content)

        return yaml_content, assumptions

    except Exception as e:
        console.print(f"[red]Error calling LLM: {e}[/red]")
        # Fallback to placeholder
        return create_placeholder_intent("powercli", ps_file.name), [
            "LLM extraction failed, using placeholder"
        ]


def extract_vrealize_intent(llm, xml_file: Path) -> tuple[str, list]:
    """
    Extract intent from vRealize workflow using LLM.

    Args:
        llm: LLM provider instance
        xml_file: Path to vRealize workflow XML

    Returns:
        tuple: (intent_yaml, assumptions_list)
    """
    from jinja2 import Template

    # Load prompt template using Jinja2
    template_file = PROJECT_ROOT / "templates/prompts/extract_vrealize.txt.j2"
    template = Template(template_file.read_text())

    # Load workflow XML content
    workflow_content = xml_file.read_text()

    # Render prompt template with Jinja2
    prompt = template.render(workflow_content=workflow_content)

    # Call LLM
    try:
        response = llm.generate(prompt, max_tokens=4096, temperature=0.0)

        # Clean up response
        yaml_content = clean_llm_response(response)

        # Extract assumptions
        assumptions = extract_assumptions_from_yaml(yaml_content)

        return yaml_content, assumptions

    except Exception as e:
        console.print(f"[red]Error calling LLM: {e}[/red]")
        # Fallback to placeholder
        return create_placeholder_intent("vrealize", xml_file.name), [
            "LLM extraction failed, using placeholder"
        ]


def clean_llm_response(response: str) -> str:
    """
    Clean up LLM response to extract pure YAML.

    Removes markdown code fences, extra whitespace, etc.
    """
    # Remove markdown code fences
    response = re.sub(r"```ya?ml\n", "", response)
    response = re.sub(r"```\n?", "", response)

    # Strip leading/trailing whitespace
    response = response.strip()

    return response


def extract_assumptions_from_yaml(yaml_content: str) -> list:
    """
    Extract assumptions section from YAML content if present.

    Returns list of assumption strings.
    """
    assumptions = []

    # Look for assumptions section in YAML
    lines = yaml_content.split("\n")
    in_assumptions = False

    for line in lines:
        if line.strip() == "assumptions:":
            in_assumptions = True
            continue

        if in_assumptions:
            if line and not line.startswith(" ") and not line.startswith("-"):
                # End of assumptions section
                break
            if line.strip().startswith("- "):
                assumptions.append(line.strip()[2:])

    return assumptions if assumptions else ["Intent extracted via LLM"]


def create_placeholder_intent(source_type: str, filename: str) -> str:
    """Create a placeholder intent YAML (fallback)."""
    return f"""schema_version: 1
sources:
  - type: {source_type}
    file: input/{source_type}/{filename}

intent:
  workflow_name: provision_vm
  workload_type: virtual_machine

  inputs:
    vm_name:
      type: string
      required: true
    environment:
      type: enum
      values: [dev, prod]
      required: true

  governance:
    approval:
      required_when:
        environment: prod
"""
