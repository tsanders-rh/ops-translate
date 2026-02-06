"""
NSX-T classifier for determining translatability of NSX operations.

Maps NSX-T networking and security operations to OpenShift equivalents and
classifies them based on how well they can be automatically translated.
"""

from typing import Any

from ops_translate.intent.classifiers.base import BaseClassifier
from ops_translate.intent.classify import (
    ClassifiedComponent,
    MigrationPath,
    TranslatabilityLevel,
)


class NsxClassifier(BaseClassifier):
    """
    Classifier for NSX-T operations detected in vRealize workflows.

    This classifier maps NSX operations to their OpenShift equivalents and
    determines the appropriate translatability level and migration path.

    Classification Rules:
    - Segments → PARTIAL (can use Multus NAD, but requires manual config)
    - Firewall Rules → PARTIAL (can use NetworkPolicy, with limitations)
    - Security Groups → BLOCKED (no direct equivalent, manual IPSet/NetworkPolicy)
    - Tier Gateways → BLOCKED (no OpenShift equivalent, requires external LB)
    - Load Balancers → PARTIAL (can use OpenShift Router/Ingress)
    - NAT Rules → BLOCKED (requires external gateway)
    - VPN → MANUAL (complex, requires specialist design)
    - Distributed Firewall → PARTIAL (NetworkPolicy with limitations)

    Example:
        >>> classifier = NSXClassifier()
        >>> analysis = {"nsx_operations": {"segments": [...]}}
        >>> components = classifier.classify(analysis)
        >>> for c in components:
        ...     print(f"{c.name}: {c.level}")
    """

    # Classification mapping: NSX operation → (level, equivalent, path, recommendations)
    CLASSIFICATION_RULES = {
        "segments": (
            TranslatabilityLevel.PARTIAL,
            "NetworkAttachmentDefinition (Multus CNI)",
            MigrationPath.PATH_A,
            [
                "Create NetworkAttachmentDefinition for each segment",
                "Configure Multus CNI plugin",
                "Update pod specs to reference NAD",
                "Map VLAN/overlay IDs to bridge/macvlan config",
                "Test pod-to-pod networking",
            ],
        ),
        "firewall_rules": (
            TranslatabilityLevel.PARTIAL,
            "NetworkPolicy",
            MigrationPath.PATH_A,
            [
                "Convert firewall rules to NetworkPolicy manifests",
                "Note: NetworkPolicy is L3/L4 only (no L7 filtering)",
                "Consider using Calico for advanced features",
                "Test egress/ingress rules in dev environment",
                "Document any unsupported rule types",
            ],
        ),
        "security_groups": (
            TranslatabilityLevel.BLOCKED,
            None,
            MigrationPath.PATH_C,
            [
                "Security groups have no direct OpenShift equivalent",
                "Option 1: Model as pod selectors in NetworkPolicy",
                "Option 2: Use labels to group pods logically",
                "Option 3: Keep NSX for security groups (hybrid)",
                "Requires specialist review of security requirements",
            ],
        ),
        "tier_gateways": (
            TranslatabilityLevel.BLOCKED,
            None,
            MigrationPath.PATH_B,
            [
                "NSX Tier-0/Tier-1 gateways have no OpenShift equivalent",
                "Recommended: Keep NSX for north-south routing (hybrid)",
                "Alternative: Use external load balancer (F5, HAProxy)",
                "OpenShift Router handles ingress within cluster only",
                "Requires networking architecture review",
            ],
        ),
        "load_balancers": (
            TranslatabilityLevel.PARTIAL,
            "OpenShift Router / Ingress",
            MigrationPath.PATH_A,
            [
                "Map NSX load balancer to OpenShift Route/Ingress",
                "Note: Limited to HTTP/HTTPS traffic",
                "For TCP/UDP: Use MetalLB or external load balancer",
                "Configure health checks as readiness probes",
                "Test failover and session persistence",
            ],
        ),
        "nat_rules": (
            TranslatabilityLevel.BLOCKED,
            None,
            MigrationPath.PATH_B,
            [
                "NAT rules require external gateway (no OpenShift equivalent)",
                "Option 1: Keep NSX for NAT (hybrid approach)",
                "Option 2: Use external router/firewall",
                "Option 3: Redesign to avoid NAT (pod-to-pod direct routing)",
                "Requires networking architecture review",
            ],
        ),
        "vpn": (
            TranslatabilityLevel.MANUAL,
            None,
            MigrationPath.PATH_C,
            [
                "VPN configurations are complex and site-specific",
                "OpenShift has no built-in VPN (cluster networking only)",
                "Options: IPSec pods, WireGuard, commercial VPN appliances",
                "Requires security and networking specialist review",
                "Consider if VPN is still needed with pod-to-pod networking",
            ],
        ),
        "distributed_firewall": (
            TranslatabilityLevel.PARTIAL,
            "NetworkPolicy (limited)",
            MigrationPath.PATH_A,
            [
                "NSX DFW is more powerful than NetworkPolicy",
                "NetworkPolicy: L3/L4 only, no application awareness",
                "For advanced features: Consider Calico, Cilium, or Istio",
                "DFW micro-segmentation → NetworkPolicy per namespace",
                "Test policy enforcement in dev cluster",
            ],
        ),
    }

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "nsx"

    @property
    def priority(self) -> int:
        """NSX classifier has high priority since it's specific to NSX operations."""
        return 20  # Higher priority than generic classifiers

    def can_classify(self, analysis: dict[str, Any]) -> bool:
        """
        Return True if NSX operations are detected in the analysis.

        Args:
            analysis: Analysis results from vRealize workflow analysis

        Returns:
            True if nsx_operations key exists and is non-empty
        """
        return bool(analysis.get("nsx_operations"))

    def classify(self, analysis: dict[str, Any]) -> list[ClassifiedComponent]:
        """
        Classify NSX operations from analysis results.

        Args:
            analysis: Analysis results from ops_translate.analyze.vrealize

        Returns:
            List of ClassifiedComponent instances for all detected NSX operations

        Example:
            >>> analysis = {
            ...     "nsx_operations": {
            ...         "segments": [
            ...             {"name": "Web-Segment", "location": "item1", "evidence": "..."}
            ...         ]
            ...     }
            ... }
            >>> classifier = NSXClassifier()
            >>> components = classifier.classify(analysis)
            >>> len(components)
            1
            >>> components[0].level
            <TranslatabilityLevel.PARTIAL: 'PARTIAL'>
        """
        classified = []

        nsx_ops = analysis.get("nsx_operations", {})

        for category, operations in nsx_ops.items():
            # Get classification rule for this category
            if category not in self.CLASSIFICATION_RULES:
                # Unknown NSX operation - mark as MANUAL for safety
                level = TranslatabilityLevel.MANUAL
                equivalent = None
                path = MigrationPath.PATH_C
                recommendations = [
                    f"Unknown NSX operation type: {category}",
                    "Requires specialist review",
                    "Check NSX-T documentation for details",
                ]
            else:
                level, equivalent, path, recommendations = self.CLASSIFICATION_RULES[category]

            # Deduplicate operations before creating components
            deduplicated = self._deduplicate_operations(operations, category)

            # Create a classified component for each deduplicated operation
            for op in deduplicated:
                component = ClassifiedComponent(
                    name=op.get("name", category),
                    component_type=f"nsx_{category}",
                    level=level,
                    reason=self._get_reason(category, level, equivalent),
                    openshift_equivalent=equivalent,
                    migration_path=path,
                    evidence=op.get("evidence"),
                    location=op.get("location"),
                    recommendations=recommendations.copy(),  # Copy to avoid mutation
                )
                classified.append(component)

        return classified

    def _deduplicate_operations(
        self, operations: list[dict[str, Any]], category: str
    ) -> list[dict[str, Any]]:
        """
        Deduplicate NSX operations that represent the same logical operation.

        Multiple detection patterns may identify the same NSX operation (e.g.,
        "nsxClient.createSecurityGroup" and "SecurityGroup" in the same location).
        This method consolidates them into a single operation with combined evidence.

        Args:
            operations: List of detected NSX operations
            category: NSX category (e.g., "security_groups")

        Returns:
            Deduplicated list of operations with combined evidence

        Example:
            >>> ops = [
            ...     {"name": "nsxClient.createSG", "location": "item1", "evidence": "API call"},
            ...     {"name": "SecurityGroup", "location": "item1", "evidence": "Object type"},
            ... ]
            >>> deduped = classifier._deduplicate_operations(ops, "security_groups")
            >>> len(deduped)
            1
        """
        if not operations:
            return []

        # Group operations by location (operations in the same location are likely duplicates)
        location_groups: dict[str, list[dict[str, Any]]] = {}
        for op in operations:
            location = op.get("location", "unknown")
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(op)

        # Deduplicate within each location group
        deduplicated = []
        for location, group in location_groups.items():
            if len(group) == 1:
                # Single operation at this location - no deduplication needed
                deduplicated.append(group[0])
            else:
                # Multiple operations at same location - merge them
                merged = self._merge_operations(group, category)
                deduplicated.append(merged)

        return deduplicated

    def _merge_operations(
        self, operations: list[dict[str, Any]], category: str
    ) -> dict[str, Any]:
        """
        Merge multiple detections of the same operation into a single entry.

        Args:
            operations: List of operations to merge (all at same location)
            category: NSX category

        Returns:
            Merged operation with combined evidence and highest confidence
        """
        # Use the most specific name (prefer API calls over object types)
        name = category  # Default
        for op in operations:
            op_name = op.get("name", "")
            if "nsxClient" in op_name:
                # API call is most specific
                name = op_name
                break
            elif op_name and op_name != category:
                # Use first non-default name
                name = op_name

        # Combine all evidence
        evidence_parts = []
        for op in operations:
            if op.get("evidence"):
                evidence_parts.append(op["evidence"])

        combined_evidence = " | ".join(evidence_parts) if evidence_parts else None

        # Use highest confidence
        confidence = max((op.get("confidence", 0.5) for op in operations), default=0.5)

        # Use first non-unknown location
        location = "unknown"
        for op in operations:
            loc = op.get("location", "unknown")
            if loc != "unknown":
                location = loc
                break

        return {
            "name": name,
            "location": location,
            "confidence": confidence,
            "evidence": combined_evidence,
        }

    def _get_reason(
        self, category: str, level: TranslatabilityLevel, equivalent: str | None
    ) -> str:
        """
        Generate human-readable reason for classification.

        Args:
            category: NSX operation category (e.g., "segments")
            level: Translatability level assigned
            equivalent: OpenShift equivalent if available

        Returns:
            Human-readable explanation string
        """
        category_name = category.replace("_", " ").title()

        if level == TranslatabilityLevel.SUPPORTED:
            return f"{category_name} can be fully translated to {equivalent}"
        elif level == TranslatabilityLevel.PARTIAL:
            return (
                f"{category_name} can be partially translated to {equivalent} "
                "with manual configuration"
            )
        elif level == TranslatabilityLevel.BLOCKED:
            return (
                f"{category_name} cannot be automatically translated - "
                "no direct OpenShift equivalent"
            )
        else:  # MANUAL
            return f"{category_name} requires custom implementation and specialist review"
