"""
Generate Kubernetes NetworkAttachmentDefinition manifests from NSX segments.

This module translates NSX-T segments detected in vRealize workflows into
Multus CNI NetworkAttachmentDefinition YAML, with clear documentation of
limitations and unsupported features.
"""

import json
import re
from typing import Any

import yaml

from ops_translate.generate.nsx_segment_mappings import NSXSegmentMapper


def generate_network_attachments(
    nsx_segments: list[dict[str, Any]],
    workflow_name: str = "workflow",
) -> dict[str, str]:
    """
    Generate NetworkAttachmentDefinition YAML files from NSX segments.

    Args:
        nsx_segments: List of detected NSX segment operations
        workflow_name: Source workflow name for metadata

    Returns:
        Dictionary mapping filename to YAML content

    Example:
        >>> segments = [
        ...     {
        ...         'name': 'Web-Tier-VLAN100',
        ...         'location': 'workflow.xml:123',
        ...         'evidence': '...createSegment({vlanIds: [100]})...'
        ...     }
        ... ]
        >>> attachments = generate_network_attachments(segments)
        >>> 'web-tier-vlan100.yaml' in attachments
        True
    """
    if not nsx_segments:
        return {}

    mapper = NSXSegmentMapper()
    attachments = {}

    for segment in nsx_segments:
        # Try to parse segment details from evidence
        segment_details = _parse_segment_from_evidence(segment)

        # Skip if we couldn't extract meaningful segment information
        if not segment_details:
            continue

        # Generate NAD name
        segment_name = segment_details.get("name", segment.get("name", "unknown-segment"))
        nad_name = mapper.sanitize_name(segment_name)

        # Build NetworkAttachmentDefinition manifest
        nad = _build_network_attachment_definition(
            segment_details, mapper, workflow_name, segment.get("location")
        )

        if not nad:
            # Couldn't generate valid NAD
            continue

        # Determine CNI type for warnings
        cni_type = mapper.determine_cni_type(segment_details)

        # Detect limitations
        warnings = _detect_limitations(segment_details, cni_type)

        # Build CNI config for header comments
        ipam = mapper.build_ipam_config(segment_details)
        cni_config = mapper.build_cni_config(cni_type, segment_details, ipam)

        # Generate YAML with header comments
        header = _generate_header_comments(segment_details, segment, warnings, cni_config)
        nad_yaml = yaml.dump(nad, default_flow_style=False, sort_keys=False)

        # Combine header and YAML
        full_content = f"{header}\n{nad_yaml}"
        attachments[f"{nad_name}.yaml"] = full_content

    return attachments


def _parse_segment_from_evidence(segment: dict[str, Any]) -> dict[str, Any] | None:
    """
    Parse segment configuration from detection evidence.

    Args:
        segment: Detected NSX segment with evidence

    Returns:
        Dict with parsed segment details, or None if cannot parse

    Example:
        >>> segment = {
        ...     'name': 'nsxClient.createSegment',
        ...     'evidence': 'createSegment({displayName: "Web", vlanIds: [100]})'
        ... }
        >>> details = _parse_segment_from_evidence(segment)
        >>> details['vlan_ids']
        [100]
    """
    evidence = segment.get("evidence", "")
    name = segment.get("name", "")

    # Initialize segment details
    details: dict[str, Any] = {
        "name": name,
        "vlan_ids": [],
        "subnets": [],
        "gateway": None,
        "transport_zone": "",
        "has_dhcp": False,
        "evidence": evidence,
    }

    mapper = NSXSegmentMapper()

    # Try to extract structured data from evidence
    # Pattern 1: createSegment API call with JSON-like structure
    create_pattern = r"createSegment\s*\(\s*\{([^}]+)\}\s*\)"
    match = re.search(create_pattern, evidence, re.DOTALL)
    if match:
        config = match.group(1)

        # Extract display name
        name_match = re.search(r'displayName["\s:]+([^",\n]+)', config)
        if name_match:
            details["name"] = name_match.group(1).strip().strip("\"'")

        # Extract transport zone
        tz_match = re.search(r'transport[_-]?zone["\s:]+([^",\n]+)', config, re.IGNORECASE)
        if tz_match:
            details["transport_zone"] = tz_match.group(1).strip().strip("\"'")

        # Check for DHCP
        if "dhcp" in config.lower():
            details["has_dhcp"] = True

    # Extract VLAN IDs using mapper
    vlan_ids = mapper.extract_vlan_ids(evidence)
    if vlan_ids:
        details["vlan_ids"] = vlan_ids

    # Extract subnets using mapper
    subnets = mapper.extract_subnets(evidence)
    if subnets:
        details["subnets"] = subnets

    # Extract gateway using mapper
    subnet = subnets[0] if subnets else None
    gateway = mapper.extract_gateway(evidence, subnet)
    if gateway:
        details["gateway"] = gateway

    # If we have minimal information, return it
    if details["vlan_ids"] or details["subnets"] or details["transport_zone"]:
        return details

    # If we couldn't parse structured data but have a name, return basic details
    if name:
        return details

    return None


