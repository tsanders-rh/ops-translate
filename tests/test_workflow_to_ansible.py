"""Tests for vRO workflow graph to Ansible tasks converter."""

from pathlib import Path

import pytest

from ops_translate.generate.workflow_to_ansible import (
    AnsibleTask,
    _convert_action_call,
    _convert_decision_node,
    _convert_user_interaction,
    _convert_workflow_call,
    _detect_action_call,
    _detect_integration_type,
    _detect_workflow_call,
    _extract_decision_condition,
    _extract_workflow_name,
    _generate_approval_fail_message,
    _js_to_jinja,
    _sanitize_role_name,
    generate_ansible_yaml,
    workflow_to_ansible_tasks,
)
from ops_translate.models.profile import (
    ApprovalConfig,
    EnvironmentConfig,
    ProfileSchema,
)
from ops_translate.translate.vrealize_workflow import WorkflowItem


@pytest.fixture
def sample_workflow_file():
    """Path to sample workflow file."""
    return Path(__file__).parent.parent / "examples/vrealize/with-approval.workflow.xml"


@pytest.fixture
def simple_workflow_file():
    """Path to simple workflow file."""
    return Path(__file__).parent.parent / "examples/vrealize/simple-provision.workflow.xml"


@pytest.fixture
def sample_task_item():
    """Create a sample WorkflowItem for testing."""
    return WorkflowItem(
        name="item1",
        item_type="task",
        display_name="Check Governance",
        script='System.log("Hello"); var x = 5;',
        in_bindings=[],
        out_bindings=[],
        out_name="item2",
    )


@pytest.fixture
def sample_decision_item():
    """Create a sample decision WorkflowItem."""
    return WorkflowItem(
        name="item2",
        item_type="decision",
        display_name="Requires Approval?",
        script="return requiresApproval;",
        in_bindings=[
            {"name": "requiresApproval", "type": "boolean", "export_name": "requiresApproval"}
        ],
        out_bindings=[],
        out_name="item3",
    )


@pytest.fixture
def sample_interaction_item():
    """Create a sample UserInteraction WorkflowItem."""
    return WorkflowItem(
        name="item3",
        item_type="interaction",
        display_name="Request Approval",
        script=None,
        in_bindings=[],
        out_bindings=[],
        out_name="item4",
    )


def test_workflow_to_ansible_tasks_with_real_workflow(sample_workflow_file):
    """Test converting a real workflow file to Ansible tasks."""
    tasks = workflow_to_ansible_tasks(sample_workflow_file)

    # Should have tasks (not empty)
    assert len(tasks) > 0

    # All tasks should be AnsibleTask objects
    assert all(isinstance(task, AnsibleTask) for task in tasks)

    # Task names should be present
    assert all(task.name for task in tasks)

    # Modules should be present
    assert all(task.module for task in tasks)


def test_workflow_preserves_execution_order(sample_workflow_file):
    """Test that task order matches workflow graph order."""
    tasks = workflow_to_ansible_tasks(sample_workflow_file)

    task_names = [t.name for t in tasks]

    # Find index of governance and provision tasks
    # Governance should come before provisioning
    governance_indices = [i for i, name in enumerate(task_names) if "governance" in name.lower()]
    provision_indices = [i for i, name in enumerate(task_names) if "provision" in name.lower()]

    # If both exist, governance should come first
    if governance_indices and provision_indices:
        assert min(governance_indices) < min(provision_indices)


def test_decision_node_conversion(sample_decision_item):
    """Test Decision node creates debug task."""
    tasks = _convert_decision_node(sample_decision_item)

    assert len(tasks) == 1
    task = tasks[0]

    assert "Decision" in task.name
    assert task.module == "ansible.builtin.debug"
    assert "decision" in task.tags


def test_extract_decision_condition():
    """Test extracting condition from decision script."""
    # Simple return statement
    script1 = "return requiresApproval;"
    assert _extract_decision_condition(script1) == "requiresApproval"

    # Return with expression
    script2 = "return environment === 'prod';"
    assert _extract_decision_condition(script2) == "environment === 'prod'"

    # Multi-line script
    script3 = """
    var result = checkSomething();
    return result;
    """
    assert "result" in _extract_decision_condition(script3)


def test_user_interaction_default_fails(sample_interaction_item):
    """Test UserInteraction creates fail task without profile."""
    tasks = _convert_user_interaction(sample_interaction_item, profile=None)

    assert len(tasks) == 1
    task = tasks[0]

    assert "BLOCKED" in task.name
    assert task.module == "ansible.builtin.fail"
    assert "approval" in task.module_args["msg"].lower()
    assert "blocked" in task.tags


