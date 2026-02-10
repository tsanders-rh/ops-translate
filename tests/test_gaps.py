"""
Unit tests for gap analysis report generation.

Tests generation of Markdown and JSON gap reports, console output, and
report content validation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from ops_translate.intent.classify import (
    ClassifiedComponent,
    MigrationPath,
    TranslatabilityLevel,
)
from ops_translate.intent.gaps import (
    generate_gap_reports,
    print_gap_summary,
)


class TestGenerateGapReports:
    """Tests for gap report generation."""

    def test_creates_output_directory(self):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "intent" / "nested"
            components = []

            generate_gap_reports(components, output_dir, "Test Workflow")

            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_generates_both_report_files(self):
        """Test that both gaps.md and gaps.json are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Test Component",
                    "test_type",
                    TranslatabilityLevel.SUPPORTED,
                    "Fully supported",
                )
            ]

            generate_gap_reports(components, output_dir, "Test Workflow")

            assert (output_dir / "gaps.md").exists()
            assert (output_dir / "gaps.json").exists()

    def test_markdown_report_structure(self):
        """Test that Markdown report has expected structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "NSX Segment",
                    "nsx_segment",
                    TranslatabilityLevel.PARTIAL,
                    "Can be replaced with NAD",
                    openshift_equivalent="NetworkAttachmentDefinition",
                    migration_path=MigrationPath.PATH_A,
                    evidence="nsxClient.createSegment()",
                    location="workflow.xml:42",
                    recommendations=["Create NAD", "Test networking"],
                )
            ]

            generate_gap_reports(components, output_dir, "NSX Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Check for required sections
            assert "# Gap Analysis Report: NSX Workflow" in md_content
            assert "## Executive Summary" in md_content
            assert "## Migration Path Recommendations" in md_content
            assert "## Detailed Component Analysis" in md_content
            assert "## Next Steps" in md_content

            # Check component details
            assert "NSX Segment" in md_content
            assert "nsx_segment" in md_content
            assert "NetworkAttachmentDefinition" in md_content
            assert "Create NAD" in md_content

    def test_json_report_structure(self):
        """Test that JSON report has expected structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Test Component",
                    "test_type",
                    TranslatabilityLevel.BLOCKED,
                    "Blocked reason",
                    migration_path=MigrationPath.PATH_C,
                )
            ]

            generate_gap_reports(components, output_dir, "Test Workflow")

            json_content = (output_dir / "gaps.json").read_text()
            report = json.loads(json_content)

            # Check top-level structure
            assert "workflow_name" in report
            assert report["workflow_name"] == "Test Workflow"
            assert "summary" in report
            assert "components" in report
            assert "migration_guidance" in report

            # Check summary section
            assert "counts" in report["summary"]
            assert "overall_assessment" in report["summary"]

            # Check components serialization
            assert len(report["components"]) == 1
            assert report["components"][0]["name"] == "Test Component"
            assert report["components"][0]["level"] == "BLOCKED"

    def test_report_with_no_components(self):
        """Test report generation with empty component list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = []

            generate_gap_reports(components, output_dir, "Empty Workflow")

            # Should still generate files
            assert (output_dir / "gaps.md").exists()
            assert (output_dir / "gaps.json").exists()

            # Check JSON content
            json_content = (output_dir / "gaps.json").read_text()
            report = json.loads(json_content)
            assert report["summary"]["total_components"] == 0
            assert report["summary"]["overall_assessment"] == "FULLY_TRANSLATABLE"

    def test_markdown_report_blocking_components(self):
        """Test Markdown report content for workflows with blocking issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Custom Plugin",
                    "servicenow_plugin",
                    TranslatabilityLevel.MANUAL,
                    "Requires custom implementation",
                    migration_path=MigrationPath.PATH_C,
                )
            ]

            generate_gap_reports(components, output_dir, "Blocked Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Should show expert-guided migration available section
            assert "🎯 Expert-Guided Migration Available" in md_content
            assert "production-grade patterns from Red Hat experts" in md_content

            # Should show Custom Implementation components section
            assert "🔧 Custom Implementation Components" in md_content

    def test_markdown_report_partial_components(self):
        """Test Markdown report for workflows with only partial components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "NSX Firewall",
                    "firewall_rule",
                    TranslatabilityLevel.PARTIAL,
                    "Use NetworkPolicy",
                    openshift_equivalent="NetworkPolicy",
                    migration_path=MigrationPath.PATH_A,
                )
            ]

            generate_gap_reports(components, output_dir, "Partial Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Should show manual configuration section
            assert "ℹ️ Manual Configuration Needed" in md_content
            assert "mostly automated" in md_content

    def test_markdown_report_fully_supported(self):
        """Test Markdown report for fully supported workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "VM Creation",
                    "vm_create",
                    TranslatabilityLevel.SUPPORTED,
                    "Fully supported via KubeVirt",
                )
            ]

            generate_gap_reports(components, output_dir, "Supported Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Should show ready for translation section
            assert "✅ Ready for Automatic Translation" in md_content
            assert "automatically translated" in md_content

    def test_migration_paths_in_markdown(self):
        """Test that migration paths are documented correctly in Markdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Component A",
                    "type_a",
                    TranslatabilityLevel.PARTIAL,
                    "Path A component",
                    migration_path=MigrationPath.PATH_A,
                ),
                ClassifiedComponent(
                    "Component B",
                    "type_b",
                    TranslatabilityLevel.BLOCKED,
                    "Path B component",
                    migration_path=MigrationPath.PATH_B,
                ),
                ClassifiedComponent(
                    "Component C",
                    "type_c",
                    TranslatabilityLevel.MANUAL,
                    "Path C component",
                    migration_path=MigrationPath.PATH_C,
                ),
            ]

            generate_gap_reports(components, output_dir, "Multi-Path Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Check all paths are documented
            assert "PATH_A: OpenShift-native replacement" in md_content
            assert "PATH_B: Hybrid approach" in md_content
            assert "PATH_C: Custom specialist implementation" in md_content

            # Check component counts
            assert "1 component(s)" in md_content  # Each path has 1 component

    def test_component_evidence_in_markdown(self):
        """Test that component evidence is included in Markdown report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "NSX API Call",
                    "nsx_operation",
                    TranslatabilityLevel.PARTIAL,
                    "NSX operation detected",
                    evidence="nsxClient.createFirewallRule({ action: 'ALLOW' })",
                    location="workflow.xml:156",
                )
            ]

            generate_gap_reports(components, output_dir, "Evidence Test")

            md_content = (output_dir / "gaps.md").read_text()

            # Check evidence section
            assert "**Evidence**:" in md_content
            assert "nsxClient.createFirewallRule" in md_content

            # Check location
            assert "**Location**: `workflow.xml:156`" in md_content

    def test_component_recommendations_in_markdown(self):
        """Test that recommendations are formatted correctly in Markdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Load Balancer",
                    "nsx_lb",
                    TranslatabilityLevel.PARTIAL,
                    "Use OpenShift Route or Service",
                    recommendations=[
                        "Create Service with type LoadBalancer",
                        "Configure health checks",
                        "Test failover scenarios",
                    ],
                )
            ]

            generate_gap_reports(components, output_dir, "Recommendations Test")

            md_content = (output_dir / "gaps.md").read_text()

            # Check recommendations section
            assert "**Recommendations**:" in md_content
            assert "- Create Service with type LoadBalancer" in md_content
            assert "- Configure health checks" in md_content
            assert "- Test failover scenarios" in md_content

    def test_json_report_migration_guidance(self):
        """Test that JSON report includes migration guidance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Component 1",
                    "type1",
                    TranslatabilityLevel.PARTIAL,
                    "Partial support",
                    migration_path=MigrationPath.PATH_A,
                ),
                ClassifiedComponent(
                    "Component 2",
                    "type2",
                    TranslatabilityLevel.BLOCKED,
                    "Blocked",
                    migration_path=MigrationPath.PATH_B,
                ),
            ]

            generate_gap_reports(components, output_dir, "Guidance Test")

            json_content = (output_dir / "gaps.json").read_text()
            report = json.loads(json_content)

            guidance = report["migration_guidance"]
            assert "overall_assessment" in guidance
            assert "has_blocking_issues" in guidance
            assert "requires_manual_work" in guidance
            assert "recommended_paths" in guidance

            # Should recommend PATH_A and PATH_B (but not NONE)
            recommended = guidance["recommended_paths"]
            assert "PATH_A" in recommended
            assert "PATH_B" in recommended
            assert "NONE" not in recommended

    def test_next_steps_for_blocking_workflow(self):
        """Test that Next Steps section is appropriate for blocking workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Blocker",
                    "type",
                    TranslatabilityLevel.BLOCKED,
                    "Cannot translate",
                )
            ]

            generate_gap_reports(components, output_dir, "Blocking Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Check for blocking-specific next steps (updated terminology)
            assert "Review Expert-Guided and Custom components" in md_content
            assert "Decide on migration path" in md_content
            assert "Consult Red Hat experts" in md_content

    def test_next_steps_for_partial_workflow(self):
        """Test Next Steps for workflows with only partial components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Partial",
                    "type",
                    TranslatabilityLevel.PARTIAL,
                    "Needs config",
                )
            ]

            generate_gap_reports(components, output_dir, "Partial Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Check for partial-specific next steps
            assert "Review generated TODO tasks" in md_content
            assert "Complete manual configuration" in md_content

    def test_next_steps_for_supported_workflow(self):
        """Test Next Steps for fully supported workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            components = [
                ClassifiedComponent(
                    "Supported",
                    "type",
                    TranslatabilityLevel.SUPPORTED,
                    "Fully supported",
                )
            ]

            generate_gap_reports(components, output_dir, "Supported Workflow")

            md_content = (output_dir / "gaps.md").read_text()

            # Check for supported-specific next steps
            assert "Review generated manifests" in md_content
            assert "Deploy to test environment" in md_content


class TestPrintGapSummary:
    """Tests for console gap summary output."""

    @patch("rich.console.Console")
    def test_prints_summary_table(self, mock_console_class):
        """Test that summary prints a table with component counts."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        components = [
            ClassifiedComponent("c1", "t1", TranslatabilityLevel.SUPPORTED, "OK"),
            ClassifiedComponent("c2", "t2", TranslatabilityLevel.PARTIAL, "Partial"),
        ]

        print_gap_summary(components)

        # Should have called console.print at least once
        assert mock_console.print.call_count >= 1

    @patch("rich.console.Console")
    def test_shows_blocking_warning(self, mock_console_class):
        """Test that blocking components trigger warning message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        components = [
            ClassifiedComponent("blocker", "type", TranslatabilityLevel.BLOCKED, "Blocked")
        ]

        print_gap_summary(components)

        # Check that warning about blocking issues was printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("blocking issues" in str(call).lower() for call in print_calls)

    @patch("rich.console.Console")
    def test_shows_success_message_for_supported(self, mock_console_class):
        """Test success message for fully supported workflows."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        components = [
            ClassifiedComponent("supported", "type", TranslatabilityLevel.SUPPORTED, "OK")
        ]

        print_gap_summary(components)

        # Check that success message was printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("fully automatically translated" in str(call).lower() for call in print_calls)
