"""
HTML report generation.

Generates static HTML reports summarizing intent, gaps, assumptions, and generated
artifacts for human review before deployment.
"""

import logging
from pathlib import Path
from typing import Any, cast

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

from ops_translate.report.loaders import (
    ReportContextBuilder,
    ReportDataLoader,
    ReportFileLocator,
)
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

    # Generate documentation HTML files
    generate_docs_html(output_path)

    return report_file


def build_report_context(workspace: Workspace, profile: str | None = None) -> dict[str, Any]:
    """
    Build data context for report template.

    Consolidates all workspace artifacts into a structured dict for rendering.
    Now uses decoupled components (FileLocator, DataLoader, ContextBuilder) for
    better testability and maintainability.

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

    # Use new decoupled components for file loading
    locator = ReportFileLocator(workspace)
    loader = ReportDataLoader()

    # Load data files using new components
    gaps_data = None
    if gaps_file := locator.gaps_file():
        gaps_data = loader.load_json(gaps_file)

    recommendations_data = None
    if recs_file := locator.recommendations_file():
        recommendations_data = loader.load_json(recs_file)

    decisions_data = None
    if decisions_file := locator.decisions_file():
        decisions_data = loader.load_yaml(decisions_file)

    questions_data = None
    if questions_file := locator.questions_file():
        questions_data = loader.load_json(questions_file)

    analysis_data = None
    if analysis_file := locator.analysis_file():
        analysis_data = loader.load_json(analysis_file)

    # Load workspace-specific data (these still have custom logic)
    intent_data = _load_intent_data(workspace)
    sources = _load_source_files(workspace, gaps_data)
    artifacts = _detect_generated_artifacts(workspace)

    # Load markdown files
    assumptions_md = None
    if assumptions_file := locator.assumptions_file():
        assumptions_md = _load_markdown_file(assumptions_file)

    conflicts_md = None
    if conflicts_file := locator.conflicts_file():
        conflicts_md = _load_markdown_file(conflicts_file)

    # Generate executive summary and consolidate supported patterns
    executive_summary = _generate_executive_summary(
        gaps_data.get("summary", {}) if gaps_data else {}, gaps_data
    )

    consolidated_supported = []
    if gaps_data:
        consolidated_supported = _consolidate_supported_patterns(gaps_data)

    # Calculate effort metrics for executive dashboard
    effort_metrics = _calculate_effort_metrics(analysis_data, gaps_data)

    # Enrich components with pattern links
    if gaps_data and "components" in gaps_data:
        for component in gaps_data["components"]:
            pattern_link = get_pattern_link(
                component.get("component_type", ""), component.get("name", "")
            )
            component["pattern_link"] = pattern_link

    # Use ContextBuilder to assemble final context
    builder = ReportContextBuilder()
    context = builder.build(
        workspace_name=workspace.root.name,
        workspace_path=str(workspace.root),
        profile=profile,
        profile_config=profile_config,
        gaps_data=gaps_data,
        recommendations_data=recommendations_data,
        decisions_data=decisions_data,
        questions_data=questions_data,
        intent_data=intent_data,
        sources=sources,
        assumptions_md=assumptions_md,
        conflicts_md=conflicts_md,
        artifacts=artifacts,
        executive_summary=executive_summary,
        consolidated_supported=consolidated_supported,
    )

    # Add effort metrics to context
    context["effort_metrics"] = effort_metrics

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
    Generate an outcome-focused executive summary for the report.

    Uses percentages and confidence language to communicate business value
    rather than technical status.

    Args:
        summary: Summary statistics from gap analysis
        gaps_data: Full gaps data with components

    Returns:
        One-sentence executive summary string
    """
    assessment = summary.get("overall_assessment", "UNKNOWN")
    has_blocking = summary.get("has_blocking_issues", False)
    counts = summary.get("counts", {})
    total = summary.get("total_components", 0)

    # Calculate automation percentage
    supported = counts.get("SUPPORTED", 0)
    partial = counts.get("PARTIAL", 0)

    if total > 0:
        automation_pct = int((supported / total) * 100)
    else:
        automation_pct = 0

    # Find blocked components for specific mention
    blocked_components = []
    if gaps_data and has_blocking:
        components = gaps_data.get("components", [])
        blocked_components = [
            comp.get("name", "Unknown") for comp in components if comp.get("level") == "BLOCKED"
        ]

    # Generate outcome-focused summary based on assessment
    if assessment == "FULLY_TRANSLATABLE":
        return (
            f"{automation_pct}% of this automation estate can migrate immediately with "
            "fully automated translation to OpenShift-native equivalents."
        )

    elif has_blocking and blocked_components:
        # Mention specific blockers with confidence language
        if len(blocked_components) == 1:
            blocker = blocked_components[0]
            return (
                f"{automation_pct}% of this automation estate can migrate immediately. "
                f"{blocker} requires design alignment, but proven patterns exist."
            )
        else:
            blocker_count = len(blocked_components)
            return (
                f"{automation_pct}% of this automation estate can migrate immediately. "
                f"{blocker_count} components require design alignment, but proven patterns exist."
            )

    elif partial > 0:
        return (
            f"{automation_pct}% of this automation estate can migrate immediately. "
            f"{partial} component{'s' if partial != 1 else ''} require configuration—"
            "standard work with clear implementation paths."
        )

    elif counts.get("MANUAL", 0) > 0:
        return (
            f"{automation_pct}% automation coverage achieved. "
            "Remaining components require specialist implementation with expert guidance available."
        )

    else:
        return f"{automation_pct}% of this automation estate is ready for immediate migration."


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


