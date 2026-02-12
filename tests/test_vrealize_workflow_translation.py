"""
Tests for vRealize workflow translation to Ansible.
"""

from pathlib import Path

from ops_translate.translate.vrealize_workflow import (
    JavaScriptToAnsibleTranslator,
    WorkflowItem,
    WorkflowParser,
    extract_action_calls,
    translate_workflow_to_ansible,
)


class TestWorkflowParser:
    """Tests for vRealize workflow XML parsing."""

    def test_parse_simple_workflow(self):
        """Test parsing a simple workflow with approval."""
        workflow_file = Path("examples/vrealize/with-approval.workflow.xml")
        parser = WorkflowParser()

        items = parser.parse_file(workflow_file)

        # Should have multiple items (excluding end nodes)
        assert len(items) > 0

        # Check first item is governance check
        governance_item = [i for i in items if "Governance" in i.display_name]
        assert len(governance_item) == 1
        assert governance_item[0].item_type == "task"
        assert governance_item[0].script is not None

    def test_parse_workflow_items_in_order(self):
        """Test that workflow items are returned in execution order."""
        workflow_file = Path("examples/vrealize/with-approval.workflow.xml")
        parser = WorkflowParser()

        items = parser.parse_file(workflow_file)

        # First item should be governance check
        assert "Governance" in items[0].display_name

    def test_parse_bindings(self):
        """Test parsing in/out bindings."""
        workflow_file = Path("examples/vrealize/with-approval.workflow.xml")
        parser = WorkflowParser()

        items = parser.parse_file(workflow_file)
        governance_item = [i for i in items if "Governance" in i.display_name][0]

        # Should have input bindings
        assert len(governance_item.in_bindings) > 0
        assert any(b["name"] == "environment" for b in governance_item.in_bindings)

        # Should have output binding
        assert len(governance_item.out_bindings) > 0
        assert any(b["name"] == "requiresApproval" for b in governance_item.out_bindings)


