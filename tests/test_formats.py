"""
Tests for output format handlers.
"""

import json
from pathlib import Path

import pytest
import yaml

from ops_translate.generate.formats import (
    ArgoCDFormat,
    JSONFormat,
    KustomizeFormat,
    YAMLFormat,
    get_format_handler,
)
from ops_translate.workspace import Workspace


@pytest.fixture
def sample_content():
    """Sample YAML content for testing."""
    return {
        "kubevirt/vm.yaml": """apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: test-vm
  namespace: default
spec:
  running: true
""",
        "ansible/site.yml": """---
- name: Test playbook
  hosts: localhost
  tasks:
    - name: Test task
      debug:
        msg: "Hello"
""",
    }


@pytest.fixture
def sample_context():
    """Sample template context for testing."""
    return {
        "intent": {
            "workflow_name": "test_workflow",
            "workload_type": "virtual_machine",
        },
        "profile": {
            "default_namespace": "default",
        },
        "profile_name": "lab",
    }


class TestYAMLFormat:
    """Tests for YAML output format."""

    def test_write_yaml(self, tmp_path, sample_content, sample_context):
        """Test writing YAML files."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = YAMLFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Check files were created
        assert (workspace.root / "output/kubevirt/vm.yaml").exists()
        assert (workspace.root / "output/ansible/site.yml").exists()

        # Verify content
        vm_content = (workspace.root / "output/kubevirt/vm.yaml").read_text()
        assert "VirtualMachine" in vm_content
        assert "test-vm" in vm_content


class TestJSONFormat:
    """Tests for JSON output format."""

    def test_write_json(self, tmp_path, sample_content, sample_context):
        """Test writing JSON files."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = JSONFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Check JSON files were created
        assert (workspace.root / "output/json/vm.json").exists()
        assert (workspace.root / "output/json/site.json").exists()

    def test_json_content_valid(self, tmp_path, sample_content, sample_context):
        """Test JSON content is valid."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = JSONFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load and validate JSON
        json_file = workspace.root / "output/json/vm.json"
        with open(json_file) as f:
            data = json.load(f)

        assert data["kind"] == "VirtualMachine"
        assert data["metadata"]["name"] == "test-vm"

    def test_json_multi_document(self, tmp_path, sample_context):
        """Test JSON handles multi-document YAML."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        content = {"multi.yaml": """---
kind: ConfigMap
metadata:
  name: config1
---
kind: ConfigMap
metadata:
  name: config2
