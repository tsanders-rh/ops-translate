"""
Tests for vRO integration call detection and translation.

Validates the trust-first, mapping-driven approach to translating
vRO integration calls (ServiceNow, REST, etc.) to Ansible modules.
"""

from ops_translate.translate.vrealize_workflow import (
    JavaScriptToAnsibleTranslator,
    WorkflowItem,
)


class TestIntegrationMappingLoader:
    """Tests for loading integration mappings."""

    def test_mapping_file_exists(self):
        """Test that the integration mappings file exists."""
        translator = JavaScriptToAnsibleTranslator()
        assert translator.integration_mappings is not None

    def test_mappings_have_required_structure(self):
        """Test that mappings have the required structure."""
        translator = JavaScriptToAnsibleTranslator()

        if not translator.integration_mappings:
            # If file doesn't exist, skip
            return

        # Check structure of first mapping
        for integration_name, methods in translator.integration_mappings.items():
            for method_name, mapping in methods.items():
                # Must have match config
                assert "match" in mapping

                # Must have ansible config
                assert "ansible" in mapping
                assert "module" in mapping["ansible"]
                assert "params" in mapping["ansible"]

                # Must have severity
                assert "severity" in mapping
                break  # Just check one
            break


class TestFalsePositivePrevention:
    """Tests to ensure we DON'T match common JavaScript patterns."""

    def test_does_not_match_system_log(self):
        """System.log() should NOT be detected as integration call."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
System.log("Starting workflow");
System.log("VM name: " + vmName);
System.log("Environment: " + environment);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        # Should return 0 integration tasks (System.log is handled by _extract_logging)
        integration_tasks = translator._detect_integration_calls(script, item)
        assert len(integration_tasks) == 0

    def test_does_not_match_math_operations(self):
        """Math.* methods should NOT be detected as integration calls."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var result = Math.max(a, b);
var rounded = Math.round(value);
var sqrt = Math.sqrt(number);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)
        assert len(integration_tasks) == 0

    def test_does_not_match_vcenter_sdk_calls(self):
        """vCenter SDK calls should NOT be detected as integration calls."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
vm.powerOffVM_Task();
vm.startVM();
vm.rebootVM();
host.enterMaintenanceMode();
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)
        assert len(integration_tasks) == 0

    def test_does_not_match_generic_object_methods(self):
        """Generic object method calls should NOT be detected."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var result = myObject.getData();
var status = workflow.getState();
var config = environment.getConfig();
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)
        assert len(integration_tasks) == 0


class TestPositiveIntegrationDetection:
    """Tests for detecting actual integration calls."""

    def test_detects_servicenow_create_incident(self):
        """ServiceNow.createIncident() should be detected and translated."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var incident = ServiceNow.createIncident(
    "VM provisioning failed",
    "Failed to provision VM: " + vmName,
    "3"
);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Create ServiceNow Incident",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)

        # Should detect ServiceNow integration
        assert len(integration_tasks) == 1

        task = integration_tasks[0]
        assert "ServiceNow" in task["name"] or "DECISION REQUIRED" in task["name"]

        # Should generate DECISION REQUIRED stub (requires profile keys)
        assert "DECISION REQUIRED" in task["name"]
        assert "ansible.builtin.fail" in task
        assert "profile.itsm.servicenow" in task["ansible.builtin.fail"]["msg"]

    def test_detects_rest_host_operation(self):
        """RESTHost usage should be detected and translated to uri module."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var restHost = new RESTHost("api.example.com");
var request = restHost.createRequest("POST", "/api/v1/resources");
request.setHeader("Content-Type", "application/json");
var response = request.execute();
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Call REST API",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)

        # Should detect REST integration
        assert len(integration_tasks) >= 1

        # Check if any task mentions REST or uri
        has_rest_task = any(
            "Rest" in task["name"] or "DECISION REQUIRED" in task["name"]
            for task in integration_tasks
        )
        assert has_rest_task

    def test_detects_infoblox_get_next_ip(self):
        """Infoblox.getNextAvailableIP() should be detected."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var nextIP = Infoblox.getNextAvailableIP(network);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Get Next IP",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)

        # Should detect Infoblox integration
        assert len(integration_tasks) == 1
        task = integration_tasks[0]
        assert "Infoblox" in task["name"] or "DECISION REQUIRED" in task["name"]

    def test_detects_active_directory_create_user(self):
        """ActiveDirectory.createUser() should be detected."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var user = ActiveDirectory.createUser(username, password, email, groups);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Create AD User",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)

        # Should detect ActiveDirectory integration
        assert len(integration_tasks) == 1
        task = integration_tasks[0]
        assert "Activedirectory" in task["name"] or "DECISION REQUIRED" in task["name"]


