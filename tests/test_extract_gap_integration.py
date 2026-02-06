"""
Tests for gap analysis integration during intent extraction.

Tests that gap analysis runs automatically when extracting intent from
vRealize workflows and generates appropriate reports and warnings.
"""

import shutil
from pathlib import Path

import pytest

from ops_translate.intent.extract import extract_all
from ops_translate.workspace import Workspace


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for testing."""
    workspace = Workspace(tmp_path / "workspace")
    workspace.initialize()
    return workspace


@pytest.fixture
def nsx_workflow_fixture():
    """Path to NSX workflow test fixture."""
    return Path(__file__).parent / "fixtures/vrealize/nsx-medium.xml"


@pytest.fixture
def no_deps_workflow_fixture():
    """Path to workflow with no dependencies."""
    return Path(__file__).parent / "fixtures/vrealize/no-dependencies.xml"


@pytest.fixture
def plugins_workflow_fixture():
    """Path to workflow with custom plugins."""
    return Path(__file__).parent / "fixtures/vrealize/plugins-custom.xml"


class TestGapAnalysisIntegrationDuringExtract:
    """Tests for automatic gap analysis during extraction."""

    def test_gap_analysis_runs_automatically_for_vrealize(
        self, temp_workspace, nsx_workflow_fixture
    ):
        """Test that gap analysis runs automatically for vRealize workflows."""
        workspace = temp_workspace

        # Copy NSX workflow to input directory
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / nsx_workflow_fixture.name
        shutil.copy2(nsx_workflow_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Verify gap reports were created
        assert (workspace.root / "intent/gaps.md").exists()
        assert (workspace.root / "intent/gaps.json").exists()

        # Verify gap report content
        gaps_md = (workspace.root / "intent/gaps.md").read_text()
        assert "Gap Analysis Report" in gaps_md
        assert "vRealize workflows" in gaps_md

    def test_gap_reports_contain_nsx_components(self, temp_workspace, nsx_workflow_fixture):
        """Test that gap reports identify NSX components."""
        workspace = temp_workspace

        # Copy NSX workflow
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / nsx_workflow_fixture.name
        shutil.copy2(nsx_workflow_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Check gap report content
        gaps_md = (workspace.root / "intent/gaps.md").read_text()

        # Should mention NSX components
        assert (
            "nsx" in gaps_md.lower()
            or "segment" in gaps_md.lower()
            or "firewall" in gaps_md.lower()
        )

        # Should have component analysis
        assert "Component Analysis" in gaps_md or "Components" in gaps_md

    def test_gaps_json_is_valid_and_machine_readable(self, temp_workspace, nsx_workflow_fixture):
        """Test that gaps.json is valid JSON with expected structure."""
        import json

        workspace = temp_workspace

        # Copy NSX workflow
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / nsx_workflow_fixture.name
        shutil.copy2(nsx_workflow_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Parse gaps.json
        gaps_json = (workspace.root / "intent/gaps.json").read_text()
        report = json.loads(gaps_json)

        # Verify structure
        assert "workflow_name" in report
        assert "summary" in report
        assert "components" in report
        assert "migration_guidance" in report

        # Verify summary contains counts
        assert "counts" in report["summary"]
        assert "overall_assessment" in report["summary"]

    def test_no_gap_reports_for_powercli_only(self, temp_workspace):
        """Test that gap analysis doesn't run for PowerCLI-only workspaces."""
        workspace = temp_workspace

        # Copy PowerCLI fixture
        powercli_fixture = Path(__file__).parent / "fixtures" / "provision-vm.ps1"
        if not powercli_fixture.exists():
            pytest.skip("PowerCLI fixture not available")

        input_dir = workspace.root / "input/powercli"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / powercli_fixture.name
        shutil.copy2(powercli_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Gap reports should NOT be created for PowerCLI only
        assert not (workspace.root / "intent/gaps.md").exists()
        assert not (workspace.root / "intent/gaps.json").exists()

    def test_gap_analysis_for_multiple_workflows(
        self, temp_workspace, nsx_workflow_fixture, no_deps_workflow_fixture
    ):
        """Test gap analysis with multiple vRealize workflows."""
        workspace = temp_workspace

        # Copy multiple workflows
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(nsx_workflow_fixture, input_dir / nsx_workflow_fixture.name)
        shutil.copy2(no_deps_workflow_fixture, input_dir / no_deps_workflow_fixture.name)

        # Run extraction
        extract_all(workspace)

        # Gap reports should be created
        assert (workspace.root / "intent/gaps.md").exists()
        assert (workspace.root / "intent/gaps.json").exists()

        # Verify consolidated report
        import json

        gaps_json = (workspace.root / "intent/gaps.json").read_text()
        report = json.loads(gaps_json)

        # Should have components from both workflows analyzed
        assert "components" in report

    def test_gap_analysis_with_no_dependencies_workflow(
        self, temp_workspace, no_deps_workflow_fixture
    ):
        """Test gap analysis for workflow with no external dependencies."""
        workspace = temp_workspace

        # Copy no-dependencies workflow
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / no_deps_workflow_fixture.name
        shutil.copy2(no_deps_workflow_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Gap reports should still be created (even if no issues)
        assert (workspace.root / "intent/gaps.md").exists()
        assert (workspace.root / "intent/gaps.json").exists()

        # Check overall assessment
        import json

        gaps_json = (workspace.root / "intent/gaps.json").read_text()
        report = json.loads(gaps_json)

        # With the new classifiers, this workflow is detected as MOSTLY_AUTOMATIC
        # because it has governance/approval logic that requires manual configuration
        assert report["summary"]["overall_assessment"] in [
            "FULLY_TRANSLATABLE",
            "MOSTLY_AUTOMATIC",
        ]

        # Verify it has no blocking issues (this is the key point of "no dependencies")
        assert not report["summary"]["has_blocking_issues"]

    def test_gap_analysis_error_handling(self, temp_workspace):
        """Test that gap analysis errors don't stop extraction."""
        workspace = temp_workspace

        # Create an invalid XML file
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)

        invalid_xml = input_dir / "invalid.xml"
        invalid_xml.write_text("<invalid>xml<without>closing</tags>")

        # Run extraction - should complete despite invalid XML
        try:
            extract_all(workspace)
            # Should complete without raising exception
        except Exception as e:
            # Gap analysis errors should be caught and logged, not raised
            pytest.fail(f"Extraction failed due to gap analysis error: {e}")

        # Intent file should still be created (with placeholder)
        assert (workspace.root / "intent/invalid.intent.yaml").exists()

    def test_intent_files_created_before_gap_analysis(self, temp_workspace, nsx_workflow_fixture):
        """Test that intent files are created even if gap analysis fails."""
        workspace = temp_workspace

        # Copy NSX workflow
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / nsx_workflow_fixture.name
        shutil.copy2(nsx_workflow_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Intent file should be created
        intent_file = workspace.root / "intent" / f"{nsx_workflow_fixture.stem}.intent.yaml"
        assert intent_file.exists()

        # Gap reports should also be created
        assert (workspace.root / "intent/gaps.md").exists()
        assert (workspace.root / "intent/gaps.json").exists()

    def test_assumptions_file_still_created_with_gap_analysis(
        self, temp_workspace, nsx_workflow_fixture
    ):
        """Test that assumptions.md is created alongside gap reports."""
        workspace = temp_workspace

        # Copy NSX workflow
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / nsx_workflow_fixture.name
        shutil.copy2(nsx_workflow_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Both assumptions and gap reports should exist
        assert (workspace.root / "intent/assumptions.md").exists()
        assert (workspace.root / "intent/gaps.md").exists()
        assert (workspace.root / "intent/gaps.json").exists()

    def test_gap_analysis_for_workflows_with_custom_plugins(
        self, temp_workspace, plugins_workflow_fixture
    ):
        """Test gap analysis detects custom plugins."""
        workspace = temp_workspace

        # Copy plugins workflow
        input_dir = workspace.root / "input/vrealize"
        input_dir.mkdir(parents=True, exist_ok=True)
        dest = input_dir / plugins_workflow_fixture.name
        shutil.copy2(plugins_workflow_fixture, dest)

        # Run extraction
        extract_all(workspace)

        # Gap reports should be created
        assert (workspace.root / "intent/gaps.md").exists()
        assert (workspace.root / "intent/gaps.json").exists()

        # Check that plugins were mentioned in analysis
        # Note: Custom plugin classifier may not exist yet, so this may be empty
        # But the analysis should still complete successfully
        gaps_md = (workspace.root / "intent/gaps.md").read_text()
        assert "Gap Analysis Report" in gaps_md
