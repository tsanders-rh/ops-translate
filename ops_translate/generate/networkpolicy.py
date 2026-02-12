"""
Generate Kubernetes NetworkPolicy manifests from NSX firewall rules.

This module translates NSX-T Distributed Firewall rules detected in vRealize
workflows into Kubernetes NetworkPolicy YAML, with clear documentation of
limitations and unsupported features.
"""

from typing import Any

import yaml

from ops_translate.generate.nsx_mappings import NSXToK8sMapper


def generate_network_policies(
    nsx_firewall_rules: list[dict[str, Any]],
    workflow_name: str = "workflow",
) -> dict[str, str]:
    """
    Generate NetworkPolicy YAML files from NSX firewall rules.

    Args:
        nsx_firewall_rules: List of detected NSX firewall rule operations
        workflow_name: Source workflow name for metadata

    Returns:
        Dictionary mapping filename to YAML content

    Example:
        >>> rules = [
        ...     {
        ...         'name': 'Allow Web to DB',
        ...         'location': 'workflow.xml:123',
        ...         'evidence': '...'
        ...     }
        ... ]
        >>> policies = generate_network_policies(rules)
        >>> 'allow-web-to-db.yaml' in policies
        True
    """
    if not nsx_firewall_rules:
        return {}

    mapper = NSXToK8sMapper()
    policies = {}

    for rule in nsx_firewall_rules:
        # Try to parse rule details from evidence
        rule_details = _parse_rule_from_evidence(rule)

        # Skip if we couldn't extract meaningful rule information
        if not rule_details:
            continue

        # Generate policy name
        rule_name = rule_details.get("name", rule.get("name", "unknown-rule"))
        policy_name = mapper.sanitize_name(rule_name)

        # Build NetworkPolicy manifest
        policy = _build_network_policy(rule_details, mapper, workflow_name, rule.get("location"))

        if not policy:
            # Couldn't generate valid policy
            continue

        # Add limitation warnings
        warnings = _detect_limitations(rule_details)

        # Generate YAML with header comments
        header = _generate_header_comments(rule_details, rule, warnings)
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
    Parse firewall rule details from detection evidence.

    Args:
        rule: Detected NSX firewall rule with evidence

    Returns:
        Dict with parsed rule details, or None if cannot parse
    """
    import re

    evidence = rule.get("evidence", "")
    name = rule.get("name", "")

    # Initialize rule details
    details: dict[str, Any] = {
        "name": name,
        "sources": [],
        "destinations": [],
        "services": [],
        "action": "ALLOW",  # Default assumption
    }

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
    # This will generate a placeholder NetworkPolicy
    if name:
        return details

    return None


def _build_network_policy(
    rule_details: dict[str, Any],
    mapper: NSXToK8sMapper,
    workflow_name: str,
    location: str | None,
) -> dict[str, Any] | None:
    """
    Build NetworkPolicy manifest from NSX firewall rule details.

    Args:
        rule_details: Parsed rule details
        mapper: NSX to Kubernetes mapper
        workflow_name: Source workflow name
        location: Rule location for metadata

    Returns:
        NetworkPolicy manifest dict, or None if cannot generate
    """
    # Skip DENY rules - NetworkPolicy is default-deny, we only express ALLOW
    if rule_details.get("action") == "DENY":
        return None

    # Map destinations to pod selectors (NetworkPolicy protects destination pods)
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

    # Build complete NetworkPolicy
    policy_name = mapper.sanitize_name(rule_details.get("name", "nsx-firewall-rule"))

    policy = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": policy_name,
            "namespace": "default",
            "labels": {
                "translated-from": "nsx-firewall",
                "source-workflow": workflow_name,
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
        metadata = policy["metadata"]
        if "annotations" not in metadata:
            metadata["annotations"] = {}  # type: ignore[index]
        metadata["annotations"]["source-location"] = location  # type: ignore[index]

    return policy


def _detect_limitations(rule_details: dict[str, Any]) -> list[str]:
    """
    Detect NSX features in the rule that don't translate to NetworkPolicy.

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
                    "NetworkPolicy is L3/L4 only. Consider using Istio or Cilium for L7 policies."
                )
                break

    # Check for FQDN destinations
    if rule_details.get("destinations"):
        for dest in rule_details["destinations"]:
            if "." in dest and not dest[0].isdigit():
                warnings.append(
                    f"Destination '{dest}' appears to be a FQDN. "
                    "NetworkPolicy requires pod selectors or IP blocks. "
                    "Consider using Calico or Cilium for FQDN support."
                )

    # Check for DENY action
    if rule_details.get("action") == "DENY":
        warnings.append(
            "NSX DENY rule detected. NetworkPolicy uses default-deny; "
            "explicit DENY rules require Calico NetworkPolicy."
        )

    return warnings


def _generate_header_comments(
    rule_details: dict[str, Any],
    original_rule: dict[str, Any],
    warnings: list[str],
) -> str:
    """
    Generate YAML header comments with context and limitations.

    Args:
        rule_details: Parsed rule details
        original_rule: Original detection data
        warnings: List of limitation warnings

    Returns:
        Formatted header comment string
    """
    rule_name = rule_details.get("name", "unknown")
    location = original_rule.get("location", "unknown")

    header_parts = [
        "---",
        "# Generated from vRealize workflow NSX firewall rule",
        f"# Source rule: {rule_name}",
        f"# Location: {location}",
        "#",
        "# LIMITATIONS - READ BEFORE DEPLOYING:",
        "# - NSX supports L7 application-aware filtering; NetworkPolicy is L3/L4 only",
        "# - NSX supports FQDN-based rules; NetworkPolicy requires pod selectors or IP/CIDR",
        "# - NSX supports time-based rules; NetworkPolicy is always active",
        "# - NSX supports user/group-based rules; NetworkPolicy is pod-based only",
        "# - Review and test thoroughly in dev environment before production",
        "#",
    ]

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
            "# For advanced networking features, consider:",
            "# - Calico NetworkPolicy for FQDN, global policies, deny rules",
            "# - Cilium for L7 policies and enhanced observability",
            "# - Istio for application-layer (L7) service mesh policies",
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
