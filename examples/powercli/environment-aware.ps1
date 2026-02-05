# Environment-Aware VM Provisioning
# Demonstrates environment branching (dev/prod) with different resource allocations

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "prod")]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [string]$OwnerEmail
)

# Connect to vCenter
Connect-VIServer -Server vcenter.example.com

# Environment-specific configuration
if ($Environment -eq "prod") {
    $CPUCount = 4
    $MemoryGB = 16
    $Datastore = "storage-gold"
    $Network = "prod-network"
    $ResourcePool = "Production"
} else {
    $CPUCount = 2
    $MemoryGB = 8
    $Datastore = "storage-standard"
    $Network = "dev-network"
    $ResourcePool = "Development"
}

# Create VM
$vm = New-VM -Name $VMName `
    -ResourcePool $ResourcePool `
    -Datastore $Datastore `
    -NumCpu $CPUCount `
    -MemoryGB $MemoryGB `
    -NetworkName $Network `
    -GuestId "rhel8_64Guest"

# Apply tags
New-TagAssignment -Tag "env:$Environment" -Entity $vm
New-TagAssignment -Tag "owner:$OwnerEmail" -Entity $vm
New-TagAssignment -Tag "managed-by:ops-translate" -Entity $vm

# Start VM
Start-VM -VM $vm

Write-Host "VM $VMName created in $Environment environment"
Write-Host "  CPU: $CPUCount cores"
Write-Host "  Memory: $MemoryGB GB"
Write-Host "  Network: $Network"
Write-Host "  Storage: $Datastore"

Disconnect-VIServer -Confirm:$false
