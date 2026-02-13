"""
Tests for profile-driven Ansible translation system.

Validates profile loading, validation, and adapter template rendering.
"""

import pytest
from pathlib import Path

from ops_translate.intent.profile import (
    load_profile,
    save_profile,
    validate_profile_schema,
    validate_profile_completeness,
)
from ops_translate.models.profile import (
    ProfileSchema,
    EnvironmentConfig,
    ApprovalConfig,
    NetworkSecurityConfig,
)


class TestProfileLoading:
    """Test profile loading from YAML files."""

    def test_load_complete_profile(self):
        """Load complete profile fixture and validate structure."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        assert profile.name == "acme-production"
        assert profile.description is not None
        assert len(profile.environments) == 2
        assert "dev" in profile.environments
        assert "prod" in profile.environments

    def test_load_minimal_profile(self):
        """Load minimal profile with only required fields."""
        profile_path = Path(__file__).parent / "fixtures/profiles/minimal_profile.yml"
        profile = load_profile(profile_path)

        assert profile.name == "minimal-profile"
        assert len(profile.environments) == 1
        assert "dev" in profile.environments
        assert profile.approval is None
        assert profile.network_security is None

    def test_environment_config_loading(self):
        """Verify environment configuration loaded correctly."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        dev_env = profile.environments["dev"]
        assert dev_env.openshift_api_url == "https://api.dev.ocp.acme.com:6443"
        assert dev_env.namespace == "acme-dev"
        assert "environment" in dev_env.node_selectors
        assert dev_env.node_selectors["environment"] == "development"

    def test_approval_config_loading(self):
        """Verify approval configuration loaded correctly."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        assert profile.approval is not None
        assert profile.approval.model == "servicenow_change"
        assert profile.approval.endpoint == "https://acme.service-now.com"
        assert profile.approval.username_var == "snow_api_user"

    def test_network_security_config_loading(self):
        """Verify network security configuration loaded correctly."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        assert profile.network_security is not None
        assert profile.network_security.model == "networkpolicy"
        assert profile.network_security.default_isolation == "namespace"

    def test_storage_tiers_loading(self):
        """Verify storage tier mappings loaded correctly."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        assert len(profile.storage_tiers) == 3
        gold_tier = next((t for t in profile.storage_tiers if t.vmware_tier == "gold"), None)
        assert gold_tier is not None
        assert "gold" in gold_tier.openshift_storage_class


class TestProfileValidation:
    """Test profile validation with JSON Schema."""

    def test_valid_complete_profile(self):
        """Complete profile should pass validation."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"

        # Should not raise
        profile = load_profile(profile_path)
        assert profile is not None

    def test_valid_minimal_profile(self):
        """Minimal profile with only required fields should pass."""
        profile_path = Path(__file__).parent / "fixtures/profiles/minimal_profile.yml"

        # Should not raise
        profile = load_profile(profile_path)
        assert profile is not None

    def test_invalid_profile_missing_name(self, tmp_path):
        """Profile without name should fail validation."""
        invalid_profile = tmp_path / "invalid.yml"
        invalid_profile.write_text("""
environments:
  dev:
    openshift_api_url: "https://api.example.com:6443"
""")

        with pytest.raises(ValueError, match="validation failed"):
            load_profile(invalid_profile)

    def test_invalid_profile_missing_environments(self, tmp_path):
        """Profile without environments should fail validation."""
        invalid_profile = tmp_path / "invalid.yml"
        invalid_profile.write_text("""
name: "test-profile"
""")

        with pytest.raises(ValueError, match="validation failed"):
            load_profile(invalid_profile)

    def test_invalid_approval_model(self, tmp_path):
        """Profile with invalid approval model should fail validation."""
        invalid_profile = tmp_path / "invalid.yml"
        invalid_profile.write_text("""
name: "test-profile"
environments:
  dev:
    openshift_api_url: "https://api.example.com:6443"
approval:
  model: "invalid_model"
""")

        with pytest.raises(ValueError, match="validation failed"):
            load_profile(invalid_profile)


