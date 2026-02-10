"""
Unit tests for report loader components.

Tests the decoupled components (FileLocator, DataLoader, ContextBuilder)
for better testability and maintainability.
"""

import json
import tempfile
from pathlib import Path

import yaml

from ops_translate.report.loaders import (
    ReportContextBuilder,
    ReportDataLoader,
    ReportFileLocator,
)
from ops_translate.workspace import Workspace


class TestReportFileLocator:
    """Tests for ReportFileLocator class."""

    def test_locator_finds_existing_gaps_file(self):
        """Test that locator finds gaps.json when it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "intent").mkdir()
            gaps_file = workspace_root / "intent/gaps.json"
            gaps_file.write_text('{"summary": {}}')

            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            assert locator.gaps_file() == gaps_file
            assert locator.gaps_file().exists()

    def test_locator_returns_none_for_missing_gaps_file(self):
        """Test that locator returns None when gaps.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            assert locator.gaps_file() is None

    def test_locator_finds_existing_recommendations_file(self):
        """Test that locator finds recommendations.json when it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "intent").mkdir()
            recs_file = workspace_root / "intent/recommendations.json"
            recs_file.write_text('{"recommendations": []}')

            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            assert locator.recommendations_file() == recs_file
            assert locator.recommendations_file().exists()

    def test_locator_finds_existing_decisions_file(self):
        """Test that locator finds decisions.yaml when it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "intent").mkdir()
            decisions_file = workspace_root / "intent/decisions.yaml"
            decisions_file.write_text("decisions: []")

            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            assert locator.decisions_file() == decisions_file

    def test_locator_finds_existing_questions_file(self):
        """Test that locator finds questions.json when it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "intent").mkdir()
            questions_file = workspace_root / "intent/questions.json"
            questions_file.write_text('{"questions": []}')

            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            assert locator.questions_file() == questions_file

    def test_locator_finds_intent_file(self):
        """Test that locator finds merged intent.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "intent").mkdir()
            intent_file = workspace_root / "intent/intent.yaml"
            intent_file.write_text("intent: {}")

            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            assert locator.intent_file() == intent_file

    def test_locator_finds_markdown_files(self):
        """Test that locator finds assumptions.md and conflicts.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "intent").mkdir()
            assumptions_file = workspace_root / "intent/assumptions.md"
            conflicts_file = workspace_root / "intent/conflicts.md"
            assumptions_file.write_text("# Assumptions")
            conflicts_file.write_text("# Conflicts")

            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            assert locator.assumptions_file() == assumptions_file
            assert locator.conflicts_file() == conflicts_file

    def test_locator_finds_input_files(self):
        """Test that locator finds input files with pattern matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            (workspace_root / "input").mkdir()
            (workspace_root / "input/script1.ps1").write_text("# PowerCLI script")
            (workspace_root / "input/script2.ps1").write_text("# PowerCLI script")
            (workspace_root / "input/workflow.xml").write_text("<workflow/>")

            workspace = Workspace(workspace_root)
            locator = ReportFileLocator(workspace)

            # Find all files
            all_files = locator.input_files()
            assert len(all_files) == 3

            # Find PowerCLI files only
            ps1_files = locator.input_files("*.ps1")
            assert len(ps1_files) == 2

            # Find XML files only
            xml_files = locator.input_files("*.xml")
            assert len(xml_files) == 1


