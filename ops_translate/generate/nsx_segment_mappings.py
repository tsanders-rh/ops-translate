"""
NSX-T segment to Kubernetes NetworkAttachmentDefinition mappings.

Maps NSX networking concepts to Multus CNI plugin configurations,
specifically for translating NSX segments to NAD manifests.
"""

import ipaddress
import re
from typing import Any


class NSXSegmentMapper:
    """Maps NSX-T segments to NetworkAttachmentDefinition configurations."""

    def determine_cni_type(self, segment_details: dict[str, Any]) -> dict[str, Any]:
        """
        Determine appropriate CNI plugin type for segment.

        Args:
            segment_details: Parsed segment configuration

        Returns:
            Dict with CNI type, mode, reason, and warnings

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper.determine_cni_type({"vlan_ids": [100]})
            {'type': 'macvlan', 'mode': 'bridge', 'reason': '...'}
        """
        # Check for VLAN segments → macvlan (most common)
        if segment_details.get("vlan_ids"):
            return {
                "type": "macvlan",
                "mode": "bridge",  # Bridge mode allows pod-to-pod on same host
                "reason": "VLAN segment detected - using macvlan for L2 connectivity",
                "requires_manual_config": False,
                "warnings": [],
            }

        # Check for overlay segments → bridge
        if self._is_overlay_segment(
            segment_details.get("transport_zone", ""),
            segment_details.get("evidence", ""),
        ):
            return {
                "type": "bridge",
                "mode": None,
                "reason": "Overlay segment - using bridge plugin for encapsulation",
                "requires_manual_config": False,
                "warnings": [
                    "NSX overlay encapsulation differs from Linux bridge",
                    "Verify L2 connectivity matches NSX configuration",
                ],
            }

        # Check for high-performance indicators → SR-IOV
        if self._is_performance_segment(
            segment_details.get("name", ""), segment_details.get("evidence", "")
        ):
            return {
                "type": "sriov",
                "mode": None,
                "reason": "High-performance segment detected - using SR-IOV",
                "requires_manual_config": True,
                "warnings": [
                    "SR-IOV requires hardware support and host configuration",
                    "Verify network interface supports SR-IOV",
                    "Configure SR-IOV network device plugin on nodes",
                    "Ensure sufficient VF resources available",
                ],
            }

        # Default to macvlan with manual config warning
        return {
            "type": "macvlan",
            "mode": "bridge",
            "reason": "Default selection - verify CNI type matches NSX segment configuration",
            "requires_manual_config": True,
            "warnings": [
                "Could not determine segment type from evidence",
                "Defaulting to macvlan - verify this matches NSX configuration",
            ],
        }

    def build_ipam_config(self, segment_details: dict[str, Any]) -> dict[str, Any]:
        """
        Build IPAM configuration for segment.

        Uses Whereabouts for dynamic allocation (closest to NSX DHCP).
        Falls back to placeholders if subnet information is missing.

        Args:
            segment_details: Parsed segment configuration

        Returns:
            IPAM configuration dict

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper.build_ipam_config({"subnets": ["10.10.10.0/24"]})
            {'type': 'whereabouts', 'range': '10.10.10.0/24', ...}
        """
        ipam_type = "whereabouts"  # Default to dynamic allocation

        subnets = segment_details.get("subnets", [])
        if subnets:
            subnet = subnets[0]  # Use first subnet

            # Extract gateway (or infer from subnet)
            gateway = segment_details.get("gateway")
            if not gateway:
                gateway = self._infer_gateway_from_subnet(subnet)

            # Calculate IP allocation pool
            range_start, range_end = self._calculate_ip_pool(subnet, gateway)

            return {
                "type": ipam_type,
                "range": subnet,
                "range_start": range_start,
                "range_end": range_end,
                "gateway": gateway,
                "routes": [{"dst": "0.0.0.0/0"}],  # Default route
            }

        # No subnet detected - generate placeholder
        return {
            "type": ipam_type,
            "range": "TODO: Configure subnet CIDR (e.g., 10.10.10.0/24)",
            "range_start": "TODO: Start IP (e.g., 10.10.10.10)",
            "range_end": "TODO: End IP (e.g., 10.10.10.250)",
            "gateway": "TODO: Gateway IP (e.g., 10.10.10.1)",
            "routes": [{"dst": "0.0.0.0/0"}],
        }

    def build_cni_config(
        self,
        cni_type: dict[str, Any],
        segment_details: dict[str, Any],
        ipam: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build complete CNI plugin configuration.

        Args:
            cni_type: CNI type information from determine_cni_type()
            segment_details: Parsed segment configuration
            ipam: IPAM configuration from build_ipam_config()

        Returns:
            Complete CNI configuration dict

        Example:
            >>> config = mapper.build_cni_config(
            ...     {"type": "macvlan", "mode": "bridge"},
            ...     {"vlan_ids": [100]},
            ...     {"type": "whereabouts", "range": "10.10.10.0/24"}
            ... )
            >>> config['type']
            'macvlan'
        """
        config: dict[str, Any] = {
            "cniVersion": "0.3.1",
            "type": cni_type["type"],
            "ipam": ipam,
        }

        # Add VLAN configuration for macvlan/bridge
        vlan_ids = segment_details.get("vlan_ids", [])
        if vlan_ids and cni_type["type"] in ["macvlan", "bridge"]:
            config["vlan"] = vlan_ids[0]
            # Master interface - default to eth1, user should configure
            config["master"] = "TODO: Specify parent interface (e.g., eth1, ens3)"

        # Add mode for macvlan
        if cni_type["type"] == "macvlan":
            config["mode"] = cni_type.get("mode", "bridge")

        # Add SR-IOV specifics
        if cni_type["type"] == "sriov":
            config["vf"] = 0  # Virtual function index
            config["deviceID"] = "TODO: Configure SR-IOV device ID"

        # Add bridge name for bridge plugin
        if cni_type["type"] == "bridge":
            name = segment_details.get("name", "segment")
            sanitized = self.sanitize_name(name)
            config["bridge"] = f"br-{sanitized}"
            config["isGateway"] = True
            config["ipMasq"] = True

        return config

    def extract_vlan_ids(self, evidence: str) -> list[int]:
        """
        Extract VLAN IDs from evidence text.

        Args:
            evidence: Detection evidence string

        Returns:
            List of VLAN IDs (integers)

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper.extract_vlan_ids('vlanIds: [100, 200]')
            [100, 200]
        """
        vlan_ids = []

        # Pattern 1: vlanIds: [100] or vlan: 100
        pattern1 = r"vlan(?:Ids?)?\s*[:=]\s*\[?(\d+(?:,\s*\d+)*)\]?"
        matches = re.finditer(pattern1, evidence, re.IGNORECASE)
        for match in matches:
            vlan_str = match.group(1)
            vlans = [int(v.strip()) for v in vlan_str.split(",")]
            vlan_ids.extend(vlans)

        # Pattern 2: VLAN ID in name (e.g., "VLAN100", "vlan-100")
        pattern2 = r"vlan[_-]?(\d+)"
        matches = re.finditer(pattern2, evidence, re.IGNORECASE)
        for match in matches:
            vlan_ids.append(int(match.group(1)))

        return list(set(vlan_ids))  # Remove duplicates

    def extract_subnets(self, evidence: str) -> list[str]:
        """
        Extract subnet CIDR from evidence text.

        Args:
            evidence: Detection evidence string

        Returns:
            List of subnet CIDR strings

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper.extract_subnets('subnet: "10.10.10.0/24"')
            ['10.10.10.0/24']
        """
        subnets = []

        # Pattern 1: CIDR notation (10.10.10.0/24)
        cidr_pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})"
        matches = re.finditer(cidr_pattern, evidence)
        for match in matches:
            cidr = match.group(1)
            # Validate CIDR
            try:
                ipaddress.ip_network(cidr, strict=False)
                subnets.append(cidr)
            except ValueError:
                # Invalid CIDR, skip
                pass

        # Pattern 2: networkAddress + netmask/prefix
        # networkAddress: "10.10.10.0", prefix: 24
        network_pattern = (
            r'networkAddress\s*[:=]\s*["\']?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})["\']?'
        )
        prefix_pattern = r"(?:prefix|netmask)\s*[:=]\s*(\d{1,2})"

        network_match = re.search(network_pattern, evidence)
        prefix_match = re.search(prefix_pattern, evidence)

        if network_match and prefix_match:
            network = network_match.group(1)
            prefix = prefix_match.group(1)
            cidr = f"{network}/{prefix}"
            try:
                ipaddress.ip_network(cidr, strict=False)
                subnets.append(cidr)
            except ValueError:
                pass

        return list(set(subnets))  # Remove duplicates

    def extract_gateway(self, evidence: str, subnet: str | None = None) -> str | None:
        """
        Extract gateway IP from evidence or infer from subnet.

        Args:
            evidence: Detection evidence string
            subnet: Subnet CIDR (optional, for inference)

        Returns:
            Gateway IP address or None

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper.extract_gateway('gateway: "10.10.10.1"')
            '10.10.10.1'
        """
        # Pattern 1: Explicit gateway
        gateway_pattern = (
            r'gateway(?:Address)?\s*[:=]\s*["\']?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})["\']?'
        )
        match = re.search(gateway_pattern, evidence, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 2: Gateway with CIDR (remove suffix)
        gateway_cidr_pattern = (
            r'gateway\s*[:=]\s*["\']?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/\d+["\']?'
        )
        match = re.search(gateway_cidr_pattern, evidence, re.IGNORECASE)
        if match:
            return match.group(1)

        # Fallback: Infer from subnet
        if subnet:
            return self._infer_gateway_from_subnet(subnet)

        return None

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize NSX segment name for Kubernetes resource name.

        Kubernetes names must be DNS-1123 compliant:
        - lowercase alphanumeric + '-'
        - start with alphanumeric
        - max 253 chars

        Args:
            name: Original NSX segment name

        Returns:
            Sanitized Kubernetes-compatible name

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper.sanitize_name("Web Tier VLAN100")
            'web-tier-vlan100'
        """
        # Convert to lowercase
        name = name.lower()

        # Replace spaces and underscores with hyphens
        name = name.replace(" ", "-").replace("_", "-")

        # Remove non-alphanumeric characters except hyphens
        name = re.sub(r"[^a-z0-9-]", "", name)

        # Remove leading/trailing hyphens
        name = name.strip("-")

        # Collapse multiple hyphens
        name = re.sub(r"-+", "-", name)

        # Ensure starts with alphanumeric
        if name and not name[0].isalnum():
            name = "nsx-" + name

        # Truncate to max 253 chars
        if len(name) > 253:
            name = name[:253].rstrip("-")

        # Default if empty
        if not name:
            name = "nsx-segment"

        return name

    def _infer_gateway_from_subnet(self, subnet: str) -> str:
        """
        Infer gateway IP from subnet CIDR.

        Uses first usable IP in subnet (.1) as gateway.

        Args:
            subnet: Subnet CIDR

        Returns:
            Gateway IP address

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper._infer_gateway_from_subnet("10.10.10.0/24")
            '10.10.10.1'
        """
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            # Use first host IP as gateway (typically .1)
            gateway = str(network.network_address + 1)
            return gateway
        except ValueError:
            # If CIDR is invalid, return placeholder
            return "TODO: Configure gateway IP"

    def _calculate_ip_pool(self, subnet: str, gateway: str | None = None) -> tuple[str, str]:
        """
        Calculate IP allocation pool from subnet.

        Reserves first 10 IPs and last 5 IPs for infrastructure.

        Args:
            subnet: Subnet CIDR
            gateway: Gateway IP (optional)

        Returns:
            Tuple of (range_start, range_end)

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper._calculate_ip_pool("10.10.10.0/24")
            ('10.10.10.10', '10.10.10.250')
        """
        try:
            network = ipaddress.ip_network(subnet, strict=False)

            # Reserve first 10 addresses (.0-.9) for network/gateway/infra
            start_offset = 10

            # Reserve last 5 addresses for broadcast/infrastructure
            end_offset = 5

            all_hosts = list(network.hosts())
            if len(all_hosts) < start_offset + end_offset:
                # Very small subnet, use all available IPs
                return (str(all_hosts[0]), str(all_hosts[-1]))

            range_start = str(all_hosts[start_offset - 1])
            range_end = str(all_hosts[-(end_offset + 1)])

            return (range_start, range_end)
        except (ValueError, IndexError):
            # If CIDR is invalid or too small, return placeholders
            return ("TODO: Start IP", "TODO: End IP")

    def _is_overlay_segment(self, transport_zone: str, evidence: str) -> bool:
        """
        Detect if segment is overlay type.

        Args:
            transport_zone: Transport zone name/type
            evidence: Detection evidence

        Returns:
            True if overlay segment

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper._is_overlay_segment("overlay-tz", "")
            True
        """
        overlay_keywords = ["overlay", "geneve", "vxlan", "nvgre"]

        # Check transport zone
        for keyword in overlay_keywords:
            if keyword in transport_zone.lower():
                return True

        # Check evidence
        for keyword in overlay_keywords:
            if keyword in evidence.lower():
                return True

        return False

    def _is_performance_segment(self, name: str, evidence: str) -> bool:
        """
        Detect if segment requires high-performance (SR-IOV).

        Args:
            name: Segment name
            evidence: Detection evidence

        Returns:
            True if high-performance segment

        Example:
            >>> mapper = NSXSegmentMapper()
            >>> mapper._is_performance_segment("High-Performance-Network", "")
            True
        """
        performance_keywords = [
            "performance",
            "sriov",
            "sr-iov",
            "dedicated",
            "low-latency",
            "dpdk",
        ]

        combined_text = f"{name} {evidence}".lower()

        for keyword in performance_keywords:
            if keyword in combined_text:
                return True

        return False