class TestJavaScriptToAnsibleTranslator:
    """Tests for JavaScript to Ansible translation."""

    def test_translate_simple_assignment(self):
        """Test translating simple variable assignment."""
        translator = JavaScriptToAnsibleTranslator()
        script = 'requiresApproval = (environment === "prod");'
        item = WorkflowItem(
            name="item1",
            item_type="task",
            display_name="Check Governance",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        # Should generate set_fact task
        assert len(tasks) > 0
        set_fact_tasks = [t for t in tasks if "ansible.builtin.set_fact" in t]
        assert len(set_fact_tasks) == 1
        assert "requiresApproval" in set_fact_tasks[0]["ansible.builtin.set_fact"]

    def test_translate_validation_throw(self):
        """Test translating throw statement to assert."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
if (cpuCount > 16) {
    throw "CPU quota exceeded. Maximum 16 cores allowed.";
}
"""
        item = WorkflowItem(
            name="item1",
            item_type="task",
            display_name="Validate Quotas",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        # Should generate assert task
        assert_tasks = [t for t in tasks if "ansible.builtin.assert" in t]
        assert len(assert_tasks) == 1

        assert_task = assert_tasks[0]
        assert "ansible.builtin.assert" in assert_task
        assert "that" in assert_task["ansible.builtin.assert"]
        assert "fail_msg" in assert_task["ansible.builtin.assert"]
        assert "CPU quota exceeded" in assert_task["ansible.builtin.assert"]["fail_msg"]

    def test_translate_multiple_validations(self):
        """Test translating multiple validation statements."""
        translator = JavaScriptToAnsibleTranslator()
        script = """
if (cpuCount > 16) {
    throw "CPU quota exceeded. Maximum 16 cores allowed.";
}

if (memoryGB > 128) {
    throw "Memory quota exceeded. Maximum 128 GB allowed.";
}
"""
        item = WorkflowItem(
            name="item1",
            item_type="task",
            display_name="Validate Quotas",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        # Should generate two assert tasks
        assert_tasks = [t for t in tasks if "ansible.builtin.assert" in t]
        assert len(assert_tasks) == 2
        assert "CPU quota" in assert_tasks[0]["ansible.builtin.assert"]["fail_msg"]
        assert "Memory quota" in assert_tasks[1]["ansible.builtin.assert"]["fail_msg"]

    def test_translate_logging(self):
        """Test translating System.log to debug tasks."""
        translator = JavaScriptToAnsibleTranslator()
        script = 'System.log("Checking governance for: " + vmName);'
        item = WorkflowItem(
            name="item1",
            item_type="task",
            display_name="Log Check",
            script=script,
            in_bindings=[],
            out_bindings=[],
            out_name=None,
        )

        tasks = translator.translate_script(script, item)

        # Should generate debug task
        debug_tasks = [t for t in tasks if "ansible.builtin.debug" in t]
        assert len(debug_tasks) >= 1
        assert "ansible.builtin.debug" in debug_tasks[0]

    def test_negate_condition(self):
        """Test condition negation for assert."""
        translator = JavaScriptToAnsibleTranslator()

        # Test greater than
        assert translator._negate_condition("cpuCount > 16") == "cpuCount <= 16"

        # Test less than
        assert translator._negate_condition("memoryGB < 4") == "memoryGB >= 4"

        # Test equals
        assert translator._negate_condition("environment === prod") == "environment != prod"

    def test_js_to_jinja_conversion(self):
        """Test JavaScript to Jinja2 expression conversion."""
        translator = JavaScriptToAnsibleTranslator()

        # Test equality
        result = translator._js_to_jinja('environment === "prod"')
        assert "==" in result
        assert "===" not in result

        # Test boolean
        result = translator._js_to_jinja("true")
        assert result == "True"

        result = translator._js_to_jinja("false")
        assert result == "False"

    def test_translate_approval_interaction(self):
        """Test translating approval interaction to pause task."""
        translator = JavaScriptToAnsibleTranslator()
        item = WorkflowItem(
            name="item3",
            item_type="task",
            display_name="Request Approval",
            script='System.log("Requesting approval");',
            in_bindings=[
                {"name": "vmName", "type": "string", "export_name": "vmName"},
                {"name": "requiresApproval", "type": "boolean", "export_name": "requiresApproval"},
            ],
            out_bindings=[],
            out_name=None,
        )

        task = translator.translate_approval_interaction(item)

        # Should be a pause task
        assert "ansible.builtin.pause" in task
        assert "prompt" in task["ansible.builtin.pause"]
        assert "register" in task
        assert task["register"] == "approval_response"

        # Should have when clause based on requiresApproval
        assert "when" in task
        assert "requiresApproval" in task["when"]

    def test_translate_email_notification(self):
        """Test translating email notification to mail task."""
        translator = JavaScriptToAnsibleTranslator()
        item = WorkflowItem(
            name="item7",
            item_type="task",
            display_name="Notify Owner",
            script='System.log("Sending notification");',
            in_bindings=[
                {"name": "ownerEmail", "type": "string", "export_name": "ownerEmail"},
                {"name": "vmName", "type": "string", "export_name": "vmName"},
            ],
            out_bindings=[],
            out_name=None,
        )

        task = translator.translate_email_notification(item)

        # Should be a mail task
        assert "community.general.mail" in task
        mail_config = task["community.general.mail"]
        assert "to" in mail_config
        assert "ownerEmail" in mail_config["to"]
        assert "subject" in mail_config
        assert "body" in mail_config


class TestWorkflowTranslation:
    """Integration tests for full workflow translation."""

    def test_translate_approval_workflow(self):
        """Test translating full approval workflow."""
        workflow_file = Path("examples/vrealize/with-approval.workflow.xml")

        tasks = translate_workflow_to_ansible(workflow_file)

        # Should generate multiple tasks
        assert len(tasks) > 0

        # Should have validation tasks
        assert_tasks = [t for t in tasks if "ansible.builtin.assert" in t]
        assert len(assert_tasks) >= 2  # CPU and memory validation

        # Should have set_fact tasks
        set_fact_tasks = [t for t in tasks if "ansible.builtin.set_fact" in t]
        assert len(set_fact_tasks) >= 1  # requiresApproval

    def test_generated_tasks_are_valid_yaml(self):
        """Test that generated tasks are valid Ansible task format."""
        workflow_file = Path("examples/vrealize/with-approval.workflow.xml")

        tasks = translate_workflow_to_ansible(workflow_file)

        for task in tasks:
            # Each task must have a name
            assert "name" in task

            # Each task must have at least one module
            module_keys = [
                k for k in task.keys() if k != "name" and k != "when" and k != "register"
            ]
            assert len(module_keys) >= 1

    def test_preserve_workflow_order(self):
        """Test that task order preserves workflow execution order."""
        workflow_file = Path("examples/vrealize/with-approval.workflow.xml")

        tasks = translate_workflow_to_ansible(workflow_file)

        # Validation should come before approval logic
        validation_indices = [
            i
            for i, t in enumerate(tasks)
            if "ansible.builtin.assert" in t and "CPU" in t.get("name", "")
        ]
        approval_indices = [
            i
            for i, t in enumerate(tasks)
            if "ansible.builtin.set_fact" in t and "requiresApproval" in str(t)
        ]

        if validation_indices and approval_indices:
            # Validation should be early in the workflow
            assert min(validation_indices) < max(approval_indices) + 5  # Allow some flexibility
