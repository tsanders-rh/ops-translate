"""
Tests for PowerCLI script parsing.

Validates statement parsing, categorization, and integration detection.
"""

from pathlib import Path

import pytest

from ops_translate.translate.powercli_script import PowerCLIScriptParser


class TestPowerCLIScriptParser:
    """Test PowerCLI script parsing."""

    def test_parse_variable_assignment(self):
        """Test parsing of variable assignments."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement('$Network = "dev-network"', 1)

        assert stmt is not None
        assert stmt.statement_type == "assignment"
        assert stmt.category == "context"
        assert stmt.parameters["variable"] == "Network"
        assert stmt.parameters["value"] == '"dev-network"'

    def test_parse_cmdlet_invocation(self):
        """Test parsing of PowerCLI cmdlet."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("New-VM -Name MyVM -NumCpu 4 -MemoryGB 8", 1)

        assert stmt is not None
        assert stmt.statement_type == "cmdlet"
        assert stmt.cmdlet == "New-VM"
        assert stmt.parameters["Name"] == "MyVM"
        assert stmt.parameters["NumCpu"] == "4"
        assert stmt.parameters["MemoryGB"] == "8"

    def test_parse_throw_statement(self):
        """Test parsing of throw statement (validation gate)."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement('throw "CPU limit exceeded"', 1)

        assert stmt is not None
        assert stmt.statement_type == "control_flow"
        assert stmt.control_type == "throw"

    def test_parse_if_statement(self):
        """Test parsing of if statement."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("if ($NumCPU -gt 16)", 1)

        assert stmt is not None
        assert stmt.statement_type == "control_flow"
        assert stmt.control_type == "if"
        assert "$NumCPU -gt 16" in stmt.condition

    def test_parse_comment(self):
        """Test parsing of comment lines."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("# This is a comment", 1)

        assert stmt is not None
        assert stmt.statement_type == "comment"

    def test_parse_empty_line(self):
        """Test parsing of empty lines."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("", 1)

        assert stmt is None

    def test_categorize_get_cmdlet_as_lookup(self):
        """Test Get-* cmdlets categorized as lookup."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("Get-VM -Name MyVM", 1)

        assert stmt is not None
        assert stmt.cmdlet == "Get-VM"
        assert stmt.category == "lookup"

    def test_categorize_new_cmdlet_as_mutation(self):
        """Test New-* cmdlets categorized as mutation."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("New-VM -Name MyVM", 1)

        assert stmt is not None
        assert stmt.cmdlet == "New-VM"
        assert stmt.category == "mutation"

    def test_categorize_tagging_as_integration(self):
        """Test New-TagAssignment categorized as integration."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement('New-TagAssignment -Entity MyVM -Tag "Env:Dev"', 1)

        assert stmt is not None
        assert stmt.cmdlet == "New-TagAssignment"
        assert stmt.category == "integration"

    def test_categorize_snapshot_as_integration(self):
        """Test New-Snapshot categorized as integration."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("New-Snapshot -VM MyVM -Name snap1", 1)

        assert stmt is not None
        assert stmt.cmdlet == "New-Snapshot"
        assert stmt.category == "integration"

    def test_categorize_network_adapter_as_integration(self):
        """Test New-NetworkAdapter categorized as integration."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement('New-NetworkAdapter -VM MyVM -NetworkName "prod"', 1)

        assert stmt is not None
        assert stmt.cmdlet == "New-NetworkAdapter"
        assert stmt.category == "integration"

    def test_detect_tagging_integration(self):
        """Test tagging integration detection."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement('New-TagAssignment -Tag "Environment:Dev"', 1)

        assert stmt is not None
        assert stmt.integration_type == "tagging"
        assert "Environment:Dev" in stmt.integration_evidence

    def test_detect_snapshot_integration(self):
        """Test snapshot integration detection."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("New-Snapshot -VM MyVM", 1)

        assert stmt is not None
        assert stmt.integration_type == "snapshot"
        assert stmt.integration_evidence == "New-Snapshot"

    def test_detect_network_integration(self):
        """Test network adapter integration detection."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement('New-NetworkAdapter -NetworkName "prod-net"', 1)

        assert stmt is not None
        assert stmt.integration_type == "network"
        assert "prod-net" in stmt.integration_evidence

    def test_parse_cmdlet_with_variable_parameters(self):
        """Test parsing cmdlet with variable parameters."""
        parser = PowerCLIScriptParser()
        stmt = parser._parse_statement("New-VM -Name $VMName -NumCpu $CPUCount", 1)

        assert stmt is not None
        assert stmt.cmdlet == "New-VM"
        assert stmt.parameters["Name"] == "$VMName"
        assert stmt.parameters["NumCpu"] == "$CPUCount"

    def test_parse_file_with_simple_script(self, tmp_path):
        """Test parsing complete PowerCLI script."""
        script_content = """# Provision VM script
$Network = "dev-network"
New-VM -Name $VMName -NumCpu 4 -MemoryGB 8
Start-VM -VM $VMName
"""
        script_file = tmp_path / "provision.ps1"
        script_file.write_text(script_content)

        parser = PowerCLIScriptParser()
        statements = parser.parse_file(script_file)

        # Filter out comments and empty lines
        non_trivial = [s for s in statements if s.statement_type not in ["comment"]]

        assert len(non_trivial) >= 3
        assert any(s.statement_type == "assignment" for s in non_trivial)
        assert any(s.cmdlet == "New-VM" for s in non_trivial)
        assert any(s.cmdlet == "Start-VM" for s in non_trivial)

    def test_parse_file_with_validation(self, tmp_path):
        """Test parsing script with validation logic."""
        script_content = """if ($NumCPU -gt 16) {
    throw "CPU limit exceeded"
}
"""
        script_file = tmp_path / "validate.ps1"
        script_file.write_text(script_content)

        parser = PowerCLIScriptParser()
        statements = parser.parse_file(script_file)

        assert any(s.control_type == "if" for s in statements)
        assert any(s.control_type == "throw" for s in statements)

    def test_parse_file_with_integrations(self, tmp_path):
        """Test parsing script with integration calls."""
        script_content = """New-VM -Name MyVM -NumCpu 4
New-TagAssignment -Entity MyVM -Tag "Environment:Dev"
New-Snapshot -VM MyVM -Name snap1
"""
        script_file = tmp_path / "integrations.ps1"
        script_file.write_text(script_content)

        parser = PowerCLIScriptParser()
        statements = parser.parse_file(script_file)

        # Check integration types detected
        integration_stmts = [s for s in statements if s.category == "integration"]
        assert len(integration_stmts) == 2  # Tagging and snapshot

        assert any(s.integration_type == "tagging" for s in integration_stmts)
        assert any(s.integration_type == "snapshot" for s in integration_stmts)

    def test_parse_existing_fixture(self):
        """Test parsing the existing simple-vm.ps1 fixture."""
        fixture_path = Path(__file__).parent / "fixtures/powercli/simple-vm.ps1"

        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        parser = PowerCLIScriptParser()
        statements = parser.parse_file(fixture_path)

        # Should successfully parse without errors
        assert len(statements) > 0

        # Check for expected statement types
        assert any(s.statement_type == "cmdlet" for s in statements)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
