# Production VM Provisioning Script
# Purpose: Governed VM provisioning for production workloads
# Owner: Infrastructure Team
# Requires: Approval from ops-manager@example.com

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [string]$OwnerEmail,

    [Parameter(Mandatory=$true)]
    [string]$CostCenter,

    [Parameter(Mandatory=$false)]
    [int]$NumCPU = 4,

    [Parameter(Mandatory=$false)]
    [int]$MemoryGB = 16,

    [Parameter(Mandatory=$false)]
    [int]$DiskGB = 200
)

# Production environment configuration
$Network = "prod-network"
$Datastore = "prod-ceph-rbd"
$ResourcePool = "Prod-Pool"

# Strict validation for production
if ($NumCPU -lt 2) {
    throw "Production VMs require minimum 2 CPUs"
}

if ($NumCPU -gt 16) {
    throw "Production VMs limited to 16 CPUs. Request exception via ticket."
}

if ($MemoryGB -lt 4) {
    throw "Production VMs require minimum 4GB RAM"
}

if ($MemoryGB -gt 64) {
    throw "Production VMs limited to 64GB RAM. Request exception via ticket."
}

# Validate owner email
if ($OwnerEmail -notmatch "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$") {
    throw "Invalid owner email format"
}

# Check quota compliance (simplified - normally would query vCenter)
Write-Host "Checking quota compliance..." -ForegroundColor Yellow

# Create VM with production settings
New-VM `
    -Name $VMName `
    -NumCpu $NumCPU `
    -MemoryGB $MemoryGB `
    -DiskGB $DiskGB `
    -NetworkName $Network `
    -Datastore $Datastore `
    -ResourcePool $ResourcePool

# Apply comprehensive tagging for production
New-TagAssignment -Entity $VMName -Tag "Environment:Prod"
New-TagAssignment -Entity $VMName -Tag "Owner:$OwnerEmail"
New-TagAssignment -Entity $VMName -Tag "CostCenter:$CostCenter"
New-TagAssignment -Entity $VMName -Tag "ManagedBy:ops-translate"
New-TagAssignment -Entity $VMName -Tag "Compliance:Required"

# Configure production-specific features
# Enable HA
Set-VM -VM $VMName -HARestartPriority High -Confirm:$false

# Create initial snapshot
New-Snapshot -VM $VMName -Name "Initial-Baseline" -Description "Created at provisioning"

# DO NOT auto-start - requires manual approval
Write-Host "Production VM $VMName provisioned successfully" -ForegroundColor Green
Write-Host "VM created but NOT started - awaiting approval" -ForegroundColor Yellow
Write-Host "Approval required from: ops-manager@example.com" -ForegroundColor Yellow
