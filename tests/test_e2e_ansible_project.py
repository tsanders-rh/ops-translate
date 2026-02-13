"""
End-to-end test for profile-driven Ansible project generation.

Tests the complete workflow:
1. Load translation profile
2. Collect workflow definitions
3. Generate full Ansible project structure
4. Verify adapters rendered with profile-conditional logic
"""

import pytest
from pathlib import Path

from ops_translate.intent.profile import load_profile
from ops_translate.generate.ansible_project import generate_ansible_project


class TestEndToEndProjectGeneration:
    """End-to-end tests for Ansible project generation."""

    def test_generate_project_with_complete_profile(self, tmp_path):
        """Generate full Ansible project with complete profile."""
        # Load complete profile
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        # Create sample workflow definitions
        workflows = [
            {
                "name": "vm_provisioning",
                "source": "vrealize",
                "source_file": "input/vrealize/vm-provisioning.workflow.xml",
            },
            {
                "name": "network_config",
                "source": "vrealize",
                "source_file": "input/vrealize/network-config.workflow.xml",
            },
        ]

        # Generate project
        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Verify project structure
        assert project_dir.exists()
        assert (project_dir / "site.yml").exists()
        assert (project_dir / "ansible.cfg").exists()
        assert (project_dir / "inventories").exists()
        assert (project_dir / "roles").exists()
        assert (project_dir / "adapters").exists()
        assert (project_dir / "docs").exists()

    def test_verify_multi_environment_inventories(self, tmp_path):
        """Verify multi-environment inventory generation from profile."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [{"name": "test_workflow", "source": "template", "source_file": "test"}]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Should have dev and prod inventories
        assert (project_dir / "inventories/dev").exists()
        assert (project_dir / "inventories/prod").exists()

        # Check dev inventory
        dev_hosts = project_dir / "inventories/dev/hosts"
        assert dev_hosts.exists()
        dev_hosts_content = dev_hosts.read_text()
        assert "api.dev.ocp.acme.com" in dev_hosts_content

        # Check prod inventory
        prod_hosts = project_dir / "inventories/prod/hosts"
        assert prod_hosts.exists()
        prod_hosts_content = prod_hosts.read_text()
        assert "api.prod.ocp.acme.com" in prod_hosts_content

        # Check group_vars
        dev_vars = project_dir / "inventories/dev/group_vars/all.yml"
        assert dev_vars.exists()
        dev_vars_content = dev_vars.read_text()
        assert "acme-dev" in dev_vars_content
        assert "development" in dev_vars_content

    def test_verify_adapter_stubs_generated(self, tmp_path):
        """Verify all adapter stubs are generated."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [{"name": "test_workflow", "source": "template", "source_file": "test"}]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Check NSX adapters
        assert (project_dir / "adapters/nsx/create_segment.yml").exists()
        assert (project_dir / "adapters/nsx/create_firewall_rule.yml").exists()

        # Check ServiceNow adapters
        assert (project_dir / "adapters/servicenow/create_change.yml").exists()
        assert (project_dir / "adapters/servicenow/create_incident.yml").exists()

        # Check DNS/IPAM adapters
        assert (project_dir / "adapters/dns/create_record.yml").exists()
        assert (project_dir / "adapters/ipam/reserve_ip.yml").exists()

    def test_verify_nsx_adapter_functional_with_profile(self, tmp_path):
        """Verify NSX adapter renders functional tasks (not BLOCKED) with profile."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [{"name": "test_workflow", "source": "template", "source_file": "test"}]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Read NSX segment adapter
        segment_adapter = project_dir / "adapters/nsx/create_segment.yml"
        segment_content = segment_adapter.read_text()

        # Should have functional task, not BLOCKED
        assert "kubernetes.core.k8s" in segment_content
        assert "NetworkAttachmentDefinition" in segment_content
        assert "BLOCKED" not in segment_content

    def test_verify_servicenow_adapter_functional_with_profile(self, tmp_path):
        """Verify ServiceNow adapter renders functional tasks with profile."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [{"name": "test_workflow", "source": "template", "source_file": "test"}]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Read ServiceNow change adapter
        change_adapter = project_dir / "adapters/servicenow/create_change.yml"
        change_content = change_adapter.read_text()

        # Should have functional ServiceNow API calls
        assert "uri:" in change_content
        assert "acme.service-now.com" in change_content
        assert "change_request" in change_content
        assert profile.approval.username_var in change_content

    def test_verify_documentation_generated(self, tmp_path):
        """Verify project documentation is generated."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [
            {"name": "vm_provisioning", "source": "vrealize", "source_file": "test.xml"},
            {"name": "network_config", "source": "vrealize", "source_file": "test2.xml"},
        ]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Check documentation files
        assert (project_dir / "docs/README.md").exists()
        assert (project_dir / "docs/profile.md").exists()
        assert (project_dir / "docs/adapters.md").exists()

        # Verify README content
        readme_content = (project_dir / "docs/README.md").read_text()
        assert profile.name in readme_content
        assert "vm_provisioning" in readme_content
        assert "network_config" in readme_content

        # Verify profile.md content
        profile_md = (project_dir / "docs/profile.md").read_text()
        assert "acme-production" in profile_md
        assert "dev" in profile_md
        assert "prod" in profile_md

        # Verify adapters.md content
        adapters_md = (project_dir / "docs/adapters.md").read_text()
        assert "NSX Adapters" in adapters_md
        assert "ServiceNow Adapters" in adapters_md
        assert "BLOCKED" in adapters_md  # Should explain BLOCKED stubs

    def test_generate_project_with_minimal_profile_creates_blocked_stubs(self, tmp_path):
        """Minimal profile should generate BLOCKED stubs for missing configs."""
        profile_path = Path(__file__).parent / "fixtures/profiles/minimal_profile.yml"
        profile = load_profile(profile_path)

        workflows = [{"name": "test_workflow", "source": "template", "source_file": "test"}]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Read NSX segment adapter (should be BLOCKED)
        segment_adapter = project_dir / "adapters/nsx/create_segment.yml"
        segment_content = segment_adapter.read_text()

        # Should have BLOCKED stub with guidance
        assert "BLOCKED" in segment_content
        assert "network_security" in segment_content
        assert "TO FIX THIS" in segment_content
        assert "ansible.builtin.fail" in segment_content

    def test_site_playbook_includes_all_roles(self, tmp_path):
        """Verify site.yml includes all workflow roles."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [
            {"name": "vm_provisioning", "source": "vrealize", "source_file": "test.xml"},
            {"name": "network_config", "source": "vrealize", "source_file": "test2.xml"},
            {"name": "storage_tier", "source": "vrealize", "source_file": "test3.xml"},
        ]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Read site.yml
        site_yml = project_dir / "site.yml"
        site_content = site_yml.read_text()

        # Should include all three workflows as roles
        assert "vm_provisioning" in site_content
        assert "network_config" in site_content
        assert "storage_tier" in site_content

    def test_ansible_cfg_generated(self, tmp_path):
        """Verify ansible.cfg is generated with correct defaults."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [{"name": "test_workflow", "source": "template", "source_file": "test"}]

        output_dir = tmp_path / "output"
        project_dir = generate_ansible_project(workflows, profile, output_dir)

        # Read ansible.cfg
        ansible_cfg = project_dir / "ansible.cfg"
        assert ansible_cfg.exists()
        cfg_content = ansible_cfg.read_text()

        # Check for expected settings
        assert "[defaults]" in cfg_content
        assert "inventory = inventories/dev" in cfg_content
        assert "roles_path = roles" in cfg_content
        assert "stdout_callback = yaml" in cfg_content


class TestDeterministicGeneration:
    """Test deterministic generation behavior."""

    def test_same_profile_produces_identical_output(self, tmp_path):
        """Same profile + workflows should produce identical output."""
        profile_path = Path(__file__).parent / "fixtures/profiles/complete_profile.yml"
        profile = load_profile(profile_path)

        workflows = [
            {"name": "vm_provisioning", "source": "vrealize", "source_file": "test.xml"}
        ]

        # Generate first time
        output_dir_1 = tmp_path / "output1"
        project_dir_1 = generate_ansible_project(workflows, profile, output_dir_1)
        adapter_1 = (project_dir_1 / "adapters/nsx/create_segment.yml").read_text()

        # Generate second time
        output_dir_2 = tmp_path / "output2"
        project_dir_2 = generate_ansible_project(workflows, profile, output_dir_2)
        adapter_2 = (project_dir_2 / "adapters/nsx/create_segment.yml").read_text()

        # Should be identical
        assert adapter_1 == adapter_2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
