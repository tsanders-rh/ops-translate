"""Integration tests for MultiNetworkPolicy end-to-end workflow.

Tests the complete pipeline from NSX analysis data through correlation
to MultiNetworkPolicy and NetworkPolicy generation.
"""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from ops_translate.workspace import Workspace


@pytest.fixture
def test_workspace(tmp_path):
    """Create a test workspace with NSX analysis data."""
    workspace_root = tmp_path / "test-workspace"
    workspace_root.mkdir()

    # Create necessary directories
    (workspace_root / "intent").mkdir()
    (workspace_root / "output").mkdir()

    # Create mock analysis data with NSX segments and firewall rules
    analysis_data = {
        "source_file": "nsx-test.workflow.xml",
        "nsx_operations": {
            "segments": [
                {
                    "name": "Web-Tier-VLAN100",
                    "location": "nsx-test.workflow.xml:24",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createSegment({displayName: 'Web-Tier-VLAN100', vlanIds: [100], subnets: ['10.10.100.0/24'], gateway: '10.10.100.1'})"
                },
                {
                    "name": "App-Tier-VLAN150",
                    "location": "nsx-test.workflow.xml:43",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createSegment({displayName: 'App-Tier-VLAN150', vlanIds: [150], subnets: ['10.10.150.0/24'], gateway: '10.10.150.1'})"
                },
                {
                    "name": "DB-Tier-VLAN200",
                    "location": "nsx-test.workflow.xml:62",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createSegment({displayName: 'DB-Tier-VLAN200', vlanIds: [200], subnets: ['10.10.200.0/24'], gateway: '10.10.200.1'})"
                }
            ],
            "firewall_rules": [
                {
                    "name": "Allow-Web-to-App",
                    "location": "nsx-test.workflow.xml:81",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createFirewallRule({name: 'Allow-Web-to-App', segment: 'Web-Tier-VLAN100', sources: ['web-sg'], destinations: ['app-sg'], services: ['HTTP', 'HTTPS'], action: 'ALLOW'})"
                },
                {
                    "name": "Allow-App-to-DB",
                    "location": "nsx-test.workflow.xml:102",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createFirewallRule({name: 'Allow-App-to-DB', segment: 'App-Tier-VLAN150', sources: ['app-sg'], destinations: ['db-sg'], services: ['MySQL'], action: 'ALLOW', destination: '10.10.200.50'})"
                },
                {
                    "name": "Allow-DB-Backup",
                    "location": "nsx-test.workflow.xml:124",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createFirewallRule({name: 'Allow-DB-Backup', segment: 'DB-Tier-VLAN200', vlan: 200, sources: ['backup-server'], destinations: ['db-sg'], destination: '10.10.200.50', services: ['SSH'], action: 'ALLOW'})"
                },
                {
                    "name": "Allow-Internet-Egress",
                    "location": "nsx-test.workflow.xml:147",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createFirewallRule({name: 'Allow-Internet-Egress', sources: ['any'], destinations: ['internet'], services: ['HTTP', 'HTTPS'], action: 'ALLOW'})"
                },
                {
                    "name": "Allow-DNS",
                    "location": "nsx-test.workflow.xml:167",
                    "confidence": 0.95,
                    "evidence": "nsxClient.createFirewallRule({name: 'Allow-DNS', sources: ['any'], destinations: ['dns-servers'], services: ['DNS'], action: 'ALLOW'})"
                }
            ]
        }
    }

    # Write analysis file
    analysis_file = workspace_root / "intent" / "analysis.vrealize.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis_data, f, indent=2)

    return workspace_root


