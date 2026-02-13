"""
Tests for automatic path selection in generate command.

Validates auto-detection logic for Direct Translation vs Intent-Based generation.
"""

from unittest.mock import patch

import pytest

from ops_translate.workspace import Workspace


class TestAutomaticPathSelection:
    """Test automatic path selection in generate_all()."""

    def test_auto_select_direct_translation_with_powercli(self, tmp_path):
        """Test auto-selection of direct translation when PowerCLI files exist."""
        # Setup workspace with PowerCLI file
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        powercli_dir = workspace_dir / "input/powercli"
        powercli_dir.mkdir(parents=True)
        (powercli_dir / "test.ps1").write_text("New-VM -Name Test")

        # Create workspace config
        config_file = workspace_dir / "ops-translate.yaml"
        config_file.write_text(
            """
llm:
  provider: mock
profiles:
  lab:
    default_namespace: test-ns
    default_network: test-net
    default_storage_class: test-storage
"""
        )

        workspace = Workspace(workspace_dir)

        # Mock the generate functions
        with patch("ops_translate.generate.generator.generate_with_templates") as mock_templates:
            from ops_translate.generate.generator import generate_all

            # Call generate_all - should auto-select direct translation
            generate_all(workspace, "lab", use_ai=False, output_format="yaml")

            # Verify generate_with_templates was called
            assert mock_templates.called
            # Verify translation_profile was auto-created (not None)
            # translation_profile is the 5th positional arg (index 4)
            call_args = mock_templates.call_args
            assert call_args[0][4] is not None  # translation_profile at position 4

    def test_auto_select_direct_translation_with_vrealize(self, tmp_path):
        """Test auto-selection of direct translation when vRealize files exist."""
        # Setup workspace with vRealize file
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        vrealize_dir = workspace_dir / "input/vrealize"
        vrealize_dir.mkdir(parents=True)
        (vrealize_dir / "test.xml").write_text("<workflow/>")

        # Create workspace config
        config_file = workspace_dir / "ops-translate.yaml"
        config_file.write_text(
            """
llm:
  provider: mock
profiles:
  lab:
    default_namespace: test-ns
    default_network: test-net
    default_storage_class: test-storage
"""
        )

        workspace = Workspace(workspace_dir)

        # Mock the generate functions
        with patch("ops_translate.generate.generator.generate_with_templates") as mock_templates:
            from ops_translate.generate.generator import generate_all

            # Call generate_all - should auto-select direct translation
            generate_all(workspace, "lab", use_ai=False, output_format="yaml")

            # Verify generate_with_templates was called with auto-generated profile
            assert mock_templates.called
            call_args = mock_templates.call_args
            # translation_profile is the 5th positional arg (index 4)
            assert call_args[0][4] is not None  # translation_profile at position 4

    def test_use_intent_when_exists(self, tmp_path):
        """Test that intent.yaml takes priority when it exists."""
        # Setup workspace with both PowerCLI and intent.yaml
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        powercli_dir = workspace_dir / "input/powercli"
        powercli_dir.mkdir(parents=True)
        (powercli_dir / "test.ps1").write_text("New-VM -Name Test")

        intent_dir = workspace_dir / "intent"
        intent_dir.mkdir()
        (intent_dir / "intent.yaml").write_text("type: powercli")

        # Create workspace config
        config_file = workspace_dir / "ops-translate.yaml"
        config_file.write_text(
            """
llm:
  provider: mock
profiles:
  lab:
    default_namespace: test-ns
    default_network: test-net
    default_storage_class: test-storage
"""
        )

        workspace = Workspace(workspace_dir)

        # Mock the generate functions
        with patch("ops_translate.generate.generator.generate_with_templates") as mock_templates:
            from ops_translate.generate.generator import generate_all

            # Call generate_all - should use intent-based generation
            generate_all(workspace, "lab", use_ai=False, output_format="yaml")

            # Verify generate_with_templates was called
            # In intent-based mode, translation_profile might be None or passed through
            assert mock_templates.called

    def test_error_when_no_files(self, tmp_path):
        """Test that helpful error is shown when no files exist."""
        # Setup empty workspace
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / "input/powercli").mkdir(parents=True)
        (workspace_dir / "input/vrealize").mkdir(parents=True)

        # Create workspace config
        config_file = workspace_dir / "ops-translate.yaml"
        config_file.write_text(
            """
llm:
  provider: mock
profiles:
  lab:
    default_namespace: test-ns
    default_network: test-net
    default_storage_class: test-storage
"""
        )

        workspace = Workspace(workspace_dir)

        # Should raise typer.Exit
        import typer

        from ops_translate.generate.generator import generate_all

        with pytest.raises(typer.Exit):
            generate_all(workspace, "lab", use_ai=False, output_format="yaml")

    def test_create_minimal_translation_profile(self, tmp_path):
        """Test helper function for creating minimal profile."""
        # Setup workspace
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        # Create workspace config
        config_file = workspace_dir / "ops-translate.yaml"
        config_file.write_text(
            """
llm:
  provider: mock
profiles:
  lab:
    default_namespace: virt-lab
    default_network: lab-net
    default_storage_class: nfs
    openshift_api_url: https://api.lab.example.com:6443
"""
        )

        workspace = Workspace(workspace_dir)

        from ops_translate.generate.generator import _create_minimal_translation_profile

        # Create minimal profile
        profile = _create_minimal_translation_profile(workspace, "lab")

        # Verify profile structure
        assert profile.name == "lab"
        assert "lab" in profile.environments
        assert profile.environments["lab"].namespace == "virt-lab"
        assert profile.environments["lab"].openshift_api_url == "https://api.lab.example.com:6443"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
