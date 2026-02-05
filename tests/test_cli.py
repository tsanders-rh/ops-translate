"""
Tests for CLI commands.
"""

from unittest.mock import patch

from typer.testing import CliRunner

from ops_translate.cli import app

runner = CliRunner()


class TestInit:
    """Tests for init command."""

    def test_init_creates_workspace(self, tmp_path):
        """Test that init creates workspace structure."""
        workspace_dir = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", str(workspace_dir)])

        assert result.exit_code == 0
        assert workspace_dir.exists()
        assert (workspace_dir / "ops-translate.yaml").exists()
        assert (workspace_dir / "input" / "powercli").exists()
        assert (workspace_dir / "input" / "vrealize").exists()
        assert (workspace_dir / "intent").exists()
        assert (workspace_dir / "output").exists()

    def test_init_shows_next_steps(self, tmp_path):
        """Test that init shows helpful next steps."""
        workspace_dir = tmp_path / "test-workspace"

        result = runner.invoke(app, ["init", str(workspace_dir)])

        assert "Next steps:" in result.stdout
        assert "ops-translate import" in result.stdout


class TestImport:
    """Tests for import command."""

    def test_import_powercli_file(self, tmp_path):
        """Test importing a PowerCLI script."""
        # Setup workspace
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create test script
        test_script = tmp_path / "test.ps1"
        test_script.write_text("param([string]$VMName)\nNew-VM -Name $VMName")

        # Change to workspace directory
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app,
                ["import", "--source", "powercli", "--file", str(test_script)],
            )

            assert result.exit_code == 0
            assert "Imported to input/powercli/test.ps1" in result.stdout
            assert (workspace / "input" / "powercli" / "test.ps1").exists()
        finally:
            os.chdir(original_dir)

    def test_import_vrealize_file(self, tmp_path):
        """Test importing a vRealize workflow."""
        # Setup workspace
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create test workflow
        test_workflow = tmp_path / "test.workflow.xml"
        test_workflow.write_text("<?xml version='1.0'?><workflow></workflow>")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app,
                ["import", "--source", "vrealize", "--file", str(test_workflow)],
            )

            assert result.exit_code == 0
            assert (workspace / "input" / "vrealize" / "test.workflow.xml").exists()
        finally:
            os.chdir(original_dir)

    def test_import_invalid_source(self, tmp_path):
        """Test import with invalid source type."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app,
                ["import", "--source", "invalid", "--file", str(test_file)],
            )

            assert result.exit_code == 1
            # Check for new error message format
            assert "Invalid source type" in result.stdout
            assert "powercli" in result.stdout
            assert "vrealize" in result.stdout
        finally:
            os.chdir(original_dir)

    def test_import_nonexistent_file(self, tmp_path):
        """Test import with nonexistent file."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app,
                ["import", "--source", "powercli", "--file", "/nonexistent/file.ps1"],
            )

            assert result.exit_code == 1
            assert "File not found" in result.stdout
        finally:
            os.chdir(original_dir)

    def test_import_outside_workspace(self, tmp_path):
        """Test import outside workspace directory."""
        test_file = tmp_path / "test.ps1"
        test_file.write_text("test")

        result = runner.invoke(
            app,
            ["import", "--source", "powercli", "--file", str(test_file)],
        )

        assert result.exit_code == 1
        # Check for new error message format
        assert "workspace" in result.stdout.lower()
        assert "init" in result.stdout


class TestSummarize:
    """Tests for summarize command."""

    def test_summarize_powercli_file(self, tmp_path):
        """Test summarizing PowerCLI scripts."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create test script with detectable features
        test_script = workspace / "input" / "powercli" / "test.ps1"
        test_script.write_text("""
param(
    [Parameter(Mandatory=$true)][ValidateSet("dev","prod")][string]$Env
)
$Network = if ($Env -eq "prod") { "prod-net" } else { "dev-net" }
New-TagAssignment -Tag "env:$Env"
""")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["summarize"])

            assert result.exit_code == 0
            assert "Summary written to intent/summary.md" in result.stdout
            assert (workspace / "intent" / "summary.md").exists()

            # Check summary content
            summary = (workspace / "intent" / "summary.md").read_text()
            assert "PowerCLI Scripts" in summary
        finally:
            os.chdir(original_dir)


class TestIntentExtract:
    """Tests for intent extract command."""

    @patch("ops_translate.intent.extract.extract_all")
    def test_intent_extract(self, mock_extract, tmp_path):
        """Test intent extraction command."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["intent", "extract"])

            assert result.exit_code == 0
            assert mock_extract.called
            assert "Intent extracted" in result.stdout
        finally:
            os.chdir(original_dir)


