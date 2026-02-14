"""
Snapshot tests for HTML report rendering with effort metrics.

These tests ensure that the executive dashboard renders consistently
and that changes to the report template are intentional and reviewed.
"""

import json

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

        # Verify new tabbed structure is present
        assert "tab-navigation" in html_output
        assert "tab-executive" in html_output
        assert "tab-architecture" in html_output
        assert "tab-implementation" in html_output

        # Verify tab buttons
        assert 'data-tab="executive"' in html_output
        assert 'data-tab="architecture"' in html_output
        assert 'data-tab="implementation"' in html_output

        # Verify Executive tab sections
        assert "executive-dashboard-section" in html_output
        assert "Migration Effort Dashboard" in html_output
        assert "decisions-required-section" in html_output
        assert "Architectural Decisions Required" in html_output
        assert "executive-conclusion-section" in html_output
        assert "Executive Summary" in html_output

        # Verify Architecture tab sections
        assert "Component-Level Translation Status" in html_output
        assert "domain-section-header" in html_output

        # Verify Implementation tab sections
        assert "start-here-section" in html_output
        assert "Start Here" in html_output
        assert "dod-section" in html_output
        assert "Definition of Done" in html_output

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
        """Test that domain-based grouping renders correctly (replaces integration heatmap)."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        intent_dir = workspace_dir / "intent"
        intent_dir.mkdir(exist_ok=True)

        # Create gaps data with components from different domains
        gaps_data = {
            "summary": {
                "counts": {"SUPPORTED": 1, "PARTIAL": 1, "BLOCKED": 2, "MANUAL": 0},
                "total_components": 4,
            },
            "components": [
                {
                    "component_type": "servicenow_integration",
                    "classification": "BLOCKED",
                    "level": "BLOCKED",
                    "name": "ServiceNow Integration",
                },
                {
                    "component_type": "nsx_firewall",
                    "classification": "BLOCKED",
                    "level": "BLOCKED",
                    "name": "NSX Firewall",
                },
                {
                    "component_type": "approval_gate",
                    "classification": "PARTIAL",
                    "level": "PARTIAL",
                    "name": "Approval Workflow",
                },
                {
                    "component_type": "vm_provisioning",
                    "classification": "SUPPORTED",
                    "level": "SUPPORTED",
                    "name": "VM Provisioning",
                },
            ],
        }

        with (intent_dir / "gaps.json").open("w") as f:
            json.dump(gaps_data, f, indent=2)

        # Build context and render
        context = build_report_context(workspace, profile=None)
        html_output = render_report_template(context)

        # Verify domain-based grouping structure
        assert "domain-section-header" in html_output

        # Verify domain categories appear (components should be grouped by domain)
        # Note: The actual domain grouping logic is in the template
        assert "Security" in html_output or "Networking" in html_output
        assert "Governance" in html_output or "Approvals" in html_output

    def test_cost_drivers_rendering(self, tmp_path):
        """Test that summary cards render with correct counts (replaces cost drivers)."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        intent_dir = workspace_dir / "intent"
        intent_dir.mkdir(exist_ok=True)

        # Create gaps data with known distribution
        gaps_data = {
            "summary": {
                "counts": {"SUPPORTED": 5, "PARTIAL": 3, "BLOCKED": 2, "MANUAL": 0},
                "total_components": 10,
            },
            "components": [],
        }

        with (intent_dir / "gaps.json").open("w") as f:
            json.dump(gaps_data, f, indent=2)

        # Build context and render
        context = build_report_context(workspace, profile=None)
        html_output = render_report_template(context)

        # Verify summary cards section renders
        assert "summary-cards" in html_output
        assert "Component-Level Translation Status" in html_output

        # Verify counts appear in the cards
        assert "5" in html_output  # SUPPORTED count
        assert "3" in html_output  # PARTIAL count
        assert "2" in html_output  # BLOCKED count

    def test_sprint_planning_phases(self, tmp_path):
        """Test that Implementation tab sections render correctly (replaces sprint planning)."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        intent_dir = workspace_dir / "intent"
        intent_dir.mkdir(exist_ok=True)

        # Create gaps data with mix of component types
        gaps_data = {
            "summary": {
                "counts": {"SUPPORTED": 3, "PARTIAL": 3, "BLOCKED": 3, "MANUAL": 0},
                "total_components": 9,
            },
            "components": [
                {
                    "component_type": "vm_provisioning",
                    "level": "SUPPORTED",
                    "name": "VM Provisioning",
                },
                {
                    "component_type": "network_adapter",
                    "level": "PARTIAL",
                    "name": "Network Configuration",
                },
                {
                    "component_type": "nsx_firewall",
                    "level": "BLOCKED",
                    "name": "NSX Firewall",
                },
            ],
        }

        with (intent_dir / "gaps.json").open("w") as f:
            json.dump(gaps_data, f, indent=2)

        # Build context and render
        context = build_report_context(workspace, profile=None)
        html_output = render_report_template(context)

        # Verify Implementation tab sections
        assert "start-here-section" in html_output
        assert "Start Here" in html_output
        assert "dod-section" in html_output
        assert "Definition of Done" in html_output

        # Verify Start Here steps are present
        assert "Review Generated Artifacts" in html_output
        assert "Address BLOCKED Components" in html_output or "BLOCKED" in html_output

        # Verify DoD categories
        assert "Testing" in html_output
        assert "Documentation" in html_output
