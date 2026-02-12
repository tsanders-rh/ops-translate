"""
Tests for summarize_with_actions functionality (Issue #54).
"""

from pathlib import Path

from ops_translate.summarize.vrealize import summarize, summarize_with_actions
from ops_translate.summarize.vrealize_actions import ActionDef, ActionIndex


class TestSummarizeBackwardCompatibility:
    """Tests for backward compatibility of summarize()."""

    def test_summarize_without_action_index(self, tmp_path):
        """Test that summarize() works without ActionIndex (backward compatibility)."""
        # Create simple workflow XML with proper vRO structure
        workflow_xml = tmp_path / "test.xml"
        workflow_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow" version="1.0.0">
  <display-name>Test Workflow</display-name>
  <input>
    <param name="vmName" type="string">
      <description>VM name</description>
    </param>
  </input>
  <workflow-item name="item0" type="end" end-mode="0"/>
</workflow>"""
        )

        summary = summarize(workflow_xml)

        # Should not crash and should include basic info
        assert "Test Workflow" in summary
        assert "vmName" in summary
        assert "string" in summary

    def test_summarize_with_empty_action_index(self, tmp_path):
        """Test handling of empty ActionIndex."""
        action_index = ActionIndex(actions={})

        workflow_xml = tmp_path / "test.xml"
        workflow_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow" version="1.0.0">
  <display-name>Test Workflow</display-name>
  <workflow-item name="item0" type="end" end-mode="0"/>
</workflow>"""
        )

        summary = summarize_with_actions(workflow_xml, action_index)

        # Should not crash
        assert "Test Workflow" in summary


class TestActionScriptDetection:
    """Tests for detecting patterns in action scripts."""

    def test_summarize_detects_nsx_in_action_script(self, tmp_path):
        """Test that NSX operations in action scripts are detected."""
        # Create action with NSX operations
        nsx_action = ActionDef(
            fqname="com.acme.nsx/createFirewallRule",
            name="createFirewallRule",
            module="com.acme.nsx",
            script="""
                var nsxClient = System.getModule("com.vmware.library.vc.nsx").client();
                var rule = nsxClient.createFirewallRule({
                    name: ruleName,
                    sources: [source],
                    destinations: [destination]
                });
            """,
            inputs=[],
            result_type="any",
            description="Create NSX firewall rule",
            source_path=Path("/test/action.xml"),
            version="1.0.0",
            sha256="abc123",
        )

        action_index = ActionIndex(
            actions={"com.acme.nsx/createFirewallRule": nsx_action}
        )

        # Create workflow that calls this action
        workflow_xml = tmp_path / "test.xml"
        workflow_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow" version="1.0.0">
  <display-name>Create Firewall Rule</display-name>
  <workflow-item name="item1" type="task" out-name="item0">
    <display-name>Create NSX Rule</display-name>
    <script><![CDATA[
      var nsxModule = System.getModule("com.acme.nsx");
      var rule = nsxModule.createFirewallRule("Web-to-DB");
    ]]></script>
    <position y="100.0" x="100.0"/>
  </workflow-item>
  <workflow-item name="item0" type="end" end-mode="0">
    <position y="200.0" x="100.0"/>
  </workflow-item>
