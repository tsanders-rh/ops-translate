"""
CLI entry point for ops-translate.
"""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path

import typer
from rich.console import Console

from ops_translate.exceptions import (
    FileNotFoundError as OpsFileNotFoundError,
)
from ops_translate.exceptions import (
    InvalidSourceTypeError,
    OpsTranslateError,
    WorkspaceNotFoundError,
    format_error_for_cli,
)
from ops_translate.util.files import ensure_dir, write_text
from ops_translate.util.hashing import sha256_file
from ops_translate.workspace import Workspace

app = typer.Typer(
    name="ops-translate",
    help="AI-assisted operational translation for VMware → OpenShift Virtualization",
    add_completion=False,
)
console = Console()
logger = logging.getLogger(__name__)

# Configuration constants
MAX_IMPORT_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def handle_errors(func):
    """Decorator to handle exceptions in CLI commands with nice formatting."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OpsTranslateError as e:
            # Our custom exceptions with helpful messages
            console.print(format_error_for_cli(e))
            raise typer.Exit(1)
        except Exception as e:
            # Unexpected errors
            console.print(f"[red]Unexpected error:[/red] {str(e)}")
            console.print("\n[yellow]This may be a bug. Please report it at:")
            console.print("https://github.com/tsanders-rh/ops-translate/issues[/yellow]")
            raise typer.Exit(1)

    return wrapper


# Create intent subcommand group
intent_app = typer.Typer(help="Intent management commands (extract, merge, edit)")
app.add_typer(intent_app, name="intent")

# Create map subcommand group
map_app = typer.Typer(help="Mapping preview commands")
app.add_typer(map_app, name="map")


@app.command()
def init(
    workspace_dir: str = typer.Argument(..., help="Workspace directory to initialize"),
    with_templates: bool = typer.Option(
        False, "--with-templates", help="Copy default templates for customization"
    ),
):
    """Initialize a new ops-translate workspace."""
    console.print(f"[bold blue]Initializing workspace:[/bold blue] {workspace_dir}")

    workspace = Workspace(Path(workspace_dir))
    workspace.initialize()

    console.print(f"[green]✓ Created directory structure in {workspace_dir}[/green]")
    console.print("[green]✓ Wrote configuration to ops-translate.yaml[/green]")

    # Copy templates if requested
    if with_templates:
        from ops_translate.util.templates import TemplateLoader

        loader = TemplateLoader(workspace.root)
        try:
            loader.copy_default_templates_to_workspace()
            console.print("[green]✓ Copied default templates to templates/[/green]")
            console.print("[dim]  You can now customize templates for your organization[/dim]")
        except FileNotFoundError as e:
            # Expected error - templates directory not found
            console.print(f"[yellow]⚠ Template directory not found: {e}[/yellow]")
            logger.warning(f"Templates not found: {e}")
        except PermissionError as e:
            # Permission issue - cannot write to workspace
            console.print(f"[red]✗ Permission denied copying templates: {e}[/red]")
            logger.error(f"Permission error copying templates: {e}")
            raise typer.Exit(1)
        except Exception as e:
            # Unexpected error
            console.print(f"[red]✗ Unexpected error copying templates: {e}[/red]")
            logger.exception("Unexpected error copying templates")
            raise typer.Exit(1)

    console.print("\n[dim]Next steps:[/dim]")
    console.print(f"  cd {workspace_dir}")
    if with_templates:
        console.print("  # Customize templates in templates/ directory")
    console.print("  ops-translate import --source powercli --file <path>")


@app.command(name="import")
@handle_errors
def import_cmd(
    source: str | None = typer.Option(
        None, "--source", help="Source type (powercli|vrealize), auto-detected if omitted"
    ),
    file: str = typer.Option(..., "--file", help="Path to file or directory to import"),
):
    """Import PowerCLI scripts or vRealize workflows from a file or directory.

    If --source is omitted, file types are auto-detected based on extension:
    - *.ps1 files are imported as powercli
    - *.xml files are imported as vrealize
    """
    # Validate source type if provided
    if source and source not in ["powercli", "vrealize"]:
        raise InvalidSourceTypeError(source)

    # Check path exists
    source_path = Path(file)
    if not source_path.exists():
        raise OpsFileNotFoundError(str(source_path))

    # Ensure we're in a workspace
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        raise WorkspaceNotFoundError()

    # Auto-detect mode: import both PowerCLI and vRealize files
    if source is None:
        if source_path.is_file():
            # Detect source type from file extension
            if source_path.suffix == ".ps1":
                source = "powercli"
            elif source_path.suffix == ".xml":
                source = "vrealize"
            else:
                console.print(
                    f"[yellow]Cannot auto-detect file type for {source_path.name}[/yellow]"
                )
                console.print("Use --source to specify type explicitly (powercli or vrealize)")
                raise typer.Exit(1)
        else:
            # Directory: import both types
            _import_directory_auto(source_path, workspace)
            return

    # Single source type import (explicit or auto-detected)
    _import_single_source(source, source_path, workspace)


def _import_directory_auto(source_path: Path, workspace: Workspace):
    """Import both PowerCLI and vRealize files from a directory."""
    # Find all PowerCLI and vRealize files
    ps1_files = list(source_path.glob("*.ps1"))
    xml_files = list(source_path.glob("*.xml"))

    total_files = len(ps1_files) + len(xml_files)

    if total_files == 0:
        console.print(
            f"No PowerCLI (*.ps1) or vRealize (*.xml) files found in {source_path.name}",
            style="yellow",
        )
        return

    console.print(
        f"[bold blue]Auto-detecting and importing files from {source_path.name}[/bold blue]"
    )

    # Import PowerCLI files
    if ps1_files:
        console.print(f"\n[dim]PowerCLI scripts ({len(ps1_files)} files):[/dim]")
        for ps1_file in ps1_files:
            _import_file(ps1_file, "powercli", workspace)

    # Import vRealize files
    if xml_files:
        console.print(f"\n[dim]vRealize workflows ({len(xml_files)} files):[/dim]")
        for xml_file in xml_files:
            _import_file(xml_file, "vrealize", workspace)

    # Summary
    console.print()
    console.print(f"[green]✓ Imported {total_files} file(s) total[/green]")
    if ps1_files:
        console.print(f"[green]  • {len(ps1_files)} PowerCLI script(s)[/green]")
    if xml_files:
        console.print(f"[green]  • {len(xml_files)} vRealize workflow(s)[/green]")


def _import_single_source(source: str, source_path: Path, workspace: Workspace):
    """Import files for a single source type."""
    # Determine file pattern based on source type
    file_pattern = "*.ps1" if source == "powercli" else "*.xml"

    # Get list of files to import
    files_to_import = []
    if source_path.is_file():
        files_to_import = [source_path]
    elif source_path.is_dir():
        # Find all matching files in directory
        files_to_import = list(source_path.glob(file_pattern))
        if not files_to_import:
            # Disable markup to avoid issues with glob patterns like *.ps1
            console.print(f"No {file_pattern} files found in {source_path}", style="yellow")
            return  # Not an error, just no files to import
    else:
        raise OpsFileNotFoundError(f"{source_path} is not a file or directory")

    # Display import plan
    if len(files_to_import) == 1:
        console.print(
            f"[bold blue]Importing {source} file:[/bold blue] " f"{files_to_import[0].name}"
        )
    else:
        console.print(
            f"[bold blue]Importing {len(files_to_import)} {source} files "
            f"from {source_path.name}[/bold blue]"
        )

    # Import each file
    imported_files = []
    for file_path in files_to_import:
        result = _import_file(file_path, source, workspace)
        if result:
            imported_files.append(result)

    # Print summary
    console.print()
    if imported_files:
        console.print(
            f"[green]✓ Imported {len(imported_files)} file(s) to " f"input/{source}/[/green]"
        )
        if len(imported_files) == 1:
            console.print(f"[green]✓ SHA256: {imported_files[0][2]}[/green]")
    else:
        console.print("[yellow]No new files imported[/yellow]")


def _import_file(
    file_path: Path, source: str, workspace: Workspace
) -> tuple[str, Path, str] | None:
    """
    Import a single file to the workspace.

    Returns:
        Tuple of (filename, dest_path, file_hash) if imported, None if skipped
    """
    # Check file size to prevent DoS
    file_size = file_path.stat().st_size
    if file_size > MAX_IMPORT_FILE_SIZE:
        console.print(
            f"[yellow]⚠ Skipping {file_path.name}: File too large "
            f"({file_size:,} bytes, max {MAX_IMPORT_FILE_SIZE:,})[/yellow]"
        )
        return None

    # Check file is readable
    if not os.access(file_path, os.R_OK):
        console.print(f"[yellow]⚠ Skipping {file_path.name}: Cannot read file[/yellow]")
        return None

    # Copy file to input directory
    input_dir = workspace.root / "input" / source
    dest_path = input_dir / file_path.name

    # Ensure input directory exists before copying
    ensure_dir(input_dir)

    # Skip if file already exists with same content
    if dest_path.exists():
        existing_hash = sha256_file(dest_path)
        new_hash = sha256_file(file_path)
        if existing_hash == new_hash:
            console.print(f"[dim]  ✓ {file_path.name} (already imported, skipping)[/dim]")
            return None

    shutil.copy2(file_path, dest_path)

    # Compute hash and write metadata
    file_hash = sha256_file(dest_path)
    timestamp = datetime.now().isoformat()
    run_dir = workspace.root / "runs" / timestamp.replace(":", "-").split(".")[0]
    ensure_dir(run_dir)

    metadata = {
        "timestamp": timestamp,
        "source_type": source,
        "original_file": str(file_path.absolute()),
        "imported_file": str(dest_path.relative_to(workspace.root)),
        "sha256": file_hash,
    }

    write_text(run_dir / "import.json", json.dumps(metadata, indent=2))

    console.print(f"[green]  ✓ {file_path.name}[/green]")
    return (file_path.name, dest_path, file_hash)


@app.command()
def summarize():
    """Summarize imported files (no AI required)."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    from ops_translate.summarize import powercli, vrealize
    from ops_translate.util.progress import track_progress

    # Count total files to analyze
    powercli_dir = workspace.root / "input/powercli"
    vrealize_dir = workspace.root / "input/vrealize"
    ps_files = list(powercli_dir.glob("*.ps1")) if powercli_dir.exists() else []
    xml_files = list(vrealize_dir.glob("*.xml")) if vrealize_dir.exists() else []
    total_files = len(ps_files) + len(xml_files)

    if total_files == 0:
        console.print("[yellow]No files to analyze[/yellow]")
        return

    summary_lines = []
    summary_lines.append("# Import Summary\n")

    # Analyze with progress bar
    with track_progress("Analyzing files", total=total_files) as progress:
        task = progress.add_task("analyzing", total=total_files)
        file_count = 0

        # Summarize PowerCLI files
        if ps_files:
            summary_lines.append("## PowerCLI Scripts\n")
            for ps_file in ps_files:
                file_count += 1
                progress.update(
                    task, description=f"Analyzing {ps_file.name} ({file_count}/{total_files})"
                )
                summary = powercli.summarize(ps_file)
                summary_lines.append(f"### {ps_file.name}\n")
                summary_lines.append(summary + "\n")
                progress.update(task, advance=1)

        # Summarize vRealize files
        if xml_files:
            summary_lines.append("## vRealize Workflows\n")
            for xml_file in xml_files:
                file_count += 1
                progress.update(
                    task, description=f"Analyzing {xml_file.name} ({file_count}/{total_files})"
                )
                summary = vrealize.summarize(xml_file)
                summary_lines.append(f"### {xml_file.name}\n")
                summary_lines.append(summary + "\n")
                progress.update(task, advance=1)

    # Write summary
    summary_file = workspace.root / "intent/summary.md"
    write_text(summary_file, "".join(summary_lines))

    console.print(f"[green]✓ Analyzed {total_files} file(s)[/green]")
    console.print("[green]✓ Summary written to intent/summary.md[/green]")


