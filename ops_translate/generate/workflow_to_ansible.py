"""
vRO workflow graph to Ansible tasks converter.

Translates vRealize Orchestrator workflow graphs into Ansible tasks,
preserving execution order, branching logic, and approval gates.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ops_translate.translate.vrealize_workflow import (
    JavaScriptToAnsibleTranslator,
    WorkflowItem,
    WorkflowParser,
)


@dataclass
class AnsibleTask:
    """Represents an Ansible task."""

    name: str
    module: str
    module_args: dict[str, Any]
    when: str | None = None
    register: str | None = None
    comment: str | None = None
    tags: list[str] | None = None


def workflow_to_ansible_tasks(
    workflow_file: Path,
    profile: dict | None = None,
    locking_backend: str = "redis",
    locking_enabled: bool = True,
) -> list[AnsibleTask]:
    """
    Convert vRO workflow graph to Ansible tasks.

    Args:
        workflow_file: Path to workflow XML
        profile: Profile configuration for adapter mapping
        locking_backend: Backend for distributed locking
        locking_enabled: Whether to generate locking tasks

    Returns:
        List of AnsibleTask objects in execution order

    Example:
        >>> tasks = workflow_to_ansible_tasks(Path("workflow.xml"))
        >>> for task in tasks:
        ...     print(task.name)
    """
    # Parse workflow items
    parser = WorkflowParser()
    items = parser.parse_file(workflow_file)

    # Items are already sorted by execution order in the parser
    # Convert each item to tasks
    tasks = []
    for item in items:
        item_tasks = _convert_item_to_tasks(item, profile, locking_backend, locking_enabled)
        tasks.extend(item_tasks)

    return tasks


def _convert_item_to_tasks(
    item: WorkflowItem,
    profile: dict | None,
    locking_backend: str,
    locking_enabled: bool,
) -> list[AnsibleTask]:
    """
    Convert single workflow item to Ansible tasks.

    Args:
        item: WorkflowItem to convert
        profile: Profile configuration
        locking_backend: Locking backend
        locking_enabled: Whether locking is enabled

    Returns:
        List of AnsibleTask objects
    """
    # Skip end nodes
    if item.item_type == "end":
        return []

    # ScriptableTask (most common)
    if item.item_type == "task" and item.script:
        return _convert_scriptable_task(item, profile, locking_backend, locking_enabled)

    # Decision node
    if item.item_type == "decision":
        return _convert_decision_node(item)

    # UserInteraction / approval
    if item.item_type == "interaction":
        return _convert_user_interaction(item, profile)

    # WorkflowCall - detect calls to other workflows
    if item.script and _detect_workflow_call(item.script):
        return _convert_workflow_call(item)

    # ActionCall - detect calls to actions/integrations
    if item.script and _detect_action_call(item.script):
        return _convert_action_call(item, profile)

    # Email notification
    if item.item_type == "email":
        return _convert_email_notification(item)

    # Default: placeholder for unknown types
    return [
        AnsibleTask(
            name=f"TODO: {item.display_name}",
            module="ansible.builtin.debug",
            module_args={"msg": f"Workflow item '{item.display_name}' (type: {item.item_type})"},
            comment=f"Workflow item: {item.name}\nType: {item.item_type}",
            tags=["todo"],
        )
    ]


def _convert_scriptable_task(
    item: WorkflowItem,
    profile: dict | None,
    locking_backend: str,
    locking_enabled: bool,
) -> list[AnsibleTask]:
    """
    Convert ScriptableTask to Ansible tasks.

    Uses the existing JavaScriptToAnsibleTranslator to convert scripts.

    Args:
        item: WorkflowItem with script
        profile: Profile configuration
        locking_backend: Locking backend
        locking_enabled: Whether locking is enabled

    Returns:
        List of AnsibleTask objects
    """
    # Use existing translator
    translator = JavaScriptToAnsibleTranslator(locking_backend, locking_enabled)

    # Translate the script to Ansible tasks
    ansible_tasks = translator.translate_script(item.script, item)

    # Convert to AnsibleTask objects
    tasks = []
    for task_dict in ansible_tasks:
        # Extract task components
        name = task_dict.get("name", item.display_name)

        # Find the module (first key that's not 'name', 'when', 'register', etc.)
        module = None
        module_args = {}

        for key, value in task_dict.items():
            if key in ["name", "when", "register", "tags", "block", "rescue", "always"]:
                continue
            # This is the module
            module = key
            module_args = value if isinstance(value, dict) else {}
            break

        if not module:
            # Default to debug if no module found
            module = "ansible.builtin.debug"
            module_args = {"msg": f"Task: {name}"}

        # Create AnsibleTask
        ansible_task = AnsibleTask(
            name=name,
            module=module,
            module_args=module_args,
            when=task_dict.get("when"),
            register=task_dict.get("register"),
            comment=f"From workflow item: {item.display_name}",
            tags=task_dict.get("tags"),
        )

        tasks.append(ansible_task)

    return tasks


def _convert_decision_node(item: WorkflowItem) -> list[AnsibleTask]:
    """
    Convert Decision node to conditional block.

    Decision nodes create branching in the workflow. We emit a debug task
    showing the condition evaluation.

    Args:
        item: WorkflowItem of type 'decision'

    Returns:
        List with debug task showing the decision logic
    """
    # Extract condition from script
    condition = _extract_decision_condition(item.script) if item.script else "unknown"

    return [
        AnsibleTask(
            name=f"Decision: {item.display_name}",
            module="ansible.builtin.debug",
            module_args={"msg": f"Evaluating decision - Condition: {condition}"},
            comment=(
                f"Decision node: {item.name}\n"
                f"Condition: {condition}\n"
                f"True path: {item.out_name}\n"
                "Note: Branching is determined by workflow graph, not runtime condition"
            ),
            tags=["decision"],
        )
    ]


def _extract_decision_condition(script: str) -> str:
    """
    Extract condition from decision node script.

    Args:
        script: JavaScript decision script

    Returns:
        Extracted condition string
    """
    # Look for return statement
    return_match = re.search(r"return\s+(.+?);", script, re.DOTALL)
    if return_match:
        return return_match.group(1).strip()

    # If no return, assume entire script is the condition
    return script.strip()


def _convert_user_interaction(item: WorkflowItem, profile: dict | None) -> list[AnsibleTask]:
    """
    Convert UserInteraction (approval) to Ansible tasks.

    Default: fail with guidance
    With profile: adapter call or pause

    Args:
        item: WorkflowItem of type 'interaction'
        profile: Profile configuration

    Returns:
        List of AnsibleTask objects for approval handling
    """
    approval_model = profile.get("approval", {}).get("model") if profile else None

    if not approval_model or approval_model == "blocked":
        # Default: FAIL with guidance
        fail_msg = _generate_approval_fail_message(item)
        return [
            AnsibleTask(
                name=f"BLOCKED: Approval required - {item.display_name}",
                module="ansible.builtin.fail",
                module_args={"msg": fail_msg},
                comment=f"UserInteraction node: {item.name}",
                tags=["blocked", "approval"],
            )
        ]

    elif approval_model == "servicenow":
        # ServiceNow adapter
        return [
            AnsibleTask(
                name=f"Request approval via ServiceNow: {item.display_name}",
                module="ansible.builtin.include_tasks",
                module_args={"file": "{{ playbook_dir }}/adapters/snow/request_approval.yml"},
                comment=f"Approval via ServiceNow: {item.display_name}",
                tags=["approval", "servicenow"],
            )
        ]

    elif approval_model == "aap_workflow":
        # AAP approval node
        return [
            AnsibleTask(
                name=f"AAP approval gate: {item.display_name}",
                module="ansible.builtin.pause",
                module_args={"prompt": f"Approve: {item.display_name}? (yes/no)"},
                register="approval_response",
                comment="AAP Workflow approval gate",
                tags=["approval", "aap"],
            )
        ]

    elif approval_model == "pause":
        # Simple pause (demo only)
        return [
            AnsibleTask(
                name=f"Manual approval: {item.display_name}",
                module="ansible.builtin.pause",
                module_args={"prompt": f"Approve {item.display_name}? (Press Enter)"},
                comment="Manual approval (demo mode)",
                tags=["approval", "manual"],
            )
        ]

    else:
        # Unknown approval model - fail with guidance
        return [
            AnsibleTask(
                name=f"ERROR: Unknown approval model '{approval_model}'",
                module="ansible.builtin.fail",
                module_args={
                    "msg": f"Unknown approval model: {approval_model}. "
                    f"Valid options: servicenow, aap_workflow, pause, blocked"
                },
                comment=f"Invalid approval configuration for: {item.display_name}",
                tags=["error"],
            )
        ]


def _generate_approval_fail_message(item: WorkflowItem) -> str:
    """Generate helpful fail message for approval gate."""
    return f"""