class TestReportDataLoader:
    """Tests for ReportDataLoader class."""

    def test_loader_loads_valid_json(self):
        """Test that loader correctly loads valid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value", "number": 42}, f)
            f.flush()

            try:
                loader = ReportDataLoader()
                data = loader.load_json(Path(f.name))

                assert data == {"key": "value", "number": 42}
            finally:
                Path(f.name).unlink()

    def test_loader_handles_invalid_json(self):
        """Test that loader returns empty dict for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()

            try:
                loader = ReportDataLoader()
                data = loader.load_json(Path(f.name))

                assert data == {}
            finally:
                Path(f.name).unlink()

    def test_loader_handles_missing_json_file(self):
        """Test that loader returns empty dict for missing file."""
        loader = ReportDataLoader()
        data = loader.load_json(Path("/nonexistent/file.json"))

        assert data == {}

    def test_loader_loads_valid_yaml(self):
        """Test that loader correctly loads valid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"key": "value", "list": [1, 2, 3]}, f)
            f.flush()

            try:
                loader = ReportDataLoader()
                data = loader.load_yaml(Path(f.name))

                assert data == {"key": "value", "list": [1, 2, 3]}
            finally:
                Path(f.name).unlink()

    def test_loader_handles_invalid_yaml(self):
        """Test that loader returns empty dict for invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid:\n  - yaml\n  that: doesn't: parse")
            f.flush()

            try:
                loader = ReportDataLoader()
                data = loader.load_yaml(Path(f.name))

                assert data == {}
            finally:
                Path(f.name).unlink()

    def test_loader_handles_missing_yaml_file(self):
        """Test that loader returns empty dict for missing YAML file."""
        loader = ReportDataLoader()
        data = loader.load_yaml(Path("/nonexistent/file.yaml"))

        assert data == {}

    def test_loader_loads_text_file(self):
        """Test that loader correctly loads text files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Markdown Title\n\nSome content here.")
            f.flush()

            try:
                loader = ReportDataLoader()
                content = loader.load_text(Path(f.name))

                assert "# Markdown Title" in content
                assert "Some content here." in content
            finally:
                Path(f.name).unlink()

    def test_loader_handles_missing_text_file(self):
        """Test that loader returns empty string for missing text file."""
        loader = ReportDataLoader()
        content = loader.load_text(Path("/nonexistent/file.md"))

        assert content == ""


class TestReportContextBuilder:
    """Tests for ReportContextBuilder class."""

    def test_builder_creates_basic_context(self):
        """Test that builder creates context with basic fields."""
        builder = ReportContextBuilder()
        context = builder.build(
            workspace_name="test-workspace",
            workspace_path="/path/to/workspace",
            profile="lab",
            profile_config={"namespace": "virt-lab"},
        )

        assert context["workspace"]["name"] == "test-workspace"
        assert context["workspace"]["path"] == "/path/to/workspace"
        assert context["profile"]["name"] == "lab"
        assert context["profile"]["config"] == {"namespace": "virt-lab"}
        assert "timestamp" in context["workspace"]

    def test_builder_includes_gaps_data(self):
        """Test that builder includes gaps data when provided."""
        gaps_data = {
            "summary": {
                "total_components": 5,
                "overall_assessment": "MOSTLY_SUPPORTED",
            },
            "components": [],
        }

        builder = ReportContextBuilder()
        context = builder.build(
            workspace_name="test",
            workspace_path="/test",
            profile="lab",
            profile_config={},
            gaps_data=gaps_data,
        )

        assert context["gaps"] == gaps_data
        assert context["summary"] == gaps_data["summary"]

    def test_builder_creates_fallback_summary_without_gaps(self):
        """Test that builder creates fallback summary when no gaps data."""
        builder = ReportContextBuilder()
        context = builder.build(
            workspace_name="test",
            workspace_path="/test",
            profile="lab",
            profile_config={},
            gaps_data=None,
        )

        assert context["summary"]["total_components"] == 0
        assert context["summary"]["overall_assessment"] == "UNKNOWN"
        assert context["summary"]["counts"] == {
            "SUPPORTED": 0,
            "PARTIAL": 0,
            "BLOCKED": 0,
            "MANUAL": 0,
        }

    def test_builder_includes_recommendations_data(self):
        """Test that builder includes recommendations data."""
        recommendations_data = {
            "recommendations": [
                {"component_name": "nsx-firewall", "owner": "Networking"},
                {"component_name": "load-balancer", "owner": "Infrastructure"},
            ]
        }

        builder = ReportContextBuilder()
        context = builder.build(
            workspace_name="test",
            workspace_path="/test",
            profile="lab",
            profile_config={},
            recommendations_data=recommendations_data,
        )

        assert context["recommendations"] == recommendations_data
        assert len(context["recommendations_by_component"]) == 2
        assert "nsx-firewall" in context["recommendations_by_component"]
        assert "load-balancer" in context["recommendations_by_component"]

    def test_builder_includes_questions_data(self):
        """Test that builder includes questions data and builds lookup."""
        questions_data = {
            "questions": [
                {"location": "script1.ps1:42", "question": "What is the network?"},
                {"location": "script1.ps1:42", "question": "What is the storage?"},
                {"location": "script2.ps1:10", "question": "What is the namespace?"},
            ]
        }

        builder = ReportContextBuilder()
        context = builder.build(
            workspace_name="test",
            workspace_path="/test",
            profile="lab",
            profile_config={},
            questions_data=questions_data,
        )

        assert context["questions"] == questions_data
        assert len(context["questions_by_location"]) == 2
        assert len(context["questions_by_location"]["script1.ps1:42"]) == 2
        assert len(context["questions_by_location"]["script2.ps1:10"]) == 1

    def test_builder_handles_empty_optional_data(self):
        """Test that builder handles all optional data being None."""
        builder = ReportContextBuilder()
        context = builder.build(
            workspace_name="test",
            workspace_path="/test",
            profile="lab",
            profile_config={},
        )

        assert context["gaps"] is None
        assert context["recommendations"] is None
        assert context["decisions"] is None
        assert context["questions"] is None
        assert context["intent"] is None
        assert context["sources"] == []
        assert context["assumptions_md"] is None
        assert context["conflicts_md"] is None
        assert context["artifacts"] == {}
        assert context["questions_by_location"] == {}
        assert context["recommendations_by_component"] == {}

    def test_builder_includes_all_data_types(self):
        """Test that builder correctly includes all data types."""
        builder = ReportContextBuilder()
        context = builder.build(
            workspace_name="comprehensive-test",
            workspace_path="/comprehensive",
            profile="prod",
            profile_config={"namespace": "virt-prod"},
            gaps_data={"summary": {}},
            recommendations_data={"recommendations": []},
            decisions_data={"decisions": []},
            questions_data={"questions": []},
            intent_data={"inputs": []},
            sources=[{"name": "script.ps1"}],
            assumptions_md="# Assumptions",
            conflicts_md="# Conflicts",
            artifacts={"kubevirt": True},
            executive_summary="All good",
            consolidated_supported=[],
        )

        # Verify all fields are present
        assert context["workspace"]["name"] == "comprehensive-test"
        assert context["profile"]["name"] == "prod"
        assert context["gaps"] is not None
        assert context["recommendations"] is not None
        assert context["decisions"] is not None
        assert context["questions"] is not None
        assert context["intent"] is not None
        assert len(context["sources"]) == 1
        assert context["assumptions_md"] == "# Assumptions"
        assert context["conflicts_md"] == "# Conflicts"
        assert context["artifacts"]["kubevirt"] is True
        assert context["executive_summary"] == "All good"
        assert context["consolidated_supported"] == []
