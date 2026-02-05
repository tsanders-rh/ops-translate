# Simple VM Provisioning
# This is the simplest example - provision a basic VM with minimal parameters

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [int]$CPUCount,

    [Parameter(Mandatory=$true)]
    [int]$MemoryGB
)

# Connect to vCenter
Connect-VIServer -Server vcenter.example.com

# Create VM
New-VM -Name $VMName `
    -ResourcePool "Production" `
    -Datastore "datastore1" `
    -NumCpu $CPUCount `
    -MemoryGB $MemoryGB `
    -NetworkName "VM Network" `
    -GuestId "rhel8_64Guest"

# Start VM
Start-VM -VM $VMName

Disconnect-VIServer -Confirm:$false
