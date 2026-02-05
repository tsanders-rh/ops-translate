"""
Tests for template loading and rendering.
"""

from pathlib import Path

import pytest
import yaml

from ops_translate.util.templates import (
    TemplateLoader,
    create_template_context,
)
from ops_translate.workspace import Workspace


class TestTemplateLoader:
    """Tests for TemplateLoader class."""

    def test_has_custom_templates_false(self, tmp_path):
        """Test has_custom_templates when no custom templates."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)
        assert not loader.has_custom_templates()

    def test_has_custom_templates_true(self, tmp_path):
        """Test has_custom_templates when custom templates exist."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create custom templates directory
        (workspace.root / "templates").mkdir()

        loader = TemplateLoader(workspace.root)
        assert loader.has_custom_templates()

    def test_get_template_path_default(self, tmp_path):
        """Test getting default template path."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)
        template_path = loader.get_template_path("kubevirt/vm.yaml.j2")

        assert template_path.exists()
        assert "kubevirt" in str(template_path)
        assert template_path.name == "vm.yaml.j2"

    def test_get_template_path_custom(self, tmp_path):
        """Test getting custom template path."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create custom template
        custom_template_dir = workspace.root / "templates/kubevirt"
        custom_template_dir.mkdir(parents=True)
        custom_template = custom_template_dir / "vm.yaml.j2"
        custom_template.write_text("# Custom template")

        loader = TemplateLoader(workspace.root)
        template_path = loader.get_template_path("kubevirt/vm.yaml.j2")

        # Should prefer custom over default
        assert template_path == custom_template

    def test_get_template_path_not_found(self, tmp_path):
        """Test getting nonexistent template."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)

        with pytest.raises(FileNotFoundError):
            loader.get_template_path("nonexistent/template.j2")

    def test_load_template(self, tmp_path):
        """Test loading a template."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)
        template = loader.load_template("kubevirt/vm.yaml.j2")

        assert template is not None
        assert hasattr(template, "render")

    def test_render_template(self, tmp_path):
        """Test rendering a template."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)

        context = {
            "intent": {
                "workflow_name": "test_workflow",
                "workload_type": "virtual_machine",
                "inputs": {},
            },
            "profile": {
                "default_namespace": "test-namespace",
            },
            "profile_name": "test",
        }

        output_file = workspace.root / "output/test.yaml"
        loader.render_template("kubevirt/vm.yaml.j2", context, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "test_workflow" in content or "test-workflow" in content
        assert "test-namespace" in content

    def test_render_template_with_timestamp(self, tmp_path):
        """Test rendering adds timestamp if not provided."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)

        context = {
            "intent": {
                "workflow_name": "test",
                "inputs": {},
            },
            "profile": {},
            "profile_name": "test",
        }

        output_file = workspace.root / "output/test.yaml"
        loader.render_template("kubevirt/vm.yaml.j2", context, output_file)

        # Check timestamp was added
        content = output_file.read_text()
        # Timestamp should be in ISO format (contains 'T')
        assert "20" in content  # Year should be in output

    def test_copy_default_templates_to_workspace(self, tmp_path):
        """Test copying default templates to workspace."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)
        loader.copy_default_templates_to_workspace()

        # Check templates were copied
        assert (workspace.root / "templates").exists()
        assert (workspace.root / "templates/kubevirt/vm.yaml.j2").exists()
        assert (workspace.root / "templates/ansible/playbook.yml.j2").exists()

    def test_copy_default_templates_backs_up_existing(self, tmp_path):
        """Test copying templates backs up existing ones."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create existing templates
        (workspace.root / "templates").mkdir()
        existing_file = workspace.root / "templates/test.txt"
        existing_file.write_text("existing content")

        loader = TemplateLoader(workspace.root)
        loader.copy_default_templates_to_workspace()

        # Check backup was created
        assert (workspace.root / "templates.backup").exists()
        assert (workspace.root / "templates.backup/test.txt").exists()

        # Check new templates were copied
        assert (workspace.root / "templates/kubevirt/vm.yaml.j2").exists()

    def test_list_available_templates(self, tmp_path):
        """Test listing available templates."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        loader = TemplateLoader(workspace.root)
        templates = loader.list_available_templates()

        # Should have at least the default templates
        assert len(templates) > 0
        template_names = [t[1] for t in templates]
        assert any("kubevirt/vm.yaml.j2" in name for name in template_names)
        assert any("ansible/playbook.yml.j2" in name for name in template_names)

    def test_list_available_templates_with_workspace(self, tmp_path):
        """Test listing templates includes workspace templates."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Add custom template
        custom_template_dir = workspace.root / "templates/custom"
        custom_template_dir.mkdir(parents=True)
        (custom_template_dir / "custom.j2").write_text("# Custom")

        loader = TemplateLoader(workspace.root)
        templates = loader.list_available_templates()

        # Should have workspace templates
        workspace_templates = [t for t in templates if t[0] == "workspace"]
        assert len(workspace_templates) > 0
        assert any("custom/custom.j2" in t[1] for t in workspace_templates)