def _build_network_attachment_definition(
    segment_details: dict[str, Any],
    mapper: NSXSegmentMapper,
    workflow_name: str,
    location: str | None,
) -> dict[str, Any] | None:
    """
    Build NetworkAttachmentDefinition manifest from NSX segment details.

    Args:
        segment_details: Parsed segment details
        mapper: NSX to Kubernetes mapper
        workflow_name: Source workflow name
        location: Segment location for metadata

    Returns:
        NetworkAttachmentDefinition manifest dict, or None if cannot generate

    Example:
        >>> details = {"name": "Web-VLAN100", "vlan_ids": [100]}
        >>> mapper = NSXSegmentMapper()
        >>> nad = _build_network_attachment_definition(details, mapper, "test", None)
        >>> nad['kind']
        'NetworkAttachmentDefinition'
    """
    # Determine CNI type
    cni_type = mapper.determine_cni_type(segment_details)

    # Build IPAM configuration
    ipam = mapper.build_ipam_config(segment_details)

    # Build complete CNI configuration
    cni_config = mapper.build_cni_config(cni_type, segment_details, ipam)

    # Build NetworkAttachmentDefinition
    nad_name = mapper.sanitize_name(segment_details.get("name", "nsx-segment"))

    nad = {
        "apiVersion": "k8s.cni.cncf.io/v1",
        "kind": "NetworkAttachmentDefinition",
        "metadata": {
            "name": nad_name,
            "namespace": "default",
            "labels": {
                "translated-from": "nsx-segment",
                "source-workflow": workflow_name,
            },
        },
        "spec": {
            "config": json.dumps(cni_config, indent=2),
        },
    }

    # Add VLAN ID label if present
    vlan_ids = segment_details.get("vlan_ids", [])
    if vlan_ids:
        nad["metadata"]["labels"]["vlan-id"] = str(vlan_ids[0])

    # Add location annotation if available
    if location:
        metadata = nad["metadata"]
        if "annotations" not in metadata:
            metadata["annotations"] = {}  # type: ignore[index]
        metadata["annotations"]["source-location"] = location  # type: ignore[index]

    return nad


def _detect_limitations(segment_details: dict[str, Any], cni_type: dict[str, Any]) -> list[str]:
    """
    Detect NSX features in the segment that don't translate to NAD.

    Args:
        segment_details: Parsed segment details
        cni_type: CNI type information

    Returns:
        List of limitation warnings

    Example:
        >>> details = {"has_dhcp": True}
        >>> cni_type = {"type": "macvlan"}
        >>> warnings = _detect_limitations(details, cni_type)
        >>> any("DHCP" in w for w in warnings)
        True
    """
    warnings = []

    # Check for DHCP
    if segment_details.get("has_dhcp"):
        warnings.append(
            "NSX DHCP server detected. Whereabouts IPAM provides dynamic allocation "
            "but uses different lease management than NSX DHCP."
        )

    # Check for missing subnet info
    if not segment_details.get("subnets"):
        warnings.append(
            "No subnet information detected. Manual IPAM configuration required. "
            "Check TODO comments in generated config."
        )

    # Check for SR-IOV requirements
    if cni_type.get("requires_manual_config"):
        warnings.append(
            "Manual configuration required. Review CNI plugin settings and "
            "verify they match your NSX segment configuration."
        )

    # Warn about SR-IOV specifics
    if cni_type["type"] == "sriov":
        warnings.append(
            "SR-IOV requires: (1) Hardware support, (2) Host configuration, "
            "(3) SR-IOV device plugin, (4) VF resources. See prerequisites in header."
        )

    # Warn about multiple VLANs
    vlan_ids = segment_details.get("vlan_ids", [])
    if len(vlan_ids) > 1:
        warnings.append(
            f"Multiple VLAN IDs detected: {vlan_ids}. Using first VLAN ({vlan_ids[0]}). "
            "Create separate NADs for additional VLANs if needed."
        )

    # Generic NSX limitations
    warnings.append(
        "NSX L2 features (MAC learning, ARP suppression) are not available in standard CNI plugins."
    )

    warnings.append("NSX QoS policies must be configured separately using Kubernetes network QoS.")

    return warnings


