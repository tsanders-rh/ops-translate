"""
Generate gap analysis reports for workflow translatability.

This module creates human-readable and machine-readable reports documenting
components that cannot be fully automatically translated, along with migration
guidance and recommendations.
"""

import json
from pathlib import Path
from typing import Any

from ops_translate.intent.classify import (
    ClassifiedComponent,
    MigrationPath,
    TranslatabilityLevel,
    generate_classification_summary,
)


def generate_gap_reports(
    components: list[ClassifiedComponent],
    output_dir: Path,
    workflow_name: str = "workflow",
) -> None:
    """
    Generate gap analysis reports in both Markdown and JSON formats.

    Creates two files in the output directory:
    - gaps.md: Human-readable report with migration guidance
    - gaps.json: Machine-readable report for tooling integration

    Args:
        components: List of classified components from classification
        output_dir: Directory to write report files (typically workspace/intent/)
        workflow_name: Name of the workflow being analyzed (for report title)

    Side Effects:
        Writes gaps.md and gaps.json to output_dir

    Example:
        >>> from ops_translate.intent.classify import classify_components
        >>> components = classify_components(analysis)
        >>> generate_gap_reports(components, Path("intent"), "MyWorkflow")
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate summary statistics
    summary = generate_classification_summary(components)

    # Write Markdown report
    md_file = output_dir / "gaps.md"
    _write_markdown_report(md_file, components, summary, workflow_name)

    # Write JSON report
    json_file = output_dir / "gaps.json"
    _write_json_report(json_file, components, summary, workflow_name)


def _write_markdown_report(
    output_file: Path,
    components: list[ClassifiedComponent],
    summary: dict[str, Any],
    workflow_name: str,
) -> None:
    """Write human-readable Markdown gap report."""
    with open(output_file, "w") as f:
        f.write(f"# Gap Analysis Report: {workflow_name}\n\n")
        f.write("## Executive Summary\n\n")

        # Overall assessment
        assessment = summary["overall_assessment"]
        assessment_emoji = {
            "FULLY_TRANSLATABLE": "✅",
            "MOSTLY_AUTOMATIC": "✅",
            "MOSTLY_MANUAL": "⚠️",
            "REQUIRES_MANUAL_WORK": "⚠️",
        }.get(assessment, "❌")

        f.write(
            f"**Overall Assessment**: {assessment_emoji} {assessment.replace('_', ' ').title()}\n\n"
        )

        # Component counts
        f.write(f"**Total Components Analyzed**: {summary['total_components']}\n\n")
        f.write("| Classification | Count |\n")
        f.write("|----------------|-------|\n")
        for level in ["SUPPORTED", "PARTIAL", "BLOCKED", "MANUAL"]:
            count = summary["counts"][level]
            emoji = TranslatabilityLevel[level].emoji
            f.write(f"| {emoji} {level} | {count} |\n")

        f.write("\n")

        # High-level recommendations
        if summary["has_blocking_issues"]:
            f.write("### ⚠️ Action Required\n\n")
            f.write(
                "This workflow contains components that **cannot be automatically translated**. "
            )
            f.write("Manual implementation or architectural changes will be required.\n\n")
        elif summary["requires_manual_work"]:
            f.write("### ℹ️ Manual Configuration Needed\n\n")
            f.write("This workflow can be mostly automated, but some components require ")
            f.write("manual configuration or review.\n\n")
        else:
            f.write("### ✅ Ready for Automatic Translation\n\n")
            f.write("All components in this workflow can be automatically translated to ")
            f.write("OpenShift-native equivalents.\n\n")

        # Migration paths
        f.write("## Migration Path Recommendations\n\n")
        for path_value in ["PATH_A", "PATH_B", "PATH_C"]:
            count = summary["migration_paths"].get(path_value, 0)
            if count > 0:
                path = MigrationPath[path_value]
                f.write(f"### {path.value}: {path.description}\n\n")
                f.write(f"**{count} component(s)** recommended for this path.\n\n")

                # Details for this path
                path_components = [c for c in components if c.migration_path == path]
                if path_components:
                    f.write("**Components:**\n")
                    for comp in path_components:
                        f.write(f"- {comp.name} ({comp.component_type})\n")
                    f.write("\n")

        # Detailed component analysis
        f.write("---\n\n")
        f.write("## Detailed Component Analysis\n\n")

        # Group by severity level
        trans_level: TranslatabilityLevel
        for trans_level in [
            TranslatabilityLevel.MANUAL,
            TranslatabilityLevel.BLOCKED,
            TranslatabilityLevel.PARTIAL,
            TranslatabilityLevel.SUPPORTED,
        ]:
            level_components = [c for c in components if c.level == trans_level]
            if not level_components:
                continue

            f.write(f"### {trans_level.emoji} {trans_level.value} Components\n\n")

            for comp in level_components:
                f.write(f"#### {comp.name}\n\n")
                f.write(f"**Type**: `{comp.component_type}`\n\n")
                f.write(f"**Reason**: {comp.reason}\n\n")

                if comp.openshift_equivalent:
                    f.write(f"**OpenShift Equivalent**: {comp.openshift_equivalent}\n\n")

                if comp.migration_path:
                    f.write(
                        f"**Migration Path**: {comp.migration_path.value} - "
                        f"{comp.migration_path.description}\n\n"
                    )

                if comp.location:
                    f.write(f"**Location**: `{comp.location}`\n\n")

                if comp.evidence:
                    f.write("**Evidence**:\n```\n")
                    f.write(comp.evidence)
                    f.write("\n```\n\n")

                if comp.recommendations:
                    f.write("**Recommendations**:\n")
                    for rec in comp.recommendations:
                        f.write(f"- {rec}\n")
                    f.write("\n")

                f.write("---\n\n")

        # Footer with next steps
        f.write("## Next Steps\n\n")
        if summary["has_blocking_issues"]:
            f.write("1. **Review BLOCKED and MANUAL components** with infrastructure specialists\n")
            f.write("2. **Decide on migration path** (A/B/C) for each component\n")
            f.write("3. **Create implementation plan** for manual components\n")
            f.write("4. **Run `ops-translate generate`** to create scaffolding with TODOs\n")
            f.write("5. **Implement manual components** following generated TODO tasks\n")
        elif summary["requires_manual_work"]:
            f.write("1. **Run `ops-translate generate`** to create Ansible playbooks\n")
            f.write("2. **Review generated TODO tasks** for PARTIAL components\n")
            f.write("3. **Complete manual configuration** as documented in TODOs\n")
            f.write("4. **Test in dev environment** before production deployment\n")
        else:
            f.write("1. **Run `ops-translate generate`** to create OpenShift artifacts\n")
            f.write("2. **Review generated manifests** for correctness\n")
            f.write("3. **Deploy to test environment** and validate\n")
            f.write("4. **Promote to production** following your deployment process\n")

        f.write("\n---\n\n")
        f.write("*Generated by ops-translate gap analysis*\n")


def _write_json_report(
    output_file: Path,
    components: list[ClassifiedComponent],
    summary: dict[str, Any],
    workflow_name: str,
) -> None:
    """Write machine-readable JSON gap report."""
    report = {
        "workflow_name": workflow_name,
        "summary": summary,
        "components": [comp.to_dict() for comp in components],
        "migration_guidance": {
            "overall_assessment": summary["overall_assessment"],
            "has_blocking_issues": summary["has_blocking_issues"],
            "requires_manual_work": summary["requires_manual_work"],
            "recommended_paths": [
                path
                for path, count in summary["migration_paths"].items()
                if count > 0 and path != "NONE"
            ],
        },
    }

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)


def print_gap_summary(components: list[ClassifiedComponent]) -> None:
    """
    Print a concise gap summary to console.

    Useful for CLI output to give users immediate feedback without reading
    full reports.

    Args:
        components: List of classified components

    Example:
        >>> print_gap_summary(components)
        Gap Analysis Summary:
        ✅ SUPPORTED: 2
        ⚠️ PARTIAL: 3
        🚫 BLOCKED: 1
        👷 MANUAL: 0
        Overall: MOSTLY_AUTOMATIC
    """
    from rich.console import Console
    from rich.table import Table

    summary = generate_classification_summary(components)
    console = Console()

    console.print("\n[bold]Gap Analysis Summary[/bold]\n")

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Classification", style="dim")
    table.add_column("Count", justify="right")

    for level in ["SUPPORTED", "PARTIAL", "BLOCKED", "MANUAL"]:
        count = summary["counts"][level]
        emoji = TranslatabilityLevel[level].emoji
        color = {
            "SUPPORTED": "green",
            "PARTIAL": "yellow",
            "BLOCKED": "red",
            "MANUAL": "magenta",
        }[level]
        table.add_row(f"{emoji} {level}", f"[{color}]{count}[/{color}]")

    console.print(table)

    # Overall assessment
    assessment = summary["overall_assessment"]
    assessment_color = {
        "FULLY_TRANSLATABLE": "green",
        "MOSTLY_AUTOMATIC": "green",
        "MOSTLY_MANUAL": "yellow",
        "REQUIRES_MANUAL_WORK": "yellow",
    }.get(assessment, "red")

    assessment_text = assessment.replace("_", " ").title()
    console.print(
        f"\n[bold]Overall Assessment:[/bold] "
        f"[{assessment_color}]{assessment_text}[/{assessment_color}]\n"
    )

    if summary["has_blocking_issues"]:
        console.print(
            "[yellow]⚠️ This workflow has blocking issues that require manual work.[/yellow]\n"
        )
        console.print("Review [cyan]intent/gaps.md[/cyan] for detailed recommendations.\n")
    elif summary["requires_manual_work"]:
        console.print("[yellow]ℹ️ Some components require manual configuration.[/yellow]\n")
        console.print("Review [cyan]intent/gaps.md[/cyan] for guidance.\n")
    else:
        console.print("[green]✅ This workflow can be fully automatically translated.[/green]\n")