def test_user_interaction_with_servicenow_profile(sample_interaction_item):
    """Test UserInteraction with ServiceNow profile."""
    profile = ProfileSchema(
        name="test",
        environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
        approval=ApprovalConfig(model="servicenow_change"),
    )
    tasks = _convert_user_interaction(sample_interaction_item, profile)

    assert len(tasks) == 1
    task = tasks[0]

    assert "ServiceNow" in task.name
    assert task.module == "ansible.builtin.include_tasks"
    assert "adapters/servicenow" in task.module_args["file"]
    assert "servicenow" in task.tags


def test_user_interaction_with_aap_workflow_profile(sample_interaction_item):
    """Test UserInteraction with AAP workflow profile."""
    profile = ProfileSchema(
        name="test",
        environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
        approval=ApprovalConfig(model="aap_workflow"),
    )
    tasks = _convert_user_interaction(sample_interaction_item, profile)

    assert len(tasks) == 1
    task = tasks[0]

    assert "AAP" in task.name
    assert task.module == "ansible.builtin.pause"
    assert task.register == "approval_response"
    assert "aap" in task.tags


def test_user_interaction_with_pause_profile(sample_interaction_item):
    """Test UserInteraction with pause profile."""
    profile = ProfileSchema(
        name="test",
        environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
        approval=ApprovalConfig(model="manual_pause"),
    )
    tasks = _convert_user_interaction(sample_interaction_item, profile)

    assert len(tasks) == 1
    task = tasks[0]

    assert "Manual approval" in task.name
    assert task.module == "ansible.builtin.pause"
    assert "manual" in task.tags


def test_user_interaction_with_unknown_profile(sample_interaction_item):
    """Test UserInteraction with unknown approval model."""
    profile = ProfileSchema(
        name="test",
        environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
        approval=ApprovalConfig(model="blocked"),
    )
    tasks = _convert_user_interaction(sample_interaction_item, profile)

    assert len(tasks) == 1
    task = tasks[0]

    assert "BLOCKED" in task.name
    assert task.module == "ansible.builtin.fail"
    assert "blocked" in task.module_args["msg"].lower()


def test_generate_approval_fail_message(sample_interaction_item):
    """Test approval fail message generation."""
    msg = _generate_approval_fail_message(sample_interaction_item)

    assert "BLOCKED" in msg
    assert "approval" in msg.lower()
    assert "servicenow" in msg.lower()
    assert "aap_workflow" in msg.lower()
    assert "pause" in msg.lower()
    assert "profile.yml" in msg


def test_js_to_jinja_simple_equality():
    """Test JavaScript to Jinja2 conversion for simple equality."""
    assert _js_to_jinja("x === y") == "x == y"
    assert _js_to_jinja("x !== y") == "x != y"


def test_js_to_jinja_logical_operators():
    """Test JavaScript to Jinja2 conversion for logical operators."""
    assert _js_to_jinja("x && y") == "x  and  y"
    assert _js_to_jinja("x || y") == "x  or  y"


def test_js_to_jinja_negation():
    """Test JavaScript to Jinja2 conversion for negation."""
    result = _js_to_jinja("!requiresApproval")
    assert "not" in result
    assert "requiresApproval" in result


def test_js_to_jinja_complex_expression():
    """Test JavaScript to Jinja2 conversion for complex expression."""
    js = "environment === 'prod' && cpuCount > 16"
    jinja = _js_to_jinja(js)

    assert "==" in jinja
    assert " and " in jinja
    assert ">" in jinja


def test_generate_ansible_yaml_basic():
    """Test YAML generation from AnsibleTask objects."""
    tasks = [
        AnsibleTask(
            name="Test task",
            module="ansible.builtin.debug",
            module_args={"msg": "Hello"},
        )
    ]

    yaml_output = generate_ansible_yaml(tasks)

    assert "---" in yaml_output
    assert "name: Test task" in yaml_output
    assert "ansible.builtin.debug" in yaml_output
    assert "msg: Hello" in yaml_output


def test_generate_ansible_yaml_with_when():
    """Test YAML generation with conditional."""
    tasks = [
        AnsibleTask(
            name="Conditional task",
            module="ansible.builtin.debug",
            module_args={"msg": "Hello"},
            when="environment == 'prod'",
        )
    ]

    yaml_output = generate_ansible_yaml(tasks)

    assert "when: environment == 'prod'" in yaml_output


def test_generate_ansible_yaml_with_register():
    """Test YAML generation with register."""
    tasks = [
        AnsibleTask(
            name="Register task",
            module="ansible.builtin.command",
            module_args={"cmd": "echo hello"},
            register="result",
        )
    ]

    yaml_output = generate_ansible_yaml(tasks)

    assert "register: result" in yaml_output


