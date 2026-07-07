"""
NSX Segment-to-Rule Correlation Engine.

Analyzes NSX firewall rule evidence to determine which network segments
(secondary networks) each rule applies to, enabling intelligent routing
of rules to MultiNetworkPolicy vs standard NetworkPolicy.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SegmentMapping:
    """Mapping of a single segment to its associated firewall rules."""

    segment_id: str
    segment_name: str
    nad_name: str  # Sanitized name for NetworkAttachmentDefinition
    vlan_ids: list[int] = field(default_factory=list)
    subnets: list[str] = field(default_factory=list)
    firewall_rules: list[str] = field(default_factory=list)
    correlation_confidence: float = 0.0
    correlation_evidence: list[str] = field(default_factory=list)


@dataclass
class SegmentRuleMapping:
    """Complete mapping of rules to primary network or specific segments."""

    primary_network_rules: list[str] = field(default_factory=list)
    segment_mappings: dict[str, SegmentMapping] = field(default_factory=dict)


class NSXCorrelationEngine:
    """
    Correlates NSX firewall rules with network segments.

    Uses multiple detection strategies to determine if a firewall rule
    applies to a specific segment (secondary network) or the primary network.

    Detection Strategies (in priority order):
    1. Direct Reference (0.9 confidence) - Rule evidence contains segment name
    2. IP Range Overlap (0.7 confidence) - Rule IPs fall within segment subnet
    3. VLAN Matching (0.7 confidence) - Same VLAN ID in rule and segment
    4. Proximity Analysis (0.4 confidence) - Same workflow location
    5. Default to Primary (0.5 confidence) - No correlation found

    Example:
        >>> engine = NSXCorrelationEngine()
        >>> segments = [{"name": "Web-Tier-VLAN100", "subnets": ["10.10.100.0/24"]}]
        >>> rules = [{"name": "Allow-Web-DB", "evidence": "segment: Web-Tier-VLAN100"}]
        >>> mapping = engine.correlate_rules_to_segments(rules, segments)
        >>> "Web-Tier-VLAN100" in mapping.segment_mappings
        True
    """

    # Confidence scores for different detection methods
    CONFIDENCE_DIRECT_REFERENCE = 0.9
    CONFIDENCE_IP_OVERLAP = 0.7
    CONFIDENCE_VLAN_MATCH = 0.7
    CONFIDENCE_PROXIMITY = 0.4
    CONFIDENCE_DEFAULT_PRIMARY = 0.5

    # Multi-signal boost (when multiple detection methods agree)
    MULTI_SIGNAL_BOOST = 0.05
    MAX_MULTI_SIGNAL_BOOST = 0.15
    MAX_CONFIDENCE = 0.95  # Never 100% certain with heuristics

    def correlate_rules_to_segments(
        self, firewall_rules: list[dict[str, Any]], segments: list[dict[str, Any]]
    ) -> SegmentRuleMapping:
        """
        Correlate firewall rules to network segments.

        Args:
            firewall_rules: List of detected NSX firewall rules with evidence
            segments: List of detected NSX segments

        Returns:
            SegmentRuleMapping with primary/secondary network rule assignments

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> rules = [
            ...     {"name": "Rule1", "evidence": "segment: Web-VLAN100"},
            ...     {"name": "Rule2", "evidence": "allow internet"}
            ... ]
            >>> segs = [{"name": "Web-VLAN100", "subnets": ["10.10.100.0/24"]}]
            >>> mapping = engine.correlate_rules_to_segments(rules, segs)
            >>> len(mapping.segment_mappings)
            1
            >>> len(mapping.primary_network_rules)
            1
        """
        # Validation
        if not firewall_rules:
            return SegmentRuleMapping()

        if not segments:
            # No segments - all rules go to primary network
            return SegmentRuleMapping(
                primary_network_rules=[r.get("name", f"rule-{i}") for i, r in enumerate(firewall_rules)]
            )

        # Initialize segment mappings
        segment_map = {}
        for seg in segments:
            seg_name = seg.get("name", "")
            if not seg_name:
                continue

            # Extract metadata for correlation (prefer parsed fields over evidence)
            vlan_ids = seg.get("vlan_ids", []) or self._extract_vlan_ids(seg.get("evidence", ""))
            subnets = seg.get("subnets", []) or self._extract_subnets(seg.get("evidence", ""))

            # Create mapping with sanitized NAD name
            nad_name = self._sanitize_nad_name(seg_name)

            segment_map[seg_name] = SegmentMapping(
                segment_id=seg_name,
                segment_name=seg_name,
                nad_name=nad_name,
                vlan_ids=vlan_ids,
                subnets=subnets,
            )

        # Correlate each rule
        primary_rules = []
        for rule in firewall_rules:
            rule_name = rule.get("name", "")
            rule_evidence = rule.get("evidence", "")
            rule_location = rule.get("location", "")

            # Try all detection strategies
            detections = []

            # Strategy 0: Parsed Segment Field (HIGHEST PRIORITY)
            # If the firewall rule has a parsed 'segment' field, use it directly
            parsed_segment = rule.get("segment")
            if parsed_segment and parsed_segment in segment_map:
                detections.append(
                    {
                        "segment": parsed_segment,
                        "method": "Parsed Segment Field",
                        "confidence": 0.95,  # Highest confidence - it's a direct field match
                        "evidence": f"Firewall rule has explicit segment field: '{parsed_segment}'",
                    }
                )

            for seg_name, seg_mapping in segment_map.items():
                # Strategy 1: Direct Reference in Evidence
                if self._detect_direct_reference(rule_evidence, seg_name):
                    detections.append(
                        {
                            "segment": seg_name,
                            "method": "Direct Reference",
                            "confidence": self.CONFIDENCE_DIRECT_REFERENCE,
                            "evidence": f"Rule evidence contains segment name '{seg_name}'",
                        }
                    )

                # Strategy 2: IP Range Overlap
                rule_ips = self._extract_ip_addresses(rule_evidence)
                if rule_ips and seg_mapping.subnets:
                    if self._detect_ip_overlap(rule_ips, seg_mapping.subnets):
                        overlap_ips = [ip for ip in rule_ips if self._ip_in_subnets(ip, seg_mapping.subnets)]
                        detections.append(
                            {
                                "segment": seg_name,
                                "method": "IP Range Overlap",
                                "confidence": self.CONFIDENCE_IP_OVERLAP,
                                "evidence": f"Rule IPs {overlap_ips} in segment subnets {seg_mapping.subnets}",
                            }
                        )

                # Strategy 3: VLAN Matching
                rule_vlans = self._extract_vlan_ids(rule_evidence)
                if rule_vlans and seg_mapping.vlan_ids:
                    common_vlans = set(rule_vlans) & set(seg_mapping.vlan_ids)
                    if common_vlans:
                        detections.append(
                            {
                                "segment": seg_name,
                                "method": "VLAN Matching",
                                "confidence": self.CONFIDENCE_VLAN_MATCH,
                                "evidence": f"Rule and segment share VLAN IDs: {list(common_vlans)}",
                            }
                        )

                # Strategy 4: Proximity Analysis
                seg_location = segments[[s.get("name") for s in segments].index(seg_name)].get("location", "")
                if rule_location and seg_location:
                    if self._detect_proximity(rule_location, seg_location):
                        detections.append(
                            {
                                "segment": seg_name,
                                "method": "Proximity Analysis",
                                "confidence": self.CONFIDENCE_PROXIMITY,
                                "evidence": f"Rule and segment in nearby locations ({rule_location}, {seg_location})",
                            }
                        )

            # Determine final assignment
            if detections:
                # Assign to segment with highest confidence
                # If multiple detections for same segment, combine confidence
                segment_detections = {}
                for det in detections:
                    seg = det["segment"]
                    if seg not in segment_detections:
                        segment_detections[seg] = []
                    segment_detections[seg].append(det)

                # Calculate combined confidence for each segment
                best_segment = None
                best_confidence = 0
                best_evidence = []

                for seg, dets in segment_detections.items():
                    confidence = self._calculate_combined_confidence(dets)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_segment = seg
                        best_evidence = [d["evidence"] for d in dets]

                # Assign to best segment
                if best_segment and best_confidence >= self.CONFIDENCE_DEFAULT_PRIMARY:
                    segment_map[best_segment].firewall_rules.append(rule_name)
                    segment_map[best_segment].correlation_evidence.extend(best_evidence)
                    # Update segment confidence (average of all rules)
                    current_rules = len(segment_map[best_segment].firewall_rules)
                    segment_map[best_segment].correlation_confidence = (
                        segment_map[best_segment].correlation_confidence * (current_rules - 1) + best_confidence
                    ) / current_rules
                else:
                    # Low confidence - assign to primary
                    primary_rules.append(rule_name)
            else:
                # No correlation found - assign to primary network
                primary_rules.append(rule_name)

        return SegmentRuleMapping(
            primary_network_rules=primary_rules, segment_mappings=segment_map
        )

    def _detect_direct_reference(self, rule_evidence: str, segment_name: str) -> bool:
        """
        Detect if rule evidence directly references segment name.

        Args:
            rule_evidence: Firewall rule evidence string
            segment_name: Segment name to search for

        Returns:
            True if segment name found in evidence

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> engine._detect_direct_reference(
            ...     "segment: 'Web-Tier-VLAN100'",
            ...     "Web-Tier-VLAN100"
            ... )
            True
        """
        # Case-insensitive search for segment name
        return segment_name.lower() in rule_evidence.lower()

    def _detect_ip_overlap(self, rule_ips: list[str], segment_subnets: list[str]) -> bool:
        """
        Detect if any rule IPs fall within segment subnets.

        Args:
            rule_ips: List of IP addresses from rule
            segment_subnets: List of CIDR subnets from segment

        Returns:
            True if any IP overlaps with subnets

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> engine._detect_ip_overlap(
            ...     ["10.10.100.50"],
            ...     ["10.10.100.0/24"]
            ... )
            True
        """
        for ip_str in rule_ips:
            if self._ip_in_subnets(ip_str, segment_subnets):
                return True
        return False

    def _ip_in_subnets(self, ip_str: str, subnets: list[str]) -> bool:
        """Check if IP address is in any of the subnets."""
        try:
            ip = ipaddress.ip_address(ip_str)
            for subnet_str in subnets:
                try:
                    subnet = ipaddress.ip_network(subnet_str, strict=False)
                    if ip in subnet:
                        return True
                except (ValueError, ipaddress.AddressValueError):
                    continue
        except (ValueError, ipaddress.AddressValueError):
            return False
        return False

    def _detect_proximity(self, rule_location: str, segment_location: str, threshold: int = 50) -> bool:
        """
        Detect if rule and segment are in nearby workflow locations.

        Args:
            rule_location: Rule location (e.g., "file.xml:145")
            segment_location: Segment location (e.g., "file.xml:160")
            threshold: Maximum line difference to consider "nearby"

        Returns:
            True if locations are nearby

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> engine._detect_proximity("workflow.xml:145", "workflow.xml:160")
            True
            >>> engine._detect_proximity("workflow.xml:100", "workflow.xml:500")
            False
        """
        # Extract filename and line number
        try:
            rule_parts = rule_location.rsplit(":", 1)
            seg_parts = segment_location.rsplit(":", 1)

            if len(rule_parts) != 2 or len(seg_parts) != 2:
                return False

            rule_file, rule_line_str = rule_parts
            seg_file, seg_line_str = seg_parts

            # Must be same file
            if rule_file != seg_file:
                return False

            # Check line number proximity
            if rule_line_str.isdigit() and seg_line_str.isdigit():
                line_diff = abs(int(rule_line_str) - int(seg_line_str))
                return line_diff <= threshold

        except (ValueError, AttributeError):
            pass

        return False

    def _extract_vlan_ids(self, evidence: str) -> list[int]:
        """
        Extract VLAN IDs from evidence string.

        Args:
            evidence: Evidence string to parse

        Returns:
            List of VLAN IDs

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> engine._extract_vlan_ids("vlanIds: [100, 200]")
            [100, 200]
        """
        vlan_ids = []

        # Pattern 1: vlanIds: [100, 200]
        vlan_array = re.search(r"vlanIds?\s*:\s*\[([^\]]+)\]", evidence, re.IGNORECASE)
        if vlan_array:
            numbers = re.findall(r"\d+", vlan_array.group(1))
            vlan_ids.extend(int(n) for n in numbers)

        # Pattern 2: VLAN 100, vlan=200
        vlan_singles = re.findall(r"vlan\s*[=:]?\s*(\d+)", evidence, re.IGNORECASE)
        vlan_ids.extend(int(v) for v in vlan_singles)

        return list(set(vlan_ids))  # Deduplicate

    def _extract_subnets(self, evidence: str) -> list[str]:
        """
        Extract subnet CIDR ranges from evidence string.

        Args:
            evidence: Evidence string to parse

        Returns:
            List of CIDR subnet strings

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> engine._extract_subnets("subnets: ['10.10.100.0/24']")
            ['10.10.100.0/24']
        """
        subnets = []

        # Pattern: IP address with CIDR notation
        cidr_pattern = r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})\b"
        cidrs = re.findall(cidr_pattern, evidence)

        for cidr in cidrs:
            try:
                # Validate it's a valid network
                ipaddress.ip_network(cidr, strict=False)
                subnets.append(cidr)
            except (ValueError, ipaddress.AddressValueError):
                continue

        return subnets

    def _extract_ip_addresses(self, evidence: str) -> list[str]:
        """
        Extract IP addresses from evidence string.

        Args:
            evidence: Evidence string to parse

        Returns:
            List of IP address strings

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> engine._extract_ip_addresses("source: 10.10.100.50, dest: 10.10.200.60")
            ['10.10.100.50', '10.10.200.60']
        """
        ip_addresses = []

        # Pattern: Standard IP address (not CIDR)
        ip_pattern = r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b(?!/)"
        ips = re.findall(ip_pattern, evidence)

        for ip_str in ips:
            try:
                # Validate it's a valid IP
                ipaddress.ip_address(ip_str)
                ip_addresses.append(ip_str)
            except (ValueError, ipaddress.AddressValueError):
                continue

        return ip_addresses

    def _sanitize_nad_name(self, segment_name: str) -> str:
        """
        Sanitize segment name for Kubernetes NetworkAttachmentDefinition naming.

        Args:
            segment_name: Original segment name

        Returns:
            DNS-1123 compliant name

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> engine._sanitize_nad_name("Web Tier VLAN100")
            'web-tier-vlan100'
        """
        # Convert to lowercase
        name = segment_name.lower()

        # Replace spaces and underscores with hyphens
        name = name.replace(" ", "-").replace("_", "-")

        # Remove non-alphanumeric characters (except hyphens)
        name = re.sub(r"[^a-z0-9-]", "", name)

        # Remove leading/trailing hyphens
        name = name.strip("-")

        # Collapse multiple hyphens
        name = re.sub(r"-+", "-", name)

        # Ensure it's not empty
        if not name:
            name = "segment"

        return name

    def _calculate_combined_confidence(self, detections: list[dict[str, Any]]) -> float:
        """
        Calculate combined confidence from multiple detection signals.

        Uses base confidence (highest) plus multi-signal boost for corroborating evidence.

        Args:
            detections: List of detection results

        Returns:
            Combined confidence score (capped at MAX_CONFIDENCE)

        Example:
            >>> engine = NSXCorrelationEngine()
            >>> dets = [
            ...     {"confidence": 0.9},  # Direct reference
            ...     {"confidence": 0.7}   # VLAN match (corroborating)
            ... ]
            >>> engine._calculate_combined_confidence(dets)
            0.95
        """
        if not detections:
            return self.CONFIDENCE_DEFAULT_PRIMARY

        # Base confidence: highest signal
        base_confidence = max(d["confidence"] for d in detections)

        # Multi-signal boost: additional signals increase confidence
        num_additional_signals = len(detections) - 1
        boost = min(num_additional_signals * self.MULTI_SIGNAL_BOOST, self.MAX_MULTI_SIGNAL_BOOST)

        # Cap at max confidence
        return min(base_confidence + boost, self.MAX_CONFIDENCE)
