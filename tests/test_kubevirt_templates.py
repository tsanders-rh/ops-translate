"""
Tests for KubeVirt template mapping functionality.
"""


import yaml

from ops_translate.generate.kubevirt import _get_source_spec


class TestKubeVirtTemplateMappings:
    """Tests for VM template mapping to CDI sources."""

    def test_get_source_spec_no_vm_source(self):
        """Test default to blank when no vm_source provided."""
        profile_config = {"default_namespace": "virt-lab"}

        source_spec = _get_source_spec(None, profile_config)

        assert source_spec == {"blank": {}}

    def test_get_source_spec_blank_type(self):
        """Test explicit blank type."""
        vm_source = {"type": "blank"}
        profile_config = {"default_namespace": "virt-lab"}

        source_spec = _get_source_spec(vm_source, profile_config)

        assert source_spec == {"blank": {}}

    def test_get_source_spec_registry_mapping(self):
        """Test registry source mapping."""
        vm_source = {"type": "template", "name": "RHEL8-Golden"}
        profile_config = {
            "default_namespace": "virt-lab",
            "template_mappings": {"RHEL8-Golden": "registry:quay.io/containerdisks/centos:8"},
        }

        source_spec = _get_source_spec(vm_source, profile_config)

        assert source_spec == {"registry": {"url": "quay.io/containerdisks/centos:8"}}

    def test_get_source_spec_pvc_mapping_simple(self):
        """Test PVC source mapping without namespace."""
        vm_source = {"type": "template", "name": "Windows-2022"}
        profile_config = {
            "default_namespace": "virt-lab",
            "template_mappings": {"Windows-2022": "pvc:windows-server-2022"},
        }

        source_spec = _get_source_spec(vm_source, profile_config)

        assert source_spec == {"pvc": {"name": "windows-server-2022"}}

    def test_get_source_spec_pvc_mapping_with_namespace(self):
        """Test PVC source mapping with namespace."""
        vm_source = {"type": "template", "name": "Ubuntu-22.04"}
        profile_config = {
            "default_namespace": "virt-lab",
            "template_mappings": {"Ubuntu-22.04": "pvc:os-images/ubuntu-22-04"},
        }

        source_spec = _get_source_spec(vm_source, profile_config)

        assert source_spec == {"pvc": {"name": "ubuntu-22-04", "namespace": "os-images"}}

    def test_get_source_spec_http_mapping(self):
        """Test HTTP source mapping."""
        vm_source = {"type": "ova", "name": "custom-app.ova"}
        profile_config = {
            "default_namespace": "virt-lab",
            "template_mappings": {
                "custom-app.ova": "http:https://storage.example.com/images/app.qcow2"
            },
        }

        source_spec = _get_source_spec(vm_source, profile_config)

        assert source_spec == {"http": {"url": "https://storage.example.com/images/app.qcow2"}}

    def test_get_source_spec_no_mapping_found(self, capsys):
        """Test fallback to blank when no mapping exists."""
        vm_source = {"type": "template", "name": "Unknown-Template"}
        profile_config = {
            "default_namespace": "virt-lab",
            "template_mappings": {"RHEL8": "registry:quay.io/..."},
        }

        source_spec = _get_source_spec(vm_source, profile_config)

        # Should fall back to blank
        assert source_spec == {"blank": {}}

        # Should print warning
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "Unknown-Template" in captured.out

    def test_get_source_spec_invalid_format(self, capsys):
        """Test handling of invalid mapping format."""
        vm_source = {"type": "template", "name": "BadTemplate"}
        profile_config = {
            "default_namespace": "virt-lab",
            "template_mappings": {"BadTemplate": "invalid-format-no-colon"},
        }

        source_spec = _get_source_spec(vm_source, profile_config)

        # Should fall back to blank
        assert source_spec == {"blank": {}}

        # Should print warning about invalid format
        captured = capsys.readouterr()
        assert "Invalid mapping format" in captured.out

    def test_get_source_spec_explicit_blank_mapping(self):
        """Test explicit 'blank' mapping."""
        vm_source = {"type": "template", "name": "EmptyTemplate"}
        profile_config = {
            "default_namespace": "virt-lab",
            "template_mappings": {"EmptyTemplate": "blank"},
        }

        source_spec = _get_source_spec(vm_source, profile_config)

        assert source_spec == {"blank": {}}

    def test_get_source_spec_no_template_mappings_section(self, capsys):
        """Test when profile has no template_mappings section at all."""
        vm_source = {"type": "template", "name": "SomeTemplate"}
        profile_config = {"default_namespace": "virt-lab"}  # No template_mappings

        source_spec = _get_source_spec(vm_source, profile_config)

        # Should fall back to blank and warn
        assert source_spec == {"blank": {}}
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_get_source_spec_clone_type(self, capsys):
        """Test clone type without mapping (should warn)."""
        vm_source = {"type": "clone", "name": "SourceVM"}
        profile_config = {"default_namespace": "virt-lab"}

        source_spec = _get_source_spec(vm_source, profile_config)

        # Should fall back to blank
        assert source_spec == {"blank": {}}
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "SourceVM" in captured.out


