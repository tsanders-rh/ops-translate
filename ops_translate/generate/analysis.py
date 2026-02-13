"""
Analysis and progress tracking for generated Ansible artifacts.

Scans generated roles to classify workflows and track migration progress.

Key Principles:
--------------
1. Deterministic: Same inputs → same outputs, always
2. No temporal state: Progress derived from current analysis, not stored history
3. Conservative classification: When in doubt, classify as BLOCKED
4. Profile-driven: Classifications upgrade when profile provides required config

Progress Model:
--------------
Progress is NOT:  compare(previous-run.json, current-run.json) as source of truth
Progress IS:      diff(current state, previous state) for visibility only

The analysis.json file contains the current state based on:
- Generated task content (BLOCKED stubs vs real tasks)
- Adapter usage percentage (30% threshold for PARTIAL)
- Module types used (native vs adapter includes)

Comparison between runs shows progress but does not affect classification logic.
"""

import json
from pathlib import Path
from typing import Any

import yaml


def analyze_generated_roles(project_dir: Path) -> dict[str, Any]:
    """
    Analyze generated Ansible roles to classify workflows.

    Args:
        project_dir: Path to generated Ansible project directory

    Returns:
        Dictionary containing classification analysis
    """
    roles_dir = project_dir / "roles"

    if not roles_dir.exists():
        return {
            "total_workflows": 0,
            "workflows": {},
            "summary": {
                "blocked": 0,
                "partial": 0,
                "automatable": 0,
            },
            "blockers": [],
        }

    analysis: dict[str, Any] = {
        "total_workflows": 0,
        "workflows": {},
        "summary": {
            "blocked": 0,
            "partial": 0,
            "automatable": 0,
        },
        "blockers": [],
    }

    # Scan each role
    for role_dir in roles_dir.iterdir():
        if not role_dir.is_dir():
            continue

        role_name = role_dir.name
        tasks_file = role_dir / "tasks" / "main.yml"

        if not tasks_file.exists():
            continue

        # Analyze tasks
        workflow_analysis = _analyze_workflow_tasks(tasks_file)
        analysis["workflows"][role_name] = workflow_analysis
        analysis["total_workflows"] += 1

        # Update summary counts
        classification = workflow_analysis["classification"]
        analysis["summary"][classification] += 1

        # Collect blockers
        if classification == "blocked":
            analysis["blockers"].extend(workflow_analysis["blockers"])

    return analysis


