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


def _run_gap_analysis_for_vrealize(workspace: Workspace, intent_files: list[Path]) -> None:
    """
    Run gap analysis on vRealize workflow intent files and generate reports.

    Analyzes extracted vRealize intent for translatability of basic VM operations,
    classifies components, and generates gap reports.

    Args:
        workspace: Workspace instance
        intent_files: List of vRealize intent YAML files that were created

    Side Effects:
        - Writes intent/gaps.md and intent/gaps.json
        - Displays console info about classification results
    """
    if not intent_files:
        return

    from ops_translate.intent.classifiers.vrealize import VrealizeClassifier
    from ops_translate.intent.gaps import generate_gap_reports

    console.print("\n[cyan]Running gap analysis on vRealize workflows...[/cyan]")

    # Collect all classified components from intent files
    all_components = []
    classifier = VrealizeClassifier()

    for intent_file in intent_files:
        try:
            console.print(f"  Analyzing: {intent_file.name}")

            # Create analysis dict for classifier
            analysis = {
                "source_type": "vrealize",
                "intent_file": str(intent_file),
            }

            # Classify the workflow
            components = classifier.classify(analysis)
            all_components.extend(components)

            # Show summary for this file
            if components:
                supported = sum(1 for c in components if c.level.value == "SUPPORTED")
                partial = sum(1 for c in components if c.level.value == "PARTIAL")
                console.print(
                    f"    [dim]✓ Classified {len(components)} components "
                    f"({supported} supported, {partial} partial)[/dim]"
                )

        except Exception as e:
            console.print(f"    [yellow]Warning: Classification failed: {e}[/yellow]")
            continue

    # Generate consolidated gap reports
    output_dir = workspace.root / "intent"
    generate_gap_reports(all_components, output_dir, "vRealize workflows")
    console.print(
        "[dim]  ✓ Gap analysis reports written to intent/gaps.md and intent/gaps.json[/dim]"
    )

    # Display summary
    supported_count = sum(1 for c in all_components if c.level.value == "SUPPORTED")
    partial_count = sum(1 for c in all_components if c.level.value == "PARTIAL")
    blocking_count = sum(1 for c in all_components if c.is_blocking)

    if supported_count > 0:
        console.print(
            f"\n[green]✓ {supported_count} vRealize operation(s) fully supported.[/green]"
        )
    if partial_count > 0:
        console.print(
            f"[yellow]ℹ {partial_count} operation(s) require manual configuration.[/yellow]"
        )
    if blocking_count > 0:
        console.print(
            f"[yellow]⚠ {blocking_count} operation(s) cannot be automatically translated.[/yellow]"
        )


