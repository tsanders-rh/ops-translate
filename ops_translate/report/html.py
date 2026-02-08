"""
HTML report generation.

Generates static HTML reports summarizing intent, gaps, assumptions, and generated
artifacts for human review before deployment.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

from ops_translate.workspace import Workspace

logger = logging.getLogger(__name__)

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

    # Load gaps data first (needed for source file status)
    gaps_data = _load_gaps_data(workspace)
    recommendations_data = _load_recommendations_data(workspace)
    decisions_data = _load_decisions_data(workspace)
    questions_data = _load_questions_data(workspace)

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
        "sources": _load_source_files(workspace, gaps_data),
        "intent": _load_intent_data(workspace),
        "gaps": gaps_data,
        "recommendations": recommendations_data,
        "decisions": decisions_data,
        "questions": questions_data,
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

    # Generate executive summary
    context["executive_summary"] = _generate_executive_summary(context["summary"], context["gaps"])

    # Consolidate SUPPORTED patterns to reduce repetition
    if context["gaps"]:
        context["consolidated_supported"] = _consolidate_supported_patterns(context["gaps"])
    else:
        context["consolidated_supported"] = []

    # Build questions lookup by component location
    if questions_data and "questions" in questions_data:
        questions_by_location: dict[str, list[dict[str, Any]]] = {}
        for question in questions_data["questions"]:
            location = question.get("location")  # Questions use "location" not "component_location"
            if location:
                if location not in questions_by_location:
                    questions_by_location[location] = []
                questions_by_location[location].append(question)
        context["questions_by_location"] = questions_by_location
    else:
        context["questions_by_location"] = {}

    # Build recommendations lookup by component name
    if recommendations_data and "recommendations" in recommendations_data:
        recommendations_by_component: dict[str, dict[str, Any]] = {}
        for rec in recommendations_data["recommendations"]:
            component_name = rec.get("component_name")
            if component_name:
                recommendations_by_component[component_name] = rec
        context["recommendations_by_component"] = recommendations_by_component
    else:
        context["recommendations_by_component"] = {}

    return context


def _consolidate_supported_patterns(gaps_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Consolidate SUPPORTED components by type to reduce repetition.

    Groups SUPPORTED components by component_type and counts occurrences.
    This allows the report to show "Standard VM provisioning patterns are
    supported across all workflows" instead of listing each instance.

    Args:
        gaps_data: Gaps data with components

    Returns:
        List of consolidated pattern dicts with:
        - component_type: The type of pattern (e.g., "vm_provisioning")
        - count: Number of occurrences
        - files: List of source files containing this pattern
        - example_name: Name of first component as example

    Example:
        >>> gaps = {"components": [
        ...     {"name": "Provision VM", "component_type": "vm_provisioning",
        ...      "level": "SUPPORTED", "location": "provision"},
        ...     {"name": "VM Memory", "component_type": "vm_provisioning",
        ...      "level": "SUPPORTED", "location": "configure"}
        ... ]}
        >>> result = _consolidate_supported_patterns(gaps)
        >>> result[0]["count"]
        2
    """
    from collections import defaultdict

    components = gaps_data.get("components", [])

    # Group SUPPORTED components by type
    supported_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for component in components:
        if component.get("level") == "SUPPORTED":
            component_type = component.get("component_type", "unknown")
            supported_by_type[component_type].append(component)

    # Build consolidated list
    consolidated = []
    for component_type, components_list in supported_by_type.items():
        # Collect unique source files
        files = list(set(comp.get("location", "unknown") for comp in components_list))

        # Format component type for display (replace underscores, capitalize)
        display_name = component_type.replace("_", " ").title()

        consolidated.append(
            {
                "component_type": component_type,
                "display_name": display_name,
                "count": len(components_list),
                "files": sorted(files),
                "example_name": components_list[0].get("name", "Unknown"),
            }
        )

    # Sort by count (most common first)
    consolidated.sort(key=lambda x: x["count"], reverse=True)

    return consolidated


def _generate_executive_summary(summary: dict[str, Any], gaps_data: dict[str, Any] | None) -> str:
    """
    Generate a one-line executive summary for the report.

    Args:
        summary: Summary statistics from gap analysis
        gaps_data: Full gaps data with components

    Returns:
        One-sentence executive summary string
    """
    assessment = summary.get("overall_assessment", "UNKNOWN")
    has_blocking = summary.get("has_blocking_issues", False)
    counts = summary.get("counts", {})

    # Find blocked components for specific mention
    blocked_components = []
    if gaps_data and has_blocking:
        components = gaps_data.get("components", [])
        blocked_components = [
            comp.get("name", "Unknown") for comp in components if comp.get("level") == "BLOCKED"
        ]

    # Generate summary based on assessment
    if assessment == "FULLY_TRANSLATABLE":
        return (
            "This workflow can be fully automatically migrated to " "OpenShift-native equivalents."
        )

    elif has_blocking and blocked_components:
        # Mention specific blockers
        if len(blocked_components) == 1:
            blocker = blocked_components[0]
            return (
                f"This workflow can be migrated with partial automation; "
                f"{blocker} requires custom design."
            )
        else:
            blocker_count = len(blocked_components)
            return (
                f"This workflow can be migrated with partial automation; "
                f"{blocker_count} components require custom design."
            )

    elif counts.get("PARTIAL", 0) > 0:
        partial_count = counts.get("PARTIAL", 0)
        if partial_count == 1:
            return (
                "This workflow can be migrated with partial automation; "
                "manual configuration required for 1 component."
            )
        else:
            return (
                f"This workflow can be migrated with partial automation; "
                f"manual configuration required for {partial_count} components."
            )

    elif counts.get("MANUAL", 0) > 0:
        return "This workflow requires custom specialist implementation for migration."

    else:
        return "This workflow is ready for automated migration review."


