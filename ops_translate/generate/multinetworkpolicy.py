"""
Generate OVN-Kubernetes MultiNetworkPolicy manifests from NSX firewall rules.

This module translates NSX-T Distributed Firewall rules that apply to specific
network segments (secondary networks) into OVN-Kubernetes MultiNetworkPolicy YAML,
with clear documentation of limitations and unsupported features.

MultiNetworkPolicy is scoped to secondary networks (NetworkAttachmentDefinitions),
while standard NetworkPolicy applies to the primary pod network.
"""

from typing import Any

import yaml

from ops_translate.generate.nsx_mappings import NSXToK8sMapper


def generate_multi_network_policies(
    segment_mapping: dict[str, Any],
    nsx_firewall_rules: list[dict[str, Any]],
    workflow_name: str = "workflow",
    namespace: str = "default",
) -> dict[str, str]:
    """
    Generate MultiNetworkPolicy YAML files from NSX firewall rules for a segment.

    Args:
        segment_mapping: SegmentMapping with segment metadata and associated rules
        nsx_firewall_rules: List of all detected NSX firewall rule operations
        workflow_name: Source workflow name for metadata
        namespace: Target namespace for MultiNetworkPolicies

    Returns:
        Dictionary mapping filename to YAML content

    Example:
        >>> from ops_translate.generate.nsx_correlation import SegmentMapping
        >>> segment = {
        ...     'segment_name': 'Web-Tier-VLAN100',
        ...     'nad_name': 'web-tier-vlan100',
        ...     'firewall_rules': ['Allow-Web-DB'],
        ...     'vlan_ids': [100],
        ...     'subnets': ['10.10.100.0/24']
        ... }
        >>> rules = [
        ...     {
        ...         'name': 'Allow-Web-DB',
        ...         'location': 'workflow.xml:123',
        ...         'evidence': '...'
        ...     }
        ... ]
        >>> policies = generate_multi_network_policies(segment, rules, 'workflow')
        >>> 'web-tier-vlan100-allow-web-db.yaml' in policies
        True
    """
    if not nsx_firewall_rules:
        return {}

    # Get segment details
    segment_name = segment_mapping.get("segment_name", "")
    nad_name = segment_mapping.get("nad_name", "")
    rule_names = segment_mapping.get("firewall_rules", [])

    if not segment_name or not nad_name or not rule_names:
        return {}

    mapper = NSXToK8sMapper()
    policies = {}

    # Filter to only rules for this segment
    segment_rules = [r for r in nsx_firewall_rules if r.get("name") in rule_names]

    for rule in segment_rules:
        # Try to parse rule details from evidence
        rule_details = _parse_rule_from_evidence(rule)

        # Skip if we couldn't extract meaningful rule information
        if not rule_details:
            continue

        # Generate policy name (include segment prefix for uniqueness)
        rule_name = rule_details.get("name", rule.get("name", "unknown-rule"))
        sanitized_rule_name = mapper.sanitize_name(rule_name)
        policy_name = f"{nad_name}-{sanitized_rule_name}"

        # Build MultiNetworkPolicy manifest
        policy = _build_multi_network_policy(
            rule_details, mapper, workflow_name, nad_name, rule.get("location"), namespace
        )

        if not policy:
            # Couldn't generate valid policy
            continue

        # Add limitation warnings
        warnings = _detect_limitations(rule_details)

        # Generate YAML with header comments
        header = _generate_header_comments(
            rule_details, rule, segment_mapping, warnings
        )
        policy_yaml = yaml.dump([policy], default_flow_style=False, sort_keys=False)

        # Remove leading "---" from yaml.dump output
        policy_yaml_lines = policy_yaml.strip().split("\n")
        if policy_yaml_lines[0] == "---":
            policy_yaml_lines = policy_yaml_lines[1:]
        policy_yaml = "\n".join(policy_yaml_lines)

        full_content = f"{header}\n{policy_yaml}"
        policies[f"{policy_name}.yaml"] = full_content

    return policies


