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

        Supports both old analysis format (nsx_operations) and new intent format.

        Args:
            analysis: Analysis results or intent file reference

        Returns:
            True if NSX features are detected
        """
        # Old format: nsx_operations key
        if analysis.get("nsx_operations"):
            return True

        # New format: intent_file with NSX integrations
        if analysis.get("intent_file"):
            from pathlib import Path

            import yaml

            intent_file = Path(analysis["intent_file"])
            if intent_file.exists():
                with open(intent_file) as f:
                    data = yaml.safe_load(f)
                    if data and "intent" in data:
                        intent = data["intent"]
                        # Check for NSX-related sections
                        if intent.get("security") or self._has_nsx_integrations(intent):
                            return True

        return False

    def _has_nsx_integrations(self, intent: dict[str, Any]) -> bool:
        """Check if intent has NSX-T integrations."""
        integrations = intent.get("integrations", [])
        return any(i.get("type") == "nsx-t" for i in integrations)

    def classify(self, analysis: dict[str, Any]) -> list[ClassifiedComponent]:
        """
        Classify NSX operations from analysis results or intent YAML.

        Supports both old analysis format (nsx_operations) and new intent format.

        Args:
            analysis: Analysis results or intent file reference

        Returns:
            List of ClassifiedComponent instances for all detected NSX operations

        Example (old format):
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

        Example (new format):
            >>> analysis = {
            ...     "source_type": "vrealize",
            ...     "intent_file": "path/to/workflow.intent.yaml"
            ... }
            >>> components = classifier.classify(analysis)
        """
        # New format: intent file
        if analysis.get("intent_file"):
            from pathlib import Path

            import yaml

            intent_file = Path(analysis["intent_file"])
            if intent_file.exists():
                with open(intent_file) as f:
                    data = yaml.safe_load(f)
                    if data and "intent" in data:
                        intent = data["intent"]
                        filename = intent_file.stem.replace(".intent", "").replace(".workflow", "")
                        return self.classify_from_intent(intent, location=filename)

        # Old format: nsx_operations
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
                # Clean up regex artifacts from the name for display
                display_name = self._clean_display_name(op.get("name", category))

                component = ClassifiedComponent(
                    name=display_name,
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

    def classify_from_intent(
        self, intent: dict[str, Any], location: str = "nsx"
    ) -> list[ClassifiedComponent]:
        """
        Classify NSX components from normalized intent structure.

        Args:
            intent: Normalized intent dict with security, integrations sections
            location: Source file identifier for evidence

        Returns:
            List of classified NSX components
        """
        components = []

        security = intent.get("security", {})
        integrations = intent.get("integrations", [])
        nsx_integrations = [i for i in integrations if i.get("type") == "nsx-t"]

        # NSX Security Groups
        if security.get("network_segmentation") or any(
            "security_group" in str(i.get("operations", [])).lower() for i in nsx_integrations
        ):
            level, equivalent, path, recommendations = self.CLASSIFICATION_RULES["security_groups"]
            components.append(
                ClassifiedComponent(
                    name="NSX Security Groups",
                    component_type="nsx_security_groups",
                    level=level,
                    reason=self._get_reason("security_groups", level, equivalent),
                    openshift_equivalent=equivalent,
                    migration_path=path,
                    location=location,
                    recommendations=recommendations.copy(),
                )
            )

        # NSX Firewall Rules
        if security.get("firewall_rules") or any(
            "firewall" in str(i.get("operations", [])).lower() for i in nsx_integrations
        ):
            level, equivalent, path, recommendations = self.CLASSIFICATION_RULES["firewall_rules"]
            components.append(
                ClassifiedComponent(
                    name="NSX Distributed Firewall",
                    component_type="nsx_firewall_rules",
                    level=level,
                    reason=self._get_reason("firewall_rules", level, equivalent),
                    openshift_equivalent=equivalent,
                    migration_path=path,
                    location=location,
                    recommendations=recommendations.copy(),
                )
            )

        # NSX Segments/Overlays
        if any("segment" in str(i.get("operations", [])).lower() for i in nsx_integrations):
            level, equivalent, path, recommendations = self.CLASSIFICATION_RULES["segments"]
            components.append(
                ClassifiedComponent(
                    name="NSX Overlay Segments",
                    component_type="nsx_segments",
                    level=level,
                    reason=self._get_reason("segments", level, equivalent),
                    openshift_equivalent=equivalent,
                    migration_path=path,
                    location=location,
                    recommendations=recommendations.copy(),
                )
            )

        # NSX Load Balancer
        if any(
            "load_balancer" in str(i.get("operations", [])).lower()
            or "lb" in str(i.get("operations", [])).lower()
            for i in nsx_integrations
        ):
            level, equivalent, path, recommendations = self.CLASSIFICATION_RULES["load_balancers"]
            components.append(
                ClassifiedComponent(
                    name="NSX Load Balancer",
                    component_type="nsx_load_balancers",
                    level=level,
                    reason=self._get_reason("load_balancers", level, equivalent),
                    openshift_equivalent=equivalent,
                    migration_path=path,
                    location=location,
                    recommendations=recommendations.copy(),
                )
            )

        return components

    def _deduplicate_operations(
        self, operations: list[dict[str, Any]], category: str
    ) -> list[dict[str, Any]]:
        """
        Deduplicate NSX operations that represent the same logical operation.

        Multiple detection patterns may identify the same NSX operation (e.g.,
        "nsxClient.createSecurityGroup" and "SecurityGroup" in the same location).
        This method consolidates them into a single operation with combined evidence.

        Also consolidates "unknown" location detections (from script content) with
        workflow item detections when they likely represent the same operation.

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

        # Group operations by location
        # For filename:line format, group nearby lines (within 5 lines) together
        location_groups: dict[str, list[dict[str, Any]]] = {}
        for op in operations:
            location = op.get("location", "unknown")

            # Try to find a nearby location group (for line numbers)
            merged_into_existing = False
            if ":" in location and location != "unknown":
                try:
                    filename, line_str = location.rsplit(":", 1)
                    if line_str.isdigit():
                        line_num = int(line_str)
                        # Check if there's a nearby location group in the same file
                        for existing_loc in list(location_groups.keys()):
                            if ":" in existing_loc:
                                exist_file, exist_line_str = existing_loc.rsplit(":", 1)
                                if exist_line_str.isdigit() and exist_file == filename:
                                    exist_line = int(exist_line_str)
                                    # If within 5 lines, consider same location
                                    if abs(line_num - exist_line) <= 5:
                                        location_groups[existing_loc].append(op)
                                        merged_into_existing = True
                                        break
                except (ValueError, AttributeError):
                    pass

            if not merged_into_existing:
                if location not in location_groups:
                    location_groups[location] = []
                location_groups[location].append(op)

        # Merge operations within each exact location
        merged_groups = []
        for location, group in location_groups.items():
            if len(group) == 1:
                merged_groups.append(group[0])
            else:
                merged = self._merge_operations(group, category)
                merged_groups.append(merged)

        # Now consolidate "unknown" location detections with workflow items
        # "unknown" detections are typically script content that's inside workflow items
        deduplicated = self._consolidate_unknown_with_workflow_items(merged_groups, category)

        return deduplicated

    def _consolidate_unknown_with_workflow_items(
        self, operations: list[dict[str, Any]], category: str
    ) -> list[dict[str, Any]]:
        """
        Consolidate "unknown" location detections with workflow item detections.

        Script content detections (location="unknown") are often from scripts inside
        workflow items. This method merges them with the workflow item that likely
        contains them.

        Args:
            operations: List of operations (after initial location-based merging)
            category: NSX category

        Returns:
            Consolidated list with unknown detections merged into workflow items
        """
        # Separate unknown detections from file:line detections
        unknown_ops = [op for op in operations if op.get("location") == "unknown"]
        # File:line format is "filename.xml:123" or "filename.xml:itemname"
        located_ops = [op for op in operations if op.get("location") != "unknown"]

        if not unknown_ops or not located_ops:
            # No consolidation possible
            return operations

        # Track which unknown ops have been matched
        matched_unknown_indices = set()
        consolidated_result = []

        # Try to match each located op with unknown ops
        for located_op in located_ops:
            located_name = located_op.get("name", "").lower()
            matching_unknowns = []

            # Find all unknown ops that match this located op
            for idx, unknown_op in enumerate(unknown_ops):
                if idx in matched_unknown_indices:
                    continue

                unknown_name = unknown_op.get("name", "").lower()

                # Match if names are related
                if self._names_are_related(located_name, unknown_name, category):
                    matching_unknowns.append(unknown_op)
                    matched_unknown_indices.add(idx)

            # Merge located op with all matching unknowns
            if matching_unknowns:
                all_ops_to_merge = [located_op] + matching_unknowns
                merged = self._merge_operations(all_ops_to_merge, category)
                consolidated_result.append(merged)
            else:
                # No matches - keep located op as-is
                consolidated_result.append(located_op)

        # Add any unmatched unknown operations
        for idx, unknown_op in enumerate(unknown_ops):
            if idx not in matched_unknown_indices:
                consolidated_result.append(unknown_op)

        return consolidated_result

    def _names_are_related(self, name1: str, name2: str, category: str) -> bool:
        """
        Check if two operation names likely refer to the same operation.

        Args:
            name1: First operation name
            name2: Second operation name
            category: NSX category

        Returns:
            True if names appear to be related
        """
        # Strip common prefixes/suffixes
        name1_clean = name1.replace("nsxclient.", "").replace("nsx", "").replace("\\", "")
        name2_clean = name2.replace("nsxclient.", "").replace("nsx", "").replace("\\", "")

        # Check for substring match (one contains the other)
        if name1_clean in name2_clean or name2_clean in name1_clean:
            return True

        # Check if both contain the category name
        category_name = category.replace("_", "")
        if category_name in name1_clean and category_name in name2_clean:
            return True

        return False

    def _merge_operations(self, operations: list[dict[str, Any]], category: str) -> dict[str, Any]:
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

        # Combine evidence, consolidating pattern matches on the same line
        combined_evidence = self._consolidate_evidence(operations)

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

    def _consolidate_evidence(self, operations: list[dict[str, Any]]) -> str | None:
        """
        Consolidate evidence entries, combining pattern matches on the same line.

        When multiple patterns match on the same line with similar context,
        combine them into a single evidence entry for better readability.

        Args:
            operations: List of operations to merge

        Returns:
            Consolidated evidence string, or None if no evidence

        Example:
            Input:
                Pattern match: nsxClient.createSG in context (file.xml:64): ...
                Pattern match: SecurityGroup in context (file.xml:64): ...
            Output:
                Pattern matches: nsxClient.createSG, SecurityGroup (file.xml:64): ...
        """
        import re

        if not operations:
            return None

        # Group evidence by location
        evidence_by_location: dict[str, list[dict[str, Any]]] = {}

        for op in operations:
            evidence = op.get("evidence")
            if not evidence:
                continue

            # Parse evidence to extract location and type
            # Format 1: "Pattern match: X in context (location): ..."
            pattern_match = re.match(r"Pattern match: (.+?) in context \((.+?)\): (.+)", evidence)
            # Format 2: "Workflow item name/type contains NSX keyword (location): ..."
            workflow_match = re.match(
                r"Workflow item name/type contains NSX keyword \((.+?)\): (.+)", evidence
            )

            if pattern_match:
                pattern_name = pattern_match.group(1)
                location = pattern_match.group(2)
                context = pattern_match.group(3)

                if location not in evidence_by_location:
                    evidence_by_location[location] = []

                evidence_by_location[location].append(
                    {
                        "type": "pattern",
                        "pattern": pattern_name,
                        "context": context,
                        "original": evidence,
                    }
                )
            elif workflow_match:
                location = workflow_match.group(1)
                keyword = workflow_match.group(2)

                if location not in evidence_by_location:
                    evidence_by_location[location] = []

                evidence_by_location[location].append(
                    {
                        "type": "workflow_item",
                        "keyword": keyword,
                        "original": evidence,
                    }
                )
            else:
                # Unknown format - keep as-is
                if "unknown" not in evidence_by_location:
                    evidence_by_location["unknown"] = []
                evidence_by_location["unknown"].append({"type": "other", "original": evidence})

        # Build consolidated evidence
        consolidated_parts = []

        for location, entries in evidence_by_location.items():
            # Separate pattern matches from workflow items
            pattern_entries = [e for e in entries if e["type"] == "pattern"]
            workflow_entries = [e for e in entries if e["type"] == "workflow_item"]
            other_entries = [e for e in entries if e["type"] == "other"]

            # Consolidate pattern matches on same line
            if pattern_entries:
                if len(pattern_entries) == 1:
                    # Single pattern - use original format
                    consolidated_parts.append(pattern_entries[0]["original"])
                else:
                    # Multiple patterns - combine them, deduplicating pattern names
                    patterns = [e["pattern"] for e in pattern_entries]
                    # Deduplicate while preserving order
                    unique_patterns = []
                    seen = set()
                    for p in patterns:
                        if p not in seen:
                            unique_patterns.append(p)
                            seen.add(p)
                    # Use the longest context (likely most complete)
                    context = max((e["context"] for e in pattern_entries), key=len)
                    consolidated_parts.append(
                        f"Pattern matches: {', '.join(unique_patterns)} ({location}): {context}"
                    )

            # Add workflow items as-is
            for entry in workflow_entries:
                consolidated_parts.append(entry["original"])

            # Add other entries as-is
            for entry in other_entries:
                consolidated_parts.append(entry["original"])

        return "\n".join(consolidated_parts) if consolidated_parts else None

    def _clean_display_name(self, name: str) -> str:
        """
        Clean up regex artifacts from operation names for user-friendly display.

        Removes regex escape characters (backslashes) that were used in pattern
        matching but shouldn't be shown to end users.

        Args:
            name: Raw operation name (may contain regex escape chars)

        Returns:
            Cleaned name suitable for display

        Example:
            >>> classifier._clean_display_name("nsxClient\\.createSecurityGroup")
            'nsxClient.createSecurityGroup'
        """
        # Remove backslash escapes used in regex patterns
        cleaned = (
            name.replace("\\.", ".").replace("\\-", "-").replace("\\(", "(").replace("\\)", ")")
        )

        return cleaned

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
