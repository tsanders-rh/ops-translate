"""
Intent merging logic.
Merges per-source intent files into a single intent.yaml.
"""
from pathlib import Path
from ops_translate.workspace import Workspace
import yaml


def merge_intents(workspace: Workspace) -> bool:
    """
    Merge per-source intent files into intent/intent.yaml.

    Returns:
        bool: True if conflicts were detected, False otherwise.
    """
    intent_dir = workspace.root / "intent"

    # Find all .intent.yaml files
    intent_files = list(intent_dir.glob("*.intent.yaml"))

    if not intent_files:
        raise FileNotFoundError("No intent files found to merge")

    # For now, just use the first intent file as base
    # TODO: Implement proper merging logic with conflict detection
    base_intent_file = intent_files[0]
    merged_intent = yaml.safe_load(base_intent_file.read_text())

    # Merge sources from all files
    all_sources = []
    for intent_file in intent_files:
        intent_data = yaml.safe_load(intent_file.read_text())
        all_sources.extend(intent_data.get('sources', []))

    merged_intent['sources'] = all_sources

    # Write merged intent
    output_file = workspace.root / "intent/intent.yaml"
    with open(output_file, 'w') as f:
        yaml.dump(merged_intent, f, default_flow_style=False, sort_keys=False)

    # Validate merged intent against schema
    from ops_translate.intent.validate import validate_intent
    from rich.console import Console
    console = Console()

    is_valid, errors = validate_intent(output_file)
    if not is_valid:
        console.print(f"[yellow]Warning: Merged intent validation failed:[/yellow]")
        for error in errors:
            console.print(f"[yellow]  {error}[/yellow]")
        console.print(f"[yellow]Merged intent written but may have schema issues.[/yellow]")
    else:
        console.print(f"[dim]✓ Merged intent schema validation passed[/dim]")

    # Check for conflicts (simplified for now)
    conflicts = detect_conflicts(intent_files)

    if conflicts:
        conflicts_file = workspace.root / "intent/conflicts.md"
        conflicts_content = "# Intent Merge Conflicts\n\n" + "\n".join(conflicts)
        conflicts_file.write_text(conflicts_content)

    return bool(conflicts)


def detect_conflicts(intent_files: list) -> list:
    """
    Detect conflicts between intent files.

    Returns:
        list: List of conflict descriptions.
    """
    conflicts = []

    if len(intent_files) < 2:
        return conflicts

    # TODO: Implement detailed conflict detection
    # For now, just a placeholder
    # conflicts.append("- Example conflict: Different approval requirements")

    return conflicts