def _parse_rule_from_evidence(rule: dict[str, Any]) -> dict[str, Any] | None:
    """
    Parse firewall rule details from detection evidence or parsed fields.

    Args:
        rule: Detected NSX firewall rule with evidence and/or parsed fields

    Returns:
        Dict with parsed rule details, or None if cannot parse
    """
    import re

    evidence = rule.get("evidence", "")
    name = rule.get("name", "")

    # Initialize rule details - prefer parsed fields over evidence extraction
    details: dict[str, Any] = {
        "name": name,
        "sources": rule.get("sources", []),
        "destinations": rule.get("destinations", []),
        "services": rule.get("services", []) or rule.get("ports", []),
        "action": (rule.get("action", "") or "ALLOW").upper(),
    }

    # If we already have parsed fields, use them and return early
    if details["sources"] or details["destinations"] or details["services"]:
        return details

    # Try to extract structured data from evidence
    # Pattern 1: createFirewallRule API call with JSON-like structure
    create_pattern = r"createFirewallRule\s*\(\s*\{([^}]+)\}\s*\)"
    match = re.search(create_pattern, evidence, re.DOTALL)
    if match:
        config = match.group(1)

        # Extract name
        name_match = re.search(r'name["\s:]+([^",\n]+)', config)
        if name_match:
            details["name"] = name_match.group(1).strip().strip("\"'")

        # Extract sources
        sources_match = re.search(r'sources["\s:]+\[([^\]]+)\]', config)
        if sources_match:
            sources_str = sources_match.group(1)
            details["sources"] = [
                s.strip().strip("\"'") for s in sources_str.split(",") if s.strip()
            ]

        # Extract destinations
        dest_match = re.search(r'destinations["\s:]+\[([^\]]+)\]', config)
        if dest_match:
            dest_str = dest_match.group(1)
            details["destinations"] = [
                d.strip().strip("\"'") for d in dest_str.split(",") if d.strip()
            ]

        # Extract services
        services_match = re.search(r'services["\s:]+\[([^\]]+)\]', config)
        if services_match:
            services_str = services_match.group(1)
            details["services"] = [
                s.strip().strip("\"'") for s in services_str.split(",") if s.strip()
            ]

        # Extract action
        action_match = re.search(r'action["\s:]+([^",\n]+)', config)
        if action_match:
            details["action"] = action_match.group(1).strip().strip("\"'").upper()

    # If we have minimal information, return it
    if details["sources"] or details["destinations"] or details["services"]:
        return details

    # If we couldn't parse structured data, create a basic rule
    # This will generate a placeholder MultiNetworkPolicy
    if name:
        return details

    return None


def _build_multi_network_policy(
    rule_details: dict[str, Any],
    mapper: NSXToK8sMapper,
    workflow_name: str,
    nad_name: str,
    location: str | None,
    namespace: str = "default",
) -> dict[str, Any] | None:
    """
    Build MultiNetworkPolicy manifest from NSX firewall rule details.

    Args:
        rule_details: Parsed rule details
        mapper: NSX to Kubernetes mapper
        workflow_name: Source workflow name
        nad_name: NetworkAttachmentDefinition name for annotation
        location: Rule location for metadata
        namespace: Target namespace for the MultiNetworkPolicy

    Returns:
        MultiNetworkPolicy manifest dict, or None if cannot generate
    """
    # Skip DENY rules - MultiNetworkPolicy is default-deny, we only express ALLOW
    if rule_details.get("action") == "DENY":
        return None

    # Map destinations to pod selectors (MultiNetworkPolicy protects destination pods)
    destination_labels = {}
    if rule_details.get("destinations"):
        dest = rule_details["destinations"][0]  # Use first destination
        # Check if it's an IP address or security group
        ip_selector = mapper.map_ip_address_to_selector(dest)
        if not ip_selector:
            # Assume it's a security group name
            destination_labels = mapper.map_security_group_to_label(dest)
    else:
        # No specific destination - protect all pods (use empty selector)
        destination_labels = {}

    # Build ingress rules from sources and services
    ingress_rules = []
    if rule_details.get("sources"):
        for source in rule_details["sources"]:
            # Map source to selector
            ip_selector = mapper.map_ip_address_to_selector(source)
            if ip_selector:
                # IP-based source
                from_selector = [ip_selector]
            else:
                # Security group-based source
                source_labels = mapper.map_security_group_to_label(source)
                from_selector = [{"podSelector": {"matchLabels": source_labels}}]

            ingress_rule: dict[str, Any] = {"from": from_selector}

            # Add port restrictions if services are specified
            if rule_details.get("services"):
                ports = []
                for service in rule_details["services"]:
                    port_def = mapper.map_service_to_port(service)
                    if port_def:
                        ports.append(port_def)

                if ports:
                    ingress_rule["ports"] = ports

            ingress_rules.append(ingress_rule)
    else:
        # No specific source - allow from anywhere
        # This means the rule is about port restrictions only
        ingress_rule = {}
        if rule_details.get("services"):
            ports = []
            for service in rule_details["services"]:
                port_def = mapper.map_service_to_port(service)
                if port_def:
                    ports.append(port_def)

            if ports:
                ingress_rule["ports"] = ports

        if ingress_rule:
            ingress_rules.append(ingress_rule)

    # If no ingress rules could be generated, skip this policy
    if not ingress_rules:
        return None

    # Build complete MultiNetworkPolicy
    policy_name = mapper.sanitize_name(rule_details.get("name", "nsx-firewall-rule"))

    # MultiNetworkPolicy uses same spec structure as NetworkPolicy
    # but different API group and requires policy-for annotation
    policy = {
        "apiVersion": "k8s.cni.cncf.io/v1beta1",
        "kind": "MultiNetworkPolicy",
        "metadata": {
            "name": f"{nad_name}-{policy_name}",
            "namespace": namespace,
            "annotations": {
                # Link to NetworkAttachmentDefinition
                "k8s.v1.cni.cncf.io/policy-for": f"{namespace}/{nad_name}",
            },
            "labels": {
                "translated-from": "nsx-firewall",
                "source-workflow": workflow_name,
                "network-scope": "secondary",
                "network-attachment": nad_name,
            },
        },
        "spec": {
            "podSelector": {"matchLabels": destination_labels} if destination_labels else {},
            "policyTypes": ["Ingress"],
            "ingress": ingress_rules,
        },
    }

    # Add location annotation if available
    if location:
        policy["metadata"]["annotations"]["source-location"] = location  # type: ignore[index]

    return policy


