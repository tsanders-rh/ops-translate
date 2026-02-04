"""
Intent extraction from source files using LLM.
"""
from pathlib import Path
from ops_translate.workspace import Workspace
from ops_translate.llm import get_provider
from rich.console import Console
import re

console = Console()

# Get project root to find prompts
PROJECT_ROOT = Path(__file__).parent.parent.parent


def extract_all(workspace: Workspace):
    """
    Extract intent from all imported source files using LLM.

    Outputs:
    - intent/powercli.intent.yaml (if PowerCLI files present)
    - intent/vrealize.intent.yaml (if vRealize files present)
    - intent/assumptions.md
    """
    # Load config and initialize LLM provider
    config = workspace.load_config()
    llm = get_provider(config)

    if not llm.is_available():
        console.print("[yellow]Warning: LLM not available. Using mock provider.[/yellow]")
        from ops_translate.llm.mock import MockProvider
        llm = MockProvider(config.get('llm', {}))

    assumptions = []

    # Process PowerCLI files
    powercli_dir = workspace.root / "input/powercli"
    if powercli_dir.exists():
        ps_files = list(powercli_dir.glob("*.ps1"))
        for ps_file in ps_files:
            console.print(f"  Extracting intent from: {ps_file.name}")
            intent_yaml, file_assumptions = extract_powercli_intent(llm, ps_file)

            output_file = workspace.root / "intent" / f"{ps_file.stem}.intent.yaml"
            output_file.write_text(intent_yaml)

            # Validate extracted intent
            from ops_translate.intent.validate import validate_intent
            is_valid, errors = validate_intent(output_file)
            if not is_valid:
                console.print(f"[yellow]  Warning: Intent validation failed for {output_file.name}:[/yellow]")
                for error in errors:
                    console.print(f"[yellow]    {error}[/yellow]")
            else:
                console.print(f"[dim]  ✓ Schema validation passed[/dim]")

            assumptions.append(f"## {ps_file.name}\n")
            assumptions.extend([f"- {a}" for a in file_assumptions])
            assumptions.append("")

    # Process vRealize files
    vrealize_dir = workspace.root / "input/vrealize"
    if vrealize_dir.exists():
        xml_files = list(vrealize_dir.glob("*.xml"))
        for xml_file in xml_files:
            console.print(f"  Extracting intent from: {xml_file.name}")
            intent_yaml, file_assumptions = extract_vrealize_intent(llm, xml_file)

            output_file = workspace.root / "intent" / f"{xml_file.stem}.intent.yaml"
            output_file.write_text(intent_yaml)

            # Validate extracted intent
            from ops_translate.intent.validate import validate_intent
            is_valid, errors = validate_intent(output_file)
            if not is_valid:
                console.print(f"[yellow]  Warning: Intent validation failed for {output_file.name}:[/yellow]")
                for error in errors:
                    console.print(f"[yellow]    {error}[/yellow]")
            else:
                console.print(f"[dim]  ✓ Schema validation passed[/dim]")

            assumptions.append(f"## {xml_file.name}\n")
            assumptions.extend([f"- {a}" for a in file_assumptions])
            assumptions.append("")

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
    # Load prompt template
    prompt_file = PROJECT_ROOT / "prompts/intent_extract_powercli.md"
    prompt_template = prompt_file.read_text()

    # Load PowerCLI script content
    script_content = ps_file.read_text()

    # Fill in prompt template
    prompt = prompt_template.replace("{script_content}", script_content)

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
    # Load prompt template
    prompt_file = PROJECT_ROOT / "prompts/intent_extract_vrealize.md"
    prompt_template = prompt_file.read_text()

    # Load workflow XML content
    workflow_content = xml_file.read_text()

    # Fill in prompt template
    prompt = prompt_template.replace("{workflow_content}", workflow_content)

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
    response = re.sub(r'```ya?ml\n', '', response)
    response = re.sub(r'```\n?', '', response)

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
    lines = yaml_content.split('\n')
    in_assumptions = False

    for line in lines:
        if line.strip() == 'assumptions:':
            in_assumptions = True
            continue

        if in_assumptions:
            if line and not line.startswith(' ') and not line.startswith('-'):
                # End of assumptions section
                break
            if line.strip().startswith('- '):
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
