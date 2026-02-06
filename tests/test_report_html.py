"""
Tests for HTML report generation.

Tests the static HTML report generation functionality including context building,
template rendering, and artifact detection.
"""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from ops_translate.report.html import (
    build_report_context,
    generate_html_report,
)
from ops_translate.workspace import Workspace


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for testing."""
    workspace = Workspace(tmp_path / "workspace")
    workspace.initialize()
    return workspace


@pytest.fixture
def workspace_with_intent(temp_workspace):
    """Create workspace with intent data."""
    intent_data = {
        "schema_version": 1,
        "sources": [{"type": "powercli", "file": "test.ps1"}],
        "intent": {
            "workflow_name": "provision_vm",
            "workload_type": "virtual_machine",
            "inputs": {
                "vm_name": {"type": "string", "required": True},
                "environment": {"type": "enum", "values": ["dev", "prod"], "required": True},
            },
            "compute": {"cpu_cores": 2, "memory_mb": 4096},
            "networking": [{"name": "default", "type": "pod"}],
            "storage": [{"size_gb": 20, "type": "persistent"}],
        },
    }

    intent_file = temp_workspace.root / "intent/intent.yaml"
    intent_file.write_text(yaml.dump(intent_data))

    return temp_workspace


@pytest.fixture
def workspace_with_gaps(temp_workspace):
    """Create workspace with gaps data."""
    gaps_data = {
        "workflow_name": "test-workflow",
        "summary": {
            "total_components": 4,
            "overall_assessment": "REQUIRES_MANUAL_WORK",
            "counts": {"SUPPORTED": 1, "PARTIAL": 2, "BLOCKED": 1, "MANUAL": 0},
            "has_blocking_issues": True,
            "requires_manual_work": True,
            "migration_paths": {"PATH_A": 2, "PATH_B": 1, "NONE": 1},
        },
        "components": [
            {
                "name": "NSX Segment",
                "component_type": "network",
                "level": "PARTIAL",
                "reason": "Requires Multus CNI configuration",
                "openshift_equivalent": "NetworkAttachmentDefinition",
                "migration_path": "PATH_A",
                "recommendations": ["Configure Multus CNI", "Create NetworkAttachmentDefinition"],
                "evidence": "nsxClient.createSegment() detected at line 23",
                "confidence": 0.95,
            },
            {
                "name": "NSX Firewall",
                "component_type": "security",
                "level": "BLOCKED",
                "reason": "No direct OpenShift equivalent",
                "migration_path": "PATH_B",
                "recommendations": ["Keep NSX temporarily", "Plan migration path"],
                "confidence": 0.9,
            },
        ],
        "migration_guidance": "Review NSX components",
    }

    gaps_file = temp_workspace.root / "intent/gaps.json"
    gaps_file.write_text(json.dumps(gaps_data))

    return temp_workspace


class TestBuildReportContext:
    """Tests for building report context from workspace artifacts."""

    def test_context_includes_workspace_metadata(self, temp_workspace):
        """Test that context includes workspace name and timestamp."""
        context = build_report_context(temp_workspace)

        assert "workspace" in context
        assert context["workspace"]["name"] == "workspace"
        assert "timestamp" in context["workspace"]

    def test_context_includes_profile_info(self, temp_workspace):
        """Test that context includes profile configuration."""
        context = build_report_context(temp_workspace, profile="lab")

        assert "profile" in context
        assert context["profile"]["name"] == "lab"

    def test_context_loads_source_files(self, temp_workspace):
        """Test that context loads source file metadata."""
        # Create test source files
        powercli_dir = temp_workspace.root / "input/powercli"
        powercli_dir.mkdir(parents=True, exist_ok=True)
        (powercli_dir / "test.ps1").write_text("# PowerCLI script")

        vrealize_dir = temp_workspace.root / "input/vrealize"
        vrealize_dir.mkdir(parents=True, exist_ok=True)
        (vrealize_dir / "workflow.xml").write_text("<workflow/>")

        context = build_report_context(temp_workspace)

        assert "sources" in context
        assert len(context["sources"]) == 2

        # Check PowerCLI source
        powercli_sources = [s for s in context["sources"] if s["type"] == "PowerCLI"]
        assert len(powercli_sources) == 1
        assert powercli_sources[0]["name"] == "test.ps1"

        # Check vRealize source
        vrealize_sources = [s for s in context["sources"] if s["type"] == "vRealize"]
        assert len(vrealize_sources) == 1
        assert vrealize_sources[0]["name"] == "workflow.xml"

    def test_context_loads_intent_data(self, workspace_with_intent):
        """Test that context loads merged intent.yaml."""
        context = build_report_context(workspace_with_intent)

        assert "intent" in context
        assert context["intent"] is not None
        assert context["intent"]["intent"]["workflow_name"] == "provision_vm"

    def test_context_loads_gaps_data(self, workspace_with_gaps):
        """Test that context loads gaps.json."""
        context = build_report_context(workspace_with_gaps)

        assert "gaps" in context
        assert context["gaps"] is not None
        assert len(context["gaps"]["components"]) == 2

    def test_context_handles_missing_intent(self, temp_workspace):
        """Test that context handles missing intent gracefully."""
        context = build_report_context(temp_workspace)

        assert "intent" in context
        assert context["intent"] is None

    def test_context_handles_missing_gaps(self, temp_workspace):
        """Test that context handles missing gaps gracefully."""
        context = build_report_context(temp_workspace)

        assert "gaps" in context
        assert context["gaps"] is None

    def test_context_detects_kubevirt_artifacts(self, temp_workspace):
        """Test that context detects generated KubeVirt artifacts."""
        # Create KubeVirt artifacts
        kubevirt_dir = temp_workspace.root / "output/kubevirt"
        kubevirt_dir.mkdir(parents=True, exist_ok=True)
        (kubevirt_dir / "vm.yaml").write_text("apiVersion: kubevirt.io/v1")

        context = build_report_context(temp_workspace)

        assert "artifacts" in context
        assert len(context["artifacts"]["kubevirt"]) == 1
        assert context["artifacts"]["kubevirt"][0]["name"] == "vm.yaml"

    def test_context_detects_ansible_artifacts(self, temp_workspace):
        """Test that context detects generated Ansible artifacts."""
        # Create Ansible artifacts
        ansible_dir = temp_workspace.root / "output/ansible"
        ansible_dir.mkdir(parents=True, exist_ok=True)
        (ansible_dir / "site.yml").write_text("---\n")

        roles_dir = ansible_dir / "roles/provision_vm"
        roles_dir.mkdir(parents=True, exist_ok=True)

        context = build_report_context(temp_workspace)

        assert "artifacts" in context
        assert len(context["artifacts"]["ansible"]) >= 1

        # Check playbook
        playbooks = [a for a in context["artifacts"]["ansible"] if a.get("type") == "playbook"]
        assert len(playbooks) == 1
        assert playbooks[0]["name"] == "site.yml"

    def test_context_builds_summary_from_gaps(self, workspace_with_gaps):
        """Test that context builds summary from gaps data."""
        context = build_report_context(workspace_with_gaps)

        assert "summary" in context
        assert context["summary"]["total_components"] == 4
        assert context["summary"]["overall_assessment"] == "REQUIRES_MANUAL_WORK"
        assert context["summary"]["has_blocking_issues"] is True


class TestGenerateHTMLReport:
    """Tests for HTML report generation."""

    def test_generates_report_file(self, temp_workspace):
        """Test that generate_html_report creates index.html."""
        report_file = generate_html_report(temp_workspace)

        assert report_file.exists()
        assert report_file.name == "index.html"
        assert "output/report" in str(report_file)

    def test_report_contains_workspace_name(self, temp_workspace):
        """Test that generated report contains workspace name."""
        report_file = generate_html_report(temp_workspace)

        content = report_file.read_text()
        assert "workspace" in content.lower()

    def test_report_contains_summary_cards(self, temp_workspace):
        """Test that report contains summary cards section."""
        report_file = generate_html_report(temp_workspace)

        content = report_file.read_text()
        assert "summary-cards" in content
        assert "Supported" in content
        assert "Review Required" in content
        assert "Blocked" in content
        assert "Manual" in content

    def test_report_shows_intent_when_available(self, workspace_with_intent):
        """Test that report displays intent when available."""
        report_file = generate_html_report(workspace_with_intent)

        content = report_file.read_text()
        assert "Intent Overview" in content
        assert "provision_vm" in content
        assert "virtual_machine" in content

    def test_report_shows_gaps_when_available(self, workspace_with_gaps):
        """Test that report displays gaps when available."""
        report_file = generate_html_report(workspace_with_gaps)

        content = report_file.read_text()
        assert "Gaps & Migration Guidance" in content
        assert "NSX Segment" in content
        assert "PARTIAL" in content

    def test_report_creates_assets_directory(self, temp_workspace):
        """Test that report creates assets directory with CSS/JS."""
        report_file = generate_html_report(temp_workspace)

        assets_dir = report_file.parent / "assets"
        assert assets_dir.exists()
        assert (assets_dir / "style.css").exists()
        assert (assets_dir / "app.js").exists()

    def test_report_custom_output_path(self, temp_workspace):
        """Test that report respects custom output path."""
        custom_path = temp_workspace.root / "custom/location"
        report_file = generate_html_report(temp_workspace, output_path=custom_path)

        assert report_file.parent == custom_path
        assert report_file.exists()

    def test_report_with_custom_profile(self, temp_workspace):
        """Test that report uses custom profile when specified."""
        report_file = generate_html_report(temp_workspace, profile="production")

        content = report_file.read_text()
        assert "production" in content.lower()

    def test_report_is_valid_html(self, temp_workspace):
        """Test that generated report is valid HTML."""
        report_file = generate_html_report(temp_workspace)

        content = report_file.read_text()
        assert content.startswith("<!DOCTYPE html>")
        assert "<html" in content
        assert "</html>" in content
        assert "<head>" in content
        assert "<body>" in content

    def test_report_includes_stylesheet_link(self, temp_workspace):
        """Test that report includes link to stylesheet."""
        report_file = generate_html_report(temp_workspace)

        content = report_file.read_text()
        assert 'href="assets/style.css"' in content

    def test_report_includes_javascript_link(self, temp_workspace):
        """Test that report includes script tag for JavaScript."""
        report_file = generate_html_report(temp_workspace)

        content = report_file.read_text()
        assert 'src="assets/app.js"' in content


class TestReportWithCompleteWorkspace:
    """Integration tests with fully populated workspace."""

    @pytest.fixture
    def complete_workspace(self, temp_workspace):
        """Create workspace with all artifacts."""
        # Add source files
        powercli_dir = temp_workspace.root / "input/powercli"
        powercli_dir.mkdir(parents=True, exist_ok=True)
        (powercli_dir / "provision.ps1").write_text("# PowerCLI")

        # Add intent
        intent_data = {
            "schema_version": 1,
            "intent": {"workflow_name": "test", "workload_type": "vm"},
        }
        intent_file = temp_workspace.root / "intent/intent.yaml"
        intent_file.write_text(yaml.dump(intent_data))

        # Add gaps
        gaps_data = {
            "summary": {
                "total_components": 1,
                "overall_assessment": "FULLY_TRANSLATABLE",
                "counts": {"SUPPORTED": 1, "PARTIAL": 0, "BLOCKED": 0, "MANUAL": 0},
                "has_blocking_issues": False,
                "requires_manual_work": False,
            },
            "components": [],
        }
        gaps_file = temp_workspace.root / "intent/gaps.json"
        gaps_file.write_text(json.dumps(gaps_data))

        # Add assumptions
        assumptions_file = temp_workspace.root / "intent/assumptions.md"
        assumptions_file.write_text("# Assumptions\n\n- Test assumption")

        # Add artifacts
        kubevirt_dir = temp_workspace.root / "output/kubevirt"
        kubevirt_dir.mkdir(parents=True, exist_ok=True)
        (kubevirt_dir / "vm.yaml").write_text("apiVersion: kubevirt.io/v1")

        return temp_workspace

    def test_complete_report_generation(self, complete_workspace):
        """Test report generation with complete workspace."""
        report_file = generate_html_report(complete_workspace)

        assert report_file.exists()

        content = report_file.read_text()

        # Check all major sections are present
        assert "Source Files" in content
        assert "Intent Overview" in content
        assert "Translation Status" in content
        assert "Generated Artifacts" in content
        assert "Assumptions" in content

    def test_report_shows_fully_translatable_status(self, complete_workspace):
        """Test that report shows fully translatable status correctly."""
        report_file = generate_html_report(complete_workspace)

        content = report_file.read_text()
        assert "FULLY_TRANSLATABLE" in content or "Fully Translatable" in content
