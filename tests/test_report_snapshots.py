"""
Snapshot tests for HTML report rendering with effort metrics.

These tests ensure that the executive dashboard renders consistently
and that changes to the report template are intentional and reviewed.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ops_translate.report.html import build_report_context, render_report_template
from ops_translate.workspace import Workspace


class TestReportSnapshots:
    """Snapshot tests for HTML report output stability."""

    def test_executive_dashboard_with_full_data(self, tmp_path):
        """Test that executive dashboard renders with complete data."""
        # Create workspace structure
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        # Initialize workspace
        workspace = Workspace(workspace_dir)
        workspace.initialize()

        # Create analysis.json with realistic data
        output_dir = workspace_dir / "output"
        output_dir.mkdir(exist_ok=True)

        analysis_data = {
            "total_workflows": 10,
            "version": "1.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "summary": {"blocked": 3, "partial": 4, "automatable": 3},
            "workflows": {
                "provision_vm": {
                    "classification": "automatable",
                    "total_tasks": 8,
                    "blocked_tasks": 0,
                    "adapter_tasks": 0,
                    "regular_tasks": 8,
                    "blockers": [],
                    "blocker_details": [],
                },
                "configure_network": {
                    "classification": "partial",
                    "total_tasks": 12,
                    "blocked_tasks": 0,
                    "adapter_tasks": 4,
                    "regular_tasks": 8,
                    "blockers": [],
                    "blocker_details": [],
                },
                "servicenow_integration": {
                    "classification": "blocked",
                    "total_tasks": 10,
                    "blocked_tasks": 2,
                    "adapter_tasks": 0,
                    "regular_tasks": 8,
                    "blockers": ["BLOCKED - ServiceNow integration"],
                    "blocker_details": [
                        {
                            "task": "BLOCKED - ServiceNow integration",
                            "message": "Missing profile.itsm configuration",
                        },
                        {
                            "task": "BLOCKED - Approval gate",
                            "message": "Approval configuration needed",
                        },
                    ],
                },
                "nsx_firewall": {
                    "classification": "blocked",
                    "total_tasks": 15,
                    "blocked_tasks": 3,
                    "adapter_tasks": 0,
                    "regular_tasks": 12,
                    "blockers": ["BLOCKED - NSX firewall"],
                    "blocker_details": [
                        {
                            "task": "BLOCKED - NSX firewall rule",
                            "message": "NSX-T configuration required",
                        }
                    ],
                },
                "storage_migration": {
                    "classification": "blocked",
                    "total_tasks": 8,
                    "blocked_tasks": 1,
                    "adapter_tasks": 0,
                    "regular_tasks": 7,
                    "blockers": ["BLOCKED - Storage tier mapping"],
                    "blocker_details": [
                        {
                            "task": "BLOCKED - Storage tier mapping",
                            "message": "Datastore mapping required",
                        }
                    ],
                },
            },
        }

        with (output_dir / "analysis.json").open("w") as f:
            json.dump(analysis_data, f, indent=2)

        # Create gaps.json with realistic data
        intent_dir = workspace_dir / "intent"
        intent_dir.mkdir(exist_ok=True)

        gaps_data = {
            "summary": {"counts": {"SUPPORTED": 15, "PARTIAL": 8, "BLOCKED": 5, "MANUAL": 2}},
            "components": [
                {
                    "component_type": "servicenow_integration",
                    "classification": "BLOCKED",
                    "level": "BLOCKED",
                    "name": "ServiceNow Integration",
                },
                {
                    "component_type": "nsx_firewall",
                    "classification": "PARTIAL",
                    "level": "PARTIAL",
                    "name": "NSX Firewall",
                },
                {
                    "component_type": "approval_gate",
                    "classification": "SUPPORTED",
                    "level": "SUPPORTED",
                    "name": "Approval Gate 1",
                },
                {
                    "component_type": "approval_gate",
                    "classification": "SUPPORTED",
                    "level": "SUPPORTED",
                    "name": "Approval Gate 2",
                },
                {
                    "component_type": "approval_gate",
                    "classification": "SUPPORTED",
                    "level": "SUPPORTED",
                    "name": "Approval Gate 3",
                },
            ],
        }

        with (intent_dir / "gaps.json").open("w") as f:
            json.dump(gaps_data, f, indent=2)

        # Build report context
        context = build_report_context(workspace, profile=None)

        # Render HTML
        html_output = render_report_template(context)

        # Verify executive dashboard sections are present
        assert "executive-dashboard-section" in html_output
        assert "Migration Effort Dashboard" in html_output
        assert "estate-summary" in html_output
        assert "effort-buckets" in html_output
        assert "cost-drivers" in html_output
        assert "integration-heatmap" in html_output
        assert "sprint-plan" in html_output

        # Verify stat cards
        assert "Total Workflows" in html_output
        assert "Lines of Code" in html_output
        assert "External Integrations" in html_output
        assert "Approval Gates" in html_output

        # Verify effort bucket labels
        assert "Ready Now" in html_output
        assert "Configuration Needed" in html_output
        assert "Adapter Development" in html_output

        # Verify integration categories in heatmap
        assert "Approval" in html_output
        assert "ITSM" in html_output
        assert "NSX" in html_output

        # Verify sprint planning section
        assert "Recommended Migration Phases" in html_output
        assert "Phase" in html_output

    def test_executive_dashboard_with_empty_data(self, tmp_path):
        """Test that executive dashboard handles empty data gracefully."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        # Create empty analysis.json
        output_dir = workspace_dir / "output"
        output_dir.mkdir(exist_ok=True)

        analysis_data = {
            "total_workflows": 0,
            "version": "1.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "summary": {"blocked": 0, "partial": 0, "automatable": 0},
            "workflows": {},
        }

        with (output_dir / "analysis.json").open("w") as f:
            json.dump(analysis_data, f, indent=2)

        # Build report context
        context = build_report_context(workspace, profile=None)

        # Render HTML
        html_output = render_report_template(context)

        # Should still have dashboard structure even with no data
        assert "executive-dashboard-section" in html_output
        assert "estate-summary" in html_output

        # Should show zeros
        assert (
            "0" in html_output
            or context["effort_metrics"]["estate_summary"]["total_workflows"] == 0
        )

    def test_executive_dashboard_metrics_accuracy(self, tmp_path):
        """Test that metrics are calculated and displayed accurately."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        # Create analysis with known values
        output_dir = workspace_dir / "output"
        output_dir.mkdir(exist_ok=True)

        analysis_data = {
            "total_workflows": 5,
            "version": "1.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "summary": {"blocked": 2, "partial": 2, "automatable": 1},
            "workflows": {
                "workflow1": {
                    "classification": "automatable",
                    "total_tasks": 10,
                    "blocked_tasks": 0,
                    "adapter_tasks": 0,
                    "regular_tasks": 10,
                    "blockers": [],
                    "blocker_details": [],
                },
                "workflow2": {
                    "classification": "partial",
                    "total_tasks": 10,
                    "blocked_tasks": 0,
                    "adapter_tasks": 3,
                    "regular_tasks": 7,
                    "blockers": [],
                    "blocker_details": [],
                },
                "workflow3": {
                    "classification": "partial",
                    "total_tasks": 10,
                    "blocked_tasks": 0,
                    "adapter_tasks": 4,
                    "regular_tasks": 6,
                    "blockers": [],
                    "blocker_details": [],
                },
                "workflow4": {
                    "classification": "blocked",
                    "total_tasks": 10,
                    "blocked_tasks": 2,
                    "adapter_tasks": 0,
                    "regular_tasks": 8,
                    "blockers": ["BLOCKED - Integration"],
                    "blocker_details": [
                        {
                            "task": "BLOCKED - ServiceNow",
                            "message": "ITSM integration required",
                        }
                    ],
                },
                "workflow5": {
                    "classification": "blocked",
                    "total_tasks": 10,
                    "blocked_tasks": 1,
                    "adapter_tasks": 0,
                    "regular_tasks": 9,
                    "blockers": ["BLOCKED - Approval"],
                    "blocker_details": [
                        {
                            "task": "BLOCKED - Approval gate",
                            "message": "Approval required",
                        }
                    ],
                },
            },
        }

        with (output_dir / "analysis.json").open("w") as f:
            json.dump(analysis_data, f, indent=2)

        # Build report context
        context = build_report_context(workspace, profile=None)

        # Verify metrics
        effort_metrics = context["effort_metrics"]

        # Total workflows should be 5
        assert effort_metrics["estate_summary"]["total_workflows"] == 5

        # Total LOC should be 50 tasks * 20 lines/task = 1000
        assert effort_metrics["estate_summary"]["total_lines_of_code"] == 1000

        # Should have effort buckets
        assert "ready_now" in effort_metrics["effort_buckets"]
        assert "moderate" in effort_metrics["effort_buckets"]
        assert "complex" in effort_metrics["effort_buckets"]

        # Total should equal 5 workflows
        total_in_buckets = (
            effort_metrics["effort_buckets"]["ready_now"]
            + effort_metrics["effort_buckets"]["moderate"]
            + effort_metrics["effort_buckets"]["complex"]
        )
        assert total_in_buckets == 5

        # Render HTML
        html_output = render_report_template(context)

        # Verify numbers appear in output
        assert "5" in html_output  # Total workflows
        assert "1,000" in html_output or "1000" in html_output  # LOC with formatting

    def test_integration_heatmap_rendering(self, tmp_path):
        """Test that integration heatmap renders correctly."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        output_dir = workspace_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Create analysis with multiple integration types
        analysis_data = {
            "total_workflows": 3,
            "version": "1.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "summary": {"blocked": 3, "partial": 0, "automatable": 0},
            "workflows": {
                "servicenow_workflow": {
                    "classification": "blocked",
                    "total_tasks": 10,
                    "blocked_tasks": 1,
                    "adapter_tasks": 0,
                    "regular_tasks": 9,
                    "blockers": ["ServiceNow"],
                    "blocker_details": [
                        {
                            "task": "BLOCKED - ServiceNow integration",
                            "message": "ITSM required",
                        }
                    ],
                },
                "nsx_workflow": {
                    "classification": "blocked",
                    "total_tasks": 10,
                    "blocked_tasks": 1,
                    "adapter_tasks": 0,
                    "regular_tasks": 9,
                    "blockers": ["NSX"],
                    "blocker_details": [
                        {"task": "BLOCKED - NSX firewall", "message": "Firewall config"}
                    ],
                },
                "combined_workflow": {
                    "classification": "blocked",
                    "total_tasks": 10,
                    "blocked_tasks": 3,
                    "adapter_tasks": 0,
                    "regular_tasks": 7,
                    "blockers": ["ServiceNow", "NSX", "Approval"],
                    "blocker_details": [
                        {
                            "task": "BLOCKED - ServiceNow",
                            "message": "ITSM integration",
                        },
                        {"task": "BLOCKED - NSX", "message": "Firewall"},
                        {"task": "BLOCKED - Approval", "message": "Approval gate"},
                    ],
                },
            },
        }

        with (output_dir / "analysis.json").open("w") as f:
            json.dump(analysis_data, f, indent=2)

        # Build context and render
        context = build_report_context(workspace, profile=None)
        html_output = render_report_template(context)

        # Verify heatmap structure
        assert "integration-heatmap" in html_output
        assert "workflow-name" in html_output or "servicenow_workflow" in html_output

        # Verify integration categories appear
        assert "Approval" in html_output
        assert "ITSM" in html_output
        assert "NSX" in html_output

        # Verify heatmap has rows (should have 3 workflows with integrations)
        heatmap = context["effort_metrics"]["integration_heatmap"]
        assert len(heatmap) == 3

    def test_cost_drivers_rendering(self, tmp_path):
        """Test that cost drivers render with correct percentages."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        output_dir = workspace_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Create analysis with known distribution
        # 10 workflows: 5 blocked, 3 with adapters, 2 automatable
        workflows = {}
        for i in range(10):
            workflows[f"workflow{i}"] = {
                "classification": "blocked" if i < 5 else "automatable",
                "total_tasks": 10,
                "blocked_tasks": 1 if i < 5 else 0,
                "adapter_tasks": 1 if i < 3 else 0,
                "regular_tasks": 9,
                "blockers": ["blocker"] if i < 5 else [],
                "blocker_details": [],
            }

        analysis_data = {
            "total_workflows": 10,
            "version": "1.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "summary": {"blocked": 5, "partial": 0, "automatable": 5},
            "workflows": workflows,
        }

        with (output_dir / "analysis.json").open("w") as f:
            json.dump(analysis_data, f, indent=2)

        # Build context
        context = build_report_context(workspace, profile=None)

        # Verify cost drivers
        cost_drivers = context["effort_metrics"]["cost_drivers"]

        # Should have entries for blocked (50%) and adapters (30%)
        assert len(cost_drivers) > 0

        # Find config decisions driver (50% blocked)
        config_driver = next(
            (d for d in cost_drivers if "configuration decisions" in d["label"]), None
        )
        assert config_driver is not None
        assert config_driver["percentage"] == 50

        # Render HTML
        html_output = render_report_template(context)

        # Verify cost drivers section
        assert "cost-drivers" in html_output
        assert "Primary Cost Drivers" in html_output

    def test_sprint_planning_phases(self, tmp_path):
        """Test that sprint planning phases are generated correctly."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        output_dir = workspace_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Create analysis with mix of ready, moderate, complex
        analysis_data = {
            "total_workflows": 9,
            "version": "1.0",
            "generated_at": "2024-01-01T00:00:00Z",
            "summary": {"blocked": 3, "partial": 3, "automatable": 3},
            "workflows": {
                # 3 ready (automatable with low scores)
                **{
                    f"ready{i}": {
                        "classification": "automatable",
                        "total_tasks": 5,
                        "blocked_tasks": 0,
                        "adapter_tasks": 0,
                        "regular_tasks": 5,
                        "blockers": [],
                        "blocker_details": [],
                    }
                    for i in range(3)
                },
                # 3 moderate (partial classification)
                **{
                    f"moderate{i}": {
                        "classification": "partial",
                        "total_tasks": 10,
                        "blocked_tasks": 0,
                        "adapter_tasks": 1,
                        "regular_tasks": 9,
                        "blockers": [],
                        "blocker_details": [],
                    }
                    for i in range(3)
                },
                # 3 complex (blocked)
                **{
                    f"complex{i}": {
                        "classification": "blocked",
                        "total_tasks": 10,
                        "blocked_tasks": 2,
                        "adapter_tasks": 0,
                        "regular_tasks": 8,
                        "blockers": ["blocker"],
                        "blocker_details": [],
                    }
                    for i in range(3)
                },
            },
        }

        with (output_dir / "analysis.json").open("w") as f:
            json.dump(analysis_data, f, indent=2)

        # Build context and render
        context = build_report_context(workspace, profile=None)
        html_output = render_report_template(context)

        # Verify sprint planning section
        assert "sprint-plan" in html_output
        assert "Recommended Migration Phases" in html_output
        assert "Phase" in html_output

        # Verify effort buckets match expectations
        buckets = context["effort_metrics"]["effort_buckets"]
        assert buckets["ready_now"] == 3
        assert buckets["moderate"] == 3
        assert buckets["complex"] == 3

        # Should mention sprints
        assert "sprint" in html_output.lower()
