# New-StandardVM.ps1
# Standard VM provisioning script - Updated version (conflicts with vRealize workflow)
# Author: Infrastructure Team
# Last Updated: 2023-08-15

<#
.SYNOPSIS
    Provisions a new virtual machine with standard configurations
.DESCRIPTION
    Creates a VM based on environment type. Uses different naming and tagging
    conventions than the vRealize orchestration workflows.
.PARAMETER vm_name
    Name of the virtual machine
.PARAMETER Environment
    Environment type: Development, Staging, Production (enum, not string!)
.PARAMETER cpu_cores
    Number of CPU cores (note: different from vRealize's cpuCount)
.PARAMETER memory_gb
    Memory in GB (integer type, not number)
.PARAMETER owner_email
    Owner's email address
.PARAMETER cost-center
    Cost center code (note: uses hyphen, not underscore)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$vm_name,

    [Parameter(Mandatory=$true)]
    [ValidateSet("Development", "Staging", "Production")]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [int]$cpu_cores,

    [Parameter(Mandatory=$true)]
    [int]$memory_gb,

    [Parameter(Mandatory=$true)]
    [string]$owner_email,

    [Parameter(Mandatory=$true)]
    [string]${cost-center}
)

# Connect to vCenter (different server than vRealize uses)
$vcServer = "vcenter-02.acme.internal"
Connect-VIServer -Server $vcServer

# Environment-based configuration (different logic than vRealize)
switch ($Environment) {
    "Production" {
        $cluster = "PROD-Cluster-01"  # Different cluster name!
        $datastore = "PROD-SAN-01"    # Different datastore!
        $network = "Production-Network"  # Different network name!
        $folder = "Production VMs"
    }
    "Staging" {
        $cluster = "STAGE-Cluster"    # PowerCLI uses STAGE, vRealize uses STAGING
        $datastore = "STAGE-SSD"
        $network = "Staging_Network"  # Underscore vs hyphen
        $folder = "Staging VMs"
    }
    "Development" {
        $cluster = "Development-Cluster"  # Full name vs DEV
        $datastore = "DEV-NFS-01"
        $network = "Dev-Net"
        $folder = "Dev VMs"
    }
}

Write-Host "Creating VM: $vm_name"
Write-Host "Environment: $Environment"
Write-Host "Cluster: $cluster"

# Create VM spec
$vmHost = Get-Cluster $cluster | Get-VMHost | Select-Object -First 1
$ds = Get-Datastore $datastore
$pg = Get-VirtualPortGroup -Name $network

# Create the VM (different approach than vRealize)
$vm = New-VM -Name $vm_name `
             -VMHost $vmHost `
             -Datastore $ds `
             -DiskGB 100 `
             -MemoryGB $memory_gb `
             -NumCpu $cpu_cores `
             -GuestId rhel8_64Guest `
             -NetworkName $network

# Apply tags (different tag structure than vRealize!)
# PowerCLI uses custom attributes differently
$vm | Set-Annotation -CustomAttribute "Environment" -Value $Environment
$vm | Set-Annotation -CustomAttribute "Owner" -Value $owner_email
$vm | Set-Annotation -CustomAttribute "cost-center" -Value ${cost-center}  # lowercase with hyphen
$vm | Set-Annotation -CustomAttribute "created-by" -Value "PowerCLI"  # Different key
$vm | Set-Annotation -CustomAttribute "creation-date" -Value (Get-Date -Format "yyyy-MM-dd")

# Move to folder
$targetFolder = Get-Folder -Name $folder
Move-VM -VM $vm -Destination $targetFolder

Write-Host "VM $vm_name created successfully"
Write-Host "IMPORTANT: Manually configure backup and monitoring"

Disconnect-VIServer -Server $vcServer -Confirm:$false
