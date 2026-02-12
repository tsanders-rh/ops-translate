"""Tests for NSX segment to NetworkAttachmentDefinition translation."""

import json

import pytest
import yaml

from ops_translate.generate.network_attachment import generate_network_attachments
from ops_translate.generate.nsx_segment_mappings import NSXSegmentMapper

# Fixtures


@pytest.fixture
def nsx_mapper():
    """Create NSX to Kubernetes segment mapper."""
    return NSXSegmentMapper()


@pytest.fixture
def vlan_segment():
    """Sample VLAN segment detection."""
    return {
        "name": "nsxClient.createSegment",
        "location": "workflow.xml:100",
        "confidence": 0.9,
        "evidence": (
            "Pattern match: nsxClient.createSegment in context (workflow.xml:100): "
            '...nsxClient.createSegment({displayName: "Web-Tier-VLAN100", '
            'vlanIds: [100], subnets: [{gateway: "10.10.10.1/24"}]})...'
        ),
    }


@pytest.fixture
def overlay_segment():
    """Sample overlay segment detection."""
    return {
        "name": "LogicalSwitch",
        "location": "workflow.xml:200",
        "confidence": 0.8,
        "evidence": (
            "Pattern match: LogicalSwitch in context (workflow.xml:200): "
            "...LogicalSwitch creation for overlay-tz transport zone..."
        ),
    }


@pytest.fixture
def segment_with_subnet():
    """Segment with complete subnet information."""
    return {
        "name": "Database-Network",
        "location": "workflow.xml:300",
        "confidence": 0.85,
        "evidence": (
            'createSegment({displayName: "Database-Network", '
            'vlanIds: [200], subnets: [{networkAddress: "10.10.20.0/24", '
            'gateway: "10.10.20.1"}]})'
        ),
    }


# NSXSegmentMapper Tests


def test_extract_vlan_ids(nsx_mapper):
    """Test VLAN ID extraction from evidence."""
    # Single VLAN
    evidence = "vlanIds: [100]"
    assert nsx_mapper.extract_vlan_ids(evidence) == [100]

    # Multiple VLANs
    evidence = "vlanIds: [100, 200]"
    vlans = nsx_mapper.extract_vlan_ids(evidence)
    assert 100 in vlans and 200 in vlans

    # VLAN in name
    evidence = "segment-vlan100"
    assert 100 in nsx_mapper.extract_vlan_ids(evidence)


def test_extract_subnets(nsx_mapper):
    """Test subnet extraction from evidence."""
    # CIDR notation
    evidence = 'subnet: "10.10.10.0/24"'
    assert nsx_mapper.extract_subnets(evidence) == ["10.10.10.0/24"]

    # Network address + prefix
    evidence = 'networkAddress: "10.10.10.0", prefix: 24'
    subnets = nsx_mapper.extract_subnets(evidence)
    assert "10.10.10.0/24" in subnets


def test_extract_gateway(nsx_mapper):
    """Test gateway extraction from evidence."""
    # Explicit gateway
    evidence = 'gateway: "10.10.10.1"'
    assert nsx_mapper.extract_gateway(evidence) == "10.10.10.1"

    # Gateway with CIDR
    evidence = 'gateway: "10.10.10.1/24"'
    assert nsx_mapper.extract_gateway(evidence) == "10.10.10.1"

    # Infer from subnet
    gateway = nsx_mapper.extract_gateway("", "10.10.10.0/24")
    assert gateway == "10.10.10.1"


def test_determine_cni_vlan_segment(nsx_mapper):
    """Test CNI selection for VLAN segment."""
    segment_details = {"vlan_ids": [100]}
    cni_type = nsx_mapper.determine_cni_type(segment_details)

    assert cni_type["type"] == "macvlan"
    assert cni_type["mode"] == "bridge"
    assert not cni_type["requires_manual_config"]


def test_determine_cni_overlay_segment(nsx_mapper):
    """Test CNI selection for overlay segment."""
    segment_details = {"transport_zone": "overlay-tz"}
    cni_type = nsx_mapper.determine_cni_type(segment_details)

    assert cni_type["type"] == "bridge"