class TestKubeVirtGeneratorIntegration:
    """Integration tests for KubeVirt generator with templates."""

    def test_generate_with_registry_template(self, tmp_path):
        """Test full generation with registry-based template."""
        from ops_translate.generate.kubevirt import generate
        from ops_translate.workspace import Workspace

        # Create workspace
        workspace = Workspace(tmp_path)
        (workspace.root / "intent").mkdir()
        (workspace.root / "output").mkdir()

        # Create config with template mapping
        config = {
            "llm": {"provider": "mock", "model": "mock"},
            "profiles": {
                "lab": {
                    "default_namespace": "virt-lab",
                    "default_network": "pod-network",
                    "default_storage_class": "nfs",
                    "template_mappings": {
                        "RHEL8-Golden": "registry:quay.io/containerdisks/centos:8"
                    },
                }
            },
        }
        with open(workspace.root / "ops-translate.yaml", "w") as f:
            yaml.dump(config, f)

        # Create intent with vm_source
        intent = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "test",
                "workload_type": "virtual_machine",
                "vm_source": {"type": "template", "name": "RHEL8-Golden"},
            },
        }
        with open(workspace.root / "intent/intent.yaml", "w") as f:
            yaml.dump(intent, f)

        # Generate
        generate(workspace, "lab")

        # Verify output
        vm_yaml = workspace.root / "output/kubevirt/vm.yaml"
        assert vm_yaml.exists()

        with open(vm_yaml) as f:
            vm_manifest = yaml.safe_load(f)

        # Check that registry source was used
        source = vm_manifest["spec"]["dataVolumeTemplates"][0]["spec"]["source"]
        assert "registry" in source
        assert source["registry"]["url"] == "quay.io/containerdisks/centos:8"

    def test_generate_without_template_mapping(self, tmp_path, capsys):
        """Test generation when template exists but no mapping configured."""
        from ops_translate.generate.kubevirt import generate
        from ops_translate.workspace import Workspace

        # Create workspace
        workspace = Workspace(tmp_path)
        (workspace.root / "intent").mkdir()
        (workspace.root / "output").mkdir()

        # Create config WITHOUT template mapping
        config = {
            "llm": {"provider": "mock", "model": "mock"},
            "profiles": {
                "lab": {
                    "default_namespace": "virt-lab",
                    "default_network": "pod-network",
                    "default_storage_class": "nfs",
                }
            },
        }
        with open(workspace.root / "ops-translate.yaml", "w") as f:
            yaml.dump(config, f)

        # Create intent with vm_source that has no mapping
        intent = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "test",
                "workload_type": "virtual_machine",
                "vm_source": {"type": "template", "name": "UnmappedTemplate"},
            },
        }
        with open(workspace.root / "intent/intent.yaml", "w") as f:
            yaml.dump(intent, f)

        # Generate
        generate(workspace, "lab")

        # Should fall back to blank and warn
        vm_yaml = workspace.root / "output/kubevirt/vm.yaml"
        assert vm_yaml.exists()

        with open(vm_yaml) as f:
            vm_manifest = yaml.safe_load(f)

        source = vm_manifest["spec"]["dataVolumeTemplates"][0]["spec"]["source"]
        assert source == {"blank": {}}

        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "UnmappedTemplate" in captured.out
        assert "template_mappings" in captured.out
