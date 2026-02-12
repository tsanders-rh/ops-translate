"""
NSX-T to Kubernetes mappings.

Maps NSX-T networking and security concepts to their Kubernetes equivalents,
specifically for translating NSX firewall rules to NetworkPolicy manifests.
"""

import re
from typing import Any


class NSXToK8sMapper:
    """Maps NSX-T networking concepts to Kubernetes equivalents."""

    # Common NSX service names mapped to Kubernetes port definitions
    SERVICE_PORT_MAP = {
        "MySQL": {"protocol": "TCP", "port": 3306},
        "PostgreSQL": {"protocol": "TCP", "port": 5432},
        "MongoDB": {"protocol": "TCP", "port": 27017},
        "Redis": {"protocol": "TCP", "port": 6379},
        "HTTP": {"protocol": "TCP", "port": 80},
        "HTTPS": {"protocol": "TCP", "port": 443},
        "SSH": {"protocol": "TCP", "port": 22},
        "FTP": {"protocol": "TCP", "port": 21},
        "SMTP": {"protocol": "TCP", "port": 25},
        "DNS": {"protocol": "UDP", "port": 53},
        "NTP": {"protocol": "UDP", "port": 123},
        "LDAP": {"protocol": "TCP", "port": 389},
        "LDAPS": {"protocol": "TCP", "port": 636},
    }

    def map_security_group_to_label(self, sg_name: str) -> dict[str, str]:
        """
        Map NSX Security Group name to Kubernetes pod label selector.

        Extracts meaningful labels from security group naming conventions.

        Args:
            sg_name: NSX Security Group name

        Returns:
            Dictionary of label key-value pairs

        Example:
            >>> mapper = NSXToK8sMapper()
            >>> mapper.map_security_group_to_label("Web-SecurityGroup")
            {'app': 'web'}
            >>> mapper.map_security_group_to_label("Database-Tier")
            {'tier': 'database'}
        """
        # Remove common NSX security group suffixes
        clean_name = (
            sg_name.replace("-SecurityGroup", "")
            .replace("SecurityGroup", "")
            .replace("-SG", "")
            .replace("_SG", "")
        )

        # Convert to lowercase and replace separators
        label_value = clean_name.lower().replace("-", "").replace("_", "")

        # Determine label key based on naming patterns
        if "tier" in sg_name.lower():
            return {"tier": label_value.replace("tier", "")}
        elif "zone" in sg_name.lower():
            return {"zone": label_value.replace("zone", "")}
        elif "app" in sg_name.lower():
            return {"app": label_value.replace("app", "")}
        elif "role" in sg_name.lower():
            return {"role": label_value.replace("role", "")}
        else:
            # Default to app label
            return {"app": label_value}

    def map_service_to_port(self, service_name: str) -> dict[str, Any] | None:
        """
        Map NSX service name to Kubernetes port definition.

        Handles both well-known service names and custom port definitions.

        Args:
            service_name: NSX service name (e.g., "MySQL", "TCP-8080")

        Returns:
            Port definition dict with 'protocol' and 'port', or None if L7/unsupported

        Example:
            >>> mapper = NSXToK8sMapper()
            >>> mapper.map_service_to_port("MySQL")
            {'protocol': 'TCP', 'port': 3306}
            >>> mapper.map_service_to_port("TCP-8080")
            {'protocol': 'TCP', 'port': 8080}
            >>> mapper.map_service_to_port("HTTP-ALG")  # L7 service
            None
        """
        # Check known services first
        if service_name in self.SERVICE_PORT_MAP:
            return self.SERVICE_PORT_MAP[service_name].copy()

        # Try to parse custom service definitions
        # Format: "TCP-8080" or "UDP-53"
        if "-" in service_name:
            parts = service_name.split("-")
            if len(parts) == 2:
                protocol, port = parts
                if protocol.upper() in ["TCP", "UDP"] and port.isdigit():
                    return {"protocol": protocol.upper(), "port": int(port)}

        # Try format: "TCP/8080" or "UDP/53"
        if "/" in service_name:
            parts = service_name.split("/")
            if len(parts) == 2:
                protocol, port = parts
                if protocol.upper() in ["TCP", "UDP"] and port.isdigit():
                    return {"protocol": protocol.upper(), "port": int(port)}

        # Check for L7 application services (not supported by NetworkPolicy)
        l7_indicators = [
            "HTTP",
            "HTTPS",
            "FTP",
            "ALG",
            "APPLICATION",
            "URL",
            "FQDN",
        ]
        if any(indicator in service_name.upper() for indicator in l7_indicators):
            # L7 service - NetworkPolicy doesn't support
            return None

        # Unknown service format
        return None

    def map_ip_address_to_selector(self, ip_address: str) -> dict[str, Any] | None:
        """
        Map NSX IP address or CIDR to Kubernetes network selector.

        Args:
            ip_address: IP address or CIDR range

        Returns:
            IPBlock selector dict, or None if not a valid IP/CIDR

        Example:
            >>> mapper = NSXToK8sMapper()
            >>> mapper.map_ip_address_to_selector("10.10.10.0/24")
            {'ipBlock': {'cidr': '10.10.10.0/24'}}
        """
        # Check if it's a valid IP or CIDR
        if self._is_ip_or_cidr(ip_address):
            # Ensure CIDR notation
            if "/" not in ip_address:
                # Single IP - add /32 for IPv4, /128 for IPv6
                if ":" in ip_address:
                    ip_address = f"{ip_address}/128"
                else:
                    ip_address = f"{ip_address}/32"

            return {"ipBlock": {"cidr": ip_address}}

        return None

    def _is_ip_or_cidr(self, value: str) -> bool:
        """
        Check if a string is a valid IP address or CIDR.

        Args:
            value: String to check

        Returns:
            True if valid IP or CIDR
        """
        # Simple regex for IPv4 addresses and CIDR
        ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$"
        if re.match(ipv4_pattern, value):
            # Basic validation that octets are in range
            parts = value.split("/")[0].split(".")
            return all(0 <= int(octet) <= 255 for octet in parts)

        # Simple check for IPv6 (basic)
        if ":" in value:
            return True  # Simplified - could use ipaddress module for full validation

        return False

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize NSX resource name for use as Kubernetes resource name.

        Kubernetes names must be DNS-1123 compliant:
        - lowercase alphanumeric + '-'
        - start with alphanumeric
        - max 253 chars

        Args:
            name: Original NSX resource name

        Returns:
            Sanitized Kubernetes-compatible name

        Example:
            >>> mapper = NSXToK8sMapper()
            >>> mapper.sanitize_name("Allow Web to Database")
            'allow-web-to-database'
            >>> mapper.sanitize_name("Firewall Rule #1")
            'firewall-rule-1'
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
            name = "nsx-rule"

        return name
