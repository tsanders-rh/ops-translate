"""
CLI entry point for ops-translate.
"""

import json
import os
import shutil
from datetime import datetime
from functools import wraps
from pathlib import Path

import typer
from rich.console import Console

from ops_translate.exceptions import (
    FileNotFoundError as OpsFileNotFoundError,
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
def init(workspace_dir: str = typer.Argument(..., help="Workspace directory to initialize")):
    """Initialize a new ops-translate workspace."""
    console.print(f"[bold blue]Initializing workspace:[/bold blue] {workspace_dir}")

    workspace = Workspace(Path(workspace_dir))
    workspace.initialize()

    console.print(f"[green]✓ Created directory structure in {workspace_dir}[/green]")
    console.print("[green]✓ Wrote configuration to ops-translate.yaml[/green]")
    console.print("\n[dim]Next steps:[/dim]")
    console.print(f"  cd {workspace_dir}")
    console.print("  ops-translate import --source powercli --file <path>")


@app.command(name="import")
@handle_errors
def import_cmd(
    source: str = typer.Option(..., "--source", help="Source type (powercli|vrealize)"),
    file: str = typer.Option(..., "--file", help="Path to file to import"),
):
    """Import a PowerCLI script or vRealize workflow."""
    # Validate source type
    if source not in ["powercli", "vrealize"]:
        raise InvalidSourceTypeError(source)

    # Check file exists
    source_path = Path(file)
    if not source_path.exists():
        raise OpsFileNotFoundError(str(source_path))

    # Ensure we're in a workspace
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        raise WorkspaceNotFoundError()

    # Copy file to input directory
    input_dir = workspace.root / "input" / source
    dest_path = input_dir / source_path.name

    console.print(f"[bold blue]Importing {source} file:[/bold blue] {source_path.name}")
    shutil.copy2(source_path, dest_path)

    # Compute hash and write metadata
    file_hash = sha256_file(dest_path)
    timestamp = datetime.now().isoformat()
    run_dir = workspace.root / "runs" / timestamp.replace(":", "-").split(".")[0]
    ensure_dir(run_dir)

    metadata = {
        "timestamp": timestamp,
        "source_type": source,
        "original_file": str(source_path.absolute()),
        "imported_file": str(dest_path.relative_to(workspace.root)),
        "sha256": file_hash,
    }

    write_text(run_dir / "import.json", json.dumps(metadata, indent=2))

    console.print(f"[green]✓ Imported to {dest_path.relative_to(workspace.root)}[/green]")
    console.print(f"[green]✓ SHA256: {file_hash}[/green]")
    console.print(
        f"[green]✓ Metadata saved to {run_dir.relative_to(workspace.root)}/import.json[/green]"
    )


@app.command()
def summarize():
    """Summarize imported files (no AI required)."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Analyzing imported files...[/bold blue]")

    from ops_translate.summarize import powercli, vrealize

    summary_lines = []
    summary_lines.append("# Import Summary\n")

    # Summarize PowerCLI files
    powercli_dir = workspace.root / "input/powercli"
    if powercli_dir.exists():
        ps_files = list(powercli_dir.glob("*.ps1"))
        if ps_files:
            summary_lines.append("## PowerCLI Scripts\n")
            for ps_file in ps_files:
                console.print(f"  Analyzing: {ps_file.name}")
                summary = powercli.summarize(ps_file)
                summary_lines.append(f"### {ps_file.name}\n")
                summary_lines.append(summary + "\n")

    # Summarize vRealize files
    vrealize_dir = workspace.root / "input/vrealize"
    if vrealize_dir.exists():
        xml_files = list(vrealize_dir.glob("*.xml"))
        if xml_files:
            summary_lines.append("## vRealize Workflows\n")
            for xml_file in xml_files:
                console.print(f"  Analyzing: {xml_file.name}")
                summary = vrealize.summarize(xml_file)
                summary_lines.append(f"### {xml_file.name}\n")
                summary_lines.append(summary + "\n")

    # Write summary
    summary_file = workspace.root / "intent/summary.md"
    write_text(summary_file, "".join(summary_lines))

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
    os.system(f"{editor} {intent_file}")


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
):
    """Generate Ansible and KubeVirt artifacts."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    config = workspace.load_config()
    if profile not in config.get("profiles", {}):
        console.print(f"[red]Error: Profile '{profile}' not found in config[/red]")
        raise typer.Exit(1)

    mode = "template-based" if no_ai else "AI-assisted"
    console.print(f"[bold blue]Generating artifacts ({mode}):[/bold blue] profile={profile}")

    from ops_translate.generate import generate_all

    # Generate all artifacts
    generate_all(workspace, profile, use_ai=not no_ai)

    console.print("[green]✓ KubeVirt manifest: output/kubevirt/vm.yaml[/green]")
    console.print("[green]✓ Ansible playbook: output/ansible/site.yml[/green]")
    console.print("[green]✓ Ansible role: output/ansible/roles/provision_vm/[/green]")
    console.print("[green]✓ README: output/README.md[/green]")


@app.command()
def dry_run():
    """Validate intent and generated artifacts."""
    workspace = Workspace(Path.cwd())
    if not workspace.config_file.exists():
        console.print("[red]Error: Not in a workspace.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Running validation checks...[/bold blue]")

    from ops_translate.intent.validate import validate_artifacts, validate_intent

    # Validate intent schema
    intent_file = workspace.root / "intent/intent.yaml"
    if intent_file.exists():
        console.print("  Validating intent schema...")
        is_valid, errors = validate_intent(intent_file)
        if is_valid:
            console.print("    [green]✓ Intent schema valid[/green]")
        else:
            console.print("    [red]✗ Intent schema invalid:[/red]")
            for error in errors:
                console.print(f"      - {error}")

    # Validate generated YAML
    console.print("  Validating generated artifacts...")
    valid, messages = validate_artifacts(workspace)

    for msg in messages:
        console.print(f"    {msg}")

    if valid:
        console.print("\n[green]✓ All validations passed[/green]")
    else:
        console.print("\n[red]✗ Validation failed[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
