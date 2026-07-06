"""Tests for NSX segment-to-rule correlation engine."""

import pytest

from ops_translate.generate.nsx_correlation import NSXCorrelationEngine, SegmentRuleMapping


class TestNSXCorrelationEngine:
    """Test NSX correlation engine functionality."""

    def test_direct_reference_correlation(self):
        """Test correlation when rule evidence contains segment name."""
        engine = NSXCorrelationEngine()

        segments = [
            {
                "name": "Web-Tier-VLAN100",
                "location": "workflow.xml:45",
                "evidence": "createSegment({displayName: 'Web-Tier-VLAN100', vlanIds: [100]})",
            }
        ]

        rules = [
            {
                "name": "Allow-Web-DB",
                "location": "workflow.xml:145",
                "evidence": "createFirewallRule({source: 'web', segment: 'Web-Tier-VLAN100'})",
            }
        ]

        mapping = engine.correlate_rules_to_segments(rules, segments)

        # Should map rule to segment with high confidence
        assert "Web-Tier-VLAN100" in mapping.segment_mappings
        assert "Allow-Web-DB" in mapping.segment_mappings["Web-Tier-VLAN100"].firewall_rules
        assert mapping.segment_mappings["Web-Tier-VLAN100"].correlation_confidence >= 0.85

    def test_ip_overlap_correlation(self):
        """Test correlation based on IP range overlap."""
        engine = NSXCorrelationEngine()

        segments = [
            {
                "name": "Web-Tier",
                "evidence": "createSegment({subnets: ['10.10.100.0/24']})",
            }
        ]

        rules = [
            {
                "name": "Allow-DB-Access",
                "evidence": "createFirewallRule({destination: '10.10.100.50'})",
            }
        ]

        mapping = engine.correlate_rules_to_segments(rules, segments)

        # Should match based on IP overlap
        assert "Web-Tier" in mapping.segment_mappings
        assert "Allow-DB-Access" in mapping.segment_mappings["Web-Tier"].firewall_rules
        assert mapping.segment_mappings["Web-Tier"].correlation_confidence >= 0.65

    def test_vlan_matching_correlation(self):
        """Test correlation based on VLAN ID matching."""
        engine = NSXCorrelationEngine()

        segments = [
            {
                "name": "App-Tier-VLAN150",
                "evidence": "createSegment({vlanIds: [150]})",
            }
        ]

        rules = [
            {
                "name": "Allow-App-Traffic",
                "evidence": "createFirewallRule({vlan: 150, services: ['HTTP']})",
            }
        ]

        mapping = engine.correlate_rules_to_segments(rules, segments)

        # Should match based on VLAN ID
        assert "App-Tier-VLAN150" in mapping.segment_mappings
        assert "Allow-App-Traffic" in mapping.segment_mappings["App-Tier-VLAN150"].firewall_rules
        assert mapping.segment_mappings["App-Tier-VLAN150"].correlation_confidence >= 0.65

    def test_no_correlation_defaults_to_primary(self):
        """Test that rules with no correlation go to primary network."""
        engine = NSXCorrelationEngine()

        segments = [
            {
                "name": "Web-Tier-VLAN100",
                "evidence": "createSegment({vlanIds: [100]})",
            }
        ]

        rules = [
            {
                "name": "Allow-Internet-Egress",
                "evidence": "createFirewallRule({source: 'any', destination: 'internet'})",
            }
        ]

        mapping = engine.correlate_rules_to_segments(rules, segments)

        # Should go to primary network (no segment reference)
        assert "Allow-Internet-Egress" in mapping.primary_network_rules
        assert len(mapping.segment_mappings["Web-Tier-VLAN100"].firewall_rules) == 0

    def test_multiple_detections_increase_confidence(self):
        """Test that multiple detection signals increase confidence."""
        engine = NSXCorrelationEngine()

        segments = [
            {
                "name": "DB-Tier-VLAN200",
                "evidence": "createSegment({vlanIds: [200], subnets: ['10.10.200.0/24']})",
                "location": "workflow.xml:60",
            }
        ]

        rules = [
            {
                "name": "Allow-Backup",
                # Multiple signals: segment name + VLAN + IP + proximity
                "evidence": "createFirewallRule({segment: 'DB-Tier-VLAN200', vlan: 200, destination: '10.10.200.50'})",
                "location": "workflow.xml:80",
            }
        ]

        mapping = engine.correlate_rules_to_segments(rules, segments)

        # Should have high confidence due to multiple corroborating signals
        assert "DB-Tier-VLAN200" in mapping.segment_mappings
        assert mapping.segment_mappings["DB-Tier-VLAN200"].correlation_confidence >= 0.90

    def test_no_segments_all_rules_to_primary(self):
        """Test that all rules go to primary when no segments detected."""
        engine = NSXCorrelationEngine()

        segments = []
        rules = [
            {"name": "Rule1", "evidence": "allow traffic"},
            {"name": "Rule2", "evidence": "deny access"},
        ]

        mapping = engine.correlate_rules_to_segments(rules, segments)

        assert len(mapping.primary_network_rules) == 2
        assert "Rule1" in mapping.primary_network_rules
        assert "Rule2" in mapping.primary_network_rules
        assert len(mapping.segment_mappings) == 0

    def test_no_rules_empty_mapping(self):
        """Test that empty rules list returns empty mapping."""
        engine = NSXCorrelationEngine()

        segments = [{"name": "Web-Tier", "evidence": "createSegment()"}]
        rules = []

        mapping = engine.correlate_rules_to_segments(rules, segments)

        assert len(mapping.primary_network_rules) == 0
        assert len(mapping.segment_mappings) == 0

    def test_nad_name_sanitization(self):
        """Test NAD name sanitization."""
        engine = NSXCorrelationEngine()

        test_cases = [
            ("Web Tier VLAN100", "web-tier-vlan100"),
            ("Database_Tier_VLAN200", "database-tier-vlan200"),
            ("App-Tier (Production)", "app-tier-production"),
            ("SPECIAL!@#CHARS$$$", "specialchars"),
        ]

        for input_name, expected in test_cases:
            assert engine._sanitize_nad_name(input_name) == expected

    def test_vlan_id_extraction(self):
        """Test VLAN ID extraction from evidence."""
        engine = NSXCorrelationEngine()

        test_cases = [
            ("vlanIds: [100, 200]", [100, 200]),
            ("VLAN 150", [150]),
            ("vlan=300", [300]),
            ("no vlan here", []),
        ]

        for evidence, expected in test_cases:
            result = engine._extract_vlan_ids(evidence)
            assert sorted(result) == sorted(expected)

    def test_subnet_extraction(self):
        """Test subnet extraction from evidence."""
        engine = NSXCorrelationEngine()

        evidence = "subnets: ['10.10.100.0/24', '192.168.1.0/24']"
        result = engine._extract_subnets(evidence)

        assert "10.10.100.0/24" in result
        assert "192.168.1.0/24" in result

    def test_ip_address_extraction(self):
        """Test IP address extraction from evidence."""
        engine = NSXCorrelationEngine()

        evidence = "source: 10.10.100.50, destination: 10.10.200.60"
        result = engine._extract_ip_addresses(evidence)

        assert "10.10.100.50" in result
        assert "10.10.200.60" in result

    def test_proximity_detection(self):
        """Test proximity detection for nearby workflow locations."""
        engine = NSXCorrelationEngine()

        # Nearby (within 50 lines)
        assert engine._detect_proximity("workflow.xml:100", "workflow.xml:120") is True

        # Too far apart
        assert engine._detect_proximity("workflow.xml:100", "workflow.xml:500") is False

        # Different files
        assert engine._detect_proximity("file1.xml:100", "file2.xml:100") is False

        # Invalid format
        assert engine._detect_proximity("invalid", "also-invalid") is False