def _calculate_effort_metrics(
    analysis_data: dict[str, Any] | None, gaps_data: dict[str, Any] | None
) -> dict[str, Any]:
    """
    Calculate effort metrics for executive dashboard.

    Uses deterministic heuristics to classify workflows by effort level:
    - Ready Now (0-1 points): No decisions required
    - Moderate Effort (2-3 points): Configuration needed
    - Complex (4+ points): Adapter development required

    Effort scoring:
    +1 per approval gate
    +1 per integration detected
    +1 per policy mapping required
    +2 per unresolved integration (BLOCKED stub)
    +2 per security/network mapping
    +3 per missing action body

    Args:
        analysis_data: Workflow classification data from analysis.json
        gaps_data: Gap analysis data from gaps.json

    Returns:
        Dictionary with:
        - estate_summary: overview stats
        - effort_buckets: ready/moderate/complex counts
        - cost_drivers: percentage-based metrics
        - integration_heatmap: matrix of workflow vs integrations
    """
    if not analysis_data:
        return {
            "estate_summary": {
                "total_workflows": 0,
                "total_lines_of_code": 0,
                "external_integrations": 0,
                "approval_gates": 0,
            },
            "effort_buckets": {"ready_now": 0, "moderate": 0, "complex": 0},
            "cost_drivers": [],
            "integration_heatmap": [],
        }

    # Extract workflow data
    workflows = analysis_data.get("workflows", {})
    total_workflows = analysis_data.get("total_workflows", 0)

    # Calculate estate overview
    total_blocked = len([w for w in workflows.values() if w.get("classification") == "blocked"])

    # Estimate LOC (approximate: 20 lines per task average)
    total_tasks = sum(w.get("total_tasks", 0) for w in workflows.values())
    estimated_loc = total_tasks * 20

    # Count external integrations from gaps data
    external_integrations = set()
    approval_gates_count = 0

    if gaps_data:
        components = gaps_data.get("components", [])
        for comp in components:
            comp_type = comp.get("component_type", "")
            if "approval" in comp_type.lower():
                approval_gates_count += 1
            if comp.get("classification") in ["PARTIAL", "BLOCKED"]:
                # Extract integration type
                if "servicenow" in comp_type.lower() or "itsm" in comp_type.lower():
                    external_integrations.add("ITSM")
                if "nsx" in comp_type.lower() or "firewall" in comp_type.lower():
                    external_integrations.add("NSX")
                if "dns" in comp_type.lower():
                    external_integrations.add("DNS")
                if "storage" in comp_type.lower():
                    external_integrations.add("Storage")
                if "ad" in comp_type.lower() or "ldap" in comp_type.lower():
                    external_integrations.add("AD")

    estate_summary = {
        "total_workflows": total_workflows,
        "total_lines_of_code": estimated_loc,
        "external_integrations": len(external_integrations),
        "approval_gates": approval_gates_count,
    }

    # Calculate effort buckets using scoring heuristic
    ready_now = 0
    moderate = 0
    complex_count = 0

    for workflow_name, workflow_data in workflows.items():
        score = 0

        # Classification-based scoring
        classification = workflow_data.get("classification", "blocked")
        if classification == "blocked":
            score += 4  # Blocked workflows are complex by default
        elif classification == "partial":
            score += 2  # Partial workflows need moderate effort

        # Task-based scoring
        adapter_tasks = workflow_data.get("adapter_tasks", 0)
        blocked_tasks = workflow_data.get("blocked_tasks", 0)

        score += min(adapter_tasks, 2)  # Cap adapter task score at +2
        score += blocked_tasks * 2  # Each blocked stub adds +2

        # Categorize by score
        if score <= 1:
            ready_now += 1
        elif score <= 3:
            moderate += 1
        else:
            complex_count += 1

    effort_buckets = {"ready_now": ready_now, "moderate": moderate, "complex": complex_count}

    # Calculate cost drivers (percentage-based)
    cost_drivers = []
    if total_workflows > 0:
        # Approval gates
        if approval_gates_count > 0:
            pct = int((approval_gates_count / total_workflows) * 100)
            cost_drivers.append(
                {
                    "label": f"{pct}% have approval gates",
                    "percentage": pct,
                    "count": approval_gates_count,
                }
            )

        # BLOCKED workflows (security/network decisions)
        if total_blocked > 0:
            pct = int((total_blocked / total_workflows) * 100)
            cost_drivers.append(
                {
                    "label": f"{pct}% require configuration decisions",
                    "percentage": pct,
                    "count": total_blocked,
                }
            )

        # Adapter tasks (integration complexity)
        workflows_with_adapters = len(
            [w for w in workflows.values() if w.get("adapter_tasks", 0) > 0]
        )
        if workflows_with_adapters > 0:
            pct = int((workflows_with_adapters / total_workflows) * 100)
            cost_drivers.append(
                {
                    "label": f"{pct}% require external integrations",
                    "percentage": pct,
                    "count": workflows_with_adapters,
                }
            )

    # Sort cost drivers by percentage descending
    cost_drivers.sort(key=lambda x: cast(int, x["percentage"]), reverse=True)

    # Generate integration heatmap
    integration_heatmap = _generate_integration_heatmap(workflows, gaps_data)

    return {
        "estate_summary": estate_summary,
        "effort_buckets": effort_buckets,
        "cost_drivers": cost_drivers,
        "integration_heatmap": integration_heatmap,
    }


