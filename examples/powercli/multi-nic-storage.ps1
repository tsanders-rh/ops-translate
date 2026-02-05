# Advanced VM with Multiple NICs and Storage
# Demonstrates network and storage profile selection

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "prod")]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [int]$CPUCount,

    [Parameter(Mandatory=$true)]
    [int]$MemoryGB,

    [Parameter(Mandatory=$false)]
    [switch]$HighAvailability
)

# Connect to vCenter
Connect-VIServer -Server vcenter.example.com

# Environment and HA-based configuration
if ($Environment -eq "prod") {
    $PrimaryNetwork = "prod-network"
    $StorageProfile = "storage-gold"
    $StorageClass = if ($HighAvailability) { "storage-gold-ha" } else { "storage-gold" }
} else {
    $PrimaryNetwork = "dev-network"
    $StorageProfile = "storage-standard"
    $StorageClass = "storage-standard"
}

# Get appropriate datastore
$Datastore = Get-Datastore -Name $StorageClass

# Create base VM
$vm = New-VM -Name $VMName `
    -ResourcePool $Environment `
    -Datastore $Datastore `
    -NumCpu $CPUCount `
    -MemoryGB $MemoryGB `
    -GuestId "rhel8_64Guest"

# Add primary network adapter
Get-NetworkAdapter -VM $vm | Remove-NetworkAdapter -Confirm:$false
New-NetworkAdapter -VM $vm `
    -NetworkName $PrimaryNetwork `
    -StartConnected `
    -Type Vmxnet3

# Add management network (all VMs get this)
New-NetworkAdapter -VM $vm `
    -NetworkName "mgmt-network" `
    -StartConnected `
    -Type Vmxnet3

# Add storage network for prod HA
if ($Environment -eq "prod" -and $HighAvailability) {
    New-NetworkAdapter -VM $vm `
        -NetworkName "storage-network" `
        -StartConnected `
        -Type Vmxnet3
}

# Add data disks
New-HardDisk -VM $vm `
    -CapacityGB 100 `
    -StorageFormat Thin `
    -Datastore $Datastore

# For HA, add second disk for replication
if ($HighAvailability) {
    New-HardDisk -VM $vm `
        -CapacityGB 100 `
        -StorageFormat Thin `
        -Datastore $Datastore
}

# Apply tags
New-TagAssignment -Tag "env:$Environment" -Entity $vm
New-TagAssignment -Tag "storage-profile:$StorageProfile" -Entity $vm
if ($HighAvailability) {
    New-TagAssignment -Tag "ha:enabled" -Entity $vm
}

# Start VM
Start-VM -VM $vm

Write-Host "VM $VMName created with:"
Write-Host "  Network Adapters:"
Get-NetworkAdapter -VM $vm | ForEach-Object {
    Write-Host "    - $($_.NetworkName) ($($_.Type))"
}
Write-Host "  Hard Disks:"
Get-HardDisk -VM $vm | ForEach-Object {
    Write-Host "    - $($_.CapacityGB) GB ($($_.StorageFormat))"
}

Disconnect-VIServer -Confirm:$false