def _run_gap_analysis_for_powercli(workspace: Workspace, intent_files: list[Path]) -> None:
    """
    Run gap analysis on PowerCLI intent files and generate reports.

    Analyzes extracted PowerCLI intent for translatability of basic VM operations,
    classifies components, and generates gap reports. Unlike vRealize analysis which
    works with raw XML, this works with extracted intent YAML files.

    Args:
        workspace: Workspace instance
        intent_files: List of PowerCLI intent YAML files that were created

    Side Effects:
        - Updates intent/gaps.md and intent/gaps.json (appends to vRealize gaps if present)
        - Displays console info about classification results
    """
    if not intent_files:
        return

    from ops_translate.intent.classifiers.powercli import PowercliClassifier
    from ops_translate.intent.gaps import generate_gap_reports

    console.print("\n[cyan]Running gap analysis on PowerCLI scripts...[/cyan]")

    all_components = []

    # Analyze each intent file
    for intent_file in intent_files:
        try:
            console.print(f"  Analyzing: {intent_file.stem}.ps1")

            # Build analysis dict for PowerCLI classifier
            analysis = {
                "source_type": "powercli",
                "intent_file": str(intent_file),
            }

            # Use PowerCLI classifier
            classifier = PowercliClassifier()
            components = classifier.classify(analysis)
            all_components.extend(components)

            # Show summary for this file
            if components:
                supported_count = sum(1 for c in components if c.level.value == "SUPPORTED")
                partial_count = sum(1 for c in components if c.level.value == "PARTIAL")
                console.print(
                    f"    [dim]✓ Classified {len(components)} components "
                    f"({supported_count} supported, {partial_count} partial)[/dim]"
                )

        except Exception as e:
            console.print(f"    [yellow]Warning: Gap analysis failed: {e}[/yellow]")
            continue

    # Load existing vRealize gaps if they exist
    existing_components = []
    gaps_json = workspace.root / "intent/gaps.json"
    if gaps_json.exists():
        import json

        with open(gaps_json) as f:
            existing_data = json.load(f)
            from ops_translate.intent.classify import (
                ClassifiedComponent,
                MigrationPath,
                TranslatabilityLevel,
            )

            # Reconstruct ClassifiedComponent objects from JSON
            for comp_dict in existing_data.get("components", []):
                level = TranslatabilityLevel[comp_dict["level"]]
                path = (
                    MigrationPath[comp_dict["migration_path"]]
                    if comp_dict.get("migration_path")
                    else None
                )
                existing_components.append(
                    ClassifiedComponent(
                        name=comp_dict["name"],
                        component_type=comp_dict["component_type"],
                        level=level,
                        reason=comp_dict["reason"],
                        openshift_equivalent=comp_dict.get("openshift_equivalent"),
                        migration_path=path,
                        evidence=comp_dict.get("evidence"),
                        location=comp_dict.get("location"),
                        recommendations=comp_dict.get("recommendations", []),
                    )
                )

    # Combine with PowerCLI components
    combined_components = existing_components + all_components

    # Generate consolidated gap reports
    output_dir = workspace.root / "intent"
    workflow_name = "PowerCLI and vRealize" if existing_components else "PowerCLI scripts"
    generate_gap_reports(combined_components, output_dir, workflow_name)
    console.print(
        "[dim]  ✓ Gap analysis reports updated in intent/gaps.md and intent/gaps.json[/dim]"
    )

    # Display summary
    supported_count = sum(1 for c in all_components if c.level.value == "SUPPORTED")
    partial_count = sum(1 for c in all_components if c.level.value == "PARTIAL")
    blocking_count = sum(1 for c in all_components if c.is_blocking)

    if supported_count > 0:
        console.print(
            f"\n[green]✓ {supported_count} PowerCLI operation(s) fully supported.[/green]"
        )
    if partial_count > 0:
        console.print(
            f"[yellow]ℹ {partial_count} operation(s) require manual configuration.[/yellow]"
        )
    if blocking_count > 0:
        console.print(
            f"[yellow]⚠ {blocking_count} operation(s) cannot be automatically translated.[/yellow]"
        )

    console.print()