"""}

        handler = JSONFormat(workspace.root)
        handler.write(content, "lab", sample_context)

        # Should create JSON array
        json_file = workspace.root / "output/json/multi.json"
        with open(json_file) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 2


class TestKustomizeFormat:
    """Tests for Kustomize output format."""

    def test_write_kustomize_structure(self, tmp_path, sample_content, sample_context):
        """Test writing Kustomize structure."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = KustomizeFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Check base directory created
        assert (workspace.root / "output/base").exists()
        assert (workspace.root / "output/base/kustomization.yaml").exists()
        assert (workspace.root / "output/base/vm.yaml").exists()

        # Check overlays created
        for env in ["dev", "staging", "prod"]:
            assert (workspace.root / f"output/overlays/{env}").exists()
            assert (workspace.root / f"output/overlays/{env}/kustomization.yaml").exists()

    def test_base_kustomization_content(self, tmp_path, sample_content, sample_context):
        """Test base kustomization.yaml content."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = KustomizeFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load and verify base kustomization
        kustomization_file = workspace.root / "output/base/kustomization.yaml"
        with open(kustomization_file) as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "Kustomization"
        assert "vm.yaml" in data["resources"]
        assert data["commonLabels"]["app"] == "test_workflow"
        assert data["commonLabels"]["managed-by"] == "ops-translate"

    def test_overlay_kustomization_content(self, tmp_path, sample_content, sample_context):
        """Test overlay kustomization.yaml content."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = KustomizeFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load and verify dev overlay
        overlay_file = workspace.root / "output/overlays/dev/kustomization.yaml"
        with open(overlay_file) as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "Kustomization"
        assert "../../base" in data["bases"]
        assert data["commonLabels"]["environment"] == "dev"
        assert len(data["patches"]) > 0

    def test_overlay_different_resources(self, tmp_path, sample_content, sample_context):
        """Test overlays have different resource configurations."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = KustomizeFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load dev and prod overlays
        dev_file = workspace.root / "output/overlays/dev/kustomization.yaml"
        prod_file = workspace.root / "output/overlays/prod/kustomization.yaml"

        with open(dev_file) as f:
            dev_data = yaml.safe_load(f)
        with open(prod_file) as f:
            prod_data = yaml.safe_load(f)

        # Dev should have different resources than prod
        dev_patch = dev_data["patches"][0]["patch"]
        prod_patch = prod_data["patches"][0]["patch"]

        assert "2Gi" in dev_patch  # Dev has 2Gi memory
        assert "8Gi" in prod_patch  # Prod has 8Gi memory


class TestArgoCDFormat:
    """Tests for ArgoCD output format."""

    def test_write_argocd_structure(self, tmp_path, sample_content, sample_context):
        """Test writing ArgoCD structure."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = ArgoCDFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Check ArgoCD directory created
        assert (workspace.root / "output/argocd").exists()
        assert (workspace.root / "output/argocd/project.yaml").exists()
        assert (workspace.root / "output/argocd/dev-application.yaml").exists()
        assert (workspace.root / "output/argocd/staging-application.yaml").exists()
        assert (workspace.root / "output/argocd/prod-application.yaml").exists()

        # Should also create Kustomize structure
        assert (workspace.root / "output/base").exists()
        assert (workspace.root / "output/overlays/dev").exists()

    def test_application_content(self, tmp_path, sample_content, sample_context):
        """Test Application manifest content."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = ArgoCDFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load dev application
        app_file = workspace.root / "output/argocd/dev-application.yaml"
        with open(app_file) as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "Application"
        assert data["metadata"]["name"] == "test_workflow-dev"
        assert data["spec"]["project"] == "test_workflow"
        assert "output/overlays/dev" in data["spec"]["source"]["path"]

    def test_dev_automated_sync(self, tmp_path, sample_content, sample_context):
        """Test dev environment has automated sync."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = ArgoCDFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load dev application
        app_file = workspace.root / "output/argocd/dev-application.yaml"
        with open(app_file) as f:
            data = yaml.safe_load(f)

        assert "automated" in data["spec"]["syncPolicy"]
        assert data["spec"]["syncPolicy"]["automated"]["prune"] is True
        assert data["spec"]["syncPolicy"]["automated"]["selfHeal"] is True

    def test_prod_manual_sync(self, tmp_path, sample_content, sample_context):
        """Test prod environment has manual sync."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = ArgoCDFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load prod application
        app_file = workspace.root / "output/argocd/prod-application.yaml"
        with open(app_file) as f:
            data = yaml.safe_load(f)

        # Prod should not have automated sync
        assert "automated" not in data["spec"]["syncPolicy"]

    def test_project_content(self, tmp_path, sample_content, sample_context):
        """Test AppProject manifest content."""
        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        handler = ArgoCDFormat(workspace.root)
        handler.write(sample_content, "lab", sample_context)

        # Load project
        project_file = workspace.root / "output/argocd/project.yaml"
        with open(project_file) as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "AppProject"
        assert data["metadata"]["name"] == "test_workflow"
        assert len(data["spec"]["sourceRepos"]) > 0
        assert len(data["spec"]["destinations"]) > 0


class TestGetFormatHandler:
    """Tests for get_format_handler function."""

    def test_get_yaml_handler(self, tmp_path):
        """Test getting YAML handler."""
        handler = get_format_handler("yaml", tmp_path)
        assert isinstance(handler, YAMLFormat)

    def test_get_json_handler(self, tmp_path):
        """Test getting JSON handler."""
        handler = get_format_handler("json", tmp_path)
        assert isinstance(handler, JSONFormat)

    def test_get_kustomize_handler(self, tmp_path):
        """Test getting Kustomize handler."""
        handler = get_format_handler("kustomize", tmp_path)
        assert isinstance(handler, KustomizeFormat)

    def test_get_gitops_alias(self, tmp_path):
        """Test gitops is alias for kustomize."""
        handler = get_format_handler("gitops", tmp_path)
        assert isinstance(handler, KustomizeFormat)

    def test_get_argocd_handler(self, tmp_path):
        """Test getting ArgoCD handler."""
        handler = get_format_handler("argocd", tmp_path)
        assert isinstance(handler, ArgoCDFormat)

    def test_invalid_format(self, tmp_path):
        """Test error on invalid format."""
        with pytest.raises(ValueError, match="Invalid format"):
            get_format_handler("invalid", tmp_path)


class TestFormatIntegration:
    """Integration tests for output formats."""

    def test_generate_with_json_format(self, tmp_path):
        """Test generating with JSON format."""
        from ops_translate.generate.generator import generate_with_templates

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create intent file
        intent_data = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "provision_vm",
                "workload_type": "virtual_machine",
                "inputs": {},
            },
        }

        intent_file = workspace.root / "intent/intent.yaml"
        intent_file.write_text(yaml.dump(intent_data))

        # Generate with JSON format
        generate_with_templates(workspace, "lab", output_format="json")

        # Check JSON output was created
        assert (workspace.root / "output/json/vm.json").exists()
        assert (workspace.root / "output/json/site.json").exists()

    def test_generate_with_kustomize_format(self, tmp_path):
        """Test generating with Kustomize format."""
        from ops_translate.generate.generator import generate_with_templates

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create intent file
        intent_data = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "provision_vm",
                "inputs": {},
            },
        }

        intent_file = workspace.root / "intent/intent.yaml"
        intent_file.write_text(yaml.dump(intent_data))

        # Generate with Kustomize format
        generate_with_templates(workspace, "lab", output_format="kustomize")

        # Check Kustomize structure was created
        assert (workspace.root / "output/base/kustomization.yaml").exists()
        assert (workspace.root / "output/overlays/dev/kustomization.yaml").exists()
        assert (workspace.root / "output/overlays/prod/kustomization.yaml").exists()

    def test_generate_with_argocd_format(self, tmp_path):
        """Test generating with ArgoCD format."""
        from ops_translate.generate.generator import generate_with_templates

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        # Create intent file
        intent_data = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "test_migration",
                "inputs": {},
            },
        }

        intent_file = workspace.root / "intent/intent.yaml"
        intent_file.write_text(yaml.dump(intent_data))

        # Generate with ArgoCD format
        generate_with_templates(workspace, "lab", output_format="argocd")

        # Check ArgoCD applications were created
        assert (workspace.root / "output/argocd/dev-application.yaml").exists()
        assert (workspace.root / "output/argocd/project.yaml").exists()
