# Simple VM Provisioning Script
param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [ValidateSet("dev","prod")]
    [string]$Environment,

    [Parameter(Mandatory=$false)]
    [int]$MemoryGB = 8,

    [Parameter(Mandatory=$false)]
    [int]$NumCPU = 4
)

# Connect to vCenter
Connect-VIServer -Server vcenter.example.com

# Select appropriate cluster based on environment
if ($Environment -eq "prod") {
    $Cluster = Get-Cluster -Name "PROD-Cluster"
    $Network = "PROD-Network"
} else {
    $Cluster = Get-Cluster -Name "DEV-Cluster"
    $Network = "DEV-Network"
}

# Create VM
$VM = New-VM `
    -Name $VMName `
    -ResourcePool $Cluster `
    -Datastore "SharedStorage" `
    -DiskGB 50 `
    -MemoryGB $MemoryGB `
    -NumCpu $NumCPU `
    -NetworkName $Network `
    -GuestId "ubuntu64Guest"

# Apply tags
New-TagAssignment -Tag "Environment:$Environment" -Entity $VM
New-TagAssignment -Tag "Managed-By:ops-translate" -Entity $VM

# Start VM
Start-VM -VM $VM

Write-Host "VM $VMName created successfully"
