"""
Generic intent classifier for determining translatability of VM operations.

A universal classifier that works with any intent structure, providing fallback
classification when source-specific classifiers (PowerCLI, vRealize) don't apply.
This classifier is designed to handle custom workflows or future source types.
"""

from pathlib import Path
from typing import Any

import yaml

from ops_translate.intent.classifiers.base import BaseClassifier
from ops_translate.intent.classify import (
    ClassifiedComponent,
    MigrationPath,
    TranslatabilityLevel,
)


class GenericClassifier(BaseClassifier):
    """
    Generic classifier for any intent structure.

    This classifier provides broad coverage for VM provisioning operations
    regardless of the source type. It runs after source-specific classifiers
    and provides baseline classification.

    Classification Rules:
    - VM Creation → SUPPORTED (maps to KubeVirt VirtualMachine)
    - Compute (CPU/Memory) → SUPPORTED (maps to resources.requests)
    - Basic Networking → SUPPORTED (maps to default pod network)
    - Basic Storage → SUPPORTED (maps to PVC/DataVolume)
    - Multi-NIC → PARTIAL (requires Multus NetworkAttachmentDefinition)
    - Advanced Storage → PARTIAL (requires CSI driver support)
    - Approval Workflows → PARTIAL (requires custom integration)

    Example:
        >>> classifier = GenericClassifier()
        >>> intent_data = {"workload_type": "virtual_machine"}
        >>> components = classifier.classify_from_intent(intent_data)
    """

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "generic"

    @property
    def priority(self) -> int:
        """Generic classifier runs with lowest priority (after specific classifiers)."""
        return 1

    def can_classify(self, analysis: dict[str, Any]) -> bool:
        """
        Generic classifier can handle any intent structure.

        Args:
            analysis: Must contain 'intent_file' path

        Returns:
            True if intent_file exists
        """
        intent_file = analysis.get("intent_file")
        return intent_file is not None and Path(intent_file).exists()

    def classify(self, analysis: dict[str, Any]) -> list:
        """
        Classify operations from extracted intent.

        Args:
            analysis: Dict with 'intent_file' path to intent YAML

        Returns:
            List of ClassifiedComponent instances
        """
        intent_file = analysis.get("intent_file")
        if not intent_file or not Path(intent_file).exists():
            return []

        # Load intent YAML
        with open(intent_file) as f:
            data = yaml.safe_load(f)

        if not data or "intent" not in data:
            return []

        intent = data["intent"]

        # Determine location from file path or workflow name
        location = Path(intent_file).stem.replace(".intent", "")
        if intent.get("workflow_name"):
            location = intent["workflow_name"]

        return self.classify_from_intent(intent, location=location)

    def classify_from_intent(
        self, intent: dict[str, Any], location: str = "workflow"
    ) -> list[ClassifiedComponent]:
        """
        Classify components from normalized intent structure.

        This method handles various intent structures by checking multiple
        possible locations for configuration data.

        Args:
            intent: Normalized intent dict
            location: Source file identifier for evidence

        Returns:
            List of classified components
        """
        components = []

        # Check for VM provisioning
        workload_type = intent.get("workload_type")
        if workload_type == "virtual_machine":
            components.append(
                ClassifiedComponent(
                    name="VM Provisioning",
                    component_type="vm_creation",
                    level=TranslatabilityLevel.SUPPORTED,
                    reason="VM creation maps directly to KubeVirt VirtualMachine resource",
                    openshift_equivalent="VirtualMachine (KubeVirt)",
                    migration_path=MigrationPath.PATH_A,
                    location=location,
                    recommendations=[
                        "Generate KubeVirt VirtualMachine manifest",
                        "Map inputs to VM spec fields",
                        "Configure default pod networking",
                    ],
                )
            )

        # Check for compute resources
        has_cpu, has_memory = self._detect_compute_resources(intent)

        if has_cpu or has_memory:
            components.append(
                ClassifiedComponent(
                    name="Compute Resources",
                    component_type="compute_allocation",
                    level=TranslatabilityLevel.SUPPORTED,
                    reason="CPU and memory allocation fully supported in KubeVirt",
                    openshift_equivalent="spec.template.spec.domain.resources",
                    migration_path=MigrationPath.PATH_A,
                    location=location,
                    recommendations=[
                        "Map CPU cores to spec.template.spec.domain.cpu.cores",
                        "Map memory to spec.template.spec.domain.resources.requests.memory",
                        "Consider setting resource limits for production",
                    ],
                )
            )

        # Check for networking
        networks = self._detect_networks(intent)

        if networks:
            if len(networks) == 1 and self._is_simple_network(networks[0]):
                # Simple single network - fully supported
                components.append(
                    ClassifiedComponent(
                        name="Basic Networking",
                        component_type="simple_networking",
                        level=TranslatabilityLevel.SUPPORTED,
                        reason="Single network interface supported via default pod network",
                        openshift_equivalent="Default pod network (OVN-Kubernetes)",
                        migration_path=MigrationPath.PATH_A,
                        location=location,
                        recommendations=[
                            "VM will use cluster's default pod network",
                            "No additional NetworkAttachmentDefinition needed",
                            "Consider using Service for external access",
                        ],
                    )
                )
            else:
                # Multiple NICs or complex networking
                components.append(
                    ClassifiedComponent(
                        name="Multi-NIC Networking",
                        component_type="multi_nic",
                        level=TranslatabilityLevel.PARTIAL,
                        reason="Multiple network interfaces require Multus CNI configuration",
                        openshift_equivalent="NetworkAttachmentDefinition (Multus)",
                        migration_path=MigrationPath.PATH_A,
                        location=location,
                        recommendations=[
                            "Create NetworkAttachmentDefinition for each network",
                            "Configure Multus CNI plugin if not already installed",
                            "Update VM spec to reference NADs",
                            "Test network connectivity between pods",
                        ],
                    )
                )

        # Check for storage
        disks = self._detect_storage(intent)

        if disks:
            # Check complexity
            has_advanced = any(
                disk.get("thin_provisioning") or disk.get("snapshot_enabled") for disk in disks
            )

            if has_advanced:
                components.append(
                    ClassifiedComponent(
                        name="Advanced Storage",
                        component_type="advanced_storage",
                        level=TranslatabilityLevel.PARTIAL,
                        reason="Advanced storage features require CSI driver support",
                        openshift_equivalent="PVC + VolumeSnapshot (if CSI supports)",
                        migration_path=MigrationPath.PATH_A,
                        location=location,
                        recommendations=[
                            "Verify CSI driver supports required features",
                            "Create PersistentVolumeClaim for each disk",
                            "Configure VolumeSnapshotClass if snapshots needed",
                            "Test storage provisioning in dev environment",
                        ],
                    )
                )
            else:
                components.append(
                    ClassifiedComponent(
                        name="Basic Storage",
                        component_type="basic_storage",
                        level=TranslatabilityLevel.SUPPORTED,
                        reason="Basic disk provisioning supported via PersistentVolumeClaims",
                        openshift_equivalent="PersistentVolumeClaim + DataVolume",
                        migration_path=MigrationPath.PATH_A,
                        location=location,
                        recommendations=[
                            "Create PVC for each disk",
                            "Map datastore to StorageClass",
                            "Use DataVolume for bootable images",
                        ],
                    )
                )

        # Check for approval workflows
        if intent.get("governance", {}).get("approval"):
            components.append(
                ClassifiedComponent(
                    name="Approval Workflow",
                    component_type="approval",
                    level=TranslatabilityLevel.PARTIAL,
                    reason=(
                        "Approval logic requires custom integration with "
                        "existing approval systems"
                    ),
                    openshift_equivalent="Custom operator or external approval system",
                    migration_path=MigrationPath.PATH_B,
                    location=location,
                    recommendations=[
                        "Integrate with existing approval system (ServiceNow, Jira, etc.)",
                        "Consider using Kubernetes admission controllers",
                        "May require custom operator development",
                        "Document approval requirements in runbook",
                    ],
                )
            )

        # Check for day2 operations
        if intent.get("day2_operations"):
            day2 = intent["day2_operations"]
            operations = day2.get("supported", [])

            if operations:
                components.append(
                    ClassifiedComponent(
                        name="VM Lifecycle Operations",
                        component_type="day2_ops",
                        level=TranslatabilityLevel.SUPPORTED,
                        reason="Start/stop/restart operations supported via VirtualMachine spec",
                        openshift_equivalent="VirtualMachine running field",
                        migration_path=MigrationPath.PATH_A,
                        location=location,
                        recommendations=[
                            "Map start/stop to spec.running: true/false",
                            "Use virtctl for CLI operations",
                            "Consider using Ansible for automation",
                        ],
                    )
                )

        return components

    def _detect_compute_resources(self, intent: dict[str, Any]) -> tuple[bool, bool]:
        """
        Detect CPU and memory resource specifications across multiple intent structures.

        Args:
            intent: Intent dictionary

        Returns:
            Tuple of (has_cpu, has_memory) booleans
        """
        has_cpu = False
        has_memory = False

        # Check inputs section
        inputs = intent.get("inputs", {})
        has_cpu = "cpu_count" in inputs or "cpu" in inputs or "cpu_cores" in inputs
        has_memory = "memory_gb" in inputs or "memory" in inputs

        # Check resources.compute section
        resources = intent.get("resources", {})
        if resources.get("compute"):
            compute = resources["compute"]
            has_cpu = has_cpu or "cpu" in compute or "cpu_cores" in compute
            has_memory = has_memory or "memory" in compute

        # Check legacy compute section
        if intent.get("compute"):
            compute = intent["compute"]
            has_cpu = has_cpu or compute.get("cpu_cores") or compute.get("cpu")
            has_memory = has_memory or compute.get("memory_gb") or compute.get("memory")

        return has_cpu, has_memory

    def _detect_networks(self, intent: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Detect network configurations across multiple intent structures.

        Args:
            intent: Intent dictionary

        Returns:
            List of network configuration dicts
        """
        networks = []
        infrastructure = intent.get("infrastructure", {})
        resources = intent.get("resources", {})

        # Check legacy networking section
        if intent.get("networking"):
            networking = intent["networking"]
            networks = networking.get("networks", [])
        # Check resources.network section
        elif resources.get("network"):
            network_name = resources["network"]
            if isinstance(network_name, str):
                networks = [{"name": network_name}]
            else:
                networks = [network_name]
        # Check infrastructure section for network info
        elif infrastructure.get("network"):
            network_name = infrastructure["network"]
            networks = [{"name": network_name}]
        # Check profiles for network configuration
        elif intent.get("profiles", {}).get("network"):
            # Has network profiles - treat as basic networking for now
            networks = [{"name": "profile-based"}]

        return networks

    def _detect_storage(self, intent: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Detect storage configurations across multiple intent structures.

        Args:
            intent: Intent dictionary

        Returns:
            List of disk configuration dicts
        """
        disks = []
        infrastructure = intent.get("infrastructure", {})
        resources = intent.get("resources", {})

        # Check storage section
        if intent.get("storage"):
            storage = intent["storage"]
            disks = storage.get("disks", [])
        # Check resources.storage section
        elif resources.get("storage"):
            storage = resources["storage"]
            if isinstance(storage, dict):
                disks = storage.get("disks", [])
        # Check infrastructure for datastore info
        elif infrastructure.get("datastore"):
            # Has datastore configured - treat as basic storage
            disks = [{"name": "boot-disk", "datastore": infrastructure["datastore"]}]

        return disks

    def _is_simple_network(self, network: dict[str, Any]) -> bool:
        """
        Check if a network config is 'simple' (default VM Network).

        Args:
            network: Network configuration dict

        Returns:
            True if this is a basic single network
        """
        network_name = network.get("name", "").lower()
        # Simple networks: "vm network", "default", or similar
        return (
            network_name in ("vm network", "default", "pod network", "profile-based")
            or not network_name
        )