def _generate_integration_heatmap(
    workflows: dict[str, Any], gaps_data: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """
    Generate integration heatmap showing which workflows use which integrations.

    Creates a matrix showing the presence of different integration types across workflows.
    Integrations are detected from both:
    1. gaps.json components (detected during analysis)
    2. analysis.json blocker_details (blocked code generation)

    Args:
        workflows: Workflow data from analysis.json
        gaps_data: Gap analysis data from gaps.json

    Returns:
        List of workflow rows with integration presence indicators
    """
    if not workflows:
        return []

    # Define integration categories to track
    integration_categories = ["Approval", "ITSM", "NSX", "DNS", "Storage", "AD"]

    # Build workflow integration map
    workflow_integrations: dict[str, dict[str, bool]] = {}

    for workflow_name in workflows.keys():
        workflow_integrations[workflow_name] = {cat: False for cat in integration_categories}

    # Source 1: Detect integrations from gaps.json components
    if gaps_data:
        components = gaps_data.get("components", [])
        for component in components:
            location = component.get("location", "")
            component_type = component.get("component_type", "").lower()
            component_name = component.get("name", "").lower()

            # Find matching workflow
            for workflow_name in workflow_integrations.keys():
                # Normalize names for comparison (handle hyphens vs underscores)
                normalized_location = location.lower().replace("-", "_").replace(" ", "_")
                normalized_workflow = workflow_name.lower().replace("-", "_").replace(" ", "_")

                # Match by location field or workflow name substring
                if (
                    normalized_location in normalized_workflow
                    or normalized_workflow in normalized_location
                ):
                    integrations = workflow_integrations[workflow_name]

                    # Map component types to integration categories
                    if "approval" in component_type or "approval" in component_name:
                        integrations["Approval"] = True
                    if "servicenow" in component_type or "itsm" in component_type:
                        integrations["ITSM"] = True
                    if (
                        "nsx" in component_type
                        or "firewall" in component_type
                        or "load_balancer" in component_type
                    ):
                        integrations["NSX"] = True
                    if "dns" in component_type:
                        integrations["DNS"] = True
                    if "storage" in component_type or "datastore" in component_type:
                        integrations["Storage"] = True
                    if (
                        "ad" in component_type
                        or "ldap" in component_type
                        or "active_directory" in component_type
                    ):
                        integrations["AD"] = True

    # Source 2: Detect integrations from analysis.json blocker details
    for workflow_name, workflow_data in workflows.items():
        integrations = workflow_integrations[workflow_name]

        blocker_details = workflow_data.get("blocker_details", [])
        for blocker in blocker_details:
            task_name = blocker.get("task", "").lower()
            message = blocker.get("message", "").lower()

            # Map to integration categories
            if "approval" in task_name or "approval" in message:
                integrations["Approval"] = True
            if "servicenow" in task_name or "itsm" in message:
                integrations["ITSM"] = True
            if "nsx" in task_name or "firewall" in message:
                integrations["NSX"] = True
            if "dns" in task_name or "dns" in message:
                integrations["DNS"] = True
            if "storage" in task_name or "datastore" in message:
                integrations["Storage"] = True
            if "ad" in task_name or "ldap" in message or "activedirectory" in message:
                integrations["AD"] = True

    # Build heatmap rows - only include workflows with at least one integration
    heatmap_rows = []
    for workflow_name, integrations in workflow_integrations.items():
        if any(integrations.values()):
            heatmap_rows.append(
                {
                    "workflow": workflow_name,
                    "integrations": integrations,
                }
            )

    return heatmap_rows


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


def generate_docs_html(output_path: Path) -> None:
    """
    Generate HTML documentation files from markdown sources.

    Converts docs/*.md files to styled HTML and includes them in the report
    output for standalone viewing.

    Args:
        output_path: Output directory for report
    """
    import shutil

    # Create docs directory in output
    docs_dir = output_path / "docs"
    docs_dir.mkdir(exist_ok=True)

    # Find documentation markdown files
    source_docs_dir = PROJECT_ROOT / "docs"
    if not source_docs_dir.exists():
        logger.warning(f"Documentation directory not found: {source_docs_dir}")
        return

    # Convert each markdown file to HTML
    for md_file in source_docs_dir.glob("*.md"):
        html_content = convert_markdown_to_html(md_file)
        output_file = docs_dir / f"{md_file.stem}.html"
        output_file.write_text(html_content)
        logger.info(f"Generated documentation: {output_file.name}")

    # Copy any images or assets from docs
    for asset_file in source_docs_dir.glob("*.png"):
        shutil.copy2(asset_file, docs_dir / asset_file.name)
    for asset_file in source_docs_dir.glob("*.jpg"):
        shutil.copy2(asset_file, docs_dir / asset_file.name)


def convert_markdown_to_html(md_file: Path) -> str:
    """
    Convert markdown file to styled HTML.

    Args:
        md_file: Path to markdown file

    Returns:
        Complete HTML document with styling
    """
    # Read markdown content
    md_content = md_file.read_text()

    # Convert to HTML with extensions
    md_converter = markdown.Markdown(
        extensions=[
            "fenced_code",  # Code blocks
            "tables",  # Tables
            "toc",  # Table of contents
            "codehilite",  # Syntax highlighting
        ]
    )
    body_html = md_converter.convert(md_content)

    # Wrap in styled HTML template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{md_file.stem.replace('_', ' ').replace('-', ' ').title()}</title>
    <link rel="stylesheet" href="../assets/style.css">
    <style>
        .doc-container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: var(--spacing-xl);
            background: white;
        }}
        .doc-header {{
            margin-bottom: var(--spacing-xl);
            padding-bottom: var(--spacing-md);
            border-bottom: 2px solid #0c4a6e;
        }}
        .doc-nav {{
            margin-bottom: var(--spacing-lg);
            padding: var(--spacing-md);
            background: #f0f9ff;
            border-radius: 8px;
        }}
        .doc-nav a {{
            color: #0c4a6e;
            text-decoration: none;
            margin-right: var(--spacing-md);
        }}
        .doc-nav a:hover {{
            text-decoration: underline;
        }}
        .doc-content {{
            line-height: 1.8;
        }}
        .doc-content h2 {{
            margin-top: var(--spacing-xl);
            padding-top: var(--spacing-lg);
            border-top: 1px solid #e2e8f0;
        }}
        .doc-content h3 {{
            margin-top: var(--spacing-lg);
            color: #0c4a6e;
        }}
        .doc-content h4 {{
            margin-top: var(--spacing-md);
            color: #0369a1;
            font-weight: 600;
        }}
        .doc-content code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .doc-content pre {{
            background: #1e293b;
            color: #e2e8f0;
            padding: var(--spacing-md);
            border-radius: 8px;
            overflow-x: auto;
            margin: var(--spacing-md) 0;
        }}
        .doc-content pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
        }}
        .doc-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: var(--spacing-md) 0;
        }}
        .doc-content th, .doc-content td {{
            border: 1px solid #cbd5e1;
            padding: var(--spacing-sm);
            text-align: left;
        }}
        .doc-content th {{
            background: #f1f5f9;
            font-weight: 600;
        }}
        .doc-content ul, .doc-content ol {{
            margin: var(--spacing-md) 0;
            padding-left: var(--spacing-xl);
        }}
        .doc-content li {{
            margin: var(--spacing-xs) 0;
        }}
        .doc-content blockquote {{
            border-left: 4px solid #0c4a6e;
            padding-left: var(--spacing-md);
            margin: var(--spacing-md) 0;
            color: #64748b;
            font-style: italic;
        }}
        .back-to-report {{
            display: inline-block;
            margin-top: var(--spacing-xl);
            padding: var(--spacing-sm) var(--spacing-md);
            background: #0c4a6e;
            color: white;
            text-decoration: none;
            border-radius: 6px;
        }}
        .back-to-report:hover {{
            background: #075985;
        }}
    </style>
