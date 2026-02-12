"""
Unit tests for vRealize action parsing and indexing.

Tests ActionDef, ActionIndex, and action XML parsing functionality.
"""

import json
import tempfile
from pathlib import Path

import pytest

from ops_translate.summarize.vrealize_actions import (
    ActionDef,
    ActionIndex,
    _extract_fqname_from_path,
    build_action_index,
    load_action_index,
    parse_action_xml,
    save_action_index,
)

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures/vrealize/actions"


class TestParseActionXML:
    """Tests for parsing action XML files."""

    def test_parse_complete_action(self):
        """Test parsing a well-formed action with all metadata."""
        action_file = FIXTURES_DIR / "com.acme.nsx" / "createFirewallRule.action.xml"
        assert action_file.exists(), f"Test fixture not found: {action_file}"

        action = parse_action_xml(action_file)

        assert action.fqname == "com.acme.nsx/createFirewallRule"
        assert action.name == "createFirewallRule"
        assert action.module == "com.acme.nsx"
        assert "nsxClient.createFirewallRule" in action.script
        assert action.result_type == "any"
        assert action.description == "Create NSX-T firewall rule with specified parameters"
        assert action.version == "1.0.0"
        assert len(action.sha256) == 64  # SHA256 hex length

    def test_parse_action_inputs(self):
        """Test parsing action input parameters."""
        action_file = FIXTURES_DIR / "com.acme.nsx" / "createFirewallRule.action.xml"

        action = parse_action_xml(action_file)

        assert len(action.inputs) == 3
        assert action.inputs[0]["name"] == "ruleName"
        assert action.inputs[0]["type"] == "string"
        assert action.inputs[0]["description"] == "Name of the firewall rule"

        assert action.inputs[1]["name"] == "source"
        assert action.inputs[2]["name"] == "destination"

    def test_parse_servicenow_action(self):
        """Test parsing ServiceNow integration action."""
        action_file = FIXTURES_DIR / "com.acme.servicenow" / "createIncident.action.xml"

        action = parse_action_xml(action_file)

        assert action.fqname == "com.acme.servicenow/createIncident"
        assert action.module == "com.acme.servicenow"
        assert "RESTHost" in action.script
        assert "servicenow" in action.script.lower()
        assert action.result_type == "string"
        assert len(action.inputs) == 3

    def test_parse_minimal_action(self):
        """Test parsing action with minimal metadata."""
        action_file = FIXTURES_DIR / "utils" / "simpleHelper.action.xml"

        action = parse_action_xml(action_file)

        assert action.name == "simpleHelper"
        assert action.script == '// Simple helper function\nreturn "Hello from action!";'
        assert action.result_type is None
        assert action.description is None
        assert action.version is None
        assert len(action.inputs) == 0

    def test_parse_action_missing_fqn_uses_path(self):
        """Test that fqname is extracted from path when not in XML."""
        action_file = FIXTURES_DIR / "utils" / "simpleHelper.action.xml"

        action = parse_action_xml(action_file)

        # Should extract fqname from file path
        assert action.fqname == "utils/simpleHelper"
        assert action.module == "utils"

    def test_parse_action_missing_script_raises_error(self):
        """Test that missing script element raises ValueError."""
        action_file = FIXTURES_DIR / "malformed" / "noScript.action.xml"

        with pytest.raises(ValueError, match="has no script content"):
            parse_action_xml(action_file)

    def test_parse_action_sha256_changes_with_script(self, tmp_path):
        """Test that SHA256 hash changes when script content changes."""
        # Create two actions with different scripts
        action1 = tmp_path / "action1.xml"
        action1.write_text("""<?xml version="1.0"?>
<dunes-script-module name="test" fqn="test/action1">
  <script><![CDATA[var x = 1;]]></script>
</dunes-script-module>""")

        action2 = tmp_path / "action2.xml"
        action2.write_text("""<?xml version="1.0"?>
<dunes-script-module name="test" fqn="test/action2">
  <script><![CDATA[var x = 2;]]></script>
</dunes-script-module>""")

        parsed1 = parse_action_xml(action1)
        parsed2 = parse_action_xml(action2)

        assert parsed1.sha256 != parsed2.sha256