def _analyze_workflow_tasks(tasks_file: Path) -> dict[str, Any]:
    """
    Analyze a single workflow's tasks file and classify it.

    Classification Decision Rules (Conservative):
    -------------------------------------------

    1. BLOCKED - Workflow has unresolved blockers that prevent automation
       - ANY task with name containing "BLOCKED" AND using ansible.builtin.fail
       - Indicates missing profile configuration or unsupported integration
       - Will NOT upgrade until ALL blockers are resolved

    2. PARTIAL - Workflow can run but requires external adapters
       - No BLOCKED tasks present
       - 30% or more tasks are adapter includes (adapters/ directory)
       - Indicates workflow delegates to user-maintained integration code
       - Can upgrade from BLOCKED when profile provides adapter configuration

    3. AUTOMATABLE - Workflow uses only native Ansible/Kubernetes modules
       - No BLOCKED tasks
       - Less than 30% adapter tasks (mostly native modules)
       - Can run without external dependencies
       - Highest confidence level for automation

    Upgrade Path: BLOCKED → PARTIAL → AUTOMATABLE
    (Conservative: only upgrades when ALL conditions are met)

    Args:
        tasks_file: Path to tasks/main.yml

    Returns:
        Dictionary with workflow classification and blocker details
    """
    try:
        with tasks_file.open() as f:
            tasks = yaml.safe_load(f)
    except Exception:
        return {
            "classification": "blocked",
            "blocked_tasks": 0,
            "total_tasks": 0,
            "blockers": ["Failed to parse tasks file"],
        }

    if not tasks or not isinstance(tasks, list):
        return {
            "classification": "automatable",
            "blocked_tasks": 0,
            "total_tasks": 0,
            "blockers": [],
        }

    total_tasks = len(tasks)
    blocked_tasks = []
    adapter_tasks = []
    regular_tasks = []

    for task in tasks:
        if not isinstance(task, dict):
            continue

        task_name = task.get("name", "")

        # Check if this is a BLOCKED stub
        if "BLOCKED" in task_name and "ansible.builtin.fail" in task:
            blocked_tasks.append(
                {
                    "task": task_name,
                    "message": task["ansible.builtin.fail"].get("msg", ""),
                }
            )
        # Check if this is an adapter include
        elif "ansible.builtin.include_tasks" in task:
            adapter_file = task["ansible.builtin.include_tasks"].get("file", "")
            if "adapters/" in adapter_file:
                adapter_tasks.append(task_name)
            else:
                regular_tasks.append(task_name)
        else:
            regular_tasks.append(task_name)

    # Classify workflow
    if blocked_tasks:
        classification = "blocked"
    elif adapter_tasks and len(adapter_tasks) >= total_tasks * 0.3:
        # If 30%+ of tasks are adapters, consider it partial
        classification = "partial"
    else:
        classification = "automatable"

    return {
        "classification": classification,
        "total_tasks": total_tasks,
        "blocked_tasks": len(blocked_tasks),
        "adapter_tasks": len(adapter_tasks),
        "regular_tasks": len(regular_tasks),
        "blockers": [b["task"] for b in blocked_tasks],
        "blocker_details": blocked_tasks,
    }


def generate_analysis_json(project_dir: Path, output_path: Path) -> None:
    """
    Generate analysis.json file with classification results.

    Args:
        project_dir: Path to generated Ansible project
        output_path: Path where analysis.json should be written
    """
    analysis = analyze_generated_roles(project_dir)

    # Add metadata
    from datetime import datetime, timezone

    analysis["generated_at"] = datetime.now(timezone.utc).isoformat()
    analysis["version"] = "1.0"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(analysis, f, indent=2)


def generate_effort_json(
    analysis_data: dict[str, Any], gaps_data: dict[str, Any] | None, output_path: Path
) -> None:
    """
    Generate effort.json file with migration effort metrics.

    This provides machine-readable data for teams who prefer JSON over HTML reports.
    Complements analysis.json with executive-focused metrics.

    Args:
        analysis_data: Workflow classification data from analysis.json
        gaps_data: Gap analysis data from gaps.json (optional)
        output_path: Path where effort.json should be written
    """
    # Import here to avoid circular dependency
    from ops_translate.report.html import _calculate_effort_metrics

    effort_metrics = _calculate_effort_metrics(analysis_data, gaps_data)

    # Add metadata
    from datetime import datetime, timezone

    effort_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        **effort_metrics,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(effort_output, f, indent=2)


def compare_analysis(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """
    Compare two analysis results to show progress.

    Args:
        previous: Previous analysis.json data
        current: Current analysis.json data

    Returns:
        Dictionary showing progress delta
    """
    prev_summary = previous.get("summary", {})
    curr_summary = current.get("summary", {})

    return {
        "blocked": {
            "before": prev_summary.get("blocked", 0),
            "after": curr_summary.get("blocked", 0),
            "delta": curr_summary.get("blocked", 0) - prev_summary.get("blocked", 0),
        },
        "partial": {
            "before": prev_summary.get("partial", 0),
            "after": curr_summary.get("partial", 0),
            "delta": curr_summary.get("partial", 0) - prev_summary.get("partial", 0),
        },
        "automatable": {
            "before": prev_summary.get("automatable", 0),
            "after": curr_summary.get("automatable", 0),
            "delta": curr_summary.get("automatable", 0) - prev_summary.get("automatable", 0),
        },
        "total_workflows": current.get("total_workflows", 0),
        "blockers_resolved": len(previous.get("blockers", [])) - len(current.get("blockers", [])),
    }
