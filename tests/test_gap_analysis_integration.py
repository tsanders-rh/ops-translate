"""
Integration tests for end-to-end gap analysis workflow.

Tests the complete pipeline from vRealize workflow analysis through
classification, gap report generation, and Ansible scaffolding.
"""

import json
import tempfile
from pathlib import Path

import pytest

from ops_translate.analyze.vrealize import analyze_vrealize_workflow
from ops_translate.intent.classify import classify_components
from ops_translate.intent.gaps import generate_gap_reports


class TestGapAnalysisIntegration:
    """Integration tests for complete gap analysis workflow."""

    def test_end_to_end_nsx_workflow(self):
        """Test complete gap analysis pipeline for NSX workflow."""
        # Step 1: Analyze vRealize workflow
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-medium.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Verify analysis results
        assert "nsx_operations" in analysis
        assert "signals" in analysis
        assert analysis["signals"]["nsx_keywords"] >= 8

        # Step 2: Classify components
        components = classify_components(analysis)

        # Verify classification
        assert len(components) > 0
        assert any(c.component_type.startswith("nsx_") for c in components)

        # Verify we have both PARTIAL and BLOCKED components
        levels = {c.level.value for c in components}
        assert "PARTIAL" in levels
        assert "BLOCKED" in levels

        # Step 3: Generate gap reports
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generate_gap_reports(components, output_dir, workflow_file.stem)

            # Verify reports were created
            assert (output_dir / "gaps.md").exists()
            assert (output_dir / "gaps.json").exists()

            # Verify Markdown report content
            md_content = (output_dir / "gaps.md").read_text()
            assert "Gap Analysis Report" in md_content
            assert "NSX" in md_content or "nsx" in md_content
            assert "Migration Path" in md_content

            # Verify JSON report structure
            json_content = (output_dir / "gaps.json").read_text()
            report = json.loads(json_content)
            assert report["workflow_name"] == workflow_file.stem
            assert report["summary"]["total_components"] > 0
            assert len(report["components"]) > 0

    def test_end_to_end_custom_plugins_workflow(self):
        """Test gap analysis detection for workflow with custom plugins."""
        # Step 1: Analyze workflow with custom plugins
        workflow_file = Path(__file__).parent / "fixtures/vrealize/plugins-custom.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Verify custom plugins detected in analysis
        assert "custom_plugins" in analysis
        assert len(analysis["custom_plugins"]) >= 2

        # Verify plugin detection includes evidence
        for plugin in analysis["custom_plugins"]:
            assert "plugin_name" in plugin
            assert "evidence" in plugin
            assert "confidence" in plugin

        # Step 2: Classify components (may be empty if no classifier for plugins)
        components = classify_components(analysis)

        # Step 3: Generate gap reports (works even with empty components)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generate_gap_reports(components, output_dir, "custom-plugins")

            # Verify JSON report structure
            json_content = (output_dir / "gaps.json").read_text()
            report = json.loads(json_content)

            # Should have migration guidance structure
            assert "migration_guidance" in report
            assert "has_blocking_issues" in report["migration_guidance"]

    def test_end_to_end_no_dependencies_workflow(self):
        """Test gap analysis for pure vCenter workflow with no external dependencies."""
        # Step 1: Analyze pure vCenter workflow
        workflow_file = Path(__file__).parent / "fixtures/vrealize/no-dependencies.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Verify no external dependencies
        assert analysis["signals"]["nsx_keywords"] == 0
        assert analysis["signals"]["plugin_refs"] == 0
        assert analysis["signals"]["rest_calls"] == 0

        # Step 2: Classify components
        components = classify_components(analysis)

        # May have some supported vCenter components or none at all
        # All should be SUPPORTED if any exist
        for component in components:
            assert component.level.value == "SUPPORTED"

        # Step 3: Generate gap reports
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generate_gap_reports(components, output_dir, "no-dependencies")

            # Verify Markdown report
            md_content = (output_dir / "gaps.md").read_text()
            assert "Gap Analysis Report" in md_content

            # Verify JSON report shows fully translatable
            json_content = (output_dir / "gaps.json").read_text()
            report = json.loads(json_content)
            assert report["summary"]["overall_assessment"] == "FULLY_TRANSLATABLE"
            assert not report["migration_guidance"]["has_blocking_issues"]

    def test_classification_severity_ordering(self):
        """Test that classified components are ordered by severity."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-medium.xml"
        analysis = analyze_vrealize_workflow(workflow_file)
        components = classify_components(analysis)

        # Verify components are sorted by severity (worst first)
        if len(components) > 1:
            prev_severity = components[0].level.severity
            for component in components[1:]:
                # Should be descending (higher severity first) or tied
                assert component.level.severity <= prev_severity
                prev_severity = component.level.severity

    def test_gap_report_has_recommendations(self):
        """Test that gap reports include actionable recommendations."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-medium.xml"
        analysis = analyze_vrealize_workflow(workflow_file)
        components = classify_components(analysis)

        # Filter for components that should have recommendations
        partial_or_blocked = [
            c for c in components if c.level.value in ("PARTIAL", "BLOCKED", "MANUAL")
        ]

        # At least some should have recommendations
        has_recommendations = any(
            c.recommendations and len(c.recommendations) > 0 for c in partial_or_blocked
        )
        assert has_recommendations

    def test_migration_paths_assigned(self):
        """Test that non-supported components have migration paths."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-medium.xml"
        analysis = analyze_vrealize_workflow(workflow_file)
        components = classify_components(analysis)

        # Filter for components that need migration paths
        needs_path = [c for c in components if c.level.value in ("PARTIAL", "BLOCKED", "MANUAL")]

        # All should have migration paths assigned
        for component in needs_path:
            assert component.migration_path is not None
            assert component.migration_path.value in ("PATH_A", "PATH_B", "PATH_C")

    def test_confidence_scores_present(self):
        """Test that analysis includes confidence scores for detections."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-medium.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Check NSX operations have confidence scores
        for category, operations in analysis["nsx_operations"].items():
            for op in operations:
                assert "confidence" in op
                assert 0.0 <= op["confidence"] <= 1.0

    def test_evidence_captured(self):
        """Test that evidence is captured for detections."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-light.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Check NSX operations have evidence
        for category, operations in analysis["nsx_operations"].items():
            for op in operations:
                assert "evidence" in op
                assert len(op["evidence"]) > 0

    def test_workflow_with_rest_calls(self):
        """Test REST API call detection in workflow analysis."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/rest-api.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Verify REST calls detected
        assert "rest_api_calls" in analysis
        assert len(analysis["rest_api_calls"]) >= 4

        # Verify different HTTP methods detected
        methods = {call.get("method") for call in analysis["rest_api_calls"]}
        assert "GET" in methods
        assert "POST" in methods

        # Verify REST call metadata
        for call in analysis["rest_api_calls"]:
            assert "method" in call
            assert "confidence" in call

        # Classify (may be empty if no REST classifier exists)
        components = classify_components(analysis)

        # Generate reports (works even with empty components)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generate_gap_reports(components, output_dir, "rest-api")

            # Verify reports created successfully
            assert (output_dir / "gaps.md").exists()
            assert (output_dir / "gaps.json").exists()

    def test_nsx_heavy_workflow_comprehensive(self):
        """Test gap analysis for comprehensive NSX workflow."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-heavy.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Verify comprehensive NSX detection
        total_nsx_ops = sum(len(ops) for ops in analysis["nsx_operations"].values())
        assert total_nsx_ops >= 10

        # Verify multiple operation categories
        assert len(analysis["nsx_operations"]) >= 3

        # Classify components (with deduplication, should be fewer than raw detections)
        components = classify_components(analysis)
        assert len(components) >= 5  # At least 5 unique components after deduplication
        assert len(components) < total_nsx_ops  # Deduplication should reduce count

        # Generate reports
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generate_gap_reports(components, output_dir, "nsx-heavy")

            # Verify comprehensive report content
            md_content = (output_dir / "gaps.md").read_text()

            # Should have multiple migration paths
            assert "PATH_A" in md_content

            # Should have detailed component analysis
            assert "Detailed Component Analysis" in md_content

    def test_json_report_machine_readable(self):
        """Test that JSON report is valid and machine-readable."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-medium.xml"
        analysis = analyze_vrealize_workflow(workflow_file)
        components = classify_components(analysis)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generate_gap_reports(components, output_dir, "test")

            # Parse JSON (should not raise exception)
            json_content = (output_dir / "gaps.json").read_text()
            report = json.loads(json_content)

            # Verify all required top-level keys
            assert "workflow_name" in report
            assert "summary" in report
            assert "components" in report
            assert "migration_guidance" in report

            # Verify components are serializable
            for component in report["components"]:
                assert "name" in component
                assert "component_type" in component
                assert "level" in component
                assert "reason" in component

    def test_error_handling_invalid_xml(self):
        """Test that invalid XML is handled gracefully."""
        from ops_translate.exceptions import FileNotFoundError as OpsFileNotFoundError

        # Non-existent file
        with pytest.raises(OpsFileNotFoundError):
            analyze_vrealize_workflow(Path("/nonexistent/file.xml"))

    def test_workflow_source_file_tracking(self):
        """Test that source file is tracked through the pipeline."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/nsx-light.xml"
        analysis = analyze_vrealize_workflow(workflow_file)

        # Verify source file is tracked
        assert "source_file" in analysis
        assert Path(analysis["source_file"]) == workflow_file
