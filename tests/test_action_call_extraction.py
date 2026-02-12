"""
Tests for vRO action call extraction and resolution (Issue #53).
"""

from pathlib import Path

from ops_translate.summarize.vrealize_actions import ActionDef, ActionIndex
from ops_translate.translate.vrealize_workflow import WorkflowParser, extract_action_calls


class TestActionCallExtraction:
    """Tests for extracting action calls from workflow scripts."""

    def test_extract_action_calls_direct(self):
        """Test extracting direct action calls via System.getModule()."""
        script = """
        var nsxModule = System.getModule("com.acme.nsx");
        var rule = nsxModule.createFirewallRule("Web-to-DB", "Web-SG", "DB-SG");
        """

        calls = extract_action_calls(script)

        # Should have no direct calls since it uses variable assignment
        # (tested separately in test_extract_action_calls_variable)
        assert len(calls) == 1
        assert calls[0]["fqname"] == "com.acme.nsx/createFirewallRule"
        assert calls[0]["module"] == "com.acme.nsx"
        assert calls[0]["method"] == "createFirewallRule"
        assert calls[0]["pattern"] == "variable_call"

    def test_extract_action_calls_direct_inline(self):
        """Test extracting inline direct action calls."""
        script = """
        var result = System.getModule("com.acme.servicenow").createIncident("Test incident");
        """

        calls = extract_action_calls(script)

        assert len(calls) == 1
        assert calls[0]["fqname"] == "com.acme.servicenow/createIncident"
        assert calls[0]["module"] == "com.acme.servicenow"
        assert calls[0]["method"] == "createIncident"
        assert calls[0]["pattern"] == "direct_call"

    def test_extract_action_calls_multiple(self):
        """Test extracting multiple action calls from same script."""
        script = """
        // Create NSX segment
        var segment = System.getModule("com.acme.nsx").createSegment("web-segment");

        // Create firewall rule
        var fwModule = System.getModule("com.acme.nsx");
        var rule = fwModule.createFirewallRule("allow-web");

        // Create ServiceNow incident
        System.getModule("com.acme.servicenow").createIncident("Provisioned");
        """

        calls = extract_action_calls(script)

        assert len(calls) == 3
        fqnames = {call["fqname"] for call in calls}
        assert "com.acme.nsx/createSegment" in fqnames
        assert "com.acme.nsx/createFirewallRule" in fqnames
        assert "com.acme.servicenow/createIncident" in fqnames

    def test_extract_action_calls_deduplication(self):
        """Test that duplicate action calls are deduplicated."""
        script = """
        System.getModule("com.acme.nsx").createSegment("segment1");
        System.getModule("com.acme.nsx").createSegment("segment2");
        System.getModule("com.acme.nsx").createSegment("segment3");
        """

        calls = extract_action_calls(script)

        # Should only have one unique call
        assert len(calls) == 1
        assert calls[0]["fqname"] == "com.acme.nsx/createSegment"

    def test_extract_action_calls_empty_script(self):
        """Test handling of empty script."""
        calls = extract_action_calls("")

        assert calls == []

    def test_extract_action_calls_no_actions(self):
        """Test script with no action calls."""
        script = """
        var x = 1;
        var y = x + 2;
        System.log("Hello world");
        """

        calls = extract_action_calls(script)

        assert calls == []

    def test_extract_action_calls_variable_pattern(self):
        """Test variable assignment pattern specifically."""
        script = """
        var ipamModule = System.getModule("com.acme.ipam");
        var ipAddress = ipamModule.getNextIP("192.168.1.0/24");
        var subnet = ipamModule.getSubnet("web-subnet");
        """

        calls = extract_action_calls(script)

        assert len(calls) == 2
        fqnames = {call["fqname"] for call in calls}
        assert "com.acme.ipam/getNextIP" in fqnames
        assert "com.acme.ipam/getSubnet" in fqnames

        # All should be variable_call pattern
        assert all(call["pattern"] == "variable_call" for call in calls)

    def test_extract_action_calls_mixed_patterns(self):
        """Test mixed direct and variable patterns."""
        script = """
        // Direct call
        var result1 = System.getModule("com.acme.nsx").createSegment("seg1");

        // Variable assignment
        var snowModule = System.getModule("com.acme.servicenow");
        var incident = snowModule.createIncident("Test");
        """

        calls = extract_action_calls(script)

        assert len(calls) == 2

        # Check patterns
        patterns = {call["fqname"]: call["pattern"] for call in calls}
        assert patterns["com.acme.nsx/createSegment"] == "direct_call"
        assert patterns["com.acme.servicenow/createIncident"] == "variable_call"

    def test_extract_action_calls_evidence_captured(self):
        """Test that evidence string is captured."""
        script = 'var x = System.getModule("com.acme.nsx").createFirewallRule('

        calls = extract_action_calls(script)

        assert len(calls) == 1
        assert "System.getModule" in calls[0]["evidence"]
        assert "createFirewallRule" in calls[0]["evidence"]