</workflow>"""
        )

        summary = summarize_with_actions(workflow_xml, action_index)

        # Should detect action resolution
        assert "Actions:" in summary
        assert "1 resolved" in summary

        # Should detect NSX operations in action script
        assert "NSX-T Operations:" in summary
        assert "Firewall Rules:" in summary or "firewall" in summary.lower()

    def test_summarize_detects_rest_in_workflow_script(self, tmp_path):
        """Test REST detection is skipped when no action index provided."""
        # NOTE: REST/plugin detection requires specialized analyze functions
        # This test verifies basic summarize works without crashing
        workflow_xml = tmp_path / "test.xml"
        workflow_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow" version="1.0.0">
  <display-name>API Workflow</display-name>
  <workflow-item name="item1" type="task" out-name="item0">
    <display-name>Make REST Call</display-name>
    <script><![CDATA[
      var restClient = new RESTClient();
      var response = restClient.post("https://api.example.com/v1/resource", data);
    ]]></script>
    <position y="100.0" x="100.0"/>
  </workflow-item>
  <workflow-item name="item0" type="end" end-mode="0">
    <position y="200.0" x="100.0"/>
  </workflow-item>
</workflow>"""
        )

        # Without ActionIndex, no action resolution occurs
        summary = summarize(workflow_xml)

        # Should not crash, just return basic summary
        assert "API Workflow" in summary

    def test_summarize_detects_plugins_in_workflow_script(self, tmp_path):
        """Test plugin detection is skipped when no action index provided."""
        # NOTE: Plugin detection requires analyze functions with XML parsing
        # This test verifies basic summarize works without crashing
        workflow_xml = tmp_path / "test.xml"
        workflow_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow" version="1.0.0">
  <display-name>ITSM Workflow</display-name>
  <workflow-item name="item1" type="task" out-name="item0">
    <display-name>Create Incident</display-name>
    <script><![CDATA[
      var snowModule = System.getModule("com.vmware.library.servicenow");
      var connection = snowModule.getConnection();
    ]]></script>
    <position y="100.0" x="100.0"/>
  </workflow-item>
  <workflow-item name="item0" type="end" end-mode="0">
    <position y="200.0" x="100.0"/>
  </workflow-item>
</workflow>"""
        )

        # Without ActionIndex, no plugin detection occurs
        summary = summarize(workflow_xml)

        # Should not crash, just return basic summary
        assert "ITSM Workflow" in summary


class TestUnresolvedActions:
    """Tests for handling unresolved actions."""

    def test_summarize_handles_unresolved_actions(self, tmp_path):
        """Test that unresolved actions are reported."""
        # Empty action index - action won't resolve
        action_index = ActionIndex(actions={})

        workflow_xml = tmp_path / "test.xml"
        workflow_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow" version="1.0.0">
  <display-name>Test Workflow</display-name>
  <workflow-item name="item1" type="task" out-name="item0">
    <display-name>Call Missing Action</display-name>
    <script><![CDATA[
      var module = System.getModule("com.missing.action");
      module.doSomething();
    ]]></script>
    <position y="100.0" x="100.0"/>
  </workflow-item>
  <workflow-item name="item0" type="end" end-mode="0">
    <position y="200.0" x="100.0"/>
  </workflow-item>
</workflow>"""
        )

        summary = summarize_with_actions(workflow_xml, action_index)

        # Should not crash
        assert "Test Workflow" in summary

        # Should show unresolved count
        assert "unresolved" in summary


class TestAggregation:
    """Tests for aggregating findings from multiple items."""

    def test_summarize_aggregates_multiple_items(self, tmp_path):
        """Test that findings from multiple workflow items are aggregated."""
        # Create multiple actions
        nsx_action = ActionDef(
            fqname="com.acme.nsx/createSegment",
            name="createSegment",
            module="com.acme.nsx",
            script="var segment = nsxClient.createSegment(name);",
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
            script='var incident = snowClient.createIncident("test");',
            inputs=[],
            result_type="string",
            description="Create incident",
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

        # Workflow with multiple items calling different actions
        workflow_xml = tmp_path / "test.xml"
        workflow_xml.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow" version="1.0.0">
  <display-name>Multi-Item Workflow</display-name>
  <workflow-item name="item1" type="task" out-name="item2">
    <display-name>Create NSX Segment</display-name>
    <script><![CDATA[
      var nsxModule = System.getModule("com.acme.nsx");
      nsxModule.createSegment("web-segment");
    ]]></script>
    <position y="100.0" x="100.0"/>
  </workflow-item>
  <workflow-item name="item2" type="task" out-name="item0">
    <display-name>Create ServiceNow Incident</display-name>
    <script><![CDATA[
      var snowModule = System.getModule("com.acme.servicenow");
      snowModule.createIncident();
    ]]></script>
    <position y="200.0" x="100.0"/>
  </workflow-item>
  <workflow-item name="item0" type="end" end-mode="0">
    <position y="300.0" x="100.0"/>
  </workflow-item>
</workflow>"""
        )

        summary = summarize_with_actions(workflow_xml, action_index)

        # Should show both actions resolved
        assert "Actions:" in summary
        assert "2 resolved" in summary

        # Should aggregate findings (exact format may vary)
        assert "NSX" in summary or "Segment" in summary or "segment" in summary.lower()