Approval workflow detected but not configured.

Evidence: Workflow item '{item.display_name}' (type: {item.item_type})

To resolve, set profile.approval.model to one of:
- servicenow: Integrate with ServiceNow approval workflow
- aap_workflow: Use AAP Controller approval nodes
- pause: Manual approval via pause (demo only)
- blocked: Keep as BLOCKED (current behavior)

Configure in: profile.yml

Example:
  approval:
    model: aap_workflow

Then re-run: ops-translate generate --profile <profile>
"""


def _convert_email_notification(item: WorkflowItem) -> list[AnsibleTask]:
    """
    Convert email notification to mail task.

    Args:
        item: WorkflowItem of type 'email'

    Returns:
        List with single mail task
    """
    # Use existing translator for email
    translator = JavaScriptToAnsibleTranslator()
    email_task = translator.translate_email_notification(item)

    # Convert to AnsibleTask
    return [
        AnsibleTask(
            name=email_task.get("name", f"Send email: {item.display_name}"),
            module="community.general.mail",
            module_args=email_task.get("community.general.mail", {}),
            comment=f"Email notification from: {item.display_name}",
            tags=["email"],
        )
    ]


def _detect_workflow_call(script: str) -> bool:
    """
    Detect if script contains calls to other workflows.

    Args:
        script: JavaScript workflow script

    Returns:
        True if script contains workflow calls
    """
    workflow_patterns = [
        "Server.getWorkflowWithId",
        "workflow.execute",
        ".executeWorkflow",
        "Workflow.execute",
    ]

    script_lower = script.lower()
    return any(pattern.lower() in script_lower for pattern in workflow_patterns)


def _detect_action_call(script: str) -> bool:
    """
    Detect if script contains calls to actions or external integrations.

    Args:
        script: JavaScript workflow script

    Returns:
        True if script contains action calls
    """
    action_patterns = [
        "System.getModule",
        ".getAction(",
        "NSXClient",
        "RESTHost",
        "ServiceNowClient",
        "InfobloxClient",
        "AD:",  # Active Directory plugin
        "SOAP:",  # SOAP plugin
        "SQL:",  # SQL plugin
    ]

    return any(pattern in script for pattern in action_patterns)


def _convert_workflow_call(item: WorkflowItem) -> list[AnsibleTask]:
    """
    Convert WorkflowCall to include_role task.

    Args:
        item: WorkflowItem containing workflow call

    Returns:
        List with include_role task
    """
    # Try to extract workflow name from script
    workflow_name = _extract_workflow_name(item.script) if item.script else None

    if workflow_name:
        role_name = _sanitize_role_name(workflow_name)
        return [
            AnsibleTask(
                name=f"Execute workflow: {workflow_name}",
                module="ansible.builtin.include_role",
                module_args={"name": role_name},
                comment=(
                    f"Workflow call from: {item.display_name}\n"
                    f"Target workflow: {workflow_name}\n"
                    f"Original script:\n{item.script}"
                ),
                tags=["workflow_call"],
            )
        ]
    else:
        # Couldn't extract workflow name - emit TODO
        return [
            AnsibleTask(
                name=f"TODO: Workflow call in {item.display_name}",
                module="ansible.builtin.debug",
                module_args={"msg": f"Implement workflow call logic from: {item.display_name}"},
                comment=(
                    f"Workflow call detected but couldn't extract target workflow name\n"
                    f"Original script:\n{item.script}"
                ),
                tags=["todo", "workflow_call"],
            )
        ]


def _convert_action_call(item: WorkflowItem, profile: dict | None) -> list[AnsibleTask]:
    """
    Convert ActionCall to adapter stub.

    Args:
        item: WorkflowItem containing action call
        profile: Profile configuration

    Returns:
        List with adapter stub tasks
    """
    # Detect integration type
    integration_type = _detect_integration_type(item.script) if item.script else None

    if integration_type:
        adapter_path = f"{{{{ playbook_dir }}}}/adapters/{integration_type}/stub.yml"
        return [
            AnsibleTask(
                name=f"Call {integration_type} adapter: {item.display_name}",
                module="ansible.builtin.include_tasks",
                module_args={"file": adapter_path},
                comment=(
                    f"Action call from: {item.display_name}\n"
                    f"Integration type: {integration_type}\n"
                    f"Original script:\n{item.script}"
                ),
                tags=["action_call", integration_type],
            )
        ]
    else:
        # Generic action call - emit TODO
        return [
            AnsibleTask(
                name=f"TODO: Action call in {item.display_name}",
                module="ansible.builtin.debug",
                module_args={"msg": f"Implement action call logic from: {item.display_name}"},
                comment=(f"Action call detected\n" f"Original script:\n{item.script}"),
                tags=["todo", "action_call"],
            )
        ]


def _extract_workflow_name(script: str) -> str | None:
    """
    Extract workflow name from workflow call script.

    Args:
        script: JavaScript script containing workflow call

    Returns:
        Workflow name if found, None otherwise
    """
    # Try to find workflow ID or name in quotes
    import re

    # Pattern: getWorkflowWithId("workflow-name") or similar
    id_patterns = [
        r'getWorkflowWithId\s*\(\s*["\']([^"\']+)["\']',
        r'executeWorkflow\s*\(\s*["\']([^"\']+)["\']',
    ]

    for pattern in id_patterns:
        match = re.search(pattern, script)
        if match:
            return match.group(1)

    return None


def _sanitize_role_name(workflow_name: str) -> str:
    """
    Sanitize workflow name for use as Ansible role name.

    Args:
        workflow_name: Original workflow name

    Returns:
        Sanitized role name
    """
    # Replace special characters with underscores
    import re

    # Convert to lowercase and replace non-alphanumeric with underscores
    sanitized = re.sub(r"[^a-z0-9_]", "_", workflow_name.lower())

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    return sanitized


def _detect_integration_type(script: str) -> str | None:
    """
    Detect integration type from action call script.

    Args:
        script: JavaScript script containing action call

    Returns:
        Integration type (nsx, servicenow, infoblox, etc.) or None
    """
    script_lower = script.lower()

    # Check for known integration patterns
    if "nsxclient" in script_lower or "nsx-t" in script_lower:
        return "nsx"
    elif "servicenow" in script_lower or "snow" in script_lower:
        return "servicenow"
    elif "infoblox" in script_lower:
        return "infoblox"
    elif "resthost" in script_lower or "rest:" in script_lower:
        return "rest"
    elif "ad:" in script_lower or "activedirectory" in script_lower:
        return "ad"
    elif "sql:" in script_lower or "database" in script_lower:
        return "sql"
    elif "soap:" in script_lower:
        return "soap"

    return None


def _js_to_jinja(js_expr: str) -> str:
    """
    Convert JavaScript expression to Jinja2.

    Handles common patterns:
    - === → ==
    - !== → !=
    - && → and
    - || → or
    - ! → not

    Args:
        js_expr: JavaScript expression

    Returns:
        Jinja2 expression
    """
    # Simple replacements
    expr = js_expr.replace("===", "==")
    expr = expr.replace("!==", "!=")
    expr = expr.replace("&&", " and ")
    expr = expr.replace("||", " or ")

    # Handle negation carefully
    if expr.startswith("!"):
        expr = "not " + expr[1:]

    return expr.strip()


def generate_ansible_yaml(tasks: list[AnsibleTask], include_comments: bool = True) -> str:
    """
    Generate Ansible YAML from task list.

    Args:
        tasks: List of AnsibleTask objects
        include_comments: Whether to include task comments

    Returns:
        YAML string with Ansible tasks
    """
    yaml_lines = ["---", "# Generated from vRO workflow", ""]

    for task in tasks:
        # Add comment if present and requested
        if include_comments and task.comment:
            for line in task.comment.split("\n"):
                if line.strip():
                    yaml_lines.append(f"# {line}")

        # Task definition
        task_dict: dict[str, Any] = {
            "name": task.name,
            task.module: task.module_args,
        }

        # Add optional fields
        if task.when:
            task_dict["when"] = task.when

        if task.register:
            task_dict["register"] = task.register

        if task.tags:
            task_dict["tags"] = task.tags

        # Convert to YAML
        task_yaml = yaml.dump([task_dict], default_flow_style=False, sort_keys=False)

        # Remove the leading "---" from individual task YAML
        task_yaml_lines = task_yaml.strip().split("\n")
        if task_yaml_lines[0] == "---":
            task_yaml_lines = task_yaml_lines[1:]

        yaml_lines.extend(task_yaml_lines)
        yaml_lines.append("")  # Blank line between tasks

    return "\n".join(yaml_lines)
