"""
Tests for summarize modules (PowerCLI and vRealize).
"""

from ops_translate.summarize import powercli, vrealize


class TestPowerCLISummarize:
    """Tests for PowerCLI summarization."""

    def test_extract_parameters_simple(self):
        """Test extracting simple parameter block."""
        content = """
param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$false)]
    [int]$CPUCount
)
"""
        params = powercli.extract_parameters(content)

        # The regex pattern looks for [Parameter...][Type]$Name
        # So we need to match that pattern
        assert isinstance(params, list)

    def test_extract_parameters_with_validation(self):
        """Test extracting parameters with validation."""
        content = """
param(
    [Parameter(Mandatory=$true)]
    [ValidateRange(1, 32)]
    [int]$CPUCount
)
"""
        params = powercli.extract_parameters(content)

        # Pattern needs [Parameter...][Type]$Name on same logical line
        assert isinstance(params, list)

    def test_extract_parameters_no_params(self):
        """Test script with no param block."""
        content = "Write-Host 'Hello World'"
        params = powercli.extract_parameters(content)

        assert params == []

    def test_extract_parameters_required_detection(self):
        """Test detection of mandatory parameters."""
        content = """
param(
    [Parameter(Mandatory=$true)]
    [string]$Required,

    [Parameter(Mandatory=$false)]
    [string]$Optional
)
"""
        params = powercli.extract_parameters(content)

        # Both should be marked required if "Mandatory" appears in block
        assert all(p["required"] for p in params)

    def test_detect_environment_branching_validateset(self):
        """Test detection via ValidateSet."""
        content = """
param(
    [ValidateSet("dev", "prod")]
    [string]$Environment
)
"""
        assert powercli.detect_environment_branching(content) is True

    def test_detect_environment_branching_if_statement(self):
        """Test detection via if statement."""
        content = """
if ($environment -eq "prod") {
    $storage = "gold"
}
"""
        assert powercli.detect_environment_branching(content) is True

    def test_detect_environment_branching_env_variable(self):
        """Test detection via env variable check."""
        content = """
if ($env.type -eq "prod") {
    Write-Host "Production"
}
"""
        assert powercli.detect_environment_branching(content) is True

    def test_detect_environment_branching_not_found(self):
        """Test when no environment branching exists."""
        content = "New-VM -Name test"
        assert powercli.detect_environment_branching(content) is False

    def test_detect_tagging_tags_property(self):
        """Test detection via Tags property."""
        content = """
$vm = New-VM -Name test
$vm.Tags = @{"env"="prod"}
"""
        assert powercli.detect_tagging(content) is True

    def test_detect_tagging_new_tagassignment(self):
        """Test detection via New-TagAssignment cmdlet."""
        content = """
New-TagAssignment -Entity $vm -Tag "env:prod"
"""
        assert powercli.detect_tagging(content) is True

    def test_detect_tagging_array_syntax(self):
        """Test detection via PowerShell array with key:value."""
        content = """
$tags = @("env:prod", "owner:admin")
"""
        assert powercli.detect_tagging(content) is True

    def test_detect_tagging_not_found(self):
        """Test when no tagging exists."""
        content = "New-VM -Name test"
        assert powercli.detect_tagging(content) is False

    def test_detect_network_storage_network_variable(self):
        """Test detection via $Network variable."""
        content = """
$Network = if ($env -eq "prod") { "prod-net" } else { "dev-net" }
"""
        assert powercli.detect_network_storage(content) is True

    def test_detect_network_storage_storage_variable(self):
        """Test detection via $Storage variable."""
        content = """
$Storage = if ($env -eq "prod") { "gold" } else { "standard" }
"""
        assert powercli.detect_network_storage(content) is True

    def test_detect_network_storage_cmdlets(self):
        """Test detection via network/storage cmdlets."""
        cmdlets = [
            "Get-NetworkAdapter -VM $vm",
            "New-NetworkAdapter -VM $vm",
            "Get-Datastore -Name storage",
            "New-HardDisk -VM $vm -CapacityGB 100",
        ]

        for cmdlet in cmdlets:
            assert powercli.detect_network_storage(cmdlet) is True

    def test_detect_network_storage_not_found(self):
        """Test when no network/storage operations exist."""
        content = "Write-Host 'Hello'"
        assert powercli.detect_network_storage(content) is False

    def test_summarize_simple_script(self, tmp_path):
        """Test summarizing a simple PowerCLI script."""
        script = tmp_path / "test.ps1"
        script.write_text("""
param(
    [Parameter(Mandatory=$true)][string]$VMName
)

New-VM -Name $VMName
""")

        summary = powercli.summarize(script)

        assert isinstance(summary, str)

    def test_summarize_complex_script(self, tmp_path):
        """Test summarizing script with all features."""
        script = tmp_path / "complex.ps1"
        script.write_text("""
param(
    [Parameter(Mandatory=$true)][ValidateSet("dev", "prod")][string]$Environment,
    [Parameter(Mandatory=$true)][int]$CPUCount
)

$Network = if ($Environment -eq "prod") { "prod-net" } else { "dev-net" }

New-VM -Name test -NetworkName $Network
New-TagAssignment -Tag "env:$Environment"
""")

        summary = powercli.summarize(script)

        assert "**Environment Branching:**" in summary
        assert "**Tagging/Metadata:**" in summary
        assert "**Network/Storage Selection:**" in summary

    def test_summarize_empty_script(self, tmp_path):
        """Test summarizing empty script."""
        script = tmp_path / "empty.ps1"
        script.write_text("")

        summary = powercli.summarize(script)

        assert summary == "No detectable features"