def extract_all(workspace: Workspace):
    """
    Extract operational intent from all imported source files using LLM.

    Processes all PowerCLI scripts (*.ps1) and vRealize workflows (*.xml)
    in the workspace's input directories, extracts operational intent using
    the configured LLM provider, and writes individual intent YAML files for
    each source. Also consolidates assumptions from all sources into a single
    markdown file.

    For vRealize workflows, automatically runs gap analysis to detect
    translatability issues (NSX operations, custom plugins, REST calls)
    and generates gap reports with migration guidance.

    The extraction process:
    1. Loads workspace configuration and initializes LLM provider
    2. Falls back to mock provider if LLM is unavailable
    3. Processes each PowerCLI script in input/powercli/
    4. Processes each vRealize workflow in input/vrealize/
    5. Validates extracted intent against schema
    6. Runs gap analysis on vRealize workflows (auto-detects translatability issues)
    7. Writes individual intent files and combined assumptions
    8. Writes gap analysis reports (if issues found)

    Args:
        workspace: Workspace instance with loaded configuration and directory structure.
            Must have input/powercli/ and/or input/vrealize/ directories with source files.

    Outputs:
        Creates the following files in the workspace:
        - intent/{filename}.intent.yaml - One file per source file
        - intent/assumptions.md - Combined assumptions from all extractions
        - intent/gaps.md - Gap analysis report (vRealize workflows only)
        - intent/gaps.json - Machine-readable gap report (vRealize workflows only)

    Raises:
        LLMProviderNotAvailableError: If LLM provider configuration is invalid.
        FileNotFoundError: If workspace input directories don't exist.

    Side Effects:
        - Makes API calls to configured LLM provider (may incur costs)
        - Writes multiple YAML and markdown files to workspace
        - Displays progress messages to console
        - Adds rate-limiting delays between API calls
        - Displays warnings if vRealize workflows have blocking translatability issues

    Example:
        >>> from pathlib import Path
        >>> from ops_translate.workspace import Workspace
        >>> ws = Workspace(Path("my-workspace"))
        >>> extract_all(ws)  # Extracts intent from all input files
        Extracting intent from: provision-vm.ps1
          ✓ Schema validation passed
        Running gap analysis on vRealize workflows...
          Analyzing: nsx-workflow.xml
          ⚠ Found 2 blocking issue(s)
        ✓ Gap analysis reports written to intent/gaps.md and intent/gaps.json
        ⚠ Warning: Found 2 component(s) that cannot be automatically translated.
          Review intent/gaps.md for migration guidance.

    Notes:
        - Rate limiting is applied between LLM calls (default: 1 second)
        - If intent validation fails, warnings are displayed but processing continues
        - Empty input directories are skipped silently
        - Gap analysis only runs for vRealize workflows (PowerCLI is fully translatable)
        - Gap analysis failures are logged as warnings but don't stop processing
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
    powercli_intent_files = []  # Track intent files for gap analysis

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

            # Track for gap analysis
            powercli_intent_files.append(output_file)

            # Rate limiting: delay before next API call (except after last file)
            if i < len(ps_files) - 1:
                delay = get_llm_rate_limit_delay()
                time.sleep(delay)

    # Process vRealize files
    vrealize_dir = workspace.root / "input/vrealize"
    vrealize_intent_files = []  # Track intent files for gap analysis

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

            # Track intent file for gap analysis
            vrealize_intent_files.append(output_file)

            # Rate limiting: delay before next API call (except after last file)
            if i < len(xml_files) - 1:
                delay = get_llm_rate_limit_delay()
                time.sleep(delay)

        # Run gap analysis on vRealize workflows
        _run_gap_analysis_for_vrealize(workspace, vrealize_intent_files)

    # Run gap analysis on PowerCLI scripts
    if powercli_intent_files:
        _run_gap_analysis_for_powercli(workspace, powercli_intent_files)

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
    import re

    # Load prompt template using Jinja2
    template_file = PROJECT_ROOT / "templates/prompts/extract_vrealize.txt.j2"
    template = Template(template_file.read_text())

    # Load workflow XML content
    workflow_content = xml_file.read_text()

    # Pre-detect NSX integration
    nsx_patterns = [
        r'RESTHostManager\.createHost\(["\']nsx',
        r'/api/v1/(firewall|ns-groups|segments|lb-)',
        r'/policy/api/v1/infra/(segments|lb-|tier-)',
        r'security[_-]group',
        r'firewall.*rule',
        r'nsx[_-]manager',
    ]

    nsx_indicators = []
    has_nsx = False

    for pattern in nsx_patterns:
        matches = re.findall(pattern, workflow_content, re.IGNORECASE)
        if matches:
            has_nsx = True
            nsx_indicators.append(f"- Found: {pattern} ({len(matches)} occurrence(s))")

    # Render prompt template with Jinja2
    prompt = template.render(
        workflow_content=workflow_content,
        has_nsx=has_nsx,
        nsx_indicators="\n".join(nsx_indicators) if nsx_indicators else ""
    )

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
