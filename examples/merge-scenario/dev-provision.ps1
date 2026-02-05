# Development VM Provisioning Script
# Purpose: Quick, simple VM provisioning for development environments
# Owner: DevOps Team

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$false)]
    [int]$NumCPU = 2,

    [Parameter(Mandatory=$false)]
    [int]$MemoryGB = 4
)

# Dev environment defaults
$Network = "dev-network"
$Datastore = "dev-nfs-storage"
$ResourcePool = "Dev-Pool"

# Simple validation
if ($NumCPU -gt 8) {
    Write-Warning "Dev VMs limited to 8 CPUs. Setting to 8."
    $NumCPU = 8
}

if ($MemoryGB -gt 32) {
    Write-Warning "Dev VMs limited to 32GB RAM. Setting to 32."
    $MemoryGB = 32
}

# Create VM
New-VM `
    -Name $VMName `
    -NumCpu $NumCPU `
    -MemoryGB $MemoryGB `
    -NetworkName $Network `
    -Datastore $Datastore `
    -ResourcePool $ResourcePool

# Apply basic tagging
New-TagAssignment -Entity $VMName -Tag "Environment:Dev"
New-TagAssignment -Entity $VMName -Tag "ManagedBy:ops-translate"

# Start the VM
Start-VM -VM $VMName

Write-Host "Dev VM $VMName provisioned successfully" -ForegroundColor Green