class TestProfileCompleteness:
    """Test profile completeness checking."""

    def test_complete_profile_no_warnings(self):
        """Complete profile should have no completeness warnings."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        warnings = validate_profile_completeness(profile)

        # Complete profile should have no warnings
        assert len(warnings) == 0

    def test_minimal_profile_warnings(self):
        """Minimal profile should have warnings for missing sections."""
        profile_path = Path(__file__).parent / "fixtures/profiles/minimal_profile.yml"
        profile = load_profile(profile_path)

        warnings = validate_profile_completeness(profile)

        # Should have warnings for missing optional sections
        assert "approval" in warnings
        assert "network_security" in warnings
        assert "itsm" in warnings
        assert "dns" in warnings
        assert "ipam" in warnings
        assert "storage_tiers" in warnings


class TestProfileSaveLoad:
    """Test profile save and load round-trip."""

    def test_save_and_load_profile(self, tmp_path):
        """Profile should survive save/load round-trip."""
        # Create a profile programmatically
        profile = ProfileSchema(
            name="test-profile",
            description="Test profile",
            environments={
                "test": EnvironmentConfig(
                    openshift_api_url="https://api.test.com:6443",
                    namespace="test-ns",
                    node_selectors={"env": "test"},
                )
            },
            approval=ApprovalConfig(
                model="manual_pause",
            ),
            network_security=NetworkSecurityConfig(
                model="networkpolicy",
                default_isolation="namespace",
            ),
        )

        # Save to file
        profile_file = tmp_path / "test_profile.yml"
        save_profile(profile, profile_file)

        # Load back
        loaded_profile = load_profile(profile_file)

        # Verify
        assert loaded_profile.name == profile.name
        assert loaded_profile.description == profile.description
        assert len(loaded_profile.environments) == 1
        assert loaded_profile.environments["test"].namespace == "test-ns"
        assert loaded_profile.approval.model == "manual_pause"
        assert loaded_profile.network_security.model == "networkpolicy"


class TestAdapterTemplateRendering:
    """Test adapter template rendering with profiles."""

    def test_nsx_segment_adapter_with_profile(self):
        """NSX segment adapter should render with network_security configured."""
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        template_dir = Path(__file__).parent.parent / "templates/ansible/adapters"
        env = Environment(loader=FileSystemLoader(template_dir))

        profile = ProfileSchema(
            name="test",
            environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
            network_security=NetworkSecurityConfig(
                model="networkpolicy",
                default_isolation="namespace",
            ),
        )

        template = env.get_template("nsx/create_segment.yml.j2")
        rendered = template.render(profile=profile)

        # Should generate functional task, not BLOCKED stub
        assert "kubernetes.core.k8s" in rendered
        assert "NetworkAttachmentDefinition" in rendered
        assert "BLOCKED" not in rendered

    def test_nsx_segment_adapter_without_profile(self):
        """NSX segment adapter should generate BLOCKED stub without network_security."""
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        template_dir = Path(__file__).parent.parent / "templates/ansible/adapters"
        env = Environment(loader=FileSystemLoader(template_dir))

        profile = ProfileSchema(
            name="test",
            environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
            # No network_security configured
        )

        template = env.get_template("nsx/create_segment.yml.j2")
        rendered = template.render(profile=profile)

        # Should generate BLOCKED stub with guidance
        assert "BLOCKED" in rendered
        assert "network_security" in rendered
        assert "TO FIX THIS" in rendered
        assert "ansible.builtin.fail" in rendered

    def test_servicenow_change_adapter_with_approval(self):
        """ServiceNow change adapter should render with approval configured."""
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        template_dir = Path(__file__).parent.parent / "templates/ansible/adapters"
        env = Environment(loader=FileSystemLoader(template_dir))

        profile = ProfileSchema(
            name="test",
            environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
            approval=ApprovalConfig(
                model="servicenow_change",
                endpoint="https://snow.example.com",
                username_var="snow_user",
                password_var="snow_pass",
            ),
        )

        template = env.get_template("servicenow/create_change.yml.j2")
        rendered = template.render(profile=profile)

        # Should generate functional ServiceNow API calls
        assert "uri:" in rendered
        assert profile.approval.endpoint in rendered
        assert "change_request" in rendered
        assert "BLOCKED" not in rendered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
