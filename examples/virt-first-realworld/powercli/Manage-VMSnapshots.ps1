# Manage-VMSnapshots.ps1
# VM snapshot management and cleanup
# Author: Backup Team
# Last Updated: 2023-11-20

<#
.SYNOPSIS
    Creates or removes VM snapshots with retention policies
.DESCRIPTION
    Manages VM snapshots for backup and maintenance windows.
    Different approach than storage-level snapshots in vRealize workflows.

    NOTE: This operates at VM level, not storage level!
    vRealize workflows may configure datastore-level snapshots differently.
.PARAMETER Action
    create or remove
.PARAMETER VMName
    Target VM name (PascalCase parameter!)
.PARAMETER SnapshotName
    Snapshot name
.PARAMETER Description
    Snapshot description
.PARAMETER RetentionDays
    Days to retain (different from vRealize storage retention)
.PARAMETER IncludeMemory
    Include memory state (boolean, not string "true"/"false")
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("create", "remove", "cleanup")]
    [string]$Action,

    [Parameter(Mandatory=$false)]
    [string]$VMName,  # PascalCase

    [Parameter(Mandatory=$false)]
    [string]$SnapshotName = "auto-snapshot-$(Get-Date -Format 'yyyyMMdd-HHmmss')",

    [Parameter(Mandatory=$false)]
    [string]$Description = "Automated snapshot",

    [Parameter(Mandatory=$false)]
    [int]$RetentionDays = 7,

    [Parameter(Mandatory=$false)]
    [bool]$IncludeMemory = $false  # Boolean, not string!
)

# Connect to vCenter
Connect-VIServer -Server "vcenter.acme.internal"

switch ($Action) {
    "create" {
        if (-not $VMName) {
            throw "VMName required for create action"
        }

        Write-Host "Creating snapshot for VM: $VMName"
        $vm = Get-VM -Name $VMName -ErrorAction Stop

        # Create snapshot
        $snapshot = New-Snapshot -VM $vm `
                                 -Name $SnapshotName `
                                 -Description $Description `
                                 -Memory:$IncludeMemory `
                                 -Quiesce:(!$IncludeMemory)

        # Add custom retention metadata
        $expirationDate = (Get-Date).AddDays($RetentionDays).ToString("yyyy-MM-dd")

        Write-Host "Snapshot created: $($snapshot.Name)"
        Write-Host "Expiration: $expirationDate"
        Write-Host "Memory included: $IncludeMemory"

        # Store metadata (different approach than vRealize)
        $vm | Set-Annotation -CustomAttribute "last-snapshot-date" -Value (Get-Date -Format "yyyy-MM-dd")
        $vm | Set-Annotation -CustomAttribute "snapshot-retention-days" -Value $RetentionDays
    }

    "remove" {
        if (-not $VMName) {
            throw "VMName required for remove action"
        }

        Write-Host "Removing snapshot: $SnapshotName from VM: $VMName"
        $vm = Get-VM -Name $VMName -ErrorAction Stop
        $snapshot = Get-Snapshot -VM $vm -Name $SnapshotName -ErrorAction Stop

        Remove-Snapshot -Snapshot $snapshot -Confirm:$false
        Write-Host "Snapshot removed successfully"
    }

    "cleanup" {
        Write-Host "=== Snapshot Cleanup (Retention Policy Enforcement) ==="
        Write-Host "Retention threshold: $RetentionDays days"
        Write-Host ""

        # Get all VMs with snapshots
        $vms = Get-VM | Where-Object {(Get-Snapshot -VM $_).Count -gt 0}

        $cleanedCount = 0
        foreach ($vm in $vms) {
            $snapshots = Get-Snapshot -VM $vm

            foreach ($snap in $snapshots) {
                $age = (Get-Date) - $snap.Created

                if ($age.Days -gt $RetentionDays) {
                    Write-Host "Removing expired snapshot: $($snap.Name) (age: $($age.Days) days) from $($vm.Name)"
                    Remove-Snapshot -Snapshot $snap -Confirm:$false
                    $cleanedCount++
                }
            }
        }

        Write-Host ""
        Write-Host "Cleanup complete: $cleanedCount snapshots removed"
    }
}

Write-Host ""
Write-Host "NOTE: This manages VM-level snapshots"
Write-Host "      Storage-level snapshots (array-based) are separate!"
Write-Host "      Check vRealize workflows for storage snapshot config"

Disconnect-VIServer -Confirm:$false
