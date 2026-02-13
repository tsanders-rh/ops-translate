"""
Tests for Ansible role skeleton generation.

Validates role generation from vRealize workflows and PowerCLI scripts.
"""

from pathlib import Path

import pytest

from ops_translate.generate.ansible_project import (
    _create_fallback_role,
    _extract_powercli_metadata,
    _extract_vrealize_metadata,
    _generate_defaults_main,
    _generate_powercli_role,
    _generate_role_meta,
    _generate_role_readme,
    _generate_tasks_main,
    _generate_vrealize_role,
    _generate_workflow_roles,
    generate_ansible_project,
)
from ops_translate.intent.profile import load_profile


class TestVRealizeRoleGeneration:
    """Test role generation from vRealize workflows."""

    def test_generate_vrealize_role_structure(self, tmp_path):
        """Verify role directory structure for vRealize workflow."""
        # Use existing fixture
        workflow_file = Path(__file__).parent / "fixtures/vrealize/simple-workflow.xml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        workflow = {
            "name": "simple_workflow",
            "source": "vrealize",
            "source_file": "input/vrealize/simple-workflow.xml",
        }

        _generate_vrealize_role(workflow, workflow_file, project_dir)

        # Verify directory structure
        role_dir = project_dir / "roles" / "simple_workflow"
        assert role_dir.exists()
        assert (role_dir / "tasks").exists()
        assert (role_dir / "tasks" / "main.yml").exists()
        assert (role_dir / "defaults").exists()
        assert (role_dir / "defaults" / "main.yml").exists()
        assert (role_dir / "meta").exists()
        assert (role_dir / "meta" / "main.yml").exists()
        assert (role_dir / "README.md").exists()

    def test_extract_vrealize_metadata(self):
        """Test metadata extraction from vRealize workflow XML."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/simple-workflow.xml"

        metadata = _extract_vrealize_metadata(workflow_file)

        assert "display_name" in metadata
        assert "description" in metadata
        assert "inputs" in metadata
        assert metadata["source_type"] == "vRealize Orchestrator Workflow"
        assert isinstance(metadata["inputs"], list)

    def test_tasks_main_contains_vrealize_metadata(self, tmp_path):
        """Verify tasks/main.yml includes vRealize input documentation."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/simple-workflow.xml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        workflow = {
            "name": "simple_workflow",
            "source": "vrealize",
            "source_file": "input/vrealize/simple-workflow.xml",
        }

        _generate_vrealize_role(workflow, workflow_file, project_dir)

        tasks_file = project_dir / "roles" / "simple_workflow" / "tasks" / "main.yml"
        tasks_content = tasks_file.read_text()

        # Should contain metadata header
        assert "# Ansible role: simple_workflow" in tasks_content
        assert "# Source: vRealize Orchestrator Workflow" in tasks_content
        assert "# Original: input/vrealize/simple-workflow.xml" in tasks_content
        assert "# Inputs:" in tasks_content
        assert "# TODO: Implement workflow logic" in tasks_content

    def test_defaults_generated_from_vrealize_inputs(self, tmp_path):
        """Verify defaults/main.yml generated from vRealize workflow inputs."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/simple-workflow.xml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        workflow = {
            "name": "simple_workflow",
            "source": "vrealize",
            "source_file": "input/vrealize/simple-workflow.xml",
        }

        _generate_vrealize_role(workflow, workflow_file, project_dir)

        defaults_file = project_dir / "roles" / "simple_workflow" / "defaults" / "main.yml"
        defaults_content = defaults_file.read_text()

        # Should contain auto-generated header
        assert "# Default variables for simple_workflow" in defaults_content
        assert "# Auto-generated from workflow inputs/parameters" in defaults_content


class TestPowerCLIRoleGeneration:
    """Test role generation from PowerCLI scripts."""

    def test_generate_powercli_role_structure(self, tmp_path):
        """Verify role directory structure for PowerCLI script."""
        # Use existing fixture
        script_file = Path(__file__).parent / "fixtures/powercli/simple-vm.ps1"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        workflow = {
            "name": "simple_vm",
            "source": "powercli",
            "source_file": "input/powercli/simple-vm.ps1",
        }

        _generate_powercli_role(workflow, script_file, project_dir)

        # Verify directory structure
        role_dir = project_dir / "roles" / "simple_vm"
        assert role_dir.exists()
        assert (role_dir / "tasks").exists()
        assert (role_dir / "tasks" / "main.yml").exists()
        assert (role_dir / "defaults").exists()
        assert (role_dir / "defaults" / "main.yml").exists()
        assert (role_dir / "meta").exists()
        assert (role_dir / "meta" / "main.yml").exists()
        assert (role_dir / "README.md").exists()

    def test_extract_powercli_metadata(self):
        """Test metadata extraction from PowerCLI script."""
        script_file = Path(__file__).parent / "fixtures/powercli/simple-vm.ps1"

        metadata = _extract_powercli_metadata(script_file)

        assert "display_name" in metadata
        assert "description" in metadata
        assert "parameters" in metadata
        assert metadata["source_type"] == "PowerCLI Script"
        assert isinstance(metadata["parameters"], list)

    def test_tasks_main_contains_powercli_metadata(self, tmp_path):
        """Verify tasks/main.yml contains translated PowerCLI tasks."""
        script_file = Path(__file__).parent / "fixtures/powercli/simple-vm.ps1"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        workflow = {
            "name": "simple_vm",
            "source": "powercli",
            "source_file": "input/powercli/simple-vm.ps1",
        }

        _generate_powercli_role(workflow, script_file, project_dir)

        tasks_file = project_dir / "roles" / "simple_vm" / "tasks" / "main.yml"
        tasks_content = tasks_file.read_text()

        # Should contain translated Ansible tasks, not placeholder comments
        assert "ansible.builtin.set_fact" in tasks_content
        assert "kubevirt.core.kubevirt_vm" in tasks_content or "TODO" in tasks_content

    def test_defaults_generated_from_powercli_parameters(self, tmp_path):
        """Verify defaults/main.yml generated from PowerCLI parameters."""
        script_file = Path(__file__).parent / "fixtures/powercli/simple-vm.ps1"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        workflow = {
            "name": "simple_vm",
            "source": "powercli",
            "source_file": "input/powercli/simple-vm.ps1",
        }

        _generate_powercli_role(workflow, script_file, project_dir)

        defaults_file = project_dir / "roles" / "simple_vm" / "defaults" / "main.yml"
        defaults_content = defaults_file.read_text()

        # Should contain auto-generated header
        assert "# Default variables for simple_vm" in defaults_content
        assert "# Auto-generated from workflow inputs/parameters" in defaults_content


class TestRoleFileGeneration:
    """Test individual role file generation functions."""

    def test_generate_tasks_main(self, tmp_path):
        """Test tasks/main.yml generation."""
        role_dir = tmp_path / "test_role"
        (role_dir / "tasks").mkdir(parents=True)

        metadata = {
            "source_type": "vRealize Orchestrator Workflow",
            "inputs": [
                {"name": "vm_name", "type": "string"},
                {"name": "cpu_count", "type": "number"},
            ],
        }

        workflow = {"source_file": "test.xml"}

        _generate_tasks_main(role_dir, "test_role", metadata, workflow)

        tasks_file = role_dir / "tasks" / "main.yml"
        assert tasks_file.exists()
        content = tasks_file.read_text()

        assert "# Ansible role: test_role" in content
        assert "vm_name: string" in content
        assert "cpu_count: number" in content
        assert "ansible.builtin.debug" in content

    def test_generate_defaults_main(self, tmp_path):
        """Test defaults/main.yml generation."""
        role_dir = tmp_path / "test_role"
        (role_dir / "defaults").mkdir(parents=True)

        metadata = {
            "inputs": [
                {"name": "vm_name", "type": "string"},
                {"name": "cpu_count", "type": "number"},
            ]
        }

        _generate_defaults_main(role_dir, "test_role", metadata)

        defaults_file = role_dir / "defaults" / "main.yml"
        assert defaults_file.exists()
        content = defaults_file.read_text()

        assert "vm_name:" in content
        assert "cpu_count:" in content

    def test_generate_role_readme(self, tmp_path):
        """Test README.md generation."""
        role_dir = tmp_path / "test_role"
        role_dir.mkdir()

        metadata = {
            "description": "Test role description",
            "source_type": "vRealize Orchestrator Workflow",
            "inputs": [
                {"name": "vm_name", "type": "string"},
            ],
        }

        workflow = {"source_file": "test.xml"}

        _generate_role_readme(role_dir, "test_role", metadata, workflow)

        readme_file = role_dir / "README.md"
        assert readme_file.exists()
        content = readme_file.read_text()

        assert "# Role: test_role" in content
        assert "Test role description" in content
        assert "vm_name" in content
        assert "Implementation Status" in content
        assert "Skeleton Only" in content

    def test_generate_role_meta(self, tmp_path):
        """Test meta/main.yml generation."""
        role_dir = tmp_path / "test_role"
        (role_dir / "meta").mkdir(parents=True)

        metadata = {"description": "Test role for Ansible Galaxy"}

        _generate_role_meta(role_dir, "test_role", metadata)

        meta_file = role_dir / "meta" / "main.yml"
        assert meta_file.exists()
        content = meta_file.read_text()

        assert "role_name: test_role" in content
        assert "author: ops-translate" in content
        assert "Test role for Ansible Galaxy" in content
        assert "license: MIT" in content


class TestIdempotentGeneration:
    """Test idempotent role generation."""

    def test_idempotent_regeneration(self, tmp_path):
        """Test re-running produces identical output."""
        workflow_file = Path(__file__).parent / "fixtures/vrealize/simple-workflow.xml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        workflow = {
            "name": "simple_workflow",
            "source": "vrealize",
            "source_file": "input/vrealize/simple-workflow.xml",
        }

        # Generate first time
        _generate_vrealize_role(workflow, workflow_file, project_dir)
        tasks_content_1 = (
            project_dir / "roles" / "simple_workflow" / "tasks" / "main.yml"
        ).read_text()

        # Generate second time (should overwrite)
        _generate_vrealize_role(workflow, workflow_file, project_dir)
        tasks_content_2 = (
            project_dir / "roles" / "simple_workflow" / "tasks" / "main.yml"
        ).read_text()

        # Should be identical
        assert tasks_content_1 == tasks_content_2


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_create_fallback_role(self, tmp_path):
        """Test fallback role creation when metadata extraction fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        _create_fallback_role("failed_role", project_dir)

        role_dir = project_dir / "roles" / "failed_role"
        assert role_dir.exists()
        assert (role_dir / "tasks").exists()
        assert (role_dir / "tasks" / "main.yml").exists()

        tasks_content = (role_dir / "tasks" / "main.yml").read_text()
        assert "Role generation failed" in tasks_content
        assert "Placeholder" in tasks_content

    def test_workflow_roles_graceful_degradation(self, tmp_path):
        """Test graceful degradation when role generation fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create workspace with invalid workflow file
        workspace_root = tmp_path
        invalid_file = workspace_root / "input/vrealize/invalid.xml"
        invalid_file.parent.mkdir(parents=True)
        invalid_file.write_text("<invalid>not a valid workflow</invalid>")

        workflows = [
            {
                "name": "invalid_workflow",
                "source": "vrealize",
                "source_file": "input/vrealize/invalid.xml",
            }
        ]

        # Load a minimal profile for the test
        from ops_translate.models.profile import ProfileSchema, EnvironmentConfig

        profile = ProfileSchema(
            name="test",
            environments={"test": EnvironmentConfig(openshift_api_url="https://test.com")},
        )

        # Should not raise, but create fallback
        _generate_workflow_roles(workflows, output_dir, project_dir, profile)

        # Fallback role should exist
        role_dir = project_dir / "roles" / "invalid_workflow"
        assert role_dir.exists()


class TestEndToEndRoleGeneration:
    """Test end-to-end role generation with full project."""

    def test_e2e_role_generation_with_vrealize(self, tmp_path):
        """Test full project generation includes vRealize role."""
        # Setup workspace - source files in tmp_path (output_dir.parent)
        workflow_src = Path(__file__).parent / "fixtures/vrealize/simple-workflow.xml"
        workflow_dst = tmp_path / "input/vrealize/simple-workflow.xml"
        workflow_dst.parent.mkdir(parents=True)

        # Copy fixture
        import shutil

        shutil.copy(workflow_src, workflow_dst)

        # Load profile
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [
            {
                "name": "simple_workflow",
                "source": "vrealize",
                "source_file": "input/vrealize/simple-workflow.xml",
            }
        ]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Verify role was generated
        role_dir = project_dir / "roles" / "simple_workflow"
        assert role_dir.exists()
        assert (role_dir / "tasks" / "main.yml").exists()
        assert (role_dir / "defaults" / "main.yml").exists()
        assert (role_dir / "README.md").exists()
        assert (role_dir / "meta" / "main.yml").exists()

    def test_e2e_role_generation_with_powercli(self, tmp_path):
        """Test full project generation includes PowerCLI role."""
        # Setup workspace - source files in tmp_path (output_dir.parent)
        script_src = Path(__file__).parent / "fixtures/powercli/simple-vm.ps1"
        script_dst = tmp_path / "input/powercli/simple-vm.ps1"
        script_dst.parent.mkdir(parents=True)

        # Copy fixture
        import shutil

        shutil.copy(script_src, script_dst)

        # Load profile
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [
            {
                "name": "simple_vm",
                "source": "powercli",
                "source_file": "input/powercli/simple-vm.ps1",
            }
        ]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Verify role was generated
        role_dir = project_dir / "roles" / "simple_vm"
        assert role_dir.exists()
        assert (role_dir / "tasks" / "main.yml").exists()
        assert (role_dir / "defaults" / "main.yml").exists()
        assert (role_dir / "README.md").exists()
        assert (role_dir / "meta" / "main.yml").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
