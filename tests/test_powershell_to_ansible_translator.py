"""
Tests for PowerShell to Ansible translation.

Validates cmdlet translation, profile-driven decisions, and BLOCKED stubs.
"""

from pathlib import Path

import pytest

from ops_translate.models.profile import (
    EnvironmentConfig,
    NetworkSecurityConfig,
    ProfileSchema,
)
from ops_translate.translate.powercli_script import (
    PowerCLIScriptParser,
    PowerCLIStatement,
    PowerShellToAnsibleTranslator,
)


class TestPowerShellToAnsibleTranslator:
    """Test PowerShell to Ansible translation."""

    def test_translate_variable_assignment(self):
        """Test translation of variable assignment to set_fact."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text='$Network = "dev-network"',
            statement_type="assignment",
            category="context",
            parameters={"variable": "Network", "value": '"dev-network"'},
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_assignment(stmt)

        assert task is not None
        assert task.module == "ansible.builtin.set_fact"
        assert "network" in task.module_args
        assert task.module_args["network"] == "dev-network"
        assert "context" in task.tags

    def test_translate_new_vm_cmdlet(self):
        """Test translation of New-VM to kubevirt_vm."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text="New-VM -Name MyVM -NumCpu 4 -MemoryGB 8",
            statement_type="cmdlet",
            category="mutation",
            cmdlet="New-VM",
            parameters={"Name": "MyVM", "NumCpu": "4", "MemoryGB": "8"},
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_cmdlet(stmt)

        assert task is not None
        assert task.module == "kubevirt.core.kubevirt_vm"
        assert task.module_args["state"] == "present"
        assert task.module_args["name"] == "MyVM"
        assert task.module_args["cpu_cores"] == "4"
        assert task.module_args["memory"] == "8Gi"

    def test_translate_start_vm_cmdlet(self):
        """Test translation of Start-VM to kubevirt_vm with running state."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text="Start-VM -VM MyVM",
            statement_type="cmdlet",
            category="mutation",
            cmdlet="Start-VM",
            parameters={"VM": "MyVM"},
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_cmdlet(stmt)

        assert task is not None
        assert task.module == "kubevirt.core.kubevirt_vm"
        assert task.module_args["state"] == "running"
        assert task.module_args["name"] == "MyVM"

    def test_translate_cmdlet_with_variables(self):
        """Test translation of cmdlet with PowerShell variables."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text="New-VM -Name $VMName -NumCpu $CPUCount",
            statement_type="cmdlet",
            category="mutation",
            cmdlet="New-VM",
            parameters={"Name": "$VMName", "NumCpu": "$CPUCount"},
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_cmdlet(stmt)

        assert task is not None
        assert "{{ vm_name }}" in task.name or "{{ vmname }}" in task.name
        assert task.module_args["name"] == "{{ vmname }}"
        assert task.module_args["cpu_cores"] == "{{ cpucount }}"

    def test_translate_validation_gate(self):
        """Test translation of throw statement to assert."""
        stmt = PowerCLIStatement(
            line_number=2,
            raw_text='    throw "CPU limit exceeded"',
            statement_type="control_flow",
            category="gate",
            control_type="throw",
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_validation(stmt, "$NumCPU -gt 16")

        assert task is not None
        assert task.module == "ansible.builtin.assert"
        assert "CPU limit exceeded" in task.module_args["fail_msg"]
        assert "that" in task.module_args
        assert "gate" in task.tags

    def test_translate_tagging_to_labels(self):
        """Test translation of New-TagAssignment to Kubernetes labels."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text='New-TagAssignment -Entity MyVM -Tag "Environment:Dev"',
            statement_type="cmdlet",
            category="integration",
            cmdlet="New-TagAssignment",
            parameters={"Entity": "MyVM", "Tag": "Environment:Dev"},
            integration_type="tagging",
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_tagging(stmt)

        assert task is not None
        assert task.module == "kubernetes.core.k8s"
        assert task.module_args["kind"] == "VirtualMachine"
        assert task.module_args["name"] == "MyVM"
        assert "labels" in task.module_args["definition"]["metadata"]
        assert "environment" in task.module_args["definition"]["metadata"]["labels"]
        assert task.module_args["definition"]["metadata"]["labels"]["environment"] == "dev"

    def test_translate_snapshot_to_volumesnapshot(self):
        """Test translation of New-Snapshot to VolumeSnapshot."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text="New-Snapshot -VM MyVM -Name snap1",
            statement_type="cmdlet",
            category="integration",
            cmdlet="New-Snapshot",
            parameters={"VM": "MyVM", "Name": "snap1"},
            integration_type="snapshot",
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_snapshot(stmt)

        assert task is not None
        assert task.module == "kubevirt.core.kubevirt_vm_snapshot"
        assert task.module_args["state"] == "present"
        assert task.module_args["name"] == "snap1"
        assert task.module_args["vm_name"] == "MyVM"

    def test_translate_network_adapter_blocked_without_profile(self):
        """Test New-NetworkAdapter generates BLOCKED stub without profile."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text='New-NetworkAdapter -VM MyVM -NetworkName "prod-net"',
            statement_type="cmdlet",
            category="integration",
            cmdlet="New-NetworkAdapter",
            parameters={"VM": "MyVM", "NetworkName": "prod-net"},
            integration_type="network",
            integration_evidence='New-NetworkAdapter -NetworkName "prod-net"',
        )

        # Translator without profile
        translator = PowerShellToAnsibleTranslator(profile=None)
        task = translator._translate_network_adapter(stmt)

        assert task is not None
        assert task.module == "ansible.builtin.fail"
        assert "BLOCKED" in task.module_args["msg"]
        assert "network_security" in task.module_args["msg"]
        assert "blocked" in task.tags

    def test_translate_network_adapter_with_profile(self):
        """Test New-NetworkAdapter generates adapter call with profile."""
        profile = ProfileSchema(
            name="test-profile",
            environments={
                "dev": EnvironmentConfig(openshift_api_url="https://api.test.com:6443")
            },
            network_security=NetworkSecurityConfig(
                model="networkpolicy", default_isolation="namespace"
            ),
        )

        stmt = PowerCLIStatement(
            line_number=1,
            raw_text='New-NetworkAdapter -VM MyVM -NetworkName "prod-net"',
            statement_type="cmdlet",
            category="integration",
            cmdlet="New-NetworkAdapter",
            parameters={"VM": "MyVM", "NetworkName": "prod-net"},
            integration_type="network",
        )

        translator = PowerShellToAnsibleTranslator(profile=profile)
        task = translator._translate_network_adapter(stmt)

        assert task is not None
        assert task.module == "ansible.builtin.include_role"
        assert "adapters/nsx/create_segment" in task.module_args["name"]
        assert "blocked" not in task.tags

    def test_translate_get_vm_to_k8s_info(self):
        """Test translation of Get-VM to k8s_info lookup."""
        stmt = PowerCLIStatement(
            line_number=1,
            raw_text="Get-VM -Name MyVM",
            statement_type="cmdlet",
            category="lookup",
            cmdlet="Get-VM",
            parameters={"Name": "MyVM"},
        )

        translator = PowerShellToAnsibleTranslator()
        task = translator._translate_lookup(stmt)

        assert task is not None
        assert task.module == "kubernetes.core.k8s_info"
        assert task.module_args["kind"] == "VirtualMachine"
        assert task.module_args["name"] == "MyVM"

    def test_translate_complete_script(self, tmp_path):
        """Test end-to-end translation of complete PowerCLI script."""
        script_content = """# Provision VM
$Network = "dev-network"
New-VM -Name TestVM -NumCpu 4 -MemoryGB 8
New-TagAssignment -Entity TestVM -Tag "Environment:Dev"
Start-VM -VM TestVM
"""
        script_file = tmp_path / "provision.ps1"
        script_file.write_text(script_content)

        # Parse script
        parser = PowerCLIScriptParser()
        statements = parser.parse_file(script_file)

        # Translate to tasks
        translator = PowerShellToAnsibleTranslator()
        tasks = translator.translate_statements(statements)

        # Verify tasks generated
        assert len(tasks) >= 4  # Assignment, New-VM, Tag, Start-VM

        # Check for expected modules
        modules = [task.module for task in tasks]
        assert "ansible.builtin.set_fact" in modules
        assert "kubevirt.core.kubevirt_vm" in modules
        assert "kubernetes.core.k8s" in modules

    def test_translate_script_with_validation(self, tmp_path):
        """Test translation of script with validation logic."""
        script_content = """if ($NumCPU -gt 16) {
    throw "Production VMs limited to 16 CPUs"
}
New-VM -Name TestVM -NumCpu 8
"""
        script_file = tmp_path / "validate.ps1"
        script_file.write_text(script_content)

        parser = PowerCLIScriptParser()
        statements = parser.parse_file(script_file)

        translator = PowerShellToAnsibleTranslator()
        tasks = translator.translate_statements(statements)

        # Should have assert task for validation
        assert any(task.module == "ansible.builtin.assert" for task in tasks)

        # Find assert task and verify
        assert_task = next(t for t in tasks if t.module == "ansible.builtin.assert")
        assert "16 CPUs" in assert_task.module_args["fail_msg"]

    def test_deterministic_translation(self, tmp_path):
        """Test that same script produces identical translation."""
        script_content = """New-VM -Name TestVM -NumCpu 4
Start-VM -VM TestVM
"""
        script_file = tmp_path / "test.ps1"
        script_file.write_text(script_content)

        # Translate twice
        parser1 = PowerCLIScriptParser()
        statements1 = parser1.parse_file(script_file)
        translator1 = PowerShellToAnsibleTranslator()
        tasks1 = translator1.translate_statements(statements1)

        parser2 = PowerCLIScriptParser()
        statements2 = parser2.parse_file(script_file)
        translator2 = PowerShellToAnsibleTranslator()
        tasks2 = translator2.translate_statements(statements2)

        # Should produce identical tasks
        assert len(tasks1) == len(tasks2)
        for t1, t2 in zip(tasks1, tasks2):
            assert t1.module == t2.module
            assert t1.module_args == t2.module_args


class TestProfileDrivenTranslation:
    """Test profile-driven translation decisions."""

    def test_minimal_profile_produces_blocked_stubs(self, tmp_path):
        """Test minimal profile generates BLOCKED stubs for missing configs."""
        minimal_profile = ProfileSchema(
            name="minimal",
            environments={
                "dev": EnvironmentConfig(openshift_api_url="https://api.test.com:6443")
            },
            # No network_security configured
        )

        script_content = 'New-NetworkAdapter -VM TestVM -NetworkName "prod-net"'
        script_file = tmp_path / "network.ps1"
        script_file.write_text(script_content)

        parser = PowerCLIScriptParser()
        statements = parser.parse_file(script_file)

        translator = PowerShellToAnsibleTranslator(profile=minimal_profile)
        tasks = translator.translate_statements(statements)

        # Should have BLOCKED stub
        assert len(tasks) == 1
        assert tasks[0].module == "ansible.builtin.fail"
        assert "BLOCKED" in tasks[0].module_args["msg"]

    def test_complete_profile_produces_functional_tasks(self, tmp_path):
        """Test complete profile generates functional tasks."""
        complete_profile = ProfileSchema(
            name="complete",
            environments={
                "dev": EnvironmentConfig(openshift_api_url="https://api.test.com:6443")
            },
            network_security=NetworkSecurityConfig(
                model="networkpolicy", default_isolation="namespace"
            ),
        )

        script_content = 'New-NetworkAdapter -VM TestVM -NetworkName "prod-net"'
        script_file = tmp_path / "network.ps1"
        script_file.write_text(script_content)

        parser = PowerCLIScriptParser()
        statements = parser.parse_file(script_file)

        translator = PowerShellToAnsibleTranslator(profile=complete_profile)
        tasks = translator.translate_statements(statements)

        # Should have functional adapter call
        assert len(tasks) == 1
        assert tasks[0].module == "ansible.builtin.include_role"
        assert "BLOCKED" not in str(tasks[0].module_args)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
