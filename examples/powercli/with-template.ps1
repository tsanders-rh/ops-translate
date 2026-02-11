# Test script with VM template usage

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$true)]
    [ValidateSet("dev","prod")]
    [string]$Environment
)

# Select template based on environment
if ($Environment -eq "prod") {
    $Template = "RHEL8-Golden-Image"
    $NumCpu = 4
    $MemoryGB = 16
} else {
    $Template = "RHEL8-Dev-Template"
    $NumCpu = 2
    $MemoryGB = 8
}

# Create VM from template
New-VM -Name $VMName -Template $Template -NumCpu $NumCpu -MemoryGB $MemoryGB -Datastore "prod-storage"

# Tag the VM
New-TagAssignment -Entity $VMName -Tag "environment:$Environment"