def _generate_header_comments(
    segment_details: dict[str, Any],
    original_segment: dict[str, Any],
    warnings: list[str],
    cni_config: dict[str, Any],
) -> str:
    """
    Generate YAML header comments with context and limitations.

    Args:
        segment_details: Parsed segment details
        original_segment: Original detection data
        warnings: List of limitation warnings
        cni_config: CNI configuration dict

    Returns:
        Formatted header comment string

    Example:
        >>> header = _generate_header_comments({...}, {...}, [], {...})
        >>> "PREREQUISITES" in header
        True
    """
    segment_name = segment_details.get("name") or "unknown"
    location = original_segment.get("location", "unknown")
    vlan_ids = segment_details.get("vlan_ids", [])
    vlan = vlan_ids[0] if vlan_ids else "N/A"
    cni_type = cni_config.get("type", "unknown")

    header_parts = [
        "---",
        "# Generated from vRealize workflow NSX segment",
        f"# Source segment: {segment_name}",
        f"# Location: {location}",
        f"# VLAN: {vlan}",
        f"# CNI Plugin: {cni_type}",
        "#",
        "# PREREQUISITES - REQUIRED BEFORE DEPLOYMENT:",
        "# 1. Install Multus CNI on your cluster",
        "#    kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/master/deployments/multus-daemonset.yml",
        "#",
        "# 2. Install Whereabouts IPAM plugin (for dynamic IP allocation)",
        "#    kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/whereabouts/master/doc/daemonset-install.yaml",
        "#",
    ]

    # Add CNI-specific prerequisites
    if cni_type == "macvlan":
        header_parts.extend(
            [
                "# 3. Configure host network interface on all nodes",
                "#    - Ensure parent interface exists (check TODO in config)",
                f"#    - For VLAN {vlan}: Interface must support 802.1Q tagging",
                "#    - Configure switch ports for VLAN trunking",
                "#",
            ]
        )
    elif cni_type == "sriov":
        header_parts.extend(
            [
                "# 3. Install SR-IOV Network Device Plugin",
                "#    https://github.com/k8snetworkplumbingwg/sriov-network-device-plugin",
                "#",
                "# 4. Configure SR-IOV on worker nodes",
                "#    - Enable SR-IOV in BIOS",
                "#    - Configure VF (Virtual Functions) on network interface",
                "#    - Install and configure SR-IOV device plugin",
                "#",
                "# 5. Label nodes with SR-IOV capability",
                "#    kubectl label node <node-name> \\",
                "#      feature.node.kubernetes.io/network-sriov.capable=true",
                "#",
            ]
        )

    # Check for TODOs in config
    config_str = json.dumps(cni_config)
    if "TODO" in config_str:
        header_parts.extend(
            [
                "# CONFIGURATION REQUIRED:",
                "# - Review all TODO comments in the config section below",
                "# - Configure parent network interface name (master field)",
            ]
        )
        if "TODO" in str(cni_config.get("ipam", {})):
            header_parts.append("# - Configure IP address range and gateway")
        header_parts.append("# - Verify settings match your NSX segment configuration")
        header_parts.append("#")

    # Add specific warnings
    if warnings:
        header_parts.append("# DETECTED LIMITATIONS FOR THIS SEGMENT:")
        for warning in warnings:
            # Word wrap warnings to fit in comments
            wrapped_lines = _wrap_comment(warning, max_length=75)
            for line in wrapped_lines:
                header_parts.append(f"# {line}")
        header_parts.append("#")

    # Add general limitations
    header_parts.extend(
        [
            "# GENERAL LIMITATIONS:",
            "# - NSX DHCP is NOT equivalent to Whereabouts IPAM (different lease tracking)",
            "# - NSX provides L2 switching features not available in basic CNI plugins",
            "# - Migration requires network downtime (cannot live-migrate segments)",
            "# - NSX segment security policies not included (use NetworkPolicy)",
            "# - Test thoroughly in dev/staging before production deployment",
            "#",
            "# POD USAGE:",
            "# Attach this network to a pod via annotation:",
            f"#   k8s.v1.cni.cncf.io/networks: {segment_name}",
            "#",
            "# For multiple networks:",
            "#   k8s.v1.cni.cncf.io/networks: '[",
            f'#     {{"name": "{segment_name}", "interface": "net1"}},',
            '#     {"name": "another-network", "interface": "net2"}',
            "#   ]'",
            "#",
            "# For advanced networking features, consider:",
            "# - Calico for network policies and advanced routing",
            "# - Cilium for eBPF-based networking and L7 policies",
            "# - OpenShift SDN for integrated networking solution",
        ]
    )

    return "\n".join(header_parts)


def _wrap_comment(text: str, max_length: int = 75) -> list[str]:
    """
    Wrap text for comment lines.

    Args:
        text: Text to wrap
        max_length: Maximum line length

    Returns:
        List of wrapped lines

    Example:
        >>> lines = _wrap_comment("This is a very long comment that needs wrapping", 20)
        >>> len(lines) > 1
        True
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_length:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]
