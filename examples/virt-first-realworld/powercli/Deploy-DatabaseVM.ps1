# Deploy-DatabaseVM.ps1
# Database VM deployment - NEW VERSION
# Replaces old vRealize workflow (conflicts expected!)
# Author: Database Team
# Created: 2024-01-10

<#
.SYNOPSIS
    Deploys database VMs with updated standards
.DESCRIPTION
    New PowerCLI-based DB provisioning. Uses different parameters and
    resource allocation than the legacy vRealize "old_DB_provisioning" workflow.

    CONFLICTS WITH VREALIZE:
    - Uses db_name vs dbname
    - Uses environment enum vs string "prod"/"dev"
    - Uses different memory sizes
    - Uses different cluster names
.PARAMETER db_name
    Database name (note: underscore, not dbname)
.PARAMETER environment
    prod/dev as string (conflicts with vRealize enum)
.PARAMETER memory_size_gb
    Memory in GB (we now use 32GB standard, not 16GB)
.PARAMETER disk_size_gb
    Disk size in GB
.PARAMETER CostCenter
    Cost center (note: PascalCase, not hyphen or underscore!)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$db_name,

    [Parameter(Mandatory=$true)]
    [ValidateSet("prod", "dev", "uat")]  # lowercase strings, includes UAT
    [string]$environment,

    [Parameter(Mandatory=$false)]
    [int]$memory_size_gb = 32,  # New standard: 32GB (vRealize uses 16GB!)

    [Parameter(Mandatory=$false)]
    [int]$disk_size_gb = 500,

    [Parameter(Mandatory=$true)]
    [string]$CostCenter  # PascalCase!
)

# Connect to vCenter
Connect-VIServer -Server "vcenter.acme.internal"

Write-Host "=== Database VM Provisioning ==="
Write-Host "Database: $db_name"
Write-Host "Environment: $environment"
Write-Host "Memory: ${memory_size_gb}GB (NEW STANDARD - updated from 16GB)"

# Select resources (DIFFERENT from vRealize!)
if ($environment -eq "prod") {
    $clusterName = "PROD-DB-Cluster-New"  # Different cluster!
    $datastoreName = "PROD-SSD-NVME-01"   # Faster storage
    $networkName = "VLAN-250-DB"          # Different VLAN (250 not 200)
    $cpuCount = 16  # More CPUs than vRealize
} elseif ($environment -eq "uat") {
    $clusterName = "UAT-Cluster"
    $datastoreName = "UAT-SSD-01"
    $networkName = "VLAN-260-DB"
    $cpuCount = 8
} else {
    $clusterName = "DEV-Cluster-03"  # Cluster 03 (vRealize uses 02)
    $datastoreName = "DEV-SSD-01"
    $networkName = "VLAN-300-DB"
    $cpuCount = 8
}

Write-Host "Cluster: $clusterName"
Write-Host "Datastore: $datastoreName"
Write-Host "Network: $networkName"

# Get vCenter objects
$cluster = Get-Cluster -Name $clusterName -ErrorAction Stop
$vmHost = $cluster | Get-VMHost | Where-Object {$_.ConnectionState -eq 'Connected'} | Select-Object -First 1
$datastore = Get-Datastore -Name $datastoreName
$network = Get-VirtualPortGroup -Name $networkName

# Create VM
Write-Host "Creating VM..."
$vm = New-VM -Name $db_name `
             -VMHost $vmHost `
             -Datastore $datastore `
             -DiskGB $disk_size_gb `
             -MemoryGB $memory_size_gb `
             -NumCpu $cpuCount `
             -GuestId rhel8_64Guest `
             -NetworkName $networkName

# Configure VM settings
Write-Host "Configuring VM settings..."
$vm | Set-VM -MemoryReservationGB $memory_size_gb -Confirm:$false  # Full reservation

# Apply metadata (different keys than vRealize!)
Write-Host "Applying metadata..."
$vm | Set-Annotation -CustomAttribute "Env" -Value $environment  # "Env" not "Environment"
$vm | Set-Annotation -CustomAttribute "CostCenter" -Value $CostCenter  # PascalCase
$vm | Set-Annotation -CustomAttribute "WorkloadType" -Value "Database"  # New field
$vm | Set-Annotation -CustomAttribute "Tier" -Value "db"
$vm | Set-Annotation -CustomAttribute "ManagedBy" -Value "PowerCLI-v2"
$vm | Set-Annotation -CustomAttribute "ProvisionDate" -Value (Get-Date).ToString("yyyy-MM-dd")

# Configure vSphere tags (different from custom attributes)
$envTag = Get-Tag -Name $environment -Category "Environment" -ErrorAction SilentlyContinue
if ($envTag) {
    New-TagAssignment -Tag $envTag -Entity $vm
}

Write-Host ""
Write-Host "SUCCESS: Database VM '$db_name' provisioned"
Write-Host ""
Write-Host "Next steps (AUTOMATED in new process):"
Write-Host "  - Backup configuration: AUTOMATED via Veeam"
Write-Host "  - Monitoring setup: AUTOMATED via Datadog"
Write-Host "  - DBA notification: AUTOMATED via email"
Write-Host "  - CMDB update: MANUAL (ServiceNow API coming soon)"
Write-Host ""
Write-Host "NOTE: This script uses NEW standards (32GB RAM, different clusters)"
Write-Host "      Conflicts with legacy vRealize workflow expected!"

Disconnect-VIServer -Confirm:$false
