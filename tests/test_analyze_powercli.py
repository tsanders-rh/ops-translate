"""
Unit tests for PowerCLI script analyzer.

Tests detection of:
- VMware cmdlets (New-VM, Set-VM, etc.)
- NSX cmdlets (Get-NsxSecurityGroup, etc.)
- REST API calls (Invoke-RestMethod, etc.)
- Risk signals (Import-Module, credentials, etc.)
"""

import tempfile
from pathlib import Path

import pytest

from ops_translate.analyze.powercli import (
    analyze_powercli_script,
    calculate_complexity,
    detect_nsx_cmdlets,
    detect_rest_calls,
    detect_risk_signals,
    detect_vmware_cmdlets,
)


class TestVMwareCmdletDetection:
    """Test VMware cmdlet detection."""

    def test_detect_vm_lifecycle_cmdlets(self):
        """Test detection of VM lifecycle cmdlets."""
        script = """
        # Create and start a VM
        New-VM -Name $VMName -NumCpu 4 -MemoryGB 8
        Start-VM -VM $VMName
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_vmware_cmdlets(script, script_file)

            assert "vm_lifecycle" in result
            assert len(result["vm_lifecycle"]) == 2

            # Check New-VM detection
            new_vm = next((op for op in result["vm_lifecycle"] if op["cmdlet"] == "New-VM"), None)
            assert new_vm is not None
            assert new_vm["confidence"] == 0.95
            assert new_vm["line"] == 3

            # Check Start-VM detection
            start_vm = next(
                (op for op in result["vm_lifecycle"] if op["cmdlet"] == "Start-VM"), None
            )
            assert start_vm is not None
            assert start_vm["line"] == 4
        finally:
            script_file.unlink()

    def test_detect_compute_cmdlets(self):
        """Test detection of compute-related cmdlets."""
        script = """
        Get-VMHost | Select-Object Name
        Get-Cluster -Name "Production"
        Get-ResourcePool
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_vmware_cmdlets(script, script_file)

            assert "compute" in result
            assert len(result["compute"]) == 3

            cmdlets = [op["cmdlet"] for op in result["compute"]]
            assert "Get-VMHost" in cmdlets
            assert "Get-Cluster" in cmdlets
            assert "Get-ResourcePool" in cmdlets
        finally:
            script_file.unlink()

    def test_detect_storage_cmdlets(self):
        """Test detection of storage cmdlets."""
        script = """
        $ds = Get-Datastore -Name "datastore1"
        New-HardDisk -VM $vm -CapacityGB 100
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_vmware_cmdlets(script, script_file)

            assert "storage" in result
            assert len(result["storage"]) == 2

            cmdlets = [op["cmdlet"] for op in result["storage"]]
            assert "Get-Datastore" in cmdlets
            assert "New-HardDisk" in cmdlets
        finally:
            script_file.unlink()

    def test_detect_tagging_cmdlets(self):
        """Test detection of tagging cmdlets."""
        script = """
        New-TagAssignment -Entity $vm -Tag "Production"
        Set-Annotation -Entity $vm -CustomAttribute "Owner" -Value "admin"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_vmware_cmdlets(script, script_file)

            assert "tagging" in result
            assert len(result["tagging"]) == 2
        finally:
            script_file.unlink()

    def test_case_insensitive_detection(self):
        """Test that cmdlet detection is case-insensitive."""
        script = """
        new-vm -Name "test"
        NEW-VM -Name "test2"
        New-Vm -Name "test3"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_vmware_cmdlets(script, script_file)

            assert "vm_lifecycle" in result
            assert len(result["vm_lifecycle"]) == 3
        finally:
            script_file.unlink()


class TestNSXCmdletDetection:
    """Test NSX cmdlet detection."""

    def test_detect_security_groups(self):
        """Test detection of NSX security group cmdlets."""
        script = """
        Get-NsxSecurityGroup -Name "WebServers"
        New-NsxSecurityGroup -Name "AppServers"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_nsx_cmdlets(script, script_file)

            assert "security_groups" in result
            assert len(result["security_groups"]) == 2

            cmdlets = [op["cmdlet"] for op in result["security_groups"]]
            assert "Get-NsxSecurityGroup" in cmdlets
            assert "New-NsxSecurityGroup" in cmdlets
        finally:
            script_file.unlink()

    def test_detect_firewall_rules(self):
        """Test detection of NSX firewall cmdlets."""
        script = """
        New-NsxFirewallRule -Name "AllowHTTP" -Source $webSg -Destination $dbSg
        Get-NsxFirewallRule
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_nsx_cmdlets(script, script_file)

            assert "firewall_rules" in result
            assert len(result["firewall_rules"]) == 2
        finally:
            script_file.unlink()

    def test_detect_load_balancers(self):
        """Test detection of NSX load balancer cmdlets."""
        script = """
        New-NsxLoadBalancer -Name "WebLB"
        New-NsxLoadBalancerPool -Name "WebPool"
        New-NsxLoadBalancerVirtualServer -Name "WebVIP"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_nsx_cmdlets(script, script_file)

            assert "load_balancers" in result
            assert len(result["load_balancers"]) == 3
        finally:
            script_file.unlink()

    def test_detect_generic_nsx_cmdlets(self):
        """Test detection of generic NSX cmdlets not in specific categories."""
        script = """
        Get-NsxEdge -Name "Edge01"
        New-NsxIpPool -Name "VIPPool"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_nsx_cmdlets(script, script_file)

            assert "other" in result
            assert len(result["other"]) == 2

            # Generic NSX cmdlets have slightly lower confidence
            for op in result["other"]:
                assert op["confidence"] == 0.85
        finally:
            script_file.unlink()


class TestRESTAPIDetection:
    """Test REST API call detection."""

    def test_detect_invoke_restmethod(self):
        """Test detection of Invoke-RestMethod."""
        script = """
        Invoke-RestMethod -Uri "https://api.example.com/v1/resource" -Method POST
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_rest_calls(script, script_file)

            assert len(result) == 1
            assert result[0]["endpoint"] == "https://api.example.com/v1/resource"
            assert result[0]["method"] == "POST"
            assert result[0]["call_type"] == "Invoke-RestMethod"
            assert result[0]["confidence"] == 0.9
        finally:
            script_file.unlink()

    def test_detect_invoke_webrequest(self):
        """Test detection of Invoke-WebRequest."""
        script = """
        Invoke-WebRequest -Uri "https://api.example.com/data" -Method GET
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_rest_calls(script, script_file)

            assert len(result) == 1
            assert result[0]["endpoint"] == "https://api.example.com/data"
            assert result[0]["method"] == "GET"
            assert result[0]["call_type"] == "Invoke-WebRequest"
        finally:
            script_file.unlink()

    def test_detect_curl(self):
        """Test detection of curl commands."""
        script = """
        curl -X POST https://api.example.com/endpoint
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_rest_calls(script, script_file)

            assert len(result) == 1
            assert result[0]["endpoint"] == "https://api.example.com/endpoint"
            assert result[0]["method"] == "POST"
            assert result[0]["call_type"] == "curl"
        finally:
            script_file.unlink()

    def test_detect_nsx_v_api(self):
        """Test detection of NSX-V API calls."""
        uri = "https://nsx-manager.example.com/api/2.0/services/securitygroup"
        script = f"""
        Invoke-RestMethod -Uri "{uri}/scope/globalroot-0" -Method GET
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_rest_calls(script, script_file)

            assert len(result) == 1
            assert result[0]["nsx_api"] is True
            assert result[0]["nsx_version"] == "NSX-V"
            assert result[0]["confidence"] == 0.95  # Higher confidence for NSX API
            assert "/api/2.0/" in result[0]["endpoint"]
        finally:
            script_file.unlink()

    def test_detect_nsx_t_api(self):
        """Test detection of NSX-T API calls."""
        uri = "https://nsx-t.example.com/policy/api/v1/infra/domains"
        script = f"""
        Invoke-RestMethod -Uri "{uri}/default/groups" -Method POST
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_rest_calls(script, script_file)

            assert len(result) == 1
            assert result[0]["nsx_api"] is True
            assert result[0]["nsx_version"] == "NSX-T"
            assert result[0]["confidence"] == 0.95
            assert "/policy/api/" in result[0]["endpoint"]
        finally:
            script_file.unlink()

    def test_detect_non_nsx_rest_call(self):
        """Test that non-NSX REST calls are not flagged as NSX API."""
        script = """
        Invoke-RestMethod -Uri "https://cmdb.example.com/api/servers" -Method GET
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_rest_calls(script, script_file)

            assert len(result) == 1
            assert result[0]["nsx_api"] is False
            assert result[0]["nsx_version"] is None
            assert result[0]["confidence"] == 0.9  # Normal confidence
        finally:
            script_file.unlink()


class TestRiskSignalDetection:
    """Test security and complexity risk signal detection."""

    def test_detect_module_import(self):
        """Test detection of Import-Module."""
        script = """
        Import-Module VMware.PowerCLI
        Import-Module CustomModule
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_risk_signals(script, script_file)

            module_imports = [sig for sig in result if sig["type"] == "module_import"]
            assert len(module_imports) == 2

            modules = [sig["module"] for sig in module_imports]
            assert "VMware.PowerCLI" in modules
            assert "CustomModule" in modules

            for sig in module_imports:
                assert sig["severity"] == "medium"
                assert sig["confidence"] == 0.95
        finally:
            script_file.unlink()

    def test_detect_type_loading(self):
        """Test detection of Add-Type."""
        script = """
        Add-Type -AssemblyName System.Windows.Forms
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_risk_signals(script, script_file)

            type_loads = [sig for sig in result if sig["type"] == "type_loading"]
            assert len(type_loads) == 1
            assert type_loads[0]["severity"] == "high"
        finally:
            script_file.unlink()

    def test_detect_process_execution(self):
        """Test detection of Start-Process."""
        script = """
        Start-Process -FilePath "notepad.exe"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_risk_signals(script, script_file)

            process_exec = [sig for sig in result if sig["type"] == "process_execution"]
            assert len(process_exec) == 1
            assert process_exec[0]["severity"] == "high"
        finally:
            script_file.unlink()

    def test_detect_ssh_command(self):
        """Test detection of SSH commands."""
        script = """
        ssh user@server "ls -la"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_risk_signals(script, script_file)

            ssh_cmds = [sig for sig in result if sig["type"] == "ssh_command"]
            assert len(ssh_cmds) == 1
            assert ssh_cmds[0]["severity"] == "medium"
        finally:
            script_file.unlink()

    def test_detect_inline_credentials(self):
        """Test detection of inline credentials."""
        script = """
        Connect-VIServer -Server vcenter -User admin -Password "P@ssw0rd123"
        $cred = ConvertTo-SecureString "secret" -AsPlainText -Force
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_risk_signals(script, script_file)

            creds = [sig for sig in result if sig["type"] == "inline_credential"]
            assert len(creds) == 2

            for sig in creds:
                assert sig["severity"] == "high"
                # Verify credentials are redacted in evidence
                assert "***REDACTED***" in sig["evidence"]
                assert "P@ssw0rd123" not in sig["evidence"]
                assert "secret" not in sig["evidence"]
        finally:
            script_file.unlink()

    def test_detect_hardcoded_endpoints(self):
        """Test detection of hardcoded IP addresses and URLs."""
        script = """
        $server = "192.168.1.100"
        Invoke-RestMethod -Uri "https://api.example.com/endpoint"
        Connect-VIServer -Server 10.0.0.1:443
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_risk_signals(script, script_file)

            endpoints = [sig for sig in result if sig["type"] == "hardcoded_endpoint"]
            assert len(endpoints) >= 3

            detected_endpoints = [sig["endpoint"] for sig in endpoints]
            assert "192.168.1.100" in detected_endpoints
            assert "10.0.0.1:443" in detected_endpoints

            for sig in endpoints:
                assert sig["severity"] == "low"
        finally:
            script_file.unlink()

    def test_skip_comments(self):
        """Test that commented-out risk signals are ignored."""
        script = """
        # Import-Module ShouldNotDetect
        # Add-Type -AssemblyName Fake
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = detect_risk_signals(script, script_file)

            # Should not detect anything in comments
            assert len(result) == 0
        finally:
            script_file.unlink()