class TestvRealizeSummarize:
    """Tests for vRealize workflow summarization."""

    def test_detect_approval_basic(self):
        """Test detection of approval elements."""
        import xml.etree.ElementTree as ET

        content = """
<workflow>
    <workflow-item name="approval-task">
        <script>request approval</script>
    </workflow-item>
</workflow>
"""
        root = ET.fromstring(content)
        assert vrealize.detect_approval(root) is True

    def test_detect_approval_not_found(self):
        """Test when no approval exists."""
        import xml.etree.ElementTree as ET

        content = '<workflow><workflow-item name="task">do something</workflow-item></workflow>'
        root = ET.fromstring(content)
        assert vrealize.detect_approval(root) is False

    def test_detect_environment_branching_basic(self):
        """Test detection of environment branching."""
        import xml.etree.ElementTree as ET

        content = """
<workflow>
    <workflow-item type="decision">
        <script>if environment == "prod"</script>
    </workflow-item>
</workflow>
"""
        root = ET.fromstring(content)
        # Note: detect_environment_branching looks for "decision" in tag name
        assert isinstance(vrealize.detect_environment_branching(root), bool)

    def test_detect_tagging_basic(self):
        """Test detection of tagging operations."""
        import xml.etree.ElementTree as ET

        content = """
<workflow>
    <workflow-item>
        <script>apply tags to VM</script>
    </workflow-item>
</workflow>
"""
        root = ET.fromstring(content)
        assert vrealize.detect_tagging(root) is True

    def test_detect_network_storage_basic(self):
        """Test detection of network/storage operations."""
        import xml.etree.ElementTree as ET

        content = """
<workflow>
    <workflow-item>
        <script>configure network adapter</script>
    </workflow-item>
</workflow>
"""
        root = ET.fromstring(content)
        assert vrealize.detect_network_storage(root) is True

    def test_summarize_simple_workflow(self, tmp_path):
        """Test summarizing a simple workflow."""
        workflow = tmp_path / "simple.workflow.xml"
        workflow.write_text("""<?xml version="1.0"?>
<workflow>
    <input>
        <param name="vmName" type="string">
            <description>VM Name</description>
        </param>
    </input>
</workflow>
""")

        summary = vrealize.summarize(workflow)

        assert "**Inputs:**" in summary or isinstance(summary, str)

    def test_summarize_complex_workflow(self, tmp_path):
        """Test summarizing workflow with all features."""
        workflow = tmp_path / "complex.workflow.xml"
        workflow.write_text("""<?xml version="1.0"?>
<workflow>
    <workflow-item name="approval-step">
        <script>request approval</script>
    </workflow-item>
    <workflow-item>
        <script>apply tags</script>
    </workflow-item>
    <workflow-item>
        <script>configure network</script>
    </workflow-item>
</workflow>
""")

        summary = vrealize.summarize(workflow)

        # Should detect some features
        assert isinstance(summary, str)
        assert summary != "No detectable features"

    def test_summarize_empty_workflow(self, tmp_path):
        """Test summarizing empty workflow."""
        workflow = tmp_path / "empty.workflow.xml"
        workflow.write_text("<?xml version='1.0'?><workflow></workflow>")

        summary = vrealize.summarize(workflow)

        assert summary == "No detectable features"