class TestCreateTemplateContext:
    """Tests for create_template_context function."""

    def test_basic_context(self):
        """Test creating basic template context."""
        intent = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "test_workflow",
                "inputs": {},
            },
        }
        profile = {"default_namespace": "default"}

        context = create_template_context(intent, profile, "lab")

        assert context["intent"]["workflow_name"] == "test_workflow"
        assert context["profile"]["default_namespace"] == "default"
        assert context["profile_name"] == "lab"
        assert context["schema_version"] == 1

    def test_context_with_sources(self):
        """Test context includes sources."""
        intent = {
            "schema_version": 1,
            "sources": [{"type": "powercli", "file": "test.ps1"}],
            "intent": {},
        }
        profile = {}

        context = create_template_context(intent, profile, "lab")

        assert len(context["sources"]) == 1
        assert context["sources"][0]["type"] == "powercli"

    def test_context_cloud_init(self):
        """Test context includes cloud_init_data placeholder."""
        intent = {"intent": {}}
        profile = {}

        context = create_template_context(intent, profile, "lab")

        assert "cloud_init_data" in context
        assert context["cloud_init_data"] == ""


class TestTemplateIntegration:
    """Integration tests for template system."""

    def test_generate_with_templates(self, tmp_path):
        """Test generating artifacts with template system."""
        from ops_translate.generate.generator import generate_with_templates

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create intent file
        intent_data = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "provision_vm",
                "workload_type": "virtual_machine",
                "inputs": {
                    "vm_name": {"type": "string", "required": True},
                    "cpu": {"type": "integer", "default": 2},
                },
            },
        }

        intent_file = workspace.root / "intent/intent.yaml"
        intent_file.write_text(yaml.dump(intent_data))

        # Generate
        generate_with_templates(workspace, "lab")

        # Check outputs were created
        assert (workspace.root / "output/kubevirt/vm.yaml").exists()
        assert (workspace.root / "output/ansible/site.yml").exists()
        assert (workspace.root / "output/ansible/roles/provision_vm/tasks/main.yml").exists()
        assert (workspace.root / "output/README.md").exists()

    def test_generate_with_custom_templates(self, tmp_path):
        """Test generating with custom templates."""
        from ops_translate.generate.generator import generate_with_templates

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create custom template
        custom_template_dir = workspace.root / "templates/kubevirt"
        custom_template_dir.mkdir(parents=True)
        custom_template = custom_template_dir / "vm.yaml.j2"
        custom_template.write_text(
            """# Custom KubeVirt template
kind: VirtualMachine
metadata:
  name: custom-{{ intent.workflow_name }}
"""
        )

        # Create intent
        intent_data = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "test",
                "inputs": {},
            },
        }
        intent_file = workspace.root / "intent/intent.yaml"
        intent_file.write_text(yaml.dump(intent_data))

        # Generate
        generate_with_templates(workspace, "lab")

        # Check custom template was used
        output_file = workspace.root / "output/kubevirt/vm.yaml"
        assert output_file.exists()
        content = output_file.read_text()
        assert "custom-test" in content