class TestMultiNetworkPolicyWorkflow:
    """Integration tests for complete MultiNetworkPolicy workflow."""

    def test_end_to_end_correlation_and_generation(self, test_workspace):
        """Test complete workflow from analysis to policy generation."""
        from ops_translate.generate.generator import (
            _correlate_segments_and_rules,
            _generate_multi_network_policies,
            _generate_network_policies,
        )

        workspace = Workspace(test_workspace)

        # Step 1: Run correlation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)

        # Verify correlation results
        assert segment_rule_mapping is not None
        assert len(segment_rule_mapping.primary_network_rules) == 2
        assert len(segment_rule_mapping.segment_mappings) == 3

        # Verify primary network rules
        assert "Allow-Internet-Egress" in segment_rule_mapping.primary_network_rules
        assert "Allow-DNS" in segment_rule_mapping.primary_network_rules

        # Verify segment mappings
        assert "Web-Tier-VLAN100" in segment_rule_mapping.segment_mappings
        assert "App-Tier-VLAN150" in segment_rule_mapping.segment_mappings
        assert "DB-Tier-VLAN200" in segment_rule_mapping.segment_mappings

        # Step 2: Generate MultiNetworkPolicies
        _generate_multi_network_policies(workspace, segment_rule_mapping)

        # Verify MultiNetworkPolicy output
        mnp_dir = test_workspace / "output" / "multi-network-policies"
        assert mnp_dir.exists()

        # Check generated files
        assert (mnp_dir / "README.md").exists()
        assert (mnp_dir / "CORRELATION_REPORT.md").exists()
        assert (mnp_dir / "web-tier-vlan100-allow-web-to-app.yaml").exists()
        assert (mnp_dir / "app-tier-vlan150-allow-app-to-db.yaml").exists()
        assert (mnp_dir / "db-tier-vlan200-allow-db-backup.yaml").exists()

        # Step 3: Generate NetworkPolicies (primary network only)
        _generate_network_policies(workspace, segment_rule_mapping)

        # Verify NetworkPolicy output
        np_dir = test_workspace / "output" / "network-policies"
        assert np_dir.exists()

        # Check generated files (only primary network rules)
        assert (np_dir / "README.md").exists()
        assert (np_dir / "allow-internet-egress.yaml").exists()
        assert (np_dir / "allow-dns.yaml").exists()

        # Verify segment-specific rules NOT in NetworkPolicy
        assert not (np_dir / "allow-web-to-app.yaml").exists()
        assert not (np_dir / "allow-app-to-db.yaml").exists()
        assert not (np_dir / "allow-db-backup.yaml").exists()

    def test_multinetworkpolicy_yaml_structure(self, test_workspace):
        """Test that generated MultiNetworkPolicy YAML has correct structure."""
        from ops_translate.generate.generator import (
            _correlate_segments_and_rules,
            _generate_multi_network_policies,
        )

        workspace = Workspace(test_workspace)

        # Run correlation and generation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)
        _generate_multi_network_policies(workspace, segment_rule_mapping)

        # Load and validate MultiNetworkPolicy YAML
        mnp_file = test_workspace / "output" / "multi-network-policies" / "web-tier-vlan100-allow-web-to-app.yaml"
        assert mnp_file.exists()

        with open(mnp_file) as f:
            content = f.read()

        # Parse YAML (skip comments)
        yaml_parts = content.split("\n---\n")
        yaml_body = yaml_parts[1] if len(yaml_parts) > 1 else yaml_parts[0]
        lines = [line for line in yaml_body.split("\n") if not line.strip().startswith("#")]
        yaml_content = "\n".join(lines)

        docs = list(yaml.safe_load_all(yaml_content))
        policy = docs[0] if isinstance(docs[0], list) else docs[0]
        if isinstance(policy, list):
            policy = policy[0]

        # Verify API version and kind
        assert policy["apiVersion"] == "k8s.cni.cncf.io/v1beta1"
        assert policy["kind"] == "MultiNetworkPolicy"

        # Verify metadata
        assert policy["metadata"]["name"] == "web-tier-vlan100-allow-web-to-app"
        assert policy["metadata"]["namespace"] == "default"

        # Verify annotations
        annotations = policy["metadata"]["annotations"]
        assert "k8s.v1.cni.cncf.io/policy-for" in annotations
        assert annotations["k8s.v1.cni.cncf.io/policy-for"] == "default/web-tier-vlan100"
        assert "source-location" in annotations

        # Verify labels
        labels = policy["metadata"]["labels"]
        assert labels["translated-from"] == "nsx-firewall"
        assert labels["network-scope"] == "secondary"
        assert labels["network-attachment"] == "web-tier-vlan100"

        # Verify spec structure
        assert "podSelector" in policy["spec"]
        assert "policyTypes" in policy["spec"]
        assert "Ingress" in policy["spec"]["policyTypes"]
        assert "ingress" in policy["spec"]

    def test_correlation_report_content(self, test_workspace):
        """Test that correlation report contains correct information."""
        from ops_translate.generate.generator import (
            _correlate_segments_and_rules,
            _generate_multi_network_policies,
        )

        workspace = Workspace(test_workspace)

        # Run correlation and generation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)
        _generate_multi_network_policies(workspace, segment_rule_mapping)

        # Read correlation report
        report_file = test_workspace / "output" / "multi-network-policies" / "CORRELATION_REPORT.md"
        assert report_file.exists()

        with open(report_file) as f:
            report = f.read()

        # Verify report contains key information
        assert "# NSX Segment-to-Rule Correlation Report" in report
        assert "**Primary Network Rules**: 2" in report
        assert "**Segments with Rules**: 3" in report

        # Verify primary network rules listed
        assert "Allow-Internet-Egress" in report
        assert "Allow-DNS" in report

        # Verify segments listed
        assert "Web-Tier-VLAN100" in report
        assert "App-Tier-VLAN150" in report
        assert "DB-Tier-VLAN200" in report

        # Verify correlation confidence shown
        assert "**Correlation Confidence**: 0.95" in report

        # Verify correlation methods documented
        assert "Direct Reference" in report
        assert "IP Range Overlap" in report
        assert "VLAN Matching" in report

    def test_networkpolicy_filtering(self, test_workspace):
        """Test that NetworkPolicy generation correctly filters segment rules."""
        from ops_translate.generate.generator import (
            _correlate_segments_and_rules,
            _generate_network_policies,
        )

        workspace = Workspace(test_workspace)

        # Run correlation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)

        # Generate NetworkPolicies with filtering
        _generate_network_policies(workspace, segment_rule_mapping)

        # Verify only primary network rules were generated
        np_dir = test_workspace / "output" / "network-policies"

        yaml_files = list(np_dir.glob("*.yaml"))
        policy_names = [f.stem for f in yaml_files]

        # Should have exactly 2 policies (primary network rules)
        assert len(policy_names) == 2
        assert "allow-internet-egress" in policy_names
        assert "allow-dns" in policy_names

        # Should NOT have segment-specific rules
        assert "allow-web-to-app" not in policy_names
        assert "allow-app-to-db" not in policy_names
        assert "allow-db-backup" not in policy_names

    def test_confidence_scoring(self, test_workspace):
        """Test that correlation produces expected confidence scores."""
        from ops_translate.generate.generator import _correlate_segments_and_rules

        workspace = Workspace(test_workspace)

        # Run correlation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)

        # Verify high confidence for direct segment references
        web_tier = segment_rule_mapping.segment_mappings["Web-Tier-VLAN100"]
        assert web_tier.correlation_confidence >= 0.85  # High confidence

        app_tier = segment_rule_mapping.segment_mappings["App-Tier-VLAN150"]
        assert app_tier.correlation_confidence >= 0.85

        db_tier = segment_rule_mapping.segment_mappings["DB-Tier-VLAN200"]
        assert db_tier.correlation_confidence >= 0.85  # Has multiple signals

    def test_segment_metadata_extraction(self, test_workspace):
        """Test that segment metadata is correctly extracted."""
        from ops_translate.generate.generator import _correlate_segments_and_rules

        workspace = Workspace(test_workspace)

        # Run correlation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)

        # Verify Web-Tier segment metadata
        web_tier = segment_rule_mapping.segment_mappings["Web-Tier-VLAN100"]
        assert web_tier.segment_name == "Web-Tier-VLAN100"
        assert web_tier.nad_name == "web-tier-vlan100"
        assert 100 in web_tier.vlan_ids
        assert "10.10.100.0/24" in web_tier.subnets
        assert len(web_tier.firewall_rules) == 1
        assert "Allow-Web-to-App" in web_tier.firewall_rules

        # Verify App-Tier segment metadata
        app_tier = segment_rule_mapping.segment_mappings["App-Tier-VLAN150"]
        assert app_tier.nad_name == "app-tier-vlan150"
        assert 150 in app_tier.vlan_ids
        assert "10.10.150.0/24" in app_tier.subnets

        # Verify DB-Tier segment metadata
        db_tier = segment_rule_mapping.segment_mappings["DB-Tier-VLAN200"]
        assert db_tier.nad_name == "db-tier-vlan200"
        assert 200 in db_tier.vlan_ids
        assert "10.10.200.0/24" in db_tier.subnets

    def test_readme_generation(self, test_workspace):
        """Test that README files are generated with correct content."""
        from ops_translate.generate.generator import (
            _correlate_segments_and_rules,
            _generate_multi_network_policies,
        )

        workspace = Workspace(test_workspace)

        # Run correlation and generation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)
        _generate_multi_network_policies(workspace, segment_rule_mapping)

        # Check MultiNetworkPolicy README
        mnp_readme = test_workspace / "output" / "multi-network-policies" / "README.md"
        assert mnp_readme.exists()

        with open(mnp_readme) as f:
            content = f.read()

        # Verify key sections
        assert "# MultiNetworkPolicy Manifests (OVN-Kubernetes)" in content
        assert "k8s.cni.cncf.io/v1beta1" in content
        assert "NetworkAttachmentDefinition" in content
        assert "k8s.v1.cni.cncf.io/networks" in content  # Pod annotation example

    def test_no_segments_fallback(self, test_workspace):
        """Test behavior when no segments are detected."""
        from ops_translate.generate.generator import _correlate_segments_and_rules

        # Modify analysis to have no segments
        analysis_file = test_workspace / "intent" / "analysis.vrealize.json"
        with open(analysis_file) as f:
            analysis = json.load(f)

        analysis["nsx_operations"]["segments"] = []

        with open(analysis_file, 'w') as f:
            json.dump(analysis, f)

        workspace = Workspace(test_workspace)

        # Run correlation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)

        # All rules should go to primary network
        assert len(segment_rule_mapping.primary_network_rules) == 5
        assert len(segment_rule_mapping.segment_mappings) == 0

    def test_no_rules_handling(self, test_workspace):
        """Test behavior when no firewall rules are detected."""
        from ops_translate.generate.generator import _correlate_segments_and_rules

        # Modify analysis to have no rules
        analysis_file = test_workspace / "intent" / "analysis.vrealize.json"
        with open(analysis_file) as f:
            analysis = json.load(f)

        analysis["nsx_operations"]["firewall_rules"] = []

        with open(analysis_file, 'w') as f:
            json.dump(analysis, f)

        workspace = Workspace(test_workspace)

        # Run correlation
        segment_rule_mapping = _correlate_segments_and_rules(workspace)

        # Should return None when no rules
        assert segment_rule_mapping is None
