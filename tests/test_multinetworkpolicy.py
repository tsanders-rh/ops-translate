"""Tests for OVN-Kubernetes MultiNetworkPolicy generation."""

import pytest
import yaml

from ops_translate.generate.multinetworkpolicy import generate_multi_network_policies


def _parse_policy_yaml(yaml_content):
    """Helper to parse policy YAML from generated content."""
    # Split on comment header (starts with ---)
    parts = yaml_content.split("\n---\n")
    # YAML body is after the first ---
    if len(parts) > 1:
        # Find the first line that's not a comment
        lines = parts[1].split("\n")
        yaml_lines = [line for line in lines if not line.strip().startswith("#")]
        yaml_body = "\n".join(yaml_lines)
    else:
        yaml_body = yaml_content

    # Parse YAML document (may be a list with one policy)
    parsed = yaml.safe_load(yaml_body)

    # If it's a list, extract the first element
    if isinstance(parsed, list):
        return parsed[0] if parsed else {}
    return parsed


class TestMultiNetworkPolicyGeneration:
    """Test OVN-K MultiNetworkPolicy generation functionality."""

    def test_basic_multinetworkpolicy_generation(self):
        """Test basic MultiNetworkPolicy manifest generation."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({name: 'Allow-Web-DB', sources: ['web'], destinations: ['db'], services: ['MySQL'], action: 'ALLOW'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        # Should generate one policy
        assert len(policies) == 1

        # Check filename includes segment prefix
        filename = list(policies.keys())[0]
        assert filename.startswith("web-tier-vlan100-")
        assert filename.endswith(".yaml")

        # Parse YAML
        yaml_content = list(policies.values())[0]
        policy = _parse_policy_yaml(yaml_content)

        # Verify API version and kind
        assert policy["apiVersion"] == "k8s.cni.cncf.io/v1beta1"
        assert policy["kind"] == "MultiNetworkPolicy"

        # Verify policy-for annotation
        assert "k8s.v1.cni.cncf.io/policy-for" in policy["metadata"]["annotations"]
        assert policy["metadata"]["annotations"]["k8s.v1.cni.cncf.io/policy-for"] == "default/web-tier-vlan100"

        # Verify network scope labels
        assert policy["metadata"]["labels"]["network-scope"] == "secondary"
        assert policy["metadata"]["labels"]["network-attachment"] == "web-tier-vlan100"

    def test_header_comments_include_segment_info(self):
        """Test that header comments include segment metadata."""
        segment_mapping = {
            "segment_name": "DB-Tier-VLAN200",
            "nad_name": "db-tier-vlan200",
            "firewall_rules": ["Allow-Backup"],
            "vlan_ids": [200],
            "subnets": ["10.10.200.0/24"],
        }

        rules = [
            {
                "name": "Allow-Backup",
                "location": "workflow.xml:80",
                "evidence": "createFirewallRule({name: 'Allow-Backup', services: ['SSH'], action: 'ALLOW'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")
        yaml_content = list(policies.values())[0]

        # Check header comments
        assert "NETWORK SCOPE: SECONDARY NETWORK" in yaml_content
        assert "Segment: DB-Tier-VLAN200" in yaml_content
        assert "NetworkAttachmentDefinition: default/db-tier-vlan200" in yaml_content
        assert "VLAN IDs: 200" in yaml_content
        assert "Subnets: 10.10.200.0/24" in yaml_content
        assert "k8s.v1.cni.cncf.io/networks: db-tier-vlan200" in yaml_content

    def test_multiple_rules_for_segment(self):
        """Test generating multiple policies for one segment."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB", "Allow-Web-Cache"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({name: 'Allow-Web-DB', sources: ['web'], destinations: ['db'], action: 'ALLOW'})",
            },
            {
                "name": "Allow-Web-Cache",
                "location": "workflow.xml:160",
                "evidence": "createFirewallRule({name: 'Allow-Web-Cache', sources: ['web'], destinations: ['cache'], action: 'ALLOW'})",
            },
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        # Should generate two policies
        assert len(policies) == 2

        # Both should be prefixed with segment NAD name
        for filename in policies.keys():
            assert filename.startswith("web-tier-vlan100-")

    def test_filter_rules_for_segment(self):
        """Test that only rules for the segment are generated."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB"],  # Only this rule
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({name: 'Allow-Web-DB', sources: ['web'], action: 'ALLOW'})",
            },
            {
                "name": "Allow-Other",
                "location": "workflow.xml:160",
                "evidence": "createFirewallRule({name: 'Allow-Other', sources: ['other'], action: 'ALLOW'})",
            },
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        # Should only generate one policy (for Allow-Web-DB)
        assert len(policies) == 1
        assert "web-tier-vlan100-allow-web-db.yaml" in policies

    def test_empty_segment_firewall_rules(self):
        """Test that no policies are generated if segment has no rules."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": [],  # No rules
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({source: 'web'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        # Should generate no policies
        assert len(policies) == 0

    def test_missing_segment_name(self):
        """Test that no policies are generated if segment name is missing."""
        segment_mapping = {
            "segment_name": "",  # Missing
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({source: 'web'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        # Should generate no policies
        assert len(policies) == 0

    def test_policy_name_sanitization(self):
        """Test that policy names are sanitized properly."""
        segment_mapping = {
            "segment_name": "Web Tier (Production) VLAN100",
            "nad_name": "web-tier-production-vlan100",
            "firewall_rules": ["Allow Web to DB"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow Web to DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({name: 'Allow Web to DB', sources: ['web'], action: 'ALLOW'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        # Should generate one policy with sanitized name
        assert len(policies) == 1
        filename = list(policies.keys())[0]

        # Name should be DNS-1123 compliant
        assert filename.startswith("web-tier-production-vlan100-")
        assert " " not in filename
        assert "(" not in filename
        assert ")" not in filename

    def test_location_annotation(self):
        """Test that source location is added as annotation."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({name: 'Allow-Web-DB', sources: ['web'], action: 'ALLOW'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        yaml_content = list(policies.values())[0]
        policy = _parse_policy_yaml(yaml_content)

        # Verify source-location annotation
        assert "source-location" in policy["metadata"]["annotations"]
        assert policy["metadata"]["annotations"]["source-location"] == "workflow.xml:145"

    def test_workflow_name_in_labels(self):
        """Test that workflow name is included in labels."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({name: 'Allow-Web-DB', sources: ['web'], action: 'ALLOW'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow-test")

        yaml_content = list(policies.values())[0]
        policy = _parse_policy_yaml(yaml_content)

        # Verify source-workflow label
        assert policy["metadata"]["labels"]["source-workflow"] == "workflow-test"

    def test_empty_rules_list(self):
        """Test that empty rules list returns empty dict."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        policies = generate_multi_network_policies(segment_mapping, [], "workflow")

        # Should return empty dict
        assert len(policies) == 0

    def test_ingress_policy_type(self):
        """Test that generated policies have Ingress policy type."""
        segment_mapping = {
            "segment_name": "Web-Tier-VLAN100",
            "nad_name": "web-tier-vlan100",
            "firewall_rules": ["Allow-Web-DB"],
            "vlan_ids": [100],
            "subnets": ["10.10.100.0/24"],
        }

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({name: 'Allow-Web-DB', sources: ['web'], destinations: ['db'], services: ['MySQL'], action: 'ALLOW'})",
            }
        ]

        policies = generate_multi_network_policies(segment_mapping, rules, "workflow")

        yaml_content = list(policies.values())[0]
        policy = _parse_policy_yaml(yaml_content)

        # Verify policy types
        assert "policyTypes" in policy["spec"]
        assert "Ingress" in policy["spec"]["policyTypes"]