class TestExtractFQNameFromPath:
    """Tests for extracting fqname from file path."""

    def test_extract_fqname_with_module(self):
        """Test extracting fqname from path with module."""
        path = Path("actions/com.acme.nsx/createFirewallRule.action.xml")
        fqname = _extract_fqname_from_path(path)
        assert fqname == "com.acme.nsx/createFirewallRule"

    def test_extract_fqname_nested_module(self):
        """Test extracting fqname from nested module path."""
        path = Path("actions/com/acme/nsx/helper.action.xml")
        fqname = _extract_fqname_from_path(path)
        assert fqname == "com.acme.nsx/helper"

    def test_extract_fqname_no_module(self):
        """Test extracting fqname with no module."""
        path = Path("actions/simpleAction.action.xml")
        fqname = _extract_fqname_from_path(path)
        assert fqname == "simpleAction"

    def test_extract_fqname_no_actions_dir(self):
        """Test fallback when 'actions' not in path."""
        path = Path("some/other/path/action.action.xml")
        fqname = _extract_fqname_from_path(path)
        assert fqname == "action.action"  # Uses stem


class TestActionIndex:
    """Tests for ActionIndex functionality."""

    def test_action_index_get(self):
        """Test retrieving action by fqname."""
        action1 = ActionDef(
            fqname="com.acme.nsx/createFirewallRule",
            name="createFirewallRule",
            module="com.acme.nsx",
            script="// script",
            inputs=[],
            result_type=None,
            description=None,
            source_path=Path("/test"),
            version=None,
            sha256="abc123",
        )

        index = ActionIndex(actions={"com.acme.nsx/createFirewallRule": action1})

        result = index.get("com.acme.nsx/createFirewallRule")
        assert result is not None
        assert result.fqname == "com.acme.nsx/createFirewallRule"

        # Non-existent action
        assert index.get("nonexistent/action") is None

    def test_action_index_find_by_module(self):
        """Test finding all actions in a module."""
        action1 = ActionDef(
            fqname="com.acme.nsx/createFirewallRule",
            name="createFirewallRule",
            module="com.acme.nsx",
            script="",
            inputs=[],
            result_type=None,
            description=None,
            source_path=Path("/test"),
            version=None,
            sha256="abc",
        )

        action2 = ActionDef(
            fqname="com.acme.nsx/createSegment",
            name="createSegment",
            module="com.acme.nsx",
            script="",
            inputs=[],
            result_type=None,
            description=None,
            source_path=Path("/test"),
            version=None,
            sha256="def",
        )

        action3 = ActionDef(
            fqname="com.acme.servicenow/createIncident",
            name="createIncident",
            module="com.acme.servicenow",
            script="",
            inputs=[],
            result_type=None,
            description=None,
            source_path=Path("/test"),
            version=None,
            sha256="ghi",
        )

        index = ActionIndex(
            actions={
                action1.fqname: action1,
                action2.fqname: action2,
                action3.fqname: action3,
            }
        )

        nsx_actions = index.find_by_module("com.acme.nsx")
        assert len(nsx_actions) == 2
        assert all(a.module == "com.acme.nsx" for a in nsx_actions)

        snow_actions = index.find_by_module("com.acme.servicenow")
        assert len(snow_actions) == 1

        empty_actions = index.find_by_module("nonexistent.module")
        assert len(empty_actions) == 0

    def test_action_index_len(self):
        """Test __len__ returns correct count."""
        index = ActionIndex(actions={})
        assert len(index) == 0

        action = ActionDef(
            fqname="test/action",
            name="action",
            module="test",
            script="",
            inputs=[],
            result_type=None,
            description=None,
            source_path=Path("/test"),
            version=None,
            sha256="abc",
        )
        index.actions["test/action"] = action
        assert len(index) == 1

    def test_action_index_contains(self):
        """Test __contains__ for membership checking."""
        action = ActionDef(
            fqname="test/action",
            name="action",
            module="test",
            script="",
            inputs=[],
            result_type=None,
            description=None,
            source_path=Path("/test"),
            version=None,
            sha256="abc",
        )

        index = ActionIndex(actions={"test/action": action})

        assert "test/action" in index
        assert "nonexistent/action" not in index