</head>
<body>
    <div class="doc-container">
        <div class="doc-header">
            <h1>{md_file.stem.replace('_', ' ').replace('-', ' ').title()}</h1>
        </div>
        <div class="doc-nav">
            <a href="../index.html">← Back to Report</a>
            <a href="#table-of-contents">Table of Contents</a>
        </div>
        <div class="doc-content">
            {body_html}
        </div>
        <div style="margin-top: var(--spacing-xl); text-align: center;">
            <a href="../index.html" class="back-to-report">← Back to Migration Report</a>
        </div>
    </div>
</body>
</html>
"""
    return html_template


def get_pattern_link(component_type: str, component_name: str) -> dict[str, str] | None:
    """
    Get pattern guide link for a component type.

    Args:
        component_type: Component type from gaps.json
        component_name: Component name

    Returns:
        Dict with 'anchor' and 'description' keys, or None if no pattern applies
    """
    # Map component types to pattern guide anchors
    pattern_mappings = {
        # NSX Components
        "nsx_security_groups": {
            "anchor": "pattern-5-nsx-security-components",
            "description": "NSX Security & Networking Alternatives",
        },
        "nsx_firewall_rules": {
            "anchor": "pattern-5-nsx-security-components",
            "description": "NSX Firewall Migration Patterns",
        },
        "nsx_distributed_firewall": {
            "anchor": "pattern-5-nsx-security-components",
            "description": "NSX Firewall Migration Patterns",
        },
        "nsx_load_balancers": {
            "anchor": "pattern-5-nsx-security-components",
            "description": "NSX Load Balancer Alternatives",
        },
        "nsx_segments": {
            "anchor": "pattern-5-nsx-security-components",
            "description": "NSX Networking Migration",
        },
        # Workflow patterns
        "workflow_delay": {
            "anchor": "pattern-1-long-running-stateful-workflows",
            "description": "Long-Running Workflow Patterns",
        },
        "long_running_workflow": {
            "anchor": "pattern-1-long-running-stateful-workflows",
            "description": "Long-Running Workflow Patterns",
        },
        # Form patterns
        "user_interaction": {
            "anchor": "pattern-2-complex-interactive-forms",
            "description": "Interactive Form Alternatives",
        },
        "approval": {
            "anchor": "pattern-2-complex-interactive-forms",
            "description": "Approval Workflow Patterns",
        },
        # Dynamic workflows
        "dynamic_workflow": {
            "anchor": "pattern-3-dynamic-workflow-generation",
            "description": "Dynamic Workflow Patterns",
        },
        # State management
        "workflow_state": {
            "anchor": "pattern-4-state-management",
            "description": "State Management Patterns",
        },
    }

    # Try exact match first
    if component_type in pattern_mappings:
        return pattern_mappings[component_type]

    # Try partial matches
    component_type_lower = component_type.lower()
    if "nsx" in component_type_lower:
        return {
            "anchor": "pattern-5-nsx-security-components",
            "description": "NSX Migration Patterns",
        }
    elif "approval" in component_type_lower or "user_interaction" in component_type_lower:
        return {
            "anchor": "pattern-2-complex-interactive-forms",
            "description": "Approval & Form Patterns",
        }
    elif "workflow" in component_type_lower and "state" in component_type_lower:
        return {
            "anchor": "pattern-4-state-management",
            "description": "State Management Patterns",
        }

    return None