def test_determine_cni_performance_segment(nsx_mapper):
    """Test CNI selection for high-performance segment."""
    segment_details = {"name": "High-Performance-Network"}
    cni_type = nsx_mapper.determine_cni_type(segment_details)

    assert cni_type["type"] == "sriov"
    assert cni_type["requires_manual_config"]


def test_build_ipam_with_subnet(nsx_mapper):
    """Test IPAM configuration with subnet."""
    segment_details = {"subnets": ["10.10.10.0/24"]}
    ipam = nsx_mapper.build_ipam_config(segment_details)

    assert ipam["type"] == "whereabouts"
    assert ipam["range"] == "10.10.10.0/24"
    assert "10.10.10" in ipam["range_start"]
    assert "10.10.10" in ipam["range_end"]
    assert ipam["gateway"] == "10.10.10.1"


def test_build_ipam_without_subnet(nsx_mapper):
    """Test IPAM placeholder generation."""
    segment_details = {}
    ipam = nsx_mapper.build_ipam_config(segment_details)

    assert ipam["type"] == "whereabouts"
    assert "TODO" in ipam["range"]
    assert "TODO" in ipam["gateway"]


def test_build_cni_config_macvlan(nsx_mapper):
    """Test macvlan CNI config generation."""
    cni_type = {"type": "macvlan", "mode": "bridge"}
    segment_details = {"vlan_ids": [100]}
    ipam = {"type": "whereabouts", "range": "10.10.10.0/24"}

    config = nsx_mapper.build_cni_config(cni_type, segment_details, ipam)

    assert config["type"] == "macvlan"
    assert config["mode"] == "bridge"
    assert config["vlan"] == 100
    assert "master" in config


def test_build_cni_config_bridge(nsx_mapper):
    """Test bridge CNI config generation."""
    cni_type = {"type": "bridge"}
    segment_details = {"name": "App-Tier"}
    ipam = {"type": "whereabouts", "range": "10.10.10.0/24"}

    config = nsx_mapper.build_cni_config(cni_type, segment_details, ipam)

    assert config["type"] == "bridge"
    assert "bridge" in config
    assert "br-" in config["bridge"]
    assert config["isGateway"]


def test_sanitize_name(nsx_mapper):
    """Test segment name sanitization."""
    assert nsx_mapper.sanitize_name("Web Tier VLAN100") == "web-tier-vlan100"
    assert nsx_mapper.sanitize_name("Database_Network") == "database-network"
    assert nsx_mapper.sanitize_name("App-Tier#1") == "app-tier1"

    # Remove leading/trailing hyphens
    assert nsx_mapper.sanitize_name("-test-segment-") == "test-segment"

    # Collapse multiple hyphens
    assert nsx_mapper.sanitize_name("test---segment") == "test-segment"

    # Empty name
    assert nsx_mapper.sanitize_name("") == "nsx-segment"


# NetworkAttachmentDefinition Generation Tests


def test_generate_nad_basic(vlan_segment):
    """Test basic NAD generation from segment."""
    attachments = generate_network_attachments([vlan_segment], "test-workflow")

    assert len(attachments) == 1
    # Should generate a file
    assert any(".yaml" in filename for filename in attachments.keys())


