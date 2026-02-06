"""
Unit tests for vRealize workflow analysis.

Tests detection of NSX operations, custom plugins, REST calls, and complexity scoring.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ops_translate.analyze.vrealize import (
    analyze_vrealize_workflow,
    calculate_detection_confidence,
    detect_custom_plugins,
    detect_nsx_operations,
    detect_rest_calls,
)

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures/vrealize"


def parse_workflow(workflow_file: Path) -> tuple[ET.Element, str]:
    """Helper to parse workflow and extract namespace."""
    tree = ET.parse(workflow_file)
    root = tree.getroot()
    namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
    return root, namespace


class TestDetectNSXOperations:
    """Tests for NSX operation detection."""

    def test_detect_nsx_segments(self):
        """Test detection of NSX segment operations."""
        workflow_file = FIXTURES_DIR / "nsx-light.xml"
        root, namespace = parse_workflow(workflow_file)
        nsx_ops = detect_nsx_operations(root, namespace)

        assert "segments" in nsx_ops
        assert len(nsx_ops["segments"]) >= 1
        # Should detect both createSegment call and Segment object type
        assert any("createsegment" in op["name"].lower() for op in nsx_ops["segments"])

    def test_detect_nsx_firewall_rules(self):
        """Test detection of NSX firewall rule operations."""
        workflow_file = FIXTURES_DIR / "nsx-medium.xml"

        root, namespace = parse_workflow(workflow_file)

        nsx_ops = detect_nsx_operations(root, namespace)

        assert "firewall_rules" in nsx_ops
        assert len(nsx_ops["firewall_rules"]) >= 2
        # Check confidence scores exist
        for op in nsx_ops["firewall_rules"]:
            assert "confidence" in op
            assert 0.0 <= op["confidence"] <= 1.0

    def test_detect_nsx_security_groups(self):
        """Test detection of NSX security group operations."""
        workflow_file = FIXTURES_DIR / "nsx-medium.xml"

        root, namespace = parse_workflow(workflow_file)

        nsx_ops = detect_nsx_operations(root, namespace)

        assert "security_groups" in nsx_ops
        assert len(nsx_ops["security_groups"]) >= 3
        # Verify evidence is captured
        for op in nsx_ops["security_groups"]:
            assert "evidence" in op
            assert len(op["evidence"]) > 0

    def test_nsx_heavy_workflow_detects_multiple_types(self):
        """Test that nsx-heavy fixture detects multiple operation types."""
        workflow_file = FIXTURES_DIR / "nsx-heavy.xml"

        root, namespace = parse_workflow(workflow_file)

        nsx_ops = detect_nsx_operations(root, namespace)

        # Should detect multiple categories
        assert len(nsx_ops) >= 3
        # Count total operations
        total_ops = sum(len(ops) for ops in nsx_ops.values())
        assert total_ops >= 10

    def test_no_nsx_operations(self):
        """Test workflow with no NSX operations."""
        workflow_file = FIXTURES_DIR / "no-dependencies.xml"

        root, namespace = parse_workflow(workflow_file)

        nsx_ops = detect_nsx_operations(root, namespace)

        # Should return empty dict or dict with empty lists
        total_ops = sum(len(ops) for ops in nsx_ops.values())
        assert total_ops == 0


class TestDetectCustomPlugins:
    """Tests for custom plugin detection."""

    def test_detect_servicenow_plugin(self):
        """Test detection of ServiceNow custom plugin."""
        workflow_file = FIXTURES_DIR / "plugins-custom.xml"

        root, namespace = parse_workflow(workflow_file)

        plugins = detect_custom_plugins(root, namespace)

        # Should detect ServiceNow plugin references
        assert len(plugins) > 0
        # Check evidence field which contains the module name
        plugin_evidence = [p["evidence"].lower() for p in plugins]
        assert any("servicenow" in evidence for evidence in plugin_evidence)

    def test_detect_infoblox_plugin(self):
        """Test detection of Infoblox custom plugin."""
        workflow_file = FIXTURES_DIR / "plugins-custom.xml"

        root, namespace = parse_workflow(workflow_file)

        plugins = detect_custom_plugins(root, namespace)

        # Should detect Infoblox plugin references
        # Check evidence field which contains the module name
        plugin_evidence = [p["evidence"].lower() for p in plugins]
        assert any("infoblox" in evidence for evidence in plugin_evidence)

    def test_no_custom_plugins(self):
        """Test workflow with no custom plugins."""
        workflow_file = FIXTURES_DIR / "no-dependencies.xml"

        root, namespace = parse_workflow(workflow_file)

        plugins = detect_custom_plugins(root, namespace)

        # Should return empty list
        assert len(plugins) == 0


class TestDetectRestCalls:
    """Tests for REST API call detection."""

    def test_detect_rest_client_calls(self):
        """Test detection of restClient.METHOD() calls."""
        workflow_file = FIXTURES_DIR / "rest-api.xml"

        root, namespace = parse_workflow(workflow_file)

        rest_calls = detect_rest_calls(root, namespace)

        # Should detect GET, POST, PUT, DELETE
        assert len(rest_calls) >= 4
        methods = {call["method"] for call in rest_calls}
        assert "GET" in methods
        assert "POST" in methods

    def test_detect_fetch_calls(self):
        """Test detection of fetch() API calls."""
        workflow_file = FIXTURES_DIR / "rest-api.xml"

        root, namespace = parse_workflow(workflow_file)

        rest_calls = detect_rest_calls(root, namespace)

        # Should detect fetch() calls
        fetch_calls = [c for c in rest_calls if c.get("call_type") == "fetch"]
        assert len(fetch_calls) >= 1

    def test_detect_xhr_calls(self):
        """Test detection of XMLHttpRequest calls."""
        workflow_file = FIXTURES_DIR / "rest-api.xml"

        root, namespace = parse_workflow(workflow_file)

        rest_calls = detect_rest_calls(root, namespace)

        # Should detect XMLHttpRequest
        xhr_calls = [c for c in rest_calls if c.get("call_type") == "XMLHttpRequest"]
        assert len(xhr_calls) >= 1

    def test_rest_call_confidence_scores(self):
        """Test that REST calls have appropriate confidence scores."""
        workflow_file = FIXTURES_DIR / "rest-api.xml"

        root, namespace = parse_workflow(workflow_file)

        rest_calls = detect_rest_calls(root, namespace)

        for call in rest_calls:
            assert "confidence" in call
            assert 0.0 <= call["confidence"] <= 1.0
            # restClient calls should have high confidence
            if call.get("call_type") == "restClient":
                assert call["confidence"] >= 0.8

    def test_no_rest_calls(self):
        """Test workflow with no REST calls."""
        workflow_file = FIXTURES_DIR / "no-dependencies.xml"

        root, namespace = parse_workflow(workflow_file)

        rest_calls = detect_rest_calls(root, namespace)

        assert len(rest_calls) == 0


class TestDetectionConfidence:
    """Tests for confidence scoring."""

    def test_api_call_high_confidence(self):
        """Test that API calls get high confidence scores."""
        confidence = calculate_detection_confidence(
            "api_call", "nsxClient.createSegment()", "createSegment"
        )
        assert confidence >= 0.85

    def test_object_type_medium_confidence(self):
        """Test that object types get medium confidence scores."""
        confidence = calculate_detection_confidence(
            "object_type", "var seg = new Segment()", "Segment"
        )
        assert 0.5 <= confidence < 0.8

    def test_keyword_low_confidence(self):
        """Test that keywords get low confidence scores."""
        confidence = calculate_detection_confidence("keyword", "nsx tier1 config", "nsx")
        assert confidence < 0.5

    def test_context_boosts_confidence(self):
        """Test that supportive context increases confidence."""
        # Without context
        base_confidence = calculate_detection_confidence("keyword", "segment", "segment")

        # With supportive context
        boosted_confidence = calculate_detection_confidence(
            "keyword", "nsxClient nsx-api-v1 createSegment segment", "segment"
        )

        assert boosted_confidence > base_confidence

    def test_confidence_capped_at_095(self):
        """Test that confidence is capped at 0.95."""
        # Even with maximum boosts, should not exceed 0.95
        confidence = calculate_detection_confidence(
            "api_call", "nsxClient nsx-api-v1 createSegment POST /api", "createSegment"
        )
        assert confidence <= 0.95


class TestAnalyzeWorkflow:
    """Integration tests for full workflow analysis."""

    def test_analyze_nsx_light(self):
        """Test analysis of light NSX workflow."""
        workflow_file = FIXTURES_DIR / "nsx-light.xml"
        result = analyze_vrealize_workflow(workflow_file)

        assert "source_file" in result
        assert "signals" in result
        assert "confidence" in result
        assert "evidence" in result
        assert "nsx_operations" in result

        # Should have detected segments
        assert len(result["nsx_operations"]["segments"]) >= 1

        # Should have signals
        assert result["signals"]["nsx_keywords"] >= 1

    def test_analyze_nsx_medium(self):
        """Test analysis of medium NSX workflow."""
        workflow_file = FIXTURES_DIR / "nsx-medium.xml"
        result = analyze_vrealize_workflow(workflow_file)

        # Should detect multiple operation types
        assert result["signals"]["nsx_keywords"] >= 8

        # Should have high or medium confidence
        assert result["confidence"] in ["medium", "high"]

        # Evidence should be sorted by confidence
        if len(result["evidence"]) > 1:
            confidences = [e["confidence"] for e in result["evidence"]]
            assert confidences == sorted(confidences, reverse=True)

    def test_analyze_plugins(self):
        """Test analysis of workflow with custom plugins."""
        workflow_file = FIXTURES_DIR / "plugins-custom.xml"
        result = analyze_vrealize_workflow(workflow_file)

        # Should detect plugins
        assert result["signals"]["plugin_refs"] >= 2
        assert len(result["custom_plugins"]) >= 2

    def test_analyze_rest_calls(self):
        """Test analysis of workflow with REST calls."""
        workflow_file = FIXTURES_DIR / "rest-api.xml"
        result = analyze_vrealize_workflow(workflow_file)

        # Should detect REST calls
        assert result["signals"]["rest_calls"] >= 4
        assert len(result["rest_api_calls"]) >= 4

    def test_analyze_no_dependencies(self):
        """Test analysis of pure vCenter workflow."""
        workflow_file = FIXTURES_DIR / "no-dependencies.xml"
        result = analyze_vrealize_workflow(workflow_file)

        # Should have no external dependencies
        assert result["signals"]["nsx_keywords"] == 0
        assert result["signals"]["plugin_refs"] == 0
        assert result["signals"]["rest_calls"] == 0
        assert not result["has_external_dependencies"]

    def test_xml_namespace_handling(self):
        """Test that XML namespaces are handled correctly."""
        workflow_file = FIXTURES_DIR / "nsx-light.xml"
        # Should not raise exception
        result = analyze_vrealize_workflow(workflow_file)
        assert "nsx_operations" in result

    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file raises appropriate error."""
        from ops_translate.exceptions import FileNotFoundError as OpsFileNotFoundError

        with pytest.raises(OpsFileNotFoundError):
            analyze_vrealize_workflow(Path("/nonexistent/file.xml"))

    def test_invalid_xml_raises_error(self):
        """Test that invalid XML raises appropriate error."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write("<invalid>xml<without>closing</tags>")
            invalid_file = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid XML"):
                analyze_vrealize_workflow(invalid_file)
        finally:
            invalid_file.unlink()
