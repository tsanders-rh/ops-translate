<#
.SYNOPSIS
    Provision a new virtual machine with environment-specific configuration

.DESCRIPTION
    This script provisions a virtual machine in VMware vSphere with
    environment-based network and storage profiles, tagging, and governance.

.PARAMETER VMName
    Name of the virtual machine to create

.PARAMETER Environment
    Target environment (dev or prod)

.PARAMETER CPUCount
    Number of CPU cores to allocate

.PARAMETER MemoryGB
    Amount of memory in GB

.PARAMETER OwnerEmail
    Email address of the VM owner

.PARAMETER CostCenter
    Optional cost center for chargeback tracking

.EXAMPLE
    .\provision-vm.ps1 -VMName "web-server-01" -Environment "dev" -CPUCount 2 -MemoryGB 4 -OwnerEmail "admin@example.com"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, HelpMessage="Name of the VM to create")]
    [ValidateNotNullOrEmpty()]
    [string]$VMName,

    [Parameter(Mandatory=$true, HelpMessage="Target environment")]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",

    [Parameter(Mandatory=$true, HelpMessage="Number of CPU cores")]
    [ValidateRange(1, 32)]
    [int]$CPUCount = 2,

    [Parameter(Mandatory=$true, HelpMessage="Memory in GB")]
    [ValidateRange(1, 256)]
    [int]$MemoryGB = 4,

    [Parameter(Mandatory=$true, HelpMessage="Owner email for tracking")]
    [ValidatePattern("^[^@]+@[^@]+\.[^@]+$")]
    [string]$OwnerEmail,

    [Parameter(Mandatory=$false, HelpMessage="Cost center code")]
    [string]$CostCenter
)

# Environment-specific configuration profiles
$NetworkProfile = if ($Environment -eq "prod") {
    "prod-network"
} else {
    "dev-network"
}

$StorageProfile = if ($Environment -eq "prod") {
    "storage-gold"
} else {
    "storage-standard"
}

$Cluster = if ($Environment -eq "prod") {
    "prod-cluster"
} else {
    "dev-cluster"
}

# Governance check for production deployments
if ($Environment -eq "prod") {
    Write-Warning "Production deployment detected. Ensure proper approval is obtained."
    Write-Host "Approval required for: $VMName in environment: $Environment"
    Write-Host "Owner: $OwnerEmail"

    # In a real scenario, this might integrate with an approval system
    $confirmation = Read-Host "Have you obtained approval? (yes/no)"
    if ($confirmation -ne "yes") {
        Write-Error "Deployment cancelled - approval not confirmed"
        exit 1
    }
}

# Display provisioning summary
Write-Host "`n========== VM Provisioning Summary =========="
Write-Host "VM Name:       $VMName"
Write-Host "Environment:   $Environment"
Write-Host "CPU:           $CPUCount cores"
Write-Host "Memory:        $MemoryGB GB"
Write-Host "Network:       $NetworkProfile"
Write-Host "Storage:       $StorageProfile"
Write-Host "Owner:         $OwnerEmail"
if ($CostCenter) {
    Write-Host "Cost Center:   $CostCenter"
}
Write-Host "============================================`n"

# Create the virtual machine
# Note: In actual use, you would connect to vCenter first
# Connect-VIServer -Server vcenter.example.com

try {
    Write-Host "Creating virtual machine: $VMName"

    # VM creation parameters
    $vmParams = @{
        Name = $VMName
        NumCpu = $CPUCount
        MemoryGB = $MemoryGB
        NetworkName = $NetworkProfile
        Datastore = $StorageProfile
        GuestId = "rhel8_64Guest"
        DiskGB = 50
    }

    # Create VM (commented out for example purposes)
    # $vm = New-VM @vmParams -Confirm:$false

    Write-Host "VM created successfully: $VMName" -ForegroundColor Green

    # Apply tags for tracking and governance
    Write-Host "Applying metadata tags..."

    $tags = @{
        "env" = $Environment
        "owner" = $OwnerEmail
        "managed-by" = "ops-translate"
        "provisioned-date" = (Get-Date -Format "yyyy-MM-dd")
    }

    if ($CostCenter) {
        $tags["costCenter"] = $CostCenter
    }

    # Apply each tag (commented out for example)
    foreach ($tagKey in $tags.Keys) {
        $tagValue = $tags[$tagKey]
        Write-Host "  - $tagKey = $tagValue"
        # New-TagAssignment -Entity $vm -Tag "${tagKey}:${tagValue}" -Confirm:$false
    }

    # Set custom attributes for additional metadata
    # Set-Annotation -Entity $vm -CustomAttribute "Owner" -Value $OwnerEmail
    # Set-Annotation -Entity $vm -CustomAttribute "Environment" -Value $Environment

    Write-Host "`nProvisioning completed successfully!" -ForegroundColor Green
    Write-Host "VM $VMName is ready for use.`n"

} catch {
    Write-Error "Failed to provision VM: $_"
    exit 1
}

# Output VM details
Write-Host "Day 2 operations supported:"
Write-Host "  - Start VM:        Start-VM -VM $VMName"
Write-Host "  - Stop VM:         Stop-VM -VM $VMName"
Write-Host "  - Reconfigure VM:  Set-VM -VM $VMName -NumCpu <count> -MemoryGB <size>"
Write-Host ""
