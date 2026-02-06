# Provision-WebTier.ps1
# Web tier provisioning with load balancing
# Author: Web Team
# Version: 2.1 (conflicts with vRealize NSX workflow)

<#
.SYNOPSIS
    Provisions web tier VMs (does NOT configure NSX - manual step!)
.DESCRIPTION
    Creates multiple web server VMs for an application.

    IMPORTANT: This script does NOT configure NSX load balancer or segments!
    NSX configuration must be done separately via vRealize or manually.

    Type conflicts with vRealize:
    - instance_count is [int], vRealize uses "number"
    - cpu_per_instance is [int], vRealize uses "cpu" as number
    - memory_per_instance uses different parameter name
.PARAMETER application_name
    Application name (underscore, not camelCase)
.PARAMETER env
    Environment (short form: prod/stage/dev, not full names)
.PARAMETER instance_count
    Number of instances (integer type)
.PARAMETER cpu_per_instance
    CPUs per instance
.PARAMETER memory_per_instance
    Memory per instance in GB
.PARAMETER load_balancer_vip
    VIP for load balancer (MANUAL NSX CONFIGURATION REQUIRED!)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$application_name,

    [Parameter(Mandatory=$true)]
    [ValidateSet("prod", "stage", "dev")]  # Short form
    [string]$env,

    [Parameter(Mandatory=$true)]
    [int]$instance_count,  # Integer, not number

    [Parameter(Mandatory=$false)]
    [int]$cpu_per_instance = 4,

    [Parameter(Mandatory=$false)]
    [int]$memory_per_instance = 8,

    [Parameter(Mandatory=$false)]
    [string]$load_balancer_vip = ""
)

# Validation
if ($instance_count -lt 1 -or $instance_count -gt 10) {
    throw "instance_count must be between 1 and 10"
}

Write-Host "=== Web Tier Provisioning ==="
Write-Host "Application: $application_name"
Write-Host "Environment: $env"
Write-Host "Instances: $instance_count"
Write-Host ""

# Connect to vCenter
Connect-VIServer -Server "vcenter.acme.internal"

# Environment configuration (different networks than vRealize!)
switch ($env) {
    "prod" {
        $cluster = "PROD-Web-Cluster"  # Dedicated web cluster
        $datastore_pattern = "PROD-WEB-*"  # Pattern, not exact name
        $portgroup = "Web-Prod-PG"  # Different from vRealize
        $folder = "Production/Web Servers"
    }
    "stage" {
        $cluster = "Staging-Cluster"
        $datastore_pattern = "STAGE-*"
        $portgroup = "Web-Stage-PG"
        $folder = "Staging/Web Servers"
    }
    "dev" {
        $cluster = "Dev-Cluster"
        $datastore_pattern = "DEV-*"
        $portgroup = "Web-Dev-PG"
        $folder = "Development/Web Servers"
    }
}

Write-Host "Target cluster: $cluster"
Write-Host "Network: $portgroup"
Write-Host ""

# Get cluster and datastores
$clusterObj = Get-Cluster -Name $cluster
$datastores = Get-Datastore -Name $datastore_pattern | Where-Object {$_.FreeSpaceGB -gt 100}

if ($datastores.Count -eq 0) {
    throw "No datastores found with sufficient space"
}

# Create VMs
$createdVMs = @()
for ($i = 1; $i -le $instance_count; $i++) {
    $vmName = "$application_name-web-$i"

    Write-Host "Creating VM $i/$instance_count : $vmName"

    # Select datastore (round-robin for balance)
    $ds = $datastores[($i - 1) % $datastores.Count]

    # Get host
    $vmHost = $clusterObj | Get-VMHost |
              Where-Object {$_.ConnectionState -eq 'Connected'} |
              Sort-Object -Property MemoryUsageGB |
              Select-Object -First 1

    # Create VM
    $vm = New-VM -Name $vmName `
                 -VMHost $vmHost `
                 -Datastore $ds `
                 -DiskGB 80 `
                 -MemoryGB $memory_per_instance `
                 -NumCpu $cpu_per_instance `
                 -GuestId ubuntu64Guest `
                 -NetworkName $portgroup

    # Apply tags (different schema!)
    $vm | Set-Annotation -CustomAttribute "app-name" -Value $application_name  # Hyphen
    $vm | Set-Annotation -CustomAttribute "env" -Value $env  # Short key
    $vm | Set-Annotation -CustomAttribute "tier" -Value "web"  # Lowercase
    $vm | Set-Annotation -CustomAttribute "instance-number" -Value $i
    $vm | Set-Annotation -CustomAttribute "provisioned-by" -Value "PowerCLI"
    $vm | Set-Annotation -CustomAttribute "provisioned-date" -Value (Get-Date -Format "yyyy-MM-dd HH:mm:ss")

    # Power on
    Start-VM -VM $vm -Confirm:$false | Out-Null

    $createdVMs += $vm
    Write-Host "  Created: $vmName on $($ds.Name)"
}

Write-Host ""
Write-Host "SUCCESS: Created $instance_count VMs"
Write-Host ""
Write-Host "MANUAL STEPS REQUIRED:"
Write-Host "  1. Configure NSX segment for $application_name-web-segment-$env"
Write-Host "  2. Move VMs to NSX segment (NOT AUTOMATED)"
Write-Host "  3. Create NSX load balancer pool with VMs"
Write-Host "  4. Create NSX virtual server at VIP: $load_balancer_vip"
Write-Host "  5. Configure health checks and persistence"
Write-Host ""
Write-Host "WARNING: This script does NOT handle NSX configuration!"
Write-Host "         Use vRealize workflow OR configure NSX manually"
Write-Host ""
Write-Host "CONFLICT: vRealize workflow creates NSX segment automatically"
Write-Host "          This script uses traditional port groups"
Write-Host "          Decide on one approach for consistency!"

Disconnect-VIServer -Confirm:$false
