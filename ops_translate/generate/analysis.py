"""
Analysis and progress tracking for generated Ansible artifacts.

Scans generated roles to classify workflows and track migration progress.
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
            "classification": {},
            "blockers": [],
            "progress": {
                "blocked": 0,
                "partial": 0,
                "automatable": 0,
            },
        }

    analysis = {
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
    Analyze a single workflow's tasks file.

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