@intent_app.command()
def extract():
    """Extract normalized intent from imported sources."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Extracting intent from source files...[/bold blue]")

    from ops_translate.intent.extract import extract_all

    extract_all(workspace)

    console.print("[green]✓ Intent extracted to intent/*.intent.yaml[/green]")
    console.print("[green]✓ Assumptions written to intent/assumptions.md[/green]")


@intent_app.command()
def merge(force: bool = typer.Option(False, "--force", help="Merge even if conflicts exist")):
    """Merge per-source intents into single intent.yaml."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Merging intent files...[/bold blue]")

    from ops_translate.intent.merge import merge_intents

    conflicts = merge_intents(workspace)

    if conflicts and not force:
        console.print("[yellow]⚠ Conflicts detected - see intent/conflicts.md[/yellow]")
        console.print("[yellow]  Run with --force to merge anyway[/yellow]")
        raise typer.Exit(1)
    elif conflicts:
        console.print("[yellow]⚠ Conflicts detected but merged (--force)[/yellow]")

    console.print("[green]✓ Merged intent written to intent/intent.yaml[/green]")


@intent_app.command()
def edit(file: str = typer.Option(None, "--file", help="Specific intent file to edit")):
    """Open intent file in $EDITOR."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    if file:
        intent_file = workspace.root / file
    else:
        intent_file = workspace.root / "intent/intent.yaml"

    if not intent_file.exists():
        console.print(f"[red]Error: File not found: {intent_file}[/red]")
        raise typer.Exit(1)

    editor = os.environ.get("EDITOR")
    if not editor:
        console.print("[yellow]$EDITOR not set. Please edit manually:[/yellow]")
        console.print(f"  {intent_file}")
        raise typer.Exit(0)

    console.print(f"[bold blue]Opening {intent_file.name} in {editor}...[/bold blue]")
    result = subprocess.run([editor, str(intent_file)], check=False)
    if result.returncode != 0:
        console.print(f"[yellow]Editor exited with code {result.returncode}[/yellow]")


@intent_app.command(name="interview-generate")
def interview_generate():
    """Generate targeted interview questions for PARTIAL/EXPERT-GUIDED components."""
    from ops_translate.intent.interview import generate_questions, save_questions

    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Generating interview questions...[/bold blue]")

    # Load gap analysis results
    gaps_file = workspace.root / "intent/gaps.json"
    if not gaps_file.exists():
        console.print(
            "[red]Error: gaps.json not found. Run 'ops-translate intent extract' first.[/red]"
        )
        raise typer.Exit(1)

    with open(gaps_file) as f:
        gaps_data = json.load(f)

    # Get classified components
    from ops_translate.intent.classify import (
        ClassifiedComponent,
        MigrationPath,
        TranslatabilityLevel,
    )

    components = []
    for comp_data in gaps_data.get("components", []):
        # Normalize evidence to string (handle both string and list from gaps.json)
        evidence_raw = comp_data.get("evidence")
        if evidence_raw:
            evidence = "\n".join(evidence_raw) if isinstance(evidence_raw, list) else evidence_raw
        else:
            evidence = None

        components.append(
            ClassifiedComponent(
                name=comp_data["name"],
                component_type=comp_data["component_type"],
                level=TranslatabilityLevel(comp_data["level"]),
                reason=comp_data.get("reason", ""),
                openshift_equivalent=comp_data.get("openshift_equivalent", ""),
                migration_path=MigrationPath(comp_data["migration_path"]),
                location=comp_data.get("location", "unknown"),
                recommendations=comp_data.get("recommendations", []),
                evidence=evidence,
            )
        )

    # Generate questions
    questions = generate_questions(components, workspace.root)

    # Count questions
    question_count = len(questions.get("questions", []))

    if question_count == 0:
        console.print("[yellow]No interview questions needed.[/yellow]")
        console.print("All components are either SUPPORTED or don't have question generators yet.")
        return

    # Save to file
    output_file = workspace.root / "intent/questions.json"
    save_questions(questions, output_file)

    console.print(f"[green]✓ Generated {question_count} questions[/green]")
    console.print(
        f"[green]✓ Questions written to {output_file.relative_to(workspace.root)}[/green]"
    )
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Review questions.json")
    console.print("  2. Create intent/answers.yaml with your answers")
    console.print("  3. Run: ops-translate intent interview-apply")


@intent_app.command(name="interview-apply")
def interview_apply():
    """Apply interview answers to derive decisions and update classifications."""
    from ops_translate.intent.classify import (
        ClassifiedComponent,
        MigrationPath,
        TranslatabilityLevel,
    )
    from ops_translate.intent.interview import apply_answers, save_decisions

    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Applying interview answers...[/bold blue]")

    # Check for answers file
    answers_file = workspace.root / "intent/answers.yaml"
    if not answers_file.exists():
        console.print(f"[red]Error: {answers_file} not found.[/red]")
        console.print("Create intent/answers.yaml with your answers first.")
        raise typer.Exit(1)

    # Load components from gaps.json
    gaps_file = workspace.root / "intent/gaps.json"
    if not gaps_file.exists():
        console.print("[red]Error: gaps.json not found.[/red]")
        raise typer.Exit(1)

    with open(gaps_file) as f:
        gaps_data = json.load(f)

    components = []
    for comp_data in gaps_data.get("components", []):
        # Normalize evidence to string (handle both string and list from gaps.json)
        evidence_raw = comp_data.get("evidence")
        if evidence_raw:
            evidence = "\n".join(evidence_raw) if isinstance(evidence_raw, list) else evidence_raw
        else:
            evidence = None

        components.append(
            ClassifiedComponent(
                name=comp_data["name"],
                component_type=comp_data["component_type"],
                level=TranslatabilityLevel(comp_data["level"]),
                reason=comp_data.get("reason", ""),
                openshift_equivalent=comp_data.get("openshift_equivalent", ""),
                migration_path=MigrationPath(comp_data["migration_path"]),
                location=comp_data.get("location", "unknown"),
                recommendations=comp_data.get("recommendations", []),
                evidence=evidence,
            )
        )

    # Apply answers and derive decisions
    decisions = apply_answers(answers_file, components)

    # Save decisions
    decisions_file = workspace.root / "intent/decisions.yaml"
    save_decisions(decisions, decisions_file)

    # Count decisions
    decision_count = len(decisions.get("decisions", {}))

    console.print(f"[green]✓ Derived {decision_count} decisions[/green]")
    console.print(
        f"[green]✓ Decisions written to {decisions_file.relative_to(workspace.root)}[/green]"
    )
    console.print()
    console.print("[bold]Classification changes:[/bold]")

    # Show summary of changes
    for location, decision in decisions.get("decisions", {}).items():
        new_classification = decision.get("classification", "UNKNOWN")
        reason = decision.get("reason", "")
        console.print(f"  • {location}: → {new_classification}")
        console.print(f"    {reason}")

    console.print()
    console.print("[bold blue]Regenerating gap reports with updated classifications...[/bold blue]")

    # Regenerate gap reports (will auto-apply decisions.yaml)
    from ops_translate.intent.gaps import generate_gap_reports

    # Write updated gap reports - generate_gap_reports will auto-apply decisions
    generate_gap_reports(components, workspace.root / "intent", workflow_name=workspace.root.name)

    console.print("[green]✓ Gap reports updated with decision-based classifications[/green]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Review updated intent/gaps.md and intent/gaps.json")
    console.print("  2. Re-run: ops-translate report (to see updated HTML report)")
    console.print("  3. Generate artifacts: ops-translate generate --profile <profile>")


@map_app.command()
def preview(target: str = typer.Option(..., "--target", help="Target platform (openshift)")):
    """Generate mapping preview showing source → target equivalents."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    if target != "openshift":
        console.print("[red]Error: Only 'openshift' target is supported in v1[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]Generating mapping preview for {target}...[/bold blue]")

    # Generate preview
    preview_content = """# Mapping Preview: VMware → OpenShift

## vRealize Workflow Concepts

| vRealize Concept | Ansible Equivalent | OpenShift Equivalent |
|-----------------|-------------------|---------------------|
| Workflow | Playbook | Job/WorkflowRun |
| Workflow Input | Playbook Variable | ConfigMap/Secret |
| Scriptable Task | Ansible Task | Container/Job |
| Decision Element | Conditional (when:) | N/A |
| Approval Policy | survey_enabled | N/A (external) |

## PowerCLI Constructs

| PowerCLI | Ansible Module | KubeVirt Resource |
|----------|---------------|------------------|
| New-VM | community.kubevirt.kubevirt_vm | VirtualMachine |
| Set-VM -MemoryGB | kubevirt_vm: memory | spec.template.spec.domain.resources.requests.memory |
| Set-VM -NumCpu | kubevirt_vm: cpu_cores | spec.template.spec.domain.cpu.cores |
| Get-VMHost | N/A | Node |
| New-NetworkAdapter | N/A | spec.template.spec.networks |
| New-HardDisk | N/A | spec.template.spec.volumes + DataVolume |

## Storage Mapping

- **VMware Datastore** → **StorageClass** (OpenShift)
- **VMDK** → **PersistentVolumeClaim** / **DataVolume** (KubeVirt)

## Network Mapping

- **VMware PortGroup** → **NetworkAttachmentDefinition** (Multus CNI)
- **VMware vSwitch** → **OVN/OVS Bridge**
"""

    preview_file = workspace.root / "mapping/preview.md"
    write_text(preview_file, preview_content)

    console.print("[green]✓ Mapping preview written to mapping/preview.md[/green]")