def test_generate_nad_vlan_structure(vlan_segment):
    """Test NAD with VLAN has correct structure."""
    attachments = generate_network_attachments([vlan_segment], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Parse YAML (skip comments)
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    nad = yaml.safe_load(yaml_text)

    # Verify NAD structure
    assert nad["apiVersion"] == "k8s.cni.cncf.io/v1"
    assert nad["kind"] == "NetworkAttachmentDefinition"
    assert "metadata" in nad
    assert "spec" in nad
    assert "config" in nad["spec"]

    # Parse CNI config
    cni_config = json.loads(nad["spec"]["config"])
    assert cni_config["type"] == "macvlan"
    assert cni_config["vlan"] == 100


def test_generate_nad_with_subnet(segment_with_subnet):
    """Test NAD generation includes subnet configuration."""
    attachments = generate_network_attachments([segment_with_subnet], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Should include subnet in IPAM
    assert "10.10.20.0/24" in yaml_content
    assert "10.10.20.1" in yaml_content


def test_generate_multiple_nads():
    """Test generation from multiple segments."""
    segments = [
        {
            "name": "Segment 1",
            "location": "workflow.xml:100",
            "evidence": 'createSegment({displayName: "Segment1", vlanIds: [100]})',
        },
        {
            "name": "Segment 2",
            "location": "workflow.xml:200",
            "evidence": 'createSegment({displayName: "Segment2", vlanIds: [200]})',
        },
    ]

    attachments = generate_network_attachments(segments, "multi-segment-workflow")

    # Should generate 2 NADs
    assert len(attachments) == 2


def test_generate_nad_empty_input():
    """Test handling of empty input."""
    attachments = generate_network_attachments([], "test-workflow")
    assert len(attachments) == 0


def test_nad_labels(vlan_segment):
    """Test that generated NAD includes proper labels."""
    attachments = generate_network_attachments([vlan_segment], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Parse YAML
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    nad = yaml.safe_load(yaml_text)

    # Check labels
    assert "labels" in nad["metadata"]
    assert nad["metadata"]["labels"]["translated-from"] == "nsx-segment"
    assert nad["metadata"]["labels"]["source-workflow"] == "test-workflow"
    assert nad["metadata"]["labels"]["vlan-id"] == "100"


def test_nad_header_comments(vlan_segment):
    """Test that limitation warnings are included in header."""
    attachments = generate_network_attachments([vlan_segment], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Check for header content
    assert "PREREQUISITES" in yaml_content
    assert "Multus" in yaml_content
    assert "Whereabouts" in yaml_content
    assert "LIMITATIONS" in yaml_content


def test_nad_with_overlay_segment(overlay_segment):
    """Test NAD generation for overlay segment uses bridge."""
    attachments = generate_network_attachments([overlay_segment], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Parse YAML
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    nad = yaml.safe_load(yaml_text)

    # Parse CNI config
    cni_config = json.loads(nad["spec"]["config"])
    assert cni_config["type"] == "bridge"


def test_nad_ipam_whereabouts(segment_with_subnet):
    """Test that IPAM uses Whereabouts."""
    attachments = generate_network_attachments([segment_with_subnet], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Parse YAML
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    nad = yaml.safe_load(yaml_text)

    # Parse CNI config
    cni_config = json.loads(nad["spec"]["config"])
    assert cni_config["ipam"]["type"] == "whereabouts"
    assert "range" in cni_config["ipam"]
    assert "gateway" in cni_config["ipam"]


def test_nad_todo_comments():
    """Test that TODO comments are included when config is incomplete."""
    segment = {
        "name": "Basic-Segment",
        "location": "workflow.xml:100",
        "evidence": "createSegment({})",  # No VLAN or subnet info
    }

    attachments = generate_network_attachments([segment], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Should include TODO comments
    assert "TODO" in yaml_content


def test_limitation_warnings_dhcp():
    """Test DHCP limitation warning."""
    segment = {
        "name": "DHCP-Segment",
        "location": "workflow.xml:100",
        "evidence": "createSegment({dhcpConfig: {...}})",
    }

    attachments = generate_network_attachments([segment], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Should warn about DHCP
    assert "DHCP" in yaml_content or "dhcp" in yaml_content.lower()


def test_nad_valid_kubernetes_structure(vlan_segment):
    """Test that NAD has all required Kubernetes fields."""
    attachments = generate_network_attachments([vlan_segment], "test-workflow")
    yaml_content = list(attachments.values())[0]

    # Parse YAML
    yaml_lines = [line for line in yaml_content.split("\n") if not line.startswith("#")]
    yaml_text = "\n".join(yaml_lines)
    nad = yaml.safe_load(yaml_text)

    # Verify required fields
    assert nad["apiVersion"]
    assert nad["kind"]
    assert nad["metadata"]["name"]
    assert nad["metadata"]["namespace"]
    assert nad["spec"]["config"]

    # Verify CNI config is valid JSON
    cni_config = json.loads(nad["spec"]["config"])
    assert cni_config["cniVersion"]
    assert cni_config["type"]
    assert cni_config["ipam"]