class TestArgumentSubstitution:
    """Tests for argument parsing and substitution."""

    def test_parse_simple_args(self):
        """Test parsing simple comma-separated arguments."""
        translator = JavaScriptToAnsibleTranslator()

        args_str = '"title", "description", "priority"'
        parsed = translator._parse_args(args_str)

        assert len(parsed) == 3
        assert '"title"' in parsed[0]
        assert '"description"' in parsed[1]
        assert '"priority"' in parsed[2]

    def test_parse_args_with_variables(self):
        """Test parsing arguments with variable names."""
        translator = JavaScriptToAnsibleTranslator()

        args_str = "vmName, environment, priority"
        parsed = translator._parse_args(args_str)

        assert len(parsed) == 3
        assert "vmName" in parsed[0]
        assert "environment" in parsed[1]
        assert "priority" in parsed[2]

    def test_substitute_params(self):
        """Test parameter substitution."""
        translator = JavaScriptToAnsibleTranslator()

        params = {
            "short_description": "{arg0}",
            "description": "{arg1}",
            "priority": "{arg2}",
        }

        args = ['"VM failed"', '"Error details"', '"3"']

        result = translator._substitute_params(params, args)

        assert result["short_description"] == "VM failed"
        assert result["description"] == "Error details"
        assert result["priority"] == "3"


class TestDecisionRequiredStubs:
    """Tests for DECISION REQUIRED stub generation."""

    def test_generates_stub_with_profile_requirements(self):
        """Test that stubs include required profile keys."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var incident = ServiceNow.createIncident("Title", "Description", "3");
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Create Incident",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)

        assert len(integration_tasks) == 1
        task = integration_tasks[0]

        # Should be a DECISION REQUIRED stub
        assert "DECISION REQUIRED" in task["name"]
        assert "ansible.builtin.fail" in task

        # Should mention profile keys
        msg = task["ansible.builtin.fail"]["msg"]
        assert "profile.itsm.servicenow" in msg
        assert "Evidence:" in msg
        assert "Action required:" in msg

    def test_stub_includes_evidence(self):
        """Test that stubs include evidence of the detected call."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var result = Infoblox.getNextAvailableIP(network);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Get IP Address",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)

        assert len(integration_tasks) == 1
        task = integration_tasks[0]

        msg = task["ansible.builtin.fail"]["msg"]
        # Should include the actual detected call or display name
        assert "Get IP Address" in msg or "Infoblox.getNextAvailableIP" in msg

    def test_stub_has_integration_tags(self):
        """Test that stubs include appropriate tags."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
var user = ActiveDirectory.createUser(username, password, email, groups);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Create User",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        integration_tasks = translator._detect_integration_calls(script, item)

        assert len(integration_tasks) == 1
        task = integration_tasks[0]

        # Should have tags
        assert "tags" in task
        assert "decision_required" in task["tags"]
        assert "integration" in task["tags"]


class TestTaskStability:
    """Tests for stable, predictable task generation."""

    def test_multiple_runs_produce_same_output(self):
        """Test that translating the same script produces consistent results."""
        script = """
var incident = ServiceNow.createIncident("Title", "Desc", "3");
var nextIP = Infoblox.getNextAvailableIP(network);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Multiple Integrations",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        # Run translation twice
        translator1 = JavaScriptToAnsibleTranslator()
        tasks1 = translator1._detect_integration_calls(script, item)

        translator2 = JavaScriptToAnsibleTranslator()
        tasks2 = translator2._detect_integration_calls(script, item)

        # Should produce same number of tasks
        assert len(tasks1) == len(tasks2)

        # Task names should be the same
        names1 = [t["name"] for t in tasks1]
        names2 = [t["name"] for t in tasks2]
        assert names1 == names2

    def test_task_ordering_is_stable(self):
        """Test that tasks are generated in a stable order."""
        script = """
ServiceNow.createIncident("A", "B", "C");
Infoblox.getNextAvailableIP(network);
ActiveDirectory.createUser(user, pass, email, groups);
"""
        item = WorkflowItem(
            name="test",
            item_type="task",
            display_name="Test",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        translator = JavaScriptToAnsibleTranslator()
        tasks = translator._detect_integration_calls(script, item)

        # Should detect all three (order matters)
        assert len(tasks) == 3

        # Order should match script order (ServiceNow first, then Infoblox, then AD)
        assert "Servicenow" in tasks[0]["name"]
        assert "Infoblox" in tasks[1]["name"]
        assert "Activedirectory" in tasks[2]["name"]
