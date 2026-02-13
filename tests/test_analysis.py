"""
Tests for analysis and progress tracking functionality.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from ops_translate.generate.analysis import (
    analyze_generated_roles,
    compare_analysis,
    generate_analysis_json,
)


class TestAnalyzeGeneratedRoles:
    """Test role analysis functionality."""

    def test_analyze_empty_directory(self, tmp_path):
        """Test analyzing a directory with no roles."""
        result = analyze_generated_roles(tmp_path)

        assert result["total_workflows"] == 0
        assert result["summary"]["blocked"] == 0
        assert result["summary"]["partial"] == 0
        assert result["summary"]["automatable"] == 0

    def test_analyze_workflow_with_blocked_tasks(self, tmp_path):
        """Test workflow with BLOCKED stubs is classified as blocked."""
        # Create role structure
        role_dir = tmp_path / "roles" / "test_workflow"
        tasks_dir = role_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create tasks with BLOCKED stub
        tasks = [
            {
                "name": "BLOCKED - ServiceNow integration",
                "ansible.builtin.fail": {"msg": "Missing profile.itsm configuration"},
                "tags": ["blocked", "integration"],
            },
            {
                "name": "Create VM",
                "kubevirt.core.kubevirt_vm": {
                    "state": "present",
                    "name": "{{ vm_name }}",
                },
                "tags": ["vm"],
            },
        ]

        with (tasks_dir / "main.yml").open("w") as f:
            yaml.dump(tasks, f)

        # Analyze
        result = analyze_generated_roles(tmp_path)

        assert result["total_workflows"] == 1
        assert result["summary"]["blocked"] == 1
        assert result["summary"]["partial"] == 0
        assert result["summary"]["automatable"] == 0
        assert len(result["blockers"]) == 1
        assert "ServiceNow" in result["blockers"][0]

    def test_analyze_workflow_with_adapter_tasks(self, tmp_path):
        """Test workflow with adapter includes is classified as partial."""
        # Create role structure
        role_dir = tmp_path / "roles" / "test_workflow"
        tasks_dir = role_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create tasks with adapter includes (>30% threshold)
        tasks = [
            {
                "name": "Create ServiceNow incident",
                "ansible.builtin.include_tasks": {
                    "file": "{{ playbook_dir }}/adapters/servicenow/create_incident.yml"
                },
                "tags": ["integration"],
            },
            {
                "name": "Reserve IP address",
                "ansible.builtin.include_tasks": {
                    "file": "{{ playbook_dir }}/adapters/ipam/reserve_ip.yml"
                },
                "tags": ["integration"],
            },
            {
                "name": "Create VM",
                "kubevirt.core.kubevirt_vm": {
                    "state": "present",
                },
                "tags": ["vm"],
            },
        ]

        with (tasks_dir / "main.yml").open("w") as f:
            yaml.dump(tasks, f)

        # Analyze
        result = analyze_generated_roles(tmp_path)

        assert result["total_workflows"] == 1
        # 2 out of 3 tasks are adapters (66%), should be partial
        assert result["summary"]["partial"] == 1
        assert result["workflows"]["test_workflow"]["adapter_tasks"] == 2

    def test_analyze_workflow_automatable(self, tmp_path):
        """Test workflow with no blockers or adapters is automatable."""
        # Create role structure
        role_dir = tmp_path / "roles" / "test_workflow"
        tasks_dir = role_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # Create tasks with all regular Ansible modules
        tasks = [
            {
                "name": "Create VM",
                "kubevirt.core.kubevirt_vm": {
                    "state": "present",
                },
            },
            {
                "name": "Start VM",
                "kubevirt.core.kubevirt_vm": {
                    "state": "running",
                },
            },
        ]

        with (tasks_dir / "main.yml").open("w") as f:
            yaml.dump(tasks, f)

        # Analyze
        result = analyze_generated_roles(tmp_path)

        assert result["total_workflows"] == 1
        assert result["summary"]["automatable"] == 1
        assert result["summary"]["blocked"] == 0
        assert len(result["blockers"]) == 0


class TestCompareAnalysis:
    """Test analysis comparison functionality."""

    def test_compare_shows_progress(self):
        """Test comparison shows improvements."""
        previous = {
            "summary": {
                "blocked": 5,
                "partial": 2,
                "automatable": 1,
            },
            "blockers": ["blocker1", "blocker2", "blocker3"],
        }

        current = {
            "summary": {
                "blocked": 2,
                "partial": 4,
                "automatable": 2,
            },
            "blockers": ["blocker1"],
        }

        result = compare_analysis(previous, current)

        assert result["blocked"]["before"] == 5
        assert result["blocked"]["after"] == 2
        assert result["blocked"]["delta"] == -3

        assert result["partial"]["before"] == 2
        assert result["partial"]["after"] == 4
        assert result["partial"]["delta"] == 2

        assert result["automatable"]["before"] == 1
        assert result["automatable"]["after"] == 2
        assert result["automatable"]["delta"] == 1

        assert result["blockers_resolved"] == 2  # 3 - 1


class TestGenerateAnalysisJson:
    """Test analysis.json generation."""

    def test_generate_analysis_json(self, tmp_path):
        """Test generating analysis.json file."""
        # Create role structure
        role_dir = tmp_path / "roles" / "test_workflow"
        tasks_dir = role_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        tasks = [
            {
                "name": "Create VM",
                "kubevirt.core.kubevirt_vm": {"state": "present"},
            }
        ]

        with (tasks_dir / "main.yml").open("w") as f:
            yaml.dump(tasks, f)

        # Generate analysis.json
        output_path = tmp_path / "output" / "analysis.json"
        generate_analysis_json(tmp_path, output_path)

        assert output_path.exists()

        with output_path.open() as f:
            data = json.load(f)

        assert data["total_workflows"] == 1
        assert data["version"] == "1.0"
        assert "generated_at" in data
        assert "workflows" in data
        assert "test_workflow" in data["workflows"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