class TestBuildActionIndex:
    """Tests for building ActionIndex from manifest."""

    def test_build_action_index(self):
        """Test building index from manifest with multiple actions."""
        manifest = {
            "actions": [
                {
                    "absolute_path": str(
                        FIXTURES_DIR / "com.acme.nsx" / "createFirewallRule.action.xml"
                    )
                },
                {
                    "absolute_path": str(
                        FIXTURES_DIR / "com.acme.servicenow" / "createIncident.action.xml"
                    )
                },
            ]
        }

        index = build_action_index(manifest)

        assert len(index) == 2
        assert "com.acme.nsx/createFirewallRule" in index
        assert "com.acme.servicenow/createIncident" in index

    def test_build_action_index_malformed_action(self):
        """Test that malformed actions are skipped with warning."""
        manifest = {
            "actions": [
                {
                    "absolute_path": str(
                        FIXTURES_DIR / "com.acme.nsx" / "createFirewallRule.action.xml"
                    )
                },
                {"absolute_path": str(FIXTURES_DIR / "malformed" / "noScript.action.xml")},
            ]
        }

        # Should log warning but not crash
        index = build_action_index(manifest)

        # Should have 1 valid action, malformed one skipped
        assert len(index) == 1
        assert "com.acme.nsx/createFirewallRule" in index
        assert "malformed/noScript" not in index

    def test_build_action_index_empty_manifest(self):
        """Test building index from empty manifest."""
        manifest = {"actions": []}

        index = build_action_index(manifest)

        assert len(index) == 0
        assert index.actions == {}


class TestActionIndexPersistence:
    """Tests for saving and loading ActionIndex."""

    def test_save_and_load_action_index(self):
        """Test round-trip save and load preserves data."""
        # Create test index
        action = parse_action_xml(FIXTURES_DIR / "com.acme.nsx" / "createFirewallRule.action.xml")
        index = ActionIndex(actions={action.fqname: action})

        # Save to temp file
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "action-index.json"
            save_action_index(index, output_file)

            # Load from file
            loaded_index = load_action_index(output_file)

        assert loaded_index is not None
        assert len(loaded_index) == len(index)

        loaded_action = loaded_index.get("com.acme.nsx/createFirewallRule")
        assert loaded_action is not None
        assert loaded_action.fqname == action.fqname
        assert loaded_action.name == action.name
        assert loaded_action.module == action.module
        assert loaded_action.script == action.script
        assert loaded_action.sha256 == action.sha256
        assert loaded_action.inputs == action.inputs

    def test_save_action_index_creates_parent_directory(self):
        """Test that save creates parent directories if needed."""
        action = parse_action_xml(FIXTURES_DIR / "utils" / "simpleHelper.action.xml")
        index = ActionIndex(actions={action.fqname: action})

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "nested" / "dir" / "action-index.json"

            save_action_index(index, output_file)

            assert output_file.exists()
            assert output_file.parent.exists()

    def test_load_action_index_nonexistent_file(self):
        """Test loading from nonexistent file returns None."""
        result = load_action_index(Path("/nonexistent/action-index.json"))
        assert result is None

    def test_load_action_index_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns None."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        result = load_action_index(invalid_file)
        assert result is None

    def test_action_index_json_structure(self):
        """Test that saved JSON has correct structure."""
        action = parse_action_xml(FIXTURES_DIR / "com.acme.nsx" / "createFirewallRule.action.xml")
        index = ActionIndex(actions={action.fqname: action})

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "action-index.json"
            save_action_index(index, output_file)

            # Read and parse JSON
            data = json.loads(output_file.read_text())

        # Check structure
        assert "actions" in data
        assert "count" in data
        assert "indexed_at" in data
        assert data["count"] == 1

        # Check action entry
        action_data = data["actions"]["com.acme.nsx/createFirewallRule"]
        assert action_data["fqname"] == "com.acme.nsx/createFirewallRule"
        assert action_data["name"] == "createFirewallRule"
        assert action_data["module"] == "com.acme.nsx"
        assert "script" in action_data
        assert "inputs" in action_data
        assert "sha256" in action_data