def test_generate_ansible_yaml_with_tags():
    """Test YAML generation with tags."""
    tasks = [
        AnsibleTask(
            name="Tagged task",
            module="ansible.builtin.debug",
            module_args={"msg": "Hello"},
            tags=["test", "debug"],
        )
    ]

    yaml_output = generate_ansible_yaml(tasks)

    assert "tags:" in yaml_output
    assert "- test" in yaml_output or "test" in yaml_output


def test_generate_ansible_yaml_with_comments():
    """Test YAML generation with comments."""
    tasks = [
        AnsibleTask(
            name="Commented task",
            module="ansible.builtin.debug",
            module_args={"msg": "Hello"},
            comment="This is a test comment",
        )
    ]

    yaml_output = generate_ansible_yaml(tasks, include_comments=True)

    assert "# This is a test comment" in yaml_output


def test_generate_ansible_yaml_without_comments():
    """Test YAML generation without comments."""
    tasks = [
        AnsibleTask(
            name="Commented task",
            module="ansible.builtin.debug",
            module_args={"msg": "Hello"},
            comment="This is a test comment",
        )
    ]

    yaml_output = generate_ansible_yaml(tasks, include_comments=False)

    assert "# This is a test comment" not in yaml_output


def test_ansible_task_dataclass():
    """Test AnsibleTask dataclass creation."""
    task = AnsibleTask(
        name="Test",
        module="ansible.builtin.debug",
        module_args={"msg": "Hello"},
        when="true",
        register="result",
        comment="Test comment",
        tags=["test"],
    )

    assert task.name == "Test"
    assert task.module == "ansible.builtin.debug"
    assert task.module_args == {"msg": "Hello"}
    assert task.when == "true"
    assert task.register == "result"
    assert task.comment == "Test comment"
    assert task.tags == ["test"]


def test_ansible_task_dataclass_minimal():
    """Test AnsibleTask dataclass with minimal fields."""
    task = AnsibleTask(
        name="Minimal",
        module="ansible.builtin.debug",
        module_args={},
    )

    assert task.name == "Minimal"
    assert task.module == "ansible.builtin.debug"
    assert task.when is None
    assert task.register is None
    assert task.comment is None
    assert task.tags is None


def test_end_nodes_are_skipped(simple_workflow_file):
    """Test that end nodes are not converted to tasks."""
    tasks = workflow_to_ansible_tasks(simple_workflow_file)

    # No task should be named "end" or have "end" as the only content
    task_names_lower = [t.name.lower() for t in tasks]

    # Should not have tasks that are just "end" nodes
    assert "end" not in task_names_lower


def test_workflow_with_no_profile():
    """Test workflow conversion with no profile."""
    workflow_file = Path(__file__).parent.parent / "examples/vrealize/simple-provision.workflow.xml"

    tasks = workflow_to_ansible_tasks(workflow_file, profile=None)

    assert len(tasks) > 0
    assert all(isinstance(task, AnsibleTask) for task in tasks)


def test_workflow_with_profile():
    """Test workflow conversion with profile."""
    workflow_file = Path(__file__).parent.parent / "examples/vrealize/simple-provision.workflow.xml"
    profile = ProfileSchema(
        name="test",
        environments={"dev": EnvironmentConfig(openshift_api_url="https://test")},
        approval=ApprovalConfig(model="manual_pause"),
    )

    tasks = workflow_to_ansible_tasks(workflow_file, profile=profile)

    assert len(tasks) > 0
    assert all(isinstance(task, AnsibleTask) for task in tasks)


def test_detect_workflow_call():
    """Test detection of workflow calls in script."""
    # Test Server.getWorkflowWithId pattern
    script1 = """
    var workflow = Server.getWorkflowWithId("provision-vm");
    workflow.execute(inputs);
    """
    assert _detect_workflow_call(script1) is True

    # Test workflow.execute pattern
    script2 = "workflow.executeWorkflow('test-workflow');"
    assert _detect_workflow_call(script2) is True

    # Test no workflow call
    script3 = "System.log('Hello world');"
    assert _detect_workflow_call(script3) is False


def test_detect_action_call():
    """Test detection of action calls in script."""
    # Test System.getModule pattern
    script1 = """
    var module = System.getModule("com.vmware.library");
    var action = module.getAction("createVM");
    """
    assert _detect_action_call(script1) is True

    # Test NSXClient pattern
    script2 = "var client = new NSXClient(nsxHost);"
    assert _detect_action_call(script2) is True

    # Test RESTHost pattern
    script3 = "var rest = new RESTHost('https://api.example.com');"
    assert _detect_action_call(script3) is True

    # Test no action call
    script4 = "var x = 5; System.log(x);"
    assert _detect_action_call(script4) is False