class TestComplexityCalculation:
    """Test complexity score calculation."""

    def test_calculate_complexity_basic(self):
        """Test basic complexity calculation."""
        vmware_ops = {"vm_lifecycle": [{"cmdlet": "New-VM"}]}  # 1 point
        nsx_ops = {"security_groups": [{"cmdlet": "Get-NsxSecurityGroup"}]}  # 5 points
        rest_calls = [{"endpoint": "api.com"}]  # 3 points
        risk_signals = [{"type": "module_import"}]  # 2 points

        complexity = calculate_complexity(vmware_ops, nsx_ops, rest_calls, risk_signals)

        assert complexity == 11  # 1 + 5 + 3 + 2

    def test_calculate_complexity_capped_at_100(self):
        """Test that complexity is capped at 100."""
        # Create enough operations to exceed 100
        vmware_ops = {"vm_lifecycle": [{"cmdlet": f"New-VM-{i}"} for i in range(50)]}
        nsx_ops = {"security_groups": [{"cmdlet": f"Get-Nsx-{i}"} for i in range(20)]}
        rest_calls = [{"endpoint": f"api{i}.com"} for i in range(10)]
        risk_signals = [{"type": "module_import"} for i in range(10)]

        complexity = calculate_complexity(vmware_ops, nsx_ops, rest_calls, risk_signals)

        assert complexity == 100  # Capped at 100