def _detect_limitations(rule_details: dict[str, Any]) -> list[str]:
    """
    Detect NSX features in the rule that don't translate to MultiNetworkPolicy.

    Args:
        rule_details: Parsed rule details

    Returns:
        List of limitation warnings
    """
    warnings = []

    # Check for L7 services
    if rule_details.get("services"):
        l7_keywords = ["HTTP", "HTTPS", "FTP", "APPLICATION", "URL", "FQDN"]
        for service in rule_details["services"]:
            if any(keyword in service.upper() for keyword in l7_keywords):
                warnings.append(
                    f"Service '{service}' may be L7 application-aware. "
                    "OVN-Kubernetes MultiNetworkPolicy is L3/L4 only. "
                    "Consider Cilium for L7 policies."
                )
                break

    # Check for FQDN destinations
    if rule_details.get("destinations"):
        for dest in rule_details["destinations"]:
            if "." in dest and not dest[0].isdigit():
                warnings.append(
                    f"Destination '{dest}' appears to be a FQDN. "
                    "MultiNetworkPolicy requires pod selectors or IP blocks. "
                    "Consider Cilium for FQDN support."
                )

    # Check for DENY action
    if rule_details.get("action") == "DENY":
        warnings.append(
            "NSX DENY rule detected. MultiNetworkPolicy uses default-deny; "
            "explicit DENY rules require Calico NetworkPolicy."
        )

    return warnings


def _generate_header_comments(
    rule_details: dict[str, Any],
    original_rule: dict[str, Any],
    segment_mapping: dict[str, Any],
    warnings: list[str],
) -> str:
    """
    Generate YAML header comments with context and limitations.

    Args:
        rule_details: Parsed rule details
        original_rule: Original detection data
        segment_mapping: Segment metadata (name, NAD, VLAN, subnets)
        warnings: List of limitation warnings

    Returns:
        Formatted header comment string
    """
    rule_name = rule_details.get("name", "unknown")
    location = original_rule.get("location", "unknown")
    segment_name = segment_mapping.get("segment_name", "unknown")
    nad_name = segment_mapping.get("nad_name", "unknown")
    vlan_ids = segment_mapping.get("vlan_ids", [])
    subnets = segment_mapping.get("subnets", [])

    header_parts = [
        "---",
        "# Generated from vRealize workflow NSX firewall rule",
        f"# Source rule: {rule_name}",
        f"# Location: {location}",
        "#",
        "# NETWORK SCOPE: SECONDARY NETWORK",
        f"# Segment: {segment_name}",
        f"# NetworkAttachmentDefinition: default/{nad_name}",
    ]

    if vlan_ids:
        header_parts.append(f"# VLAN IDs: {', '.join(map(str, vlan_ids))}")
    if subnets:
        header_parts.append(f"# Subnets: {', '.join(subnets)}")

    header_parts.extend([
        "#",
        "# This MultiNetworkPolicy applies ONLY to traffic on the secondary network",
        f"# (NetworkAttachmentDefinition: {nad_name}) and does NOT affect traffic on",
        "# the primary pod network or other secondary networks.",
        "#",
        "# IMPORTANT: Pods must be attached to the secondary network for this policy",
        "# to apply. Add this annotation to pod metadata:",
        f"#   k8s.v1.cni.cncf.io/networks: {nad_name}",
        "#",
        "# LIMITATIONS - READ BEFORE DEPLOYING:",
        "# - NSX supports L7 application-aware filtering; MultiNetworkPolicy is L3/L4 only",
        "# - NSX supports FQDN-based rules; MultiNetworkPolicy requires pod selectors or IP/CIDR",
        "# - NSX supports time-based rules; MultiNetworkPolicy is always active",
        "# - NSX supports user/group-based rules; MultiNetworkPolicy is pod-based only",
        "# - Review and test thoroughly in dev environment before production",
        "#",
    ])

    # Add specific warnings if any
    if warnings:
        header_parts.append("# DETECTED LIMITATIONS FOR THIS RULE:")
        for warning in warnings:
            # Word wrap warnings to fit in comments
            wrapped_lines = _wrap_comment(warning, max_length=75)
            for line in wrapped_lines:
                header_parts.append(f"# {line}")
        header_parts.append("#")

    header_parts.extend(
        [
            "# For advanced networking features on secondary networks, consider:",
            "# - Cilium for L7 policies, FQDN support, and enhanced observability",
            "# - Calico NetworkPolicy for global policies and deny rules",
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
