# VM Provisioning with Governance
# Demonstrates governance policies, quotas, and approval requirements

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "prod")]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [ValidateRange(1, 32)]
    [int]$CPUCount,

    [Parameter(Mandatory=$true)]
    [ValidateRange(1, 256)]
    [int]$MemoryGB,

    [Parameter(Mandatory=$true)]
    [ValidateRange(20, 2000)]
    [int]$DiskGB,

    [Parameter(Mandatory=$true)]
    [string]$OwnerEmail,

    [Parameter(Mandatory=$false)]
    [string]$CostCenter,

    [Parameter(Mandatory=$false)]
    [string]$ApprovalTicket
)

# Governance check: Prod requires approval
if ($Environment -eq "prod" -and [string]::IsNullOrEmpty($ApprovalTicket)) {
    Write-Error "Production deployments require an approval ticket number"
    exit 1
}

# Quota validation
if ($CPUCount -gt 16) {
    Write-Error "CPU quota exceeded. Maximum 16 cores allowed."
    exit 1
}

if ($MemoryGB -gt 128) {
    Write-Error "Memory quota exceeded. Maximum 128 GB allowed."
    exit 1
}

# Connect to vCenter
Connect-VIServer -Server vcenter.example.com

# Environment-specific configuration
if ($Environment -eq "prod") {
    $Network = "prod-network"
    $Datastore = "storage-gold"
    $ResourcePool = "Production"
} else {
    $Network = "dev-network"
    $Datastore = "storage-standard"
    $ResourcePool = "Development"
}

# Create VM
$vm = New-VM -Name $VMName `
    -ResourcePool $ResourcePool `
    -Datastore $Datastore `
    -NumCpu $CPUCount `
    -MemoryGB $MemoryGB `
    -DiskGB $DiskGB `
    -NetworkName $Network `
    -GuestId "rhel8_64Guest"

# Apply comprehensive tags
$tags = @{
    "env" = $Environment
    "owner" = $OwnerEmail
    "managed-by" = "ops-translate"
    "created-date" = (Get-Date -Format "yyyy-MM-dd")
}

if (![string]::IsNullOrEmpty($CostCenter)) {
    $tags["cost-center"] = $CostCenter
}

if (![string]::IsNullOrEmpty($ApprovalTicket)) {
    $tags["approval-ticket"] = $ApprovalTicket
}

foreach ($key in $tags.Keys) {
    New-TagAssignment -Tag "$key:$($tags[$key])" -Entity $vm
}

# Configure additional settings
Set-VM -VM $vm -Notes "Owner: $OwnerEmail`nEnvironment: $Environment`nProvisioned: $(Get-Date)" -Confirm:$false

# Start VM
Start-VM -VM $vm

Write-Host "VM $VMName provisioned successfully"
Write-Host "  Environment: $Environment"
Write-Host "  Resources: $CPUCount vCPU, $MemoryGB GB RAM, $DiskGB GB Disk"
Write-Host "  Owner: $OwnerEmail"
if ($ApprovalTicket) {
    Write-Host "  Approval: $ApprovalTicket"
}

Disconnect-VIServer -Confirm:$false
