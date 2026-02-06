"""
HTML report generation.

Generates static HTML reports summarizing intent, gaps, assumptions, and generated
artifacts for human review before deployment.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, Template

from ops_translate.workspace import Workspace

# Get project root to find templates
PROJECT_ROOT = Path(__file__).parent.parent.parent


def generate_html_report(
    workspace: Workspace,
    profile: str | None = None,
    output_path: Path | None = None,
) -> Path:
    """
    Generate static HTML report for translation review.

    Creates a self-contained HTML report that consolidates intent, gaps,
    assumptions, and generated artifacts into a shareable review document.

    Args:
        workspace: Workspace instance
        profile: Optional profile name (defaults to workspace default)
        output_path: Optional output directory (defaults to output/report/)

    Returns:
        Path to generated index.html file

    Outputs:
        - output/report/index.html
        - output/report/assets/style.css
        - output/report/assets/app.js (optional)

    Example:
        >>> ws = Workspace(Path("my-workspace"))
        >>> report_path = generate_html_report(ws, profile="lab")
        >>> print(f"Report: {report_path}")
        Report: /path/to/my-workspace/output/report/index.html
    """
    # Determine output directory
    if output_path is None:
        output_path = workspace.root / "output/report"

    output_path.mkdir(parents=True, exist_ok=True)

    # Build report context from workspace artifacts
    context = build_report_context(workspace, profile)

    # Render HTML template
    html_content = render_report_template(context)

    # Write report HTML
    report_file = output_path / "index.html"
    report_file.write_text(html_content)

    # Copy static assets
    copy_static_assets(output_path)

    return report_file


def build_report_context(workspace: Workspace, profile: str | None = None) -> dict[str, Any]:
    """
    Build data context for report template.

    Consolidates all workspace artifacts into a structured dict for rendering.

    Args:
        workspace: Workspace instance
        profile: Optional profile name

    Returns:
        Dictionary with report data:
        - workspace: metadata (name, timestamp)
        - profile: profile config
        - sources: list of source files
        - intent: parsed intent data
        - gaps: gap analysis data
        - assumptions_md: assumptions content
        - conflicts_md: conflicts content
        - artifacts: generated artifacts info
        - summary: overall translation status

    Example:
        >>> context = build_report_context(workspace, "lab")
        >>> print(context["workspace"]["name"])
        my-workspace
    """
    config = workspace.load_config()

    # Determine profile
    if profile is None:
        profile = config.get("profiles", {}).get("default", "default")

    profile_config = config.get("profiles", {}).get(profile, {})

    # Build context
    context: dict[str, Any] = {
        "workspace": {
            "name": workspace.root.name,
            "path": str(workspace.root),
            "timestamp": datetime.now().isoformat(),
        },
        "profile": {
            "name": profile,
            "config": profile_config,
        },
        "sources": _load_source_files(workspace),
        "intent": _load_intent_data(workspace),
        "gaps": _load_gaps_data(workspace),
        "assumptions_md": _load_markdown_file(workspace.root / "intent/assumptions.md"),
        "conflicts_md": _load_markdown_file(workspace.root / "intent/conflicts.md"),
        "artifacts": _detect_generated_artifacts(workspace),
        "summary": {},  # Will be populated from gaps/intent
    }

    # Build summary from gaps if available
    if context["gaps"]:
        context["summary"] = context["gaps"].get("summary", {})
    else:
        # Fallback summary if no gaps
        context["summary"] = {
            "total_components": 0,
            "overall_assessment": "UNKNOWN",
            "counts": {"SUPPORTED": 0, "PARTIAL": 0, "BLOCKED": 0, "MANUAL": 0},
            "has_blocking_issues": False,
            "requires_manual_work": False,
        }

    return context


def _load_source_files(workspace: Workspace) -> list[dict[str, Any]]:
    """
    Load list of source files from workspace.

    Returns:
        List of dicts with source file metadata
    """
    sources = []

    # PowerCLI sources
    powercli_dir = workspace.root / "input/powercli"
    if powercli_dir.exists():
        for ps_file in powercli_dir.glob("*.ps1"):
            sources.append(
                {
                    "name": ps_file.name,
                    "type": "PowerCLI",
                    "path": str(ps_file.relative_to(workspace.root)),
                    "size": ps_file.stat().st_size,
                }
            )

    # vRealize sources
    vrealize_dir = workspace.root / "input/vrealize"
    if vrealize_dir.exists():
        for xml_file in vrealize_dir.glob("*.xml"):
            sources.append(
                {
                    "name": xml_file.name,
                    "type": "vRealize",
                    "path": str(xml_file.relative_to(workspace.root)),
                    "size": xml_file.stat().st_size,
                }
            )

    return sources


def _load_intent_data(workspace: Workspace) -> dict[str, Any] | None:
    """
    Load merged intent.yaml or fallback to individual intent files.

    Returns:
        Intent data dict or None if no intent found
    """
    # Try merged intent first
    merged_intent = workspace.root / "intent/intent.yaml"
    if merged_intent.exists():
        try:
            return yaml.safe_load(merged_intent.read_text())
        except yaml.YAMLError:
            pass

    # Fallback: try to load individual intent files
    intent_dir = workspace.root / "intent"
    if intent_dir.exists():
        for intent_file in intent_dir.glob("*.intent.yaml"):
            try:
                return yaml.safe_load(intent_file.read_text())
            except yaml.YAMLError:
                continue

    return None


def _load_gaps_data(workspace: Workspace) -> dict[str, Any] | None:
    """
    Load gaps.json data if available.

    Returns:
        Gaps data dict or None if not found
    """
    gaps_file = workspace.root / "intent/gaps.json"
    if not gaps_file.exists():
        return None

    try:
        return json.loads(gaps_file.read_text())
    except json.JSONDecodeError:
        return None


def _load_markdown_file(file_path: Path) -> str | None:
    """
    Load markdown file content.

    Returns:
        File content or None if not found
    """
    if not file_path.exists():
        return None

    return file_path.read_text()


def _detect_generated_artifacts(workspace: Workspace) -> dict[str, Any]:
    """
    Detect generated artifacts in output directory.

    Returns:
        Dict with artifact paths and metadata
    """
    artifacts: dict[str, Any] = {
        "kubevirt": [],
        "ansible": [],
        "other": [],
    }

    output_dir = workspace.root / "output"
    if not output_dir.exists():
        return artifacts

    # KubeVirt artifacts
    kubevirt_dir = output_dir / "kubevirt"
    if kubevirt_dir.exists():
        for yaml_file in kubevirt_dir.glob("*.yaml"):
            artifacts["kubevirt"].append(
                {
                    "name": yaml_file.name,
                    "path": str(yaml_file.relative_to(workspace.root)),
                    "size": yaml_file.stat().st_size,
                }
            )

    # Ansible artifacts
    ansible_dir = output_dir / "ansible"
    if ansible_dir.exists():
        # Playbook
        playbook = ansible_dir / "site.yml"
        if playbook.exists():
            artifacts["ansible"].append(
                {
                    "name": "site.yml",
                    "path": str(playbook.relative_to(workspace.root)),
                    "size": playbook.stat().st_size,
                    "type": "playbook",
                }
            )

        # Roles
        roles_dir = ansible_dir / "roles"
        if roles_dir.exists():
            for role_dir in roles_dir.iterdir():
                if role_dir.is_dir():
                    artifacts["ansible"].append(
                        {
                            "name": f"role: {role_dir.name}",
                            "path": str(role_dir.relative_to(workspace.root)),
                            "type": "role",
                        }
                    )

    return artifacts


def render_report_template(context: dict[str, Any]) -> str:
    """
    Render HTML template with report context.

    Args:
        context: Report data dict

    Returns:
        Rendered HTML string
    """
    # Load Jinja2 template
    template_dir = PROJECT_ROOT / "templates/report"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

    template = env.get_template("index.html.j2")

    # Render with context
    return template.render(**context)


def copy_static_assets(output_path: Path) -> None:
    """
    Copy static assets (CSS, JS) to output directory.

    Args:
        output_path: Output directory for report
    """
    import shutil

    # Create assets directory
    assets_dir = output_path / "assets"
    assets_dir.mkdir(exist_ok=True)

    # Copy CSS
    template_dir = PROJECT_ROOT / "templates/report"
    css_file = template_dir / "style.css"
    if css_file.exists():
        shutil.copy2(css_file, assets_dir / "style.css")

    # Copy JS (optional)
    js_file = template_dir / "app.js"
    if js_file.exists():
        shutil.copy2(js_file, assets_dir / "app.js")
