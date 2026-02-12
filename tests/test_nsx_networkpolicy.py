"""Tests for NSX firewall rule to NetworkPolicy translation."""

import pytest
import yaml

from ops_translate.generate.networkpolicy import generate_network_policies
from ops_translate.generate.nsx_mappings import NSXToK8sMapper

# Fixtures


@pytest.fixture
def nsx_mapper():
    """Create NSX to Kubernetes mapper."""
    return NSXToK8sMapper()


@pytest.fixture
def sample_firewall_rule():
    """Sample NSX firewall rule detection."""
    return {
        "name": "Allow Web to DB",
        "location": "workflow.xml:123",
        "confidence": 0.85,
        "evidence": (
            "Pattern match: nsxClient.createFirewallRule in context (workflow.xml:123): "
            '...nsxClient.createFirewallRule({name: "Allow Web to DB", sources: '
            '["Web-SecurityGroup"], destinations: ["Database-SecurityGroup"], '
            'services: ["MySQL"], action: "ALLOW"})...'
        ),
    }


@pytest.fixture
def basic_firewall_rule():
    """Basic firewall rule with minimal information."""
    return {
        "name": "Basic Rule",
        "location": "workflow.xml:456",
        "confidence": 0.7,
        "evidence": "Pattern match: FirewallRule in context",
    }


# NSXToK8sMapper Tests


def test_map_security_group_to_label(nsx_mapper):
    """Test security group to pod label mapping."""
    # Standard security group naming
    assert nsx_mapper.map_security_group_to_label("Web-SecurityGroup") == {"app": "web"}
    assert nsx_mapper.map_security_group_to_label("Database-SG") == {"app": "database"}

    # Tier-based naming
    assert nsx_mapper.map_security_group_to_label("Database-Tier") == {"tier": "database"}

    # Zone-based naming
    assert nsx_mapper.map_security_group_to_label("DMZ-Zone") == {"zone": "dmz"}


def test_map_service_to_port_known_services(nsx_mapper):
    """Test mapping of well-known service names."""
    assert nsx_mapper.map_service_to_port("MySQL") == {"protocol": "TCP", "port": 3306}
    assert nsx_mapper.map_service_to_port("PostgreSQL") == {"protocol": "TCP", "port": 5432}
    assert nsx_mapper.map_service_to_port("HTTP") == {"protocol": "TCP", "port": 80}
    assert nsx_mapper.map_service_to_port("HTTPS") == {"protocol": "TCP", "port": 443}
    assert nsx_mapper.map_service_to_port("DNS") == {"protocol": "UDP", "port": 53}


def test_map_service_to_port_custom_format(nsx_mapper):
    """Test mapping of custom port definitions."""
    # TCP-PORT format
    assert nsx_mapper.map_service_to_port("TCP-8080") == {"protocol": "TCP", "port": 8080}
    assert nsx_mapper.map_service_to_port("UDP-53") == {"protocol": "UDP", "port": 53}

    # TCP/PORT format
    assert nsx_mapper.map_service_to_port("TCP/9000") == {"protocol": "TCP", "port": 9000}


def test_map_service_to_port_l7_services(nsx_mapper):
    """Test that L7 services return None (not supported)."""
    assert nsx_mapper.map_service_to_port("HTTP-ALG") is None
    assert nsx_mapper.map_service_to_port("HTTPS-APPLICATION") is None
    assert nsx_mapper.map_service_to_port("FTP-ALG") is None


def test_map_ip_address_to_selector(nsx_mapper):
    """Test IP address to selector mapping."""
    # CIDR notation
    result = nsx_mapper.map_ip_address_to_selector("10.10.10.0/24")
    assert result == {"ipBlock": {"cidr": "10.10.10.0/24"}}

    # Single IP (should add /32)
    result = nsx_mapper.map_ip_address_to_selector("192.168.1.100")
    assert result == {"ipBlock": {"cidr": "192.168.1.100/32"}}

    # Not an IP address
    assert nsx_mapper.map_ip_address_to_selector("Web-SecurityGroup") is None


def test_sanitize_name(nsx_mapper):
    """Test resource name sanitization."""
    assert nsx_mapper.sanitize_name("Allow Web to Database") == "allow-web-to-database"
    assert nsx_mapper.sanitize_name("Firewall Rule #1") == "firewall-rule-1"
    assert nsx_mapper.sanitize_name("Web_App-Tier") == "web-app-tier"

    # Remove leading/trailing hyphens
    assert nsx_mapper.sanitize_name("-test-rule-") == "test-rule"

    # Collapse multiple hyphens
    assert nsx_mapper.sanitize_name("test---rule") == "test-rule"

    # Empty name
    assert nsx_mapper.sanitize_name("") == "nsx-rule"


# NetworkPolicy Generation Tests


def test_generate_network_policies_basic(sample_firewall_rule):
    """Test basic NetworkPolicy generation from firewall rule."""
    policies = generate_network_policies([sample_firewall_rule], "test-workflow")

    assert len(policies) == 1
    assert "allow-web-to-db.yaml" in policies

    # Parse generated YAML
    yaml_content = policies["allow-web-to-db.yaml"]
    assert "---" in yaml_content
    assert "NetworkPolicy" in yaml_content
    assert "test-workflow" in yaml_content

    # Parse the YAML (skip comments)
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    documents = list(yaml.safe_load_all(yaml_text))

    assert len(documents) > 0
    # The YAML dump creates a list with one element (the policy dict)
    policy_list = documents[0]
    assert isinstance(policy_list, list)
    assert len(policy_list) > 0
    policy = policy_list[0]

    assert policy["kind"] == "NetworkPolicy"
    assert policy["apiVersion"] == "networking.k8s.io/v1"
    assert policy["metadata"]["name"] == "allow-web-to-db"


