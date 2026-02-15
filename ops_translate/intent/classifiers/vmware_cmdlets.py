"""
VMware cmdlet classifier for PowerCLI analyzer results.

Maps VMware PowerCLI cmdlets to OpenShift/KubeVirt equivalents and
classifies them based on how well they can be automatically translated.
"""

from typing import Any

from ops_translate.intent.classifiers.base import BaseClassifier
from ops_translate.intent.classify import (
    ClassifiedComponent,
    MigrationPath,
    TranslatabilityLevel,
)


class Vmware_cmdletsClassifier(BaseClassifier):
    """
    Classifier for VMware PowerCLI cmdlets detected in PowerCLI scripts.

    This classifier maps VMware cmdlets to their OpenShift/KubeVirt equivalents
    and determines the appropriate translatability level.

    Classification Rules:
    - VM Lifecycle (New-VM, Start-VM, Stop-VM) → SUPPORTED
    - Compute (Get-VMHost, Get-Cluster) → SUPPORTED
    - Basic Networking (Get-VirtualPortGroup) → SUPPORTED
    - Storage (Get-Datastore, New-HardDisk) → SUPPORTED
    - Tagging (New-TagAssignment) → SUPPORTED
    """

    # Classification mapping: category → (level, equivalent, path, recommendations)
    CLASSIFICATION_RULES = {
        "vm_lifecycle": (
            TranslatabilityLevel.SUPPORTED,
            "KubeVirt VirtualMachine",
            MigrationPath.PATH_A,
            [
                "VM lifecycle operations map directly to KubeVirt",
                "New-VM → VirtualMachine manifest",
                "Start-VM → virtctl start",
                "Stop-VM → virtctl stop",
                "Remove-VM → kubectl delete vm",
            ],
        ),
        "compute": (
            TranslatabilityLevel.SUPPORTED,
            "VirtualMachine.spec.template.spec.domain",
            MigrationPath.PATH_A,
            [
                "CPU/memory specifications map to resources.requests/limits",
                "Get-VMHost → OpenShift Node (for placement)",
                "Get-Cluster → OpenShift cluster/node selector",
                "Get-ResourcePool → Namespace resource quotas",
            ],
        ),
        "networking": (
            TranslatabilityLevel.SUPPORTED,
            "Pod Networking / NetworkAttachmentDefinition",
            MigrationPath.PATH_A,
            [
                "Basic networking maps to default pod network",
                "Single NIC → default pod interface",
                "Port groups → NetworkAttachmentDefinition (if Multus available)",
                "Network adapters → VirtualMachine.spec.template.spec.networks",
            ],
        ),
        "storage": (
            TranslatabilityLevel.SUPPORTED,
            "PersistentVolumeClaim / DataVolume",
            MigrationPath.PATH_A,
            [
                "Datastores → StorageClass",
                "Hard disks → DataVolume or PVC",
                "Disk size → storage.resources.requests",
                "Get-Datastore → StorageClass discovery",
            ],
        ),
        "tagging": (
            TranslatabilityLevel.SUPPORTED,
            "Labels and Annotations",
            MigrationPath.PATH_A,
            [
                "VMware tags → Kubernetes labels",
                "Custom attributes → annotations",
                "New-TagAssignment → metadata.labels",
                "Set-Annotation → metadata.annotations",
            ],
        ),
    }

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "vmware_cmdlets"

    @property
    def priority(self) -> int:
        """VMware cmdlet classifier runs with medium priority."""
        return 20

    def can_classify(self, analysis: dict[str, Any]) -> bool:
        """
        Return True if VMware cmdlet operations are detected in the analysis.

        Args:
            analysis: Analysis results from PowerCLI analyzer

        Returns:
            True if VMware operations are detected
        """
        return bool(analysis.get("vmware_operations"))

    def classify(self, analysis: dict[str, Any]) -> list[ClassifiedComponent]:
        """
        Classify VMware cmdlets from PowerCLI analyzer results.

        Args:
            analysis: Dict with 'vmware_operations' from PowerCLI analyzer

        Returns:
            List of ClassifiedComponent instances
        """
        vmware_ops = analysis.get("vmware_operations", {})
        if not vmware_ops:
            return []

        components: list[ClassifiedComponent] = []
        source_file = analysis.get("source_file", "unknown")

        # Classify each category of VMware operations
        for category, ops in vmware_ops.items():
            if not ops:  # Skip empty categories
                continue

            # Get classification rule for this category
            rule = self.CLASSIFICATION_RULES.get(category)
            if not rule:
                # Unknown category - mark as PARTIAL
                level = TranslatabilityLevel.PARTIAL
                equivalent = f"Unknown equivalent for {category}"
                path = MigrationPath.PATH_B
                recommendations = [
                    f"Manual review required for {category} operations",
                    "Consult KubeVirt documentation",
                ]
            else:
                level, equivalent, path, recommendations = rule

            # Create evidence string from detections (first example)
            evidence = None
            if ops:
                first_op = ops[0]
                cmdlet = first_op.get("cmdlet", "unknown")
                line = first_op.get("line", 0)
                snippet = first_op.get("evidence", "")
                evidence = f"{cmdlet} at line {line}: {snippet}"

            # Create component
            component = ClassifiedComponent(
                name=f"VMware {category.replace('_', ' ').title()}",
                component_type=f"vmware_{category}",
                level=level,
                reason=f"Detected {len(ops)} {category} operation(s)",
                location=source_file,
                openshift_equivalent=equivalent if level != TranslatabilityLevel.BLOCKED else None,
                migration_path=path,
                recommendations=recommendations,
                evidence=evidence,
            )
            components.append(component)

        return components