@app.command()
def generate(
    profile: str = typer.Option(..., "--profile", help="Profile to use (lab|prod)"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Use templates only, no AI"),
    format: str = typer.Option(
        "yaml",
        "--format",
        help="Output format: yaml, json, kustomize, argocd",
    ),
    assume_existing_vms: bool = typer.Option(
        False,
        "--assume-existing-vms",
        help="Assume VMs exist (MTV mode) - generate validation/day-2 ops only, not VM YAMLs",
    ),
    eda: bool = typer.Option(
        False,
        "--eda",
        help="Also generate Event-Driven Ansible rulebooks from vRO event subscriptions",
    ),
    eda_only: bool = typer.Option(
        False,
        "--eda-only",
        help="Generate only EDA rulebooks (skip Ansible/KubeVirt artifacts)",
    ),
    locking_backend: str = typer.Option(
        "redis",
        "--locking-backend",
        help="Distributed locking backend: redis, consul, file",
    ),
    no_locking: bool = typer.Option(
        False,
        "--no-locking",
        help="Disable distributed locking for LockingSystem calls (not recommended for production)",
    ),
):
    """Generate Ansible and KubeVirt artifacts in various formats.

    By default, generates VM definitions for greenfield deployments.
    Use --assume-existing-vms when VMs were migrated via MTV or already exist.

    Use --eda to also generate Event-Driven Ansible rulebooks from vRO event subscriptions.
    Use --eda-only to generate only EDA rulebooks.

    Use --locking-backend to choose distributed locking backend (redis, consul, file).
    Use --no-locking to disable locking (only for testing/development).
    """
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    config = workspace.load_config()
    if profile not in config.get("profiles", {}):
        console.print(f"[red]Error: Profile '{profile}' not found in config[/red]")
        raise typer.Exit(1)

    # Validate locking backend
    valid_backends = ["redis", "consul", "file"]
    if locking_backend not in valid_backends:
        console.print(
            f"[red]Error: Invalid locking backend '{locking_backend}'. "
            f"Must be one of: {', '.join(valid_backends)}[/red]"
        )
        raise typer.Exit(1)

    # Determine locking settings (CLI overrides profile config)
    locking_enabled = not no_locking
    profile_config = config["profiles"][profile]
    backend = locking_backend or profile_config.get("locking", {}).get("backend", "redis")

    # Check for workspace-level setting, CLI flag overrides
    workspace_setting = config.get("assume_existing_vms", False)
    assume_existing = assume_existing_vms or workspace_setting

    mode = "template-based" if no_ai else "AI-assisted"
    vm_mode = "MTV mode (existing VMs)" if assume_existing else "greenfield"

    # Handle EDA-only mode
    if eda_only:
        console.print("[bold blue]Generating Event-Driven Ansible rulebooks:[/bold blue]")
        from ops_translate.generate.eda_rulebook import generate_eda_artifacts

        # Find all vRO policy files
        vrealize_dir = workspace.root / "input/vrealize"
        if not vrealize_dir.exists():
            console.print("[red]Error: No vRealize files found to process[/red]")
            console.print(
                "[dim]Hint: Run 'ops-translate import --source vrealize-events' first[/dim]"
            )
            raise typer.Exit(1)

        policy_files = list(vrealize_dir.glob("*policy*.xml")) + list(
            vrealize_dir.glob("*event*.xml")
        )
        if not policy_files:
            console.print(
                "[yellow]Warning: No event policy files found in input/vrealize/[/yellow]"
            )
            console.print("[dim]Looking for files matching: *policy*.xml or *event*.xml[/dim]")
            raise typer.Exit(1)

        generate_eda_artifacts(workspace, policy_files, use_job_templates=True, categorize=True)
        return

    # Standard generation
    console.print(
        f"[bold blue]Generating artifacts ({mode}, {vm_mode}):[/bold blue] "
        f"profile={profile}, format={format}"
    )

    from ops_translate.generate import generate_all

    # Generate all artifacts (success messages printed by generator)
    generate_all(
        workspace,
        profile,
        use_ai=not no_ai,
        output_format=format,
        assume_existing_vms=assume_existing,
    )

    # Generate locking setup documentation if vRealize workflows exist
    if locking_enabled:
        vrealize_dir = workspace.root / "input/vrealize"
        if vrealize_dir.exists():
            workflow_files = list(vrealize_dir.glob("*.xml"))
            if workflow_files:
                from ops_translate.generate.ansible_locking import generate_locking_setup_doc

                output_dir = workspace.root / "output/ansible"
                output_dir.mkdir(parents=True, exist_ok=True)
                doc_path = output_dir / "LOCKING_SETUP.md"

                doc_content = generate_locking_setup_doc(backend, str(doc_path))

                with open(doc_path, "w") as f:
                    f.write(doc_content)

                console.print(
                    f"[green]✓ Generated: {doc_path.relative_to(workspace.root)}[/green]"
                )

    # Also generate EDA if requested
    if eda:
        console.print("\n[bold blue]Generating Event-Driven Ansible rulebooks:[/bold blue]")
        from ops_translate.generate.eda_rulebook import generate_eda_artifacts

        vrealize_dir = workspace.root / "input/vrealize"
        if vrealize_dir.exists():
            policy_files = list(vrealize_dir.glob("*policy*.xml")) + list(
                vrealize_dir.glob("*event*.xml")
            )
            if policy_files:
                generate_eda_artifacts(
                    workspace, policy_files, use_job_templates=True, categorize=True
                )
            else:
                console.print(
                    "[yellow]No event policy files found - skipping EDA generation[/yellow]"
                )
        else:
            console.print("[yellow]No vRealize files found - skipping EDA generation[/yellow]")


@app.command()
@handle_errors
def analyze():
    """
    Analyze imported vRealize workflows for external dependencies and translatability.

    Detects NSX-T operations, custom plugins, and REST API calls, then classifies
    them by translatability level (SUPPORTED/PARTIAL/BLOCKED/MANUAL).
    Generates gap reports with migration guidance.

    No LLM required - runs offline using pattern matching.
    """
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Analyzing workflows for external dependencies...[/bold blue]\n")

    from ops_translate.analyze.vrealize import (
        analyze_vrealize_workflow,
        write_analysis_report,
    )
    from ops_translate.intent.classify import classify_components
    from ops_translate.intent.gaps import generate_gap_reports, print_gap_summary

    # Find all vRealize workflows
    vrealize_dir = workspace.root / "input/vrealize"
    if not vrealize_dir.exists():
        console.print("[yellow]No vRealize workflows found to analyze.[/yellow]")
        console.print(
            "[dim]Import vRealize workflows with: "
            "ops-translate import --source vrealize --file <path>[/dim]"
        )
        raise typer.Exit(0)

    xml_files = list(vrealize_dir.glob("*.xml"))
    if not xml_files:
        console.print("[yellow]No XML files found in input/vrealize/[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found {len(xml_files)} workflow(s) to analyze\n")

    all_components = []

    # Analyze each workflow
    for xml_file in xml_files:
        console.print(f"[dim]Analyzing {xml_file.name}...[/dim]")

        # Run analysis
        analysis = analyze_vrealize_workflow(xml_file)

        # Write analysis report
        write_analysis_report(analysis, workspace.root / "intent")

        # Classify components
        components = classify_components(analysis)
        all_components.extend(components)

        # Show quick summary
        if analysis["has_external_dependencies"]:
            console.print(f"  [yellow]⚠ {xml_file.name}: Found external dependencies[/yellow]")
        else:
            console.print(f"  [green]✓ {xml_file.name}: No external dependencies[/green]")

    console.print()

    # Generate combined gap reports
    if all_components:
        generate_gap_reports(all_components, workspace.root / "intent")
        console.print("[green]✓ Analysis reports written to intent/[/green]")
        console.print("  [cyan]• analysis.vrealize.json[/cyan] - Detection details")
        console.print("  [cyan]• analysis.vrealize.md[/cyan] - Human-readable analysis")
        console.print("  [cyan]• gaps.json[/cyan] - Classification data")
        console.print("  [cyan]• gaps.md[/cyan] - Migration guidance")

        # Print summary to console
        print_gap_summary(all_components)
    else:
        console.print(
            "[green]✓ No external dependencies detected - workflows are fully translatable[/green]"
        )


@app.command()
def dry_run():
    """Validate intent and generated artifacts with detailed analysis."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Running enhanced dry-run validation...[/bold blue]")

    from ops_translate.intent.dry_run import print_dry_run_results, run_enhanced_dry_run
    from ops_translate.intent.validate import validate_intent

    # Load config
    config = workspace.load_config()

    # Basic schema validation first
    intent_file = workspace.root / "intent/intent.yaml"
    if intent_file.exists():
        console.print("\n[dim]Validating intent schema...[/dim]")
        is_valid, errors = validate_intent(intent_file)
        if not is_valid:
            console.print("[red]✗ Intent schema validation failed:[/red]")
            for error in errors:
                console.print(f"  {error}")
            raise typer.Exit(1)
        console.print("[green]✓ Intent schema valid[/green]")

    # Enhanced validation
    is_safe, result = run_enhanced_dry_run(workspace, config)

    # Print detailed results
    print_dry_run_results(result)

    # Exit with appropriate code
    if not is_safe:
        raise typer.Exit(1)


@app.command()
def report(
    format: str = typer.Option("html", help="Report format (html)"),
    profile: str | None = typer.Option(None, help="Target profile name"),
    out: Path | None = typer.Option(None, help="Output directory (default: output/report/)"),
):
    """
    Generate static HTML report for translation review.

    Creates a shareable HTML report that consolidates intent, gaps, assumptions,
    and generated artifacts for human review before deployment.

    Example:
        ops-translate report --format html --profile lab
        open output/report/index.html
    """
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    # Only HTML format supported in v1
    if format != "html":
        console.print(f"[red]Error: Unsupported format '{format}'. Only 'html' is supported.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Generating HTML report...[/bold blue]")

    try:
        from ops_translate.report import generate_html_report

        # Generate report
        report_file = generate_html_report(workspace, profile=profile, output_path=out)

        console.print("[green]✓ Report generated successfully[/green]")
        console.print(f"\n[bold]Report location:[/bold] {report_file}")
        console.print("\n[dim]Open the report in your browser:[/dim]")
        console.print(f"  open {report_file}")

    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