def test_generate_network_policies_with_services(sample_firewall_rule):
    """Test NetworkPolicy generation includes port restrictions."""
    policies = generate_network_policies([sample_firewall_rule], "test-workflow")
    yaml_content = policies["allow-web-to-db.yaml"]

    # Should include MySQL port
    assert "3306" in yaml_content
    assert "TCP" in yaml_content


def test_generate_network_policies_empty_input():
    """Test handling of empty input."""
    policies = generate_network_policies([], "test-workflow")
    assert len(policies) == 0


def test_generate_network_policies_no_parseable_rules(basic_firewall_rule):
    """Test handling of rules that can't be parsed."""
    policies = generate_network_policies([basic_firewall_rule], "test-workflow")

    # Should generate an empty dict or basic placeholder
    # depending on implementation
    assert isinstance(policies, dict)


def test_generate_network_policies_limitation_warnings(sample_firewall_rule):
    """Test that limitation warnings are included in comments."""
    policies = generate_network_policies([sample_firewall_rule], "test-workflow")
    yaml_content = policies["allow-web-to-db.yaml"]

    # Check for limitation warnings in comments
    assert "LIMITATIONS" in yaml_content
    assert "L3/L4" in yaml_content
    assert "FQDN" in yaml_content or "pod selectors" in yaml_content


def test_generate_network_policies_multiple_rules():
    """Test generation from multiple firewall rules."""
    rules = [
        {
            "name": "Rule 1",
            "location": "workflow.xml:100",
            "evidence": (
                'nsxClient.createFirewallRule({name: "Rule 1", '
                'sources: ["Web"], destinations: ["App"], services: ["HTTP"]})'
            ),
        },
        {
            "name": "Rule 2",
            "location": "workflow.xml:200",
            "evidence": (
                'nsxClient.createFirewallRule({name: "Rule 2", '
                'sources: ["App"], destinations: ["DB"], services: ["MySQL"]})'
            ),
        },
    ]

    policies = generate_network_policies(rules, "multi-rule-workflow")

    # Should generate 2 policies
    assert len(policies) == 2
    assert "rule-1.yaml" in policies
    assert "rule-2.yaml" in policies


def test_network_policy_structure():
    """Test that generated NetworkPolicy has correct structure."""
    rule = {
        "name": "Test Rule",
        "location": "test.xml:1",
        "evidence": (
            'nsxClient.createFirewallRule({name: "Test Rule", '
            'sources: ["Source-SG"], destinations: ["Dest-SG"], '
            'services: ["TCP-8080"], action: "ALLOW"})'
        ),
    }

    policies = generate_network_policies([rule], "test")
    yaml_content = list(policies.values())[0]

    # Parse YAML
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    documents = list(yaml.safe_load_all(yaml_text))

    assert len(documents) > 0
    # The YAML dump creates a list with one element (the policy dict)
    policy_list = documents[0]
    assert isinstance(policy_list, list)
    assert len(policy_list) > 0
    policy = policy_list[0]

    # Verify required NetworkPolicy structure
    assert "metadata" in policy
    assert "spec" in policy
    assert "podSelector" in policy["spec"]
    assert "policyTypes" in policy["spec"]
    assert "Ingress" in policy["spec"]["policyTypes"]
    assert "ingress" in policy["spec"]
    assert isinstance(policy["spec"]["ingress"], list)


def test_network_policy_labels():
    """Test that generated NetworkPolicy includes proper labels."""
    rule = {
        "name": "Labeled Rule",
        "location": "test.xml:1",
        "evidence": (
            'nsxClient.createFirewallRule({name: "Labeled Rule", '
            'sources: ["Web"], destinations: ["DB"]})'
        ),
    }

    policies = generate_network_policies([rule], "test-workflow")
    yaml_content = list(policies.values())[0]

    # Parse YAML
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    documents = list(yaml.safe_load_all(yaml_text))

    assert len(documents) > 0
    # The YAML dump creates a list with one element (the policy dict)
    policy_list = documents[0]
    assert isinstance(policy_list, list)
    assert len(policy_list) > 0
    policy = policy_list[0]

    # Check labels
    assert "labels" in policy["metadata"]
    assert policy["metadata"]["labels"]["translated-from"] == "nsx-firewall"
    assert policy["metadata"]["labels"]["source-workflow"] == "test-workflow"


def test_ip_based_source():
    """Test NetworkPolicy generation with IP-based sources."""
    rule = {
        "name": "IP Rule",
        "location": "test.xml:1",
        "evidence": (
            'nsxClient.createFirewallRule({name: "IP Rule", '
            'sources: ["10.10.10.0/24"], destinations: ["App-SG"], '
            'services: ["HTTPS"]})'
        ),
    }

    policies = generate_network_policies([rule], "test")
    yaml_content = list(policies.values())[0]

    # Should include ipBlock for IP-based source
    assert "ipBlock" in yaml_content
    assert "10.10.10.0/24" in yaml_content
