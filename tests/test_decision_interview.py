"""
Tests for Decision Interview functionality.

Tests the full workflow from UI rendering to decision persistence
and classification updates.
"""

import json

import yaml

from ops_translate.decisions import DecisionManager
from ops_translate.report.html import build_report_context, render_report_template
from ops_translate.workspace import Workspace


class TestDecisionManager:
    """Tests for DecisionManager class."""

    def test_load_nonexistent_decisions(self, tmp_path):
        """Test loading decisions when file doesn't exist."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        manager = DecisionManager(workspace_dir)
        decisions = manager.load_decisions()

        assert decisions is None
        assert not manager.has_decisions()

    def test_save_and_load_decisions(self, tmp_path):
        """Test saving and loading decisions."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        manager = DecisionManager(workspace_dir)

        # Create test decisions
        decisions = {
            "schema_version": 1,
            "decisions": {
                "security": {
                    "label_key": "security.zone",
                    "namespace_model": "per-app",
                    "default_policy": "deny",
                },
                "governance": {
                    "approval_system": "aap",
                    "timeout_minutes": 60,
                },
            },
        }

        # Save decisions
        manager.save_decisions(decisions)

        # Verify file exists
        assert manager.has_decisions()
        assert manager.decisions_file.exists()

        # Load decisions
        loaded = manager.load_decisions()
        assert loaded is not None
        assert loaded["schema_version"] == 1
        assert loaded["decisions"]["security"]["label_key"] == "security.zone"
        assert loaded["decisions"]["governance"]["approval_system"] == "aap"

    def test_get_decision(self, tmp_path):
        """Test getting specific decision values."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        manager = DecisionManager(workspace_dir)

        decisions = {
            "schema_version": 1,
            "decisions": {
                "security": {
                    "label_key": "app.tier",
                }
            },
        }

        manager.save_decisions(decisions)

        # Test get_decision
        assert manager.get_decision("security", "label_key") == "app.tier"
        assert manager.get_decision("security", "nonexistent", "default") == "default"
        assert manager.get_decision("nonexistent", "key", None) is None

    def test_apply_to_nsx_security_group(self, tmp_path):
        """Test applying decisions to NSX security group component."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        manager = DecisionManager(workspace_dir)

        # Create decisions with security taxonomy
        decisions = {
            "schema_version": 1,
            "decisions": {
                "security": {
                    "label_key": "security.zone",
                    "namespace_model": "per-app",
                    "default_policy": "deny",
                }
            },
        }

        manager.save_decisions(decisions)

        # Test component (BLOCKED NSX security group)
        component = {
            "name": "NSX-Group-Web",
            "component_type": "nsx-security-group",
            "level": "BLOCKED",
            "reason": "Missing label taxonomy",
        }

        # Apply decisions
        updated = manager.apply_to_component(component)

        # Should be upgraded to PARTIAL
        assert updated["level"] == "PARTIAL"
        assert "Label taxonomy defined" in updated["reason"]

    def test_apply_to_firewall_component(self, tmp_path):
        """Test applying decisions to firewall component."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        manager = DecisionManager(workspace_dir)

        decisions = {
            "schema_version": 1,
            "decisions": {
                "firewall": {
                    "egress_model": "egressfirewall",
                    "l7_features": "no",
                }
            },
        }

        manager.save_decisions(decisions)

        component = {
            "name": "NSX Firewall Rules",
            "component_type": "nsx-firewall",
            "level": "BLOCKED",
            "reason": "Missing policy approach",
        }

        updated = manager.apply_to_component(component)

        assert updated["level"] == "PARTIAL"
        assert "Firewall policy approach defined" in updated["reason"]

    def test_no_upgrade_for_supported_components(self, tmp_path):
        """Test that SUPPORTED components are not modified."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        manager = DecisionManager(workspace_dir)

        decisions = {
            "schema_version": 1,
            "decisions": {
                "security": {
                    "label_key": "security.zone",
                }
            },
        }

        manager.save_decisions(decisions)

        component = {
            "name": "VM Provisioning",
            "component_type": "vm-provisioning",
            "level": "SUPPORTED",
        }

        updated = manager.apply_to_component(component)

        # Should remain SUPPORTED
        assert updated["level"] == "SUPPORTED"