class TestIntentMerge:
    """Tests for intent merge command."""

    @patch("ops_translate.intent.merge.merge_intents")
    def test_intent_merge_no_conflicts(self, mock_merge, tmp_path):
        """Test merging without conflicts."""
        mock_merge.return_value = []  # No conflicts

        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["intent", "merge"])

            assert result.exit_code == 0
            assert "Merged intent written" in result.stdout
        finally:
            os.chdir(original_dir)

    @patch("ops_translate.intent.merge.merge_intents")
    def test_intent_merge_with_conflicts(self, mock_merge, tmp_path):
        """Test merging with conflicts."""
        mock_merge.return_value = ["Conflict 1", "Conflict 2"]

        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["intent", "merge"])

            assert result.exit_code == 1
            assert "Conflicts detected" in result.stdout
        finally:
            os.chdir(original_dir)

    @patch("ops_translate.intent.merge.merge_intents")
    def test_intent_merge_force(self, mock_merge, tmp_path):
        """Test forced merge with conflicts."""
        mock_merge.return_value = ["Conflict"]

        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["intent", "merge", "--force"])

            assert result.exit_code == 0
            assert "Conflicts detected but merged" in result.stdout
        finally:
            os.chdir(original_dir)


class TestIntentEdit:
    """Tests for intent edit command."""

    @patch.dict("os.environ", {"EDITOR": "echo"})
    def test_intent_edit_default_file(self, tmp_path):
        """Test editing default intent file."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create intent file
        intent_file = workspace / "intent" / "intent.yaml"
        intent_file.write_text("test: content")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["intent", "edit"])

            # Should attempt to open editor
            assert result.exit_code == 0
        finally:
            os.chdir(original_dir)

    def test_intent_edit_no_editor(self, tmp_path):
        """Test edit without EDITOR set."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        intent_file = workspace / "intent" / "intent.yaml"
        intent_file.write_text("test: content")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            # Unset EDITOR
            with patch.dict("os.environ", {"EDITOR": ""}, clear=True):
                result = runner.invoke(app, ["intent", "edit"])

                assert result.exit_code == 0
                assert "$EDITOR not set" in result.stdout
        finally:
            os.chdir(original_dir)


class TestMapPreview:
    """Tests for map preview command."""

    def test_map_preview_openshift(self, tmp_path):
        """Test generating mapping preview."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["map", "preview", "--target", "openshift"])

            assert result.exit_code == 0
            assert "Mapping preview written" in result.stdout
            assert (workspace / "mapping" / "preview.md").exists()
        finally:
            os.chdir(original_dir)

    def test_map_preview_invalid_target(self, tmp_path):
        """Test with invalid target."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["map", "preview", "--target", "invalid"])

            assert result.exit_code == 1
            assert "Only 'openshift' target is supported" in result.stdout
        finally:
            os.chdir(original_dir)


class TestGenerate:
    """Tests for generate command."""

    @patch("ops_translate.generate.generate_all")
    def test_generate_with_ai(self, mock_generate, tmp_path):
        """Test generation with AI assistance."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["generate", "--profile", "lab"])

            assert result.exit_code == 0
            assert mock_generate.called
            # Check that use_ai=True was passed
            call_args = mock_generate.call_args
            assert call_args[1]["use_ai"] is True
        finally:
            os.chdir(original_dir)

    @patch("ops_translate.generate.generate_all")
    def test_generate_no_ai(self, mock_generate, tmp_path):
        """Test template-based generation."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["generate", "--profile", "lab", "--no-ai"])

            assert result.exit_code == 0
            assert mock_generate.called
            # Check that use_ai=False was passed
            call_args = mock_generate.call_args
            assert call_args[1]["use_ai"] is False
        finally:
            os.chdir(original_dir)

    def test_generate_invalid_profile(self, tmp_path):
        """Test with invalid profile."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["generate", "--profile", "nonexistent"])

            assert result.exit_code == 1
            assert "Profile 'nonexistent' not found" in result.stdout
        finally:
            os.chdir(original_dir)


class TestDryRun:
    """Tests for dry-run command."""

    def test_dry_run_success(self, tmp_path):
        """Test successful validation with enhanced dry-run."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create valid intent file
        intent_file = workspace / "intent" / "intent.yaml"
        intent_data = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "test_workflow",
                "workload_type": "virtual_machine",
                "inputs": {"vm_name": {"type": "string", "required": True}},
            },
        }
        import yaml

        intent_file.write_text(yaml.dump(intent_data))

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["dry-run"])

            # Enhanced dry-run should show execution plan
            assert "Execution Plan" in result.stdout or "Summary" in result.stdout
            # Should be safe to proceed
            assert result.exit_code == 0
        finally:
            os.chdir(original_dir)

    @patch("ops_translate.intent.validate.validate_intent")
    def test_dry_run_invalid_intent(self, mock_intent, tmp_path):
        """Test with invalid intent schema."""
        mock_intent.return_value = (False, ["Schema error 1", "Schema error 2"])

        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        intent_file = workspace / "intent" / "intent.yaml"
        intent_file.write_text("invalid: yaml")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["dry-run"])

            # Should fail on schema validation
            assert result.exit_code == 1
            assert "Schema error" in result.stdout
        finally:
            os.chdir(original_dir)

    def test_dry_run_no_intent_file(self, tmp_path):
        """Test without intent file."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["dry-run"])

            # Should report missing intent file as blocking issue
            assert result.exit_code == 1
            assert "Intent file not found" in result.stdout or "BLOCKING" in result.stdout
        finally:
            os.chdir(original_dir)