def _load_source_files(
    workspace: Workspace, gaps_data: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """
    Load list of source files from workspace.

    Args:
        workspace: Workspace instance
        gaps_data: Optional gaps data to determine status for each file

    Returns:
        List of dicts with source file metadata including status
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

    # Enrich with status from gaps data
    if gaps_data:
        _enrich_source_status(sources, gaps_data)

    return sources


def _enrich_source_status(sources: list[dict[str, Any]], gaps_data: dict[str, Any]) -> None:
    """
    Enrich source files with status based on gap analysis.

    Determines status for each source file by analyzing components:
    - BLOCKED components → ⛔ Blocked
    - PARTIAL/MANUAL components → ⚠ Needs Review
    - All SUPPORTED → ✅ Supported
    - No components → ⚠ Needs Review

    Args:
        sources: List of source file dicts (modified in-place)
        gaps_data: Gaps data with components
    """
    components = gaps_data.get("components", [])

    for source in sources:
        filename = source["name"]
        # Get filename without extension for matching
        filename_base = filename.replace(".workflow.xml", "").replace(".ps1", "")

        # Find components from this file
        # Components have location like "provision-vm-with-nsx-firewall"
        # while source files have names like "provision-vm-with-nsx-firewall.workflow.xml"
        file_components = [
            comp
            for comp in components
            if comp.get("location", "") == filename_base
            or comp.get("location", "").startswith(filename_base + ".")
        ]

        if not file_components:
            # No gaps found - file is clean or fully supported
            source["status"] = "NO_ISSUES"
            source["status_icon"] = "✓"
            source["status_text"] = "No Issues Found"
        else:
            # Check component levels
            levels = [comp.get("level") for comp in file_components]

            if "BLOCKED" in levels:
                source["status"] = "BLOCKED"
                source["status_icon"] = "⛔"
                source["status_text"] = "Blocked"
            elif "PARTIAL" in levels or "MANUAL" in levels:
                source["status"] = "NEEDS_REVIEW"
                source["status_icon"] = "⚠"
                source["status_text"] = "Needs Review"
            elif all(level == "SUPPORTED" for level in levels):
                source["status"] = "SUPPORTED"
                source["status_icon"] = "✅"
                source["status_text"] = "Supported"
            else:
                source["status"] = "NEEDS_REVIEW"
                source["status_icon"] = "⚠"
                source["status_text"] = "Needs Review"

        # Store component count for the action link
        source["component_count"] = len(file_components)


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
            return cast(dict[str, Any], yaml.safe_load(merged_intent.read_text()))
        except yaml.YAMLError:
            pass

    # Fallback: try to load individual intent files
    intent_dir = workspace.root / "intent"
    if intent_dir.exists():
        for intent_file in intent_dir.glob("*.intent.yaml"):
            try:
                return cast(dict[str, Any], yaml.safe_load(intent_file.read_text()))
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
        return cast(dict[str, Any], json.loads(gaps_file.read_text()))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse {gaps_file}: {e}")
        return None


def _load_recommendations_data(workspace: Workspace) -> dict[str, Any] | None:
    """
    Load recommendations.json data if available.

    Returns:
        Recommendations data dict or None if not found
    """
    recommendations_file = workspace.root / "intent/recommendations.json"
    if not recommendations_file.exists():
        return None

    try:
        return cast(dict[str, Any], json.loads(recommendations_file.read_text()))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse {recommendations_file}: {e}")
        return None


def _load_decisions_data(workspace: Workspace) -> dict[str, Any] | None:
    """
    Load decisions.yaml data if available.

    Returns:
        Decisions data dict or None if not found
    """
    decisions_file = workspace.root / "intent/decisions.yaml"
    if not decisions_file.exists():
        return None

    try:
        return cast(dict[str, Any], yaml.safe_load(decisions_file.read_text()))
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse {decisions_file}: {e}")
        return None


def _load_questions_data(workspace: Workspace) -> dict[str, Any] | None:
    """
    Load questions.json data if available.

    Returns:
        Questions data dict or None if not found
    """
    questions_file = workspace.root / "intent/questions.json"
    if not questions_file.exists():
        return None

    try:
        return cast(dict[str, Any], json.loads(questions_file.read_text()))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse {questions_file}: {e}")
        return None
    except OSError as e:
        logger.warning(f"Failed to read {questions_file}: {e}")
        return None


def _load_markdown_file(file_path: Path) -> str | None:
    """
    Load markdown file and convert to HTML.

    Returns None if file doesn't exist or only contains meaningless content.

    Returns:
        HTML content or None if not found or empty/meaningless
    """
    if not file_path.exists():
        return None

    markdown_text = file_path.read_text().strip()

    # Check if content is meaningless (only default text)
    if _is_meaningless_assumptions(markdown_text):
        return None

    return markdown.markdown(markdown_text)


def _is_meaningless_assumptions(content: str) -> bool:
    """
    Check if assumptions content is meaningless/default only.

    Returns True if content only contains:
    - Header text
    - Default "Intent extracted via LLM" messages
    - File name headers with no real content
    - Empty sections
    """
    # Normalize content
    normalized = content.lower().strip()

    # Get all lines
    lines = [line.strip() for line in normalized.split("\n") if line.strip()]

    # Filter to only assumption lines (bullet points starting with -)
    assumption_lines = [line for line in lines if line.startswith("-")]

    # If no assumption lines at all, it's meaningless
    if not assumption_lines:
        return True

    # Check if all assumptions are just the default message
    meaningful_assumptions = [
        line for line in assumption_lines if "intent extracted via llm" not in line.lower()
    ]

    # If no meaningful assumptions remain, it's meaningless
    return len(meaningful_assumptions) == 0


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
