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
            assert "✓ Imported 1 file(s) to input/powercli/" in result.stdout
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

    def test_import_powercli_directory(self, tmp_path):
        """Test importing multiple PowerCLI scripts from directory."""
        # Setup workspace
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create directory with multiple PowerCLI scripts
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "create_vm.ps1").write_text("New-VM -Name test")
        (scripts_dir / "delete_vm.ps1").write_text("Remove-VM -Name test")
        (scripts_dir / "modify_vm.ps1").write_text("Set-VM -Name test")

        # Change to workspace directory
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app,
                ["import", "--source", "powercli", "--file", str(scripts_dir)],
            )

            assert result.exit_code == 0
            assert "Importing 3 powercli files" in result.stdout
            assert (workspace / "input" / "powercli" / "create_vm.ps1").exists()
            assert (workspace / "input" / "powercli" / "delete_vm.ps1").exists()
            assert (workspace / "input" / "powercli" / "modify_vm.ps1").exists()
        finally:
            os.chdir(original_dir)

    def test_import_vrealize_directory(self, tmp_path):
        """Test importing multiple vRealize workflows from directory."""
        # Setup workspace
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create directory with multiple workflows
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "workflow1.xml").write_text(
            "<?xml version='1.0'?><workflow name='w1'></workflow>"
        )
        (workflows_dir / "workflow2.xml").write_text(
            "<?xml version='1.0'?><workflow name='w2'></workflow>"
        )

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app,
                ["import", "--source", "vrealize", "--file", str(workflows_dir)],
            )

            assert result.exit_code == 0
            assert "Importing 2 vrealize files" in result.stdout
            assert (workspace / "input" / "vrealize" / "workflow1.xml").exists()
            assert (workspace / "input" / "vrealize" / "workflow2.xml").exists()
        finally:
            os.chdir(original_dir)

    def test_import_directory_empty(self, tmp_path):
        """Test importing from empty directory."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app,
                ["import", "--source", "powercli", "--file", str(empty_dir)],
            )

            assert result.exit_code == 0
            assert "No *.ps1 files found" in result.stdout
        finally:
            os.chdir(original_dir)

    def test_import_directory_with_duplicates(self, tmp_path):
        """Test importing directory with already imported files."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create directory with scripts
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.ps1").write_text("New-VM -Name test")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            # Import once
            result1 = runner.invoke(
                app,
                ["import", "--source", "powercli", "--file", str(scripts_dir)],
            )
            assert result1.exit_code == 0

            # Import again - should skip
            result2 = runner.invoke(
                app,
                ["import", "--source", "powercli", "--file", str(scripts_dir)],
            )
            assert result2.exit_code == 0
            assert "already imported, skipping" in result2.stdout
        finally:
            os.chdir(original_dir)

    def test_import_directory_mixed_files(self, tmp_path):
        """Test importing directory with mixed file types."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create directory with mixed files
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        (mixed_dir / "script.ps1").write_text("New-VM")
        (mixed_dir / "readme.txt").write_text("Documentation")
        (mixed_dir / "config.xml").write_text("<config/>")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            # Import with powercli source - should only get .ps1
            result = runner.invoke(
                app,
                ["import", "--source", "powercli", "--file", str(mixed_dir)],
            )

            assert result.exit_code == 0
            assert "Importing powercli file: script.ps1" in result.stdout
            assert (workspace / "input" / "powercli" / "script.ps1").exists()
            assert not (workspace / "input" / "powercli" / "readme.txt").exists()
            assert not (workspace / "input" / "powercli" / "config.xml").exists()
        finally:
            os.chdir(original_dir)

    def test_import_auto_detect_powercli_file(self, tmp_path):
        """Test auto-detecting PowerCLI file without --source."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create test script
        test_script = tmp_path / "test.ps1"
        test_script.write_text("New-VM -Name test")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["import", "--file", str(test_script)])

            assert result.exit_code == 0
            assert "✓ Imported 1 file(s) to input/powercli/" in result.stdout
            assert (workspace / "input" / "powercli" / "test.ps1").exists()
        finally:
            os.chdir(original_dir)

    def test_import_auto_detect_vrealize_file(self, tmp_path):
        """Test auto-detecting vRealize file without --source."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create test workflow
        test_workflow = tmp_path / "workflow.xml"
        test_workflow.write_text("<?xml version='1.0'?><workflow></workflow>")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["import", "--file", str(test_workflow)])

            assert result.exit_code == 0
            assert (workspace / "input" / "vrealize" / "workflow.xml").exists()
        finally:
            os.chdir(original_dir)

    def test_import_auto_detect_mixed_directory(self, tmp_path):
        """Test auto-detecting both PowerCLI and vRealize files from directory."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create directory with both types
        mixed_dir = tmp_path / "mixed"
        mixed_dir.mkdir()
        (mixed_dir / "script1.ps1").write_text("New-VM")
        (mixed_dir / "script2.ps1").write_text("Remove-VM")
        (mixed_dir / "workflow1.xml").write_text("<workflow/>")
        (mixed_dir / "readme.txt").write_text("Documentation")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["import", "--file", str(mixed_dir)])

            assert result.exit_code == 0
            assert "Auto-detecting" in result.stdout
            assert "PowerCLI scripts (2 files)" in result.stdout
            assert "vRealize workflows (1 files)" in result.stdout
            assert (workspace / "input" / "powercli" / "script1.ps1").exists()
            assert (workspace / "input" / "powercli" / "script2.ps1").exists()
            assert (workspace / "input" / "vrealize" / "workflow1.xml").exists()
            assert not (workspace / "input" / "powercli" / "readme.txt").exists()
        finally:
            os.chdir(original_dir)

    def test_import_auto_detect_unsupported_file(self, tmp_path):
        """Test auto-detecting file with unsupported extension."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        # Create file with unsupported extension
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["import", "--file", str(test_file)])

            assert result.exit_code == 1
            assert "Cannot auto-detect file type" in result.stdout
        finally:
            os.chdir(original_dir)


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

    @patch("ops_translate.generate.generate_all")
    def test_generate_assume_existing_vms_flag(self, mock_generate, tmp_path):
        """Test generation with --assume-existing-vms flag (MTV mode)."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(
                app, ["generate", "--profile", "lab", "--no-ai", "--assume-existing-vms"]
            )

            assert result.exit_code == 0
            assert mock_generate.called
            # Check that assume_existing_vms=True was passed
            call_args = mock_generate.call_args
            assert call_args[1]["assume_existing_vms"] is True
            # Should show MTV mode in output
            assert "MTV mode" in result.stdout
        finally:
            os.chdir(original_dir)

    @patch("ops_translate.generate.generate_all")
    def test_generate_greenfield_mode(self, mock_generate, tmp_path):
        """Test generation without --assume-existing-vms (greenfield mode)."""
        workspace = tmp_path / "workspace"
        runner.invoke(app, ["init", str(workspace)])

        import os

        original_dir = os.getcwd()
        try:
            os.chdir(workspace)

            result = runner.invoke(app, ["generate", "--profile", "lab", "--no-ai"])

            assert result.exit_code == 0
            assert mock_generate.called
            # Check that assume_existing_vms=False was passed
            call_args = mock_generate.call_args
            assert call_args[1]["assume_existing_vms"] is False
            # Should show greenfield in output
            assert "greenfield" in result.stdout
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