def test_extract_workflow_name():
    """Test extraction of workflow name from script."""
    # Test getWorkflowWithId with double quotes
    script1 = 'var wf = Server.getWorkflowWithId("provision-vm");'
    assert _extract_workflow_name(script1) == "provision-vm"

    # Test getWorkflowWithId with single quotes
    script2 = "var wf = Server.getWorkflowWithId('my-workflow');"
    assert _extract_workflow_name(script2) == "my-workflow"

    # Test executeWorkflow pattern
    script3 = 'executeWorkflow("test-workflow", params);'
    assert _extract_workflow_name(script3) == "test-workflow"

    # Test no match
    script4 = "System.log('hello');"
    assert _extract_workflow_name(script4) is None


def test_sanitize_role_name():
    """Test role name sanitization."""
    # Test with hyphens
    assert _sanitize_role_name("provision-vm") == "provision_vm"

    # Test with spaces
    assert _sanitize_role_name("Provision VM") == "provision_vm"

    # Test with special characters
    assert _sanitize_role_name("vm/provision@prod") == "vm_provision_prod"

    # Test with multiple special chars
    assert _sanitize_role_name("VM--Provision__Test") == "vm_provision_test"

    # Test already clean
    assert _sanitize_role_name("clean_role_name") == "clean_role_name"


def test_detect_integration_type():
    """Test detection of integration type from script."""
    # NSX integration
    script1 = "var client = new NSXClient(host);"
    assert _detect_integration_type(script1) == "nsx"

    # ServiceNow integration
    script2 = "var snow = new ServiceNowClient();"
    assert _detect_integration_type(script2) == "servicenow"

    # Infoblox integration
    script3 = "var ipam = new InfobloxClient(server);"
    assert _detect_integration_type(script3) == "infoblox"

    # REST integration
    script4 = "var rest = new RESTHost('https://api.example.com');"
    assert _detect_integration_type(script4) == "rest"

    # Active Directory
    script5 = "var ad = AD:getUserByName(username);"
    assert _detect_integration_type(script5) == "ad"

    # No integration
    script6 = "System.log('Hello world');"
    assert _detect_integration_type(script6) is None


def test_convert_workflow_call():
    """Test conversion of workflow call to include_role."""
    item = WorkflowItem(
        name="item1",
        item_type="task",
        display_name="Call Provision Workflow",
        script='var wf = Server.getWorkflowWithId("provision-vm");\nwf.execute();',
        in_bindings=[],
        out_bindings=[],
        out_name="item2",
    )

    tasks = _convert_workflow_call(item)

    assert len(tasks) == 1
    task = tasks[0]

    assert "Execute workflow" in task.name
    assert task.module == "ansible.builtin.include_role"
    assert "provision_vm" in task.module_args["name"]
    assert "workflow_call" in task.tags


def test_convert_workflow_call_without_name():
    """Test conversion of workflow call when name cannot be extracted."""
    item = WorkflowItem(
        name="item1",
        item_type="task",
        display_name="Call Workflow",
        script="var wf = getWorkflow(); wf.execute();",
        in_bindings=[],
        out_bindings=[],
        out_name="item2",
    )

    tasks = _convert_workflow_call(item)

    assert len(tasks) == 1
    task = tasks[0]

    assert "TODO" in task.name
    assert task.module == "ansible.builtin.debug"
    assert "workflow_call" in task.tags


def test_convert_action_call_with_integration():
    """Test conversion of action call with detected integration."""
    item = WorkflowItem(
        name="item1",
        item_type="task",
        display_name="Call NSX API",
        script="var client = new NSXClient(host);\nclient.createSegment(name);",
        in_bindings=[],
        out_bindings=[],
        out_name="item2",
    )

    tasks = _convert_action_call(item, profile=None)

    assert len(tasks) == 1
    task = tasks[0]

    assert "adapter" in task.name.lower()
    assert task.module == "ansible.builtin.include_tasks"
    assert "nsx" in task.module_args["file"]
    assert "action_call" in task.tags
    assert "nsx" in task.tags


def test_convert_action_call_without_integration():
    """Test conversion of action call without detected integration."""
    item = WorkflowItem(
        name="item1",
        item_type="task",
        display_name="Call Action",
        script="var action = System.getModule('test').getAction('doSomething');",
        in_bindings=[],
        out_bindings=[],
        out_name="item2",
    )

    tasks = _convert_action_call(item, profile=None)

    assert len(tasks) == 1
    task = tasks[0]

    assert "TODO" in task.name
    assert task.module == "ansible.builtin.debug"
    assert "action_call" in task.tags