class TestActionResolution:
    """Tests for resolving action calls against ActionIndex."""

    def test_resolve_action_calls_success(self, tmp_path):
        """Test successfully resolving action calls with ActionIndex."""
        # Create action index with test action
        action_def = ActionDef(
            fqname="com.acme.nsx/createFirewallRule",
            name="createFirewallRule",
            module="com.acme.nsx",
            script="var rule = nsxClient.createFirewallRule(...);",
            inputs=[{"name": "ruleName", "type": "string", "description": "Rule name"}],
            result_type="any",
            description="Create NSX firewall rule",
            source_path=Path("/test/action.xml"),
            version="1.0.0",
            sha256="abc123",
        )
        action_index = ActionIndex(actions={"com.acme.nsx/createFirewallRule": action_def})

        # Create test workflow that calls this action
        workflow_xml = tmp_path / "test_workflow.xml"
        workflow_xml.write_text("""<?xml version="1.0"?>
<workflow xmlns="http://vmware.com/vco/workflow">
  <workflow-item name="item1" type="task">
    <display-name>Create NSX Rule</display-name>
    <script><![CDATA[
      var nsxModule = System.getModule("com.acme.nsx");
      var rule = nsxModule.createFirewallRule("Web-to-DB", "Web-SG", "DB-SG");
      System.log("Rule created: " + rule.id);
    ]]></script>
  </workflow-item>
</workflow>""")

        # Parse with ActionIndex
        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_xml)

        # Should have resolved the action
        assert len(items) == 1
        item = items[0]

        assert len(item.action_calls) == 1
        assert item.action_calls[0]["fqname"] == "com.acme.nsx/createFirewallRule"

        assert len(item.resolved_actions) == 1
        assert item.resolved_actions[0].fqname == "com.acme.nsx/createFirewallRule"
        assert item.resolved_actions[0].script == "var rule = nsxClient.createFirewallRule(...);"

        assert len(item.unresolved_actions) == 0

    def test_resolve_action_calls_missing_action(self, tmp_path):
        """Test handling of action calls when action is not in index."""
        # Create empty action index
        action_index = ActionIndex(actions={})

        # Create test workflow that calls an action
        workflow_xml = tmp_path / "test_workflow.xml"
        workflow_xml.write_text("""<?xml version="1.0"?>
<workflow xmlns="http://vmware.com/vco/workflow">
  <workflow-item name="item1" type="task">
    <display-name>Create NSX Rule</display-name>
    <script><![CDATA[
      var rule = System.getModule("com.acme.nsx").createFirewallRule("test");
    ]]></script>
  </workflow-item>
</workflow>""")

        # Parse with ActionIndex
        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_xml)

        # Should have detected but not resolved the action
        assert len(items) == 1
        item = items[0]

        assert len(item.action_calls) == 1
        assert item.action_calls[0]["fqname"] == "com.acme.nsx/createFirewallRule"

        assert len(item.resolved_actions) == 0

        assert len(item.unresolved_actions) == 1
        assert item.unresolved_actions[0] == "com.acme.nsx/createFirewallRule"

    def test_resolve_multiple_actions(self, tmp_path):
        """Test resolving multiple different actions in one workflow."""
        # Create action index with multiple actions
        nsx_action = ActionDef(
            fqname="com.acme.nsx/createSegment",
            name="createSegment",
            module="com.acme.nsx",
            script="nsxClient.createSegment(...);",
            inputs=[],
            result_type="any",
            description="Create NSX segment",
            source_path=Path("/test/nsx.xml"),
            version="1.0.0",
            sha256="abc123",
        )
        snow_action = ActionDef(
            fqname="com.acme.servicenow/createIncident",
            name="createIncident",
            module="com.acme.servicenow",
            script="snowClient.createIncident(...);",
            inputs=[],
            result_type="string",
            description="Create ServiceNow incident",
            source_path=Path("/test/snow.xml"),
            version="1.0.0",
            sha256="def456",
        )

        action_index = ActionIndex(
            actions={
                "com.acme.nsx/createSegment": nsx_action,
                "com.acme.servicenow/createIncident": snow_action,
            }
        )

        # Create workflow calling both actions
        workflow_xml = tmp_path / "test_workflow.xml"
        workflow_xml.write_text("""<?xml version="1.0"?>
<workflow xmlns="http://vmware.com/vco/workflow">
  <workflow-item name="item1" type="task">
    <display-name>Provision Resources</display-name>
    <script><![CDATA[
      var segment = System.getModule("com.acme.nsx").createSegment("web-seg");
      var incident = System.getModule("com.acme.servicenow").createIncident("Provisioned");
    ]]></script>
  </workflow-item>
</workflow>""")

        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_xml)

        assert len(items) == 1
        item = items[0]

        assert len(item.action_calls) == 2
        assert len(item.resolved_actions) == 2
        assert len(item.unresolved_actions) == 0

        fqnames = {action.fqname for action in item.resolved_actions}
        assert "com.acme.nsx/createSegment" in fqnames
        assert "com.acme.servicenow/createIncident" in fqnames

    def test_no_action_resolution_without_index(self, tmp_path):
        """Test that without ActionIndex, no resolution occurs."""
        # Create workflow with action calls
        workflow_xml = tmp_path / "test_workflow.xml"
        workflow_xml.write_text("""<?xml version="1.0"?>
<workflow xmlns="http://vmware.com/vco/workflow">
  <workflow-item name="item1" type="task">
    <display-name>Test</display-name>
    <script><![CDATA[
      System.getModule("com.acme.nsx").createSegment("test");
    ]]></script>
  </workflow-item>
</workflow>""")

        # Parse without ActionIndex
        parser = WorkflowParser()
        items = parser.parse_file(workflow_xml)

        assert len(items) == 1
        item = items[0]

        # No resolution should have occurred
        assert len(item.action_calls) == 0
        assert len(item.resolved_actions) == 0
        assert len(item.unresolved_actions) == 0

    def test_workflow_without_scripts(self, tmp_path):
        """Test that workflows without scripts don't cause errors."""
        action_index = ActionIndex(actions={})

        workflow_xml = tmp_path / "test_workflow.xml"
        workflow_xml.write_text("""<?xml version="1.0"?>
<workflow xmlns="http://vmware.com/vco/workflow">
  <workflow-item name="item1" type="decision">
    <display-name>Check Approval</display-name>
  </workflow-item>
</workflow>""")

        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(workflow_xml)

        assert len(items) == 1
        item = items[0]

        # No crashes, just empty lists
        assert len(item.action_calls) == 0
        assert len(item.resolved_actions) == 0
        assert len(item.unresolved_actions) == 0