class TestFullAnalysis:
    """Test full PowerCLI script analysis."""

    def test_analyze_simple_script(self):
        """Test analyzing a simple PowerCLI script."""
        script = """
        # Simple VM provisioning
        Connect-VIServer -Server vcenter.example.com
        New-VM -Name "web-server" -NumCpu 4 -MemoryGB 8
        Start-VM -VM "web-server"
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = analyze_powercli_script(script_file)

            # Check basic structure
            assert "source_file" in result
            assert "signals" in result
            assert "vmware_operations" in result
            assert "has_external_dependencies" in result

            # Check VMware operations detected
            assert result["has_external_dependencies"] is True
            assert len(result["vmware_operations"]["vm_lifecycle"]) == 2

            # Check risk signals (hardcoded endpoint)
            assert "risk_signals" in result
            endpoints = [s for s in result["risk_signals"] if s["type"] == "hardcoded_endpoint"]
            assert len(endpoints) >= 1

            # Check complexity
            assert result["complexity_score"] > 0
        finally:
            script_file.unlink()

    def test_analyze_complex_script_with_nsx(self):
        """Test analyzing a complex script with NSX operations."""
        script = """
        Import-Module VMware.PowerCLI
        Connect-VIServer -Server vcenter.example.com

        # Create VM
        $vm = New-VM -Name "app-server" -NumCpu 8 -MemoryGB 16

        # NSX Security
        $sg = New-NsxSecurityGroup -Name "AppServers"
        New-NsxFirewallRule -Name "AllowHTTP" -Source $sg

        # REST API call
        Invoke-RestMethod -Uri "https://cmdb.example.com/api/register" -Method POST
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = analyze_powercli_script(script_file)

            # Check all detection categories
            assert len(result["vmware_operations"]["vm_lifecycle"]) >= 1
            assert len(result["nsx_operations"]["security_groups"]) >= 1
            assert len(result["nsx_operations"]["firewall_rules"]) >= 1
            assert len(result["rest_api_calls"]) >= 1

            # Check risk signals
            module_imports = [s for s in result["risk_signals"] if s["type"] == "module_import"]
            assert len(module_imports) >= 1

            # Higher complexity due to NSX
            assert result["complexity_score"] >= 10
        finally:
            script_file.unlink()

    def test_analyze_empty_script(self):
        """Test analyzing an empty script."""
        script = """
        # Just comments
        # No actual commands
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as f:
            f.write(script)
            f.flush()
            script_file = Path(f.name)

        try:
            result = analyze_powercli_script(script_file)

            assert result["has_external_dependencies"] is False
            assert result["complexity_score"] == 0
            assert len(result["risk_signals"]) == 0
        finally:
            script_file.unlink()

    def test_analyze_nonexistent_file(self):
        """Test analyzing a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            analyze_powercli_script(Path("/nonexistent/script.ps1"))