class TestDecisionInterviewReport:
    """Tests for Decision Interview tab in report."""

    def test_decision_tab_renders(self, tmp_path):
        """Test that Decision Interview tab renders in report."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        # Create gaps data with BLOCKED components
        intent_dir = workspace_dir / "intent"
        intent_dir.mkdir(exist_ok=True)

        gaps_data = {
            "summary": {
                "counts": {"SUPPORTED": 0, "PARTIAL": 1, "BLOCKED": 2, "MANUAL": 0},
                "total_components": 3,
            },
            "components": [
                {
                    "name": "NSX Security Group",
                    "component_type": "nsx-security-group",
                    "level": "BLOCKED",
                },
                {
                    "name": "Approval Workflow",
                    "component_type": "approval-gate",
                    "level": "BLOCKED",
                },
                {
                    "name": "Network Adapter",
                    "component_type": "network-adapter",
                    "level": "PARTIAL",
                },
            ],
        }

        with (intent_dir / "gaps.json").open("w") as f:
            json.dump(gaps_data, f)

        # Build report context
        context = build_report_context(workspace, profile=None)

        # Render HTML
        html_output = render_report_template(context)

        # Verify Decision Interview tab exists
        assert "tab-decisions" in html_output
        assert 'data-tab="decisions"' in html_output
        assert "Decision Interview" in html_output

        # Verify badge shows components needing decisions
        assert "tab-badge" in html_output

        # Verify overview section
        assert "decision-overview-section" in html_output
        assert "Components Need Decisions" in html_output

        # Verify question packs render based on component types
        assert "question-packs-section" in html_output
        assert "Security: NSX Groups" in html_output or "Security" in html_output
        assert "Governance: Approval" in html_output or "Approval" in html_output

    def test_report_applies_decisions_to_components(self, tmp_path):
        """Test that report automatically applies decisions to components."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        # Create gaps data
        intent_dir = workspace_dir / "intent"
        intent_dir.mkdir(exist_ok=True)

        gaps_data = {
            "summary": {
                "counts": {"SUPPORTED": 0, "PARTIAL": 0, "BLOCKED": 1, "MANUAL": 0},
                "total_components": 1,
            },
            "components": [
                {
                    "name": "NSX Security Group",
                    "component_type": "nsx-security-group",
                    "level": "BLOCKED",
                }
            ],
        }

        with (intent_dir / "gaps.json").open("w") as f:
            json.dump(gaps_data, f)

        # Create decisions
        decisions_dir = workspace_dir / ".ops-translate"
        decisions_dir.mkdir(exist_ok=True)

        decisions = {
            "schema_version": 1,
            "decisions": {
                "security": {
                    "label_key": "security.zone",
                    "namespace_model": "per-app",
                }
            },
        }

        with (decisions_dir / "decisions.yaml").open("w") as f:
            yaml.dump(decisions, f)

        # Build report context - should apply decisions
        context = build_report_context(workspace, profile=None)

        # Verify component was upgraded
        components = context["gaps"]["components"]
        assert len(components) == 1
        assert components[0]["level"] == "PARTIAL"  # Upgraded from BLOCKED
        assert "Label taxonomy defined" in components[0]["reason"]

    def test_no_question_packs_when_no_gaps(self, tmp_path):
        """Test that question packs don't appear when no gaps exist."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        workspace = Workspace(workspace_dir)
        workspace.initialize()

        # Build report without gaps
        context = build_report_context(workspace, profile=None)
        html_output = render_report_template(context)

        # Decision tab should still exist but show different message
        assert "tab-decisions" in html_output
        assert "No gaps data available" in html_output or "No decisions needed" in html_output
