"""
vRealize workflow-to-Ansible translator.

Parses vRealize Orchestrator workflow XML and translates workflow items
into executable Ansible tasks.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from lxml import etree


@dataclass
class WorkflowItem:
    """Represents a vRealize workflow item."""

    name: str
    item_type: str  # task, decision, interaction, email
    display_name: str
    script: str | None
    in_bindings: list[dict[str, str]]
    out_bindings: list[dict[str, str]]
    out_name: str | None  # Next item in workflow
    position: tuple[float, float] | None = None


class WorkflowParser:
    """
    Parse vRealize workflow XML to extract workflow items.

    Example:
        >>> parser = WorkflowParser()
        >>> items = parser.parse_file(Path("workflow.xml"))
        >>> for item in items:
        ...     print(f"{item.display_name}: {item.item_type}")
    """

    def parse_file(self, workflow_file: Path) -> list[WorkflowItem]:
        """
        Parse vRealize workflow XML file.

        Args:
            workflow_file: Path to workflow XML file

        Returns:
            List of WorkflowItem objects in execution order

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            etree.XMLSyntaxError: If XML is malformed
        """
        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_file}")

        tree = etree.parse(str(workflow_file))
        root = tree.getroot()

        # Parse all workflow items
        items = []
        for elem in root.findall(".//{http://vmware.com/vco/workflow}workflow-item"):
            item = self._parse_workflow_item(elem)
            if item:
                items.append(item)

        # Sort by execution order (following out-name links)
        return self._sort_by_execution_order(items)

    def _parse_workflow_item(self, elem: etree._Element) -> WorkflowItem | None:
        """Parse a single workflow-item element."""
        name = elem.get("name", "")
        item_type = elem.get("type", "task")
        out_name = elem.get("out-name")

        # Skip end nodes
        if item_type == "end":
            return None

        # Get display name
        display_elem = elem.find(".//{http://vmware.com/vco/workflow}display-name")
        display_name = (
            display_elem.text if display_elem is not None and display_elem.text else None
        ) or name

        # Get script content
        script_elem = elem.find(".//{http://vmware.com/vco/workflow}script")
        script = script_elem.text.strip() if script_elem is not None and script_elem.text else None

        # Parse bindings
        in_bindings = self._parse_bindings(elem, "in-binding")
        out_bindings = self._parse_bindings(elem, "out-binding")

        # Get position
        pos_elem = elem.find(".//{http://vmware.com/vco/workflow}position")
        position = None
        if pos_elem is not None:
            x = float(pos_elem.get("x", 0))
            y = float(pos_elem.get("y", 0))
            position = (x, y)

        return WorkflowItem(
            name=name,
            item_type=item_type,
            display_name=display_name,
            script=script,
            in_bindings=in_bindings,
            out_bindings=out_bindings,
            out_name=out_name,
            position=position,
        )

    def _parse_bindings(self, elem: etree._Element, binding_type: str) -> list[dict[str, str]]:
        """Parse in-binding or out-binding elements."""
        bindings = []
        binding_elem = elem.find(f".//{{{elem.nsmap[None]}}}{binding_type}")
        if binding_elem is not None:
            for bind in binding_elem.findall(f".//{{{elem.nsmap[None]}}}bind"):
                bindings.append(
                    {
                        "name": bind.get("name", ""),
                        "type": bind.get("type", ""),
                        "export_name": bind.get("export-name", ""),
                    }
                )
        return bindings

    def _sort_by_execution_order(self, items: list[WorkflowItem]) -> list[WorkflowItem]:
        """
        Sort workflow items by execution order following out-name links.

        Returns items in the order they would execute, starting from the root item.
        """
        if not items:
            return []

        # Build name->item lookup
        item_map = {item.name: item for item in items}

        # Find root (no items point to it, or first by position)
        referenced = {item.out_name for item in items if item.out_name}
        roots = [item for item in items if item.name not in referenced]

        if not roots:
            # Fallback: use first item by position
            roots = [
                min(items, key=lambda i: i.position if i.position else (float("inf"), float("inf")))
            ]

        # Traverse from root following out-name
        ordered = []
        visited = set()
        stack = roots[:]

        while stack:
            current = stack.pop(0)
            if current.name in visited:
                continue

            visited.add(current.name)
            ordered.append(current)

            # Add next item if it exists
            if current.out_name and current.out_name in item_map:
                next_item = item_map[current.out_name]
                if next_item.name not in visited:
                    stack.append(next_item)

        return ordered


class JavaScriptToAnsibleTranslator:
    """
    Translate JavaScript logic from vRealize workflows to Ansible tasks.

    Handles common patterns:
    - Variable assignments → set_fact
    - Conditionals (if/else) → set_fact + when
    - Validation (throw) → assert
    - Logging → debug
    - Approval interactions → pause
    - Email notifications → mail
    - Integration calls → Ansible modules/adapters (mapping-driven)
    - LockingSystem calls → distributed locking (Redis/Consul/file)
    """

    def __init__(self, locking_backend: str = "redis", locking_enabled: bool = True):
        """
        Initialize translator and load integration mappings.

        Args:
            locking_backend: Backend for distributed locking (redis, consul, file)
            locking_enabled: Whether to generate locking tasks
        """
        self.integration_mappings = self._load_integration_mappings()
        self.locking_backend = locking_backend
        self.locking_enabled = locking_enabled

    def _load_integration_mappings(self) -> dict[str, Any]:
        """
        Load vRO integration mappings from YAML file.

        Returns:
            Dictionary of integration mappings, or empty dict if file not found
        """
        mappings_file = Path(__file__).parent / "vro_integration_mappings.yaml"
        if not mappings_file.exists():
            return {}

        try:
            with open(mappings_file) as f:
                mappings = yaml.safe_load(f)
                return mappings if mappings else {}
        except Exception as e:
            # Log warning but don't fail - just skip integration detection
            print(f"Warning: Failed to load integration mappings: {e}")
            return {}

    def translate_script(self, script: str, item: WorkflowItem) -> list[dict[str, Any]]:
        """
        Translate JavaScript script to Ansible tasks.

        Args:
            script: JavaScript code from workflow item
            item: WorkflowItem containing the script

        Returns:
            List of Ansible task dictionaries
        """
        # Check if script contains locking patterns
        if self.locking_enabled:
            from ops_translate.summarize.vrealize_locking import detect_locking_patterns

            lock_patterns = detect_locking_patterns(script)
            if lock_patterns:
                # Translate with locking structure
                return self._translate_with_locking(script, item, lock_patterns)

        # Check if script contains error handling (try/catch/finally)
        error_handling = self._extract_error_handling(script)
        if error_handling:
            # Translate with block/rescue/always structure
            return self._translate_error_handling(error_handling, item)

        # Normal translation (no error handling or locking)
        tasks = []

        # Detect and translate integration calls (trust-first, allowlist-based)
        integration_tasks = self._detect_integration_calls(script, item)
        tasks.extend(integration_tasks)

        # Remove System.log statements and replace with debug tasks
        log_tasks = self._extract_logging(script, item.display_name)
        tasks.extend(log_tasks)

        # Extract validation logic (throw statements)
        validation_tasks = self._extract_validations(script, item.display_name)
        tasks.extend(validation_tasks)

        # Extract variable assignments
        assignment_tasks = self._extract_assignments(script, item.display_name)
        tasks.extend(assignment_tasks)

        return tasks

    def _translate_with_locking(
        self, script: str, item: WorkflowItem, lock_patterns: list[Any]
    ) -> list[dict[str, Any]]:
        """
        Translate script with locking patterns to Ansible block/always structure.

        Args:
            script: JavaScript code with LockingSystem calls
            item: WorkflowItem for context
            lock_patterns: Detected lock patterns from detect_locking_patterns()

        Returns:
            List containing block/always task structures with locking
        """
        from ops_translate.generate.ansible_locking import LockingTaskGenerator

        # For now, handle single lock pattern (most common case)
        # TODO: Handle nested/multiple locks
        if len(lock_patterns) > 1:
            # Multiple locks - use first one and add TODO comment
            pattern = lock_patterns[0]
            tasks = [
                {
                    "name": "TODO: Multiple locks detected - review and implement",
                    "ansible.builtin.debug": {
                        "msg": (
                            "This workflow uses multiple locks. "
                            "Current implementation uses first lock only. "
                            "Review vRO workflow for proper lock ordering."
                        )
                    },
                    "tags": ["todo", "multiple_locks"],
                }
            ]
        else:
            tasks = []
            pattern = lock_patterns[0]

        # Extract work tasks (code between lock and unlock)
        work_script = self._extract_locked_work(script, pattern)

        # Translate work tasks (without checking for locking again)
        work_tasks = self._translate_script_fragment(work_script, item)

        # If no work tasks were translated, add a placeholder
        if not work_tasks:
            work_tasks = [
                {
                    "name": f"Work while holding lock: {pattern.resource}",
                    "ansible.builtin.debug": {
                        "msg": "Locked work section - implement business logic here"
                    },
                    "tags": ["todo", "locked_work"],
                }
            ]

        # Generate locking structure
        generator = LockingTaskGenerator(backend=self.locking_backend)
        lock_task = generator.generate_lock_tasks(pattern, work_tasks)

        tasks.append(lock_task)
        return tasks

    def _extract_locked_work(self, script: str, pattern: Any) -> str:
        """
        Extract the code between lock acquisition and release.

        Args:
            script: Full JavaScript code
            pattern: LockPattern with lock_position and unlock_position

        Returns:
            Code fragment between lock and unlock calls
        """
        # Find the end of the lock call (after the semicolon)
        lock_end = script.find(";", pattern.lock_position)
        if lock_end == -1:
            lock_end = pattern.lock_position + 100  # Fallback

        # Find the start of unlock call
        unlock_start = pattern.unlock_position if pattern.unlock_position else len(script)

        # Extract work between lock and unlock
        work_script = script[lock_end + 1 : unlock_start].strip()

        return work_script

    def translate_approval_interaction(self, item: WorkflowItem) -> dict[str, Any]:
        """
        Translate approval interaction workflow item to pause task.

        Args:
            item: WorkflowItem of type 'interaction' or 'task' with approval script

        Returns:
            Ansible pause task dictionary
        """
        # Extract VM info from bindings
        vm_name_var = "vm_name"
        for binding in item.in_bindings:
            if "vm" in binding["name"].lower() and "name" in binding["name"].lower():
                vm_name_var = binding["name"]
                break

        # Check if approval is conditional (from script or previous logic)
        prompt_text = f"""
VM Provisioning Request
VM: {{{{ {vm_name_var} }}}}

This request requires approval.
Approve? (yes/no)
""".strip()

        task = {
            "name": f"Request approval: {item.display_name}",
            "ansible.builtin.pause": {"prompt": prompt_text},
            "register": "approval_response",
        }

        # If this approval is conditional, add when clause
        # (This would be determined from workflow context - for now we check bindings)
        for binding in item.in_bindings:
            if "approval" in binding["name"].lower() and "require" in binding["name"].lower():
                task["when"] = f"{{{{ {binding['export_name']} }}}}"
                break

        return task

    def translate_email_notification(
        self, item: WorkflowItem, recipient_var: str = "owner_email", subject: str | None = None
    ) -> dict[str, Any]:
        """
        Translate email notification to mail task.

        Args:
            item: WorkflowItem containing email logic
            recipient_var: Variable name containing recipient email
            subject: Email subject (extracted from script if not provided)

        Returns:
            Ansible mail task dictionary
        """
        # Try to extract subject from script
        if not subject and item.script:
            # Look for subject in script
            subject_match = re.search(r'subject["\s:]+([^"]+)', item.script, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
            else:
                subject = f"Notification: {item.display_name}"

        # Try to find recipient from bindings
        for binding in item.in_bindings:
            if "email" in binding["name"].lower() or "owner" in binding["name"].lower():
                recipient_var = binding["export_name"]
                break

        task = {
            "name": f"Send notification: {item.display_name}",
            "community.general.mail": {
                "host": "{{ smtp_host | default('localhost') }}",
                "port": "{{ smtp_port | default(25) }}",
                "to": f"{{{{ {recipient_var} }}}}",
                "subject": subject or f"Notification from {item.display_name}",
                "body": f"Your request has been processed.\n\nWorkflow: {item.display_name}",
            },
        }

        return task

    def _extract_logging(self, script: str, display_name: str) -> list[dict[str, Any]]:
        """Extract System.log statements and convert to debug tasks."""
        tasks = []
        # Match System.log("text" + var + "text") or System.log("text")
        log_pattern = r"System\.log\s*\(\s*(.+?)\s*\)\s*;"

        for match in re.finditer(log_pattern, script):
            log_expr = match.group(1)
            # Convert JavaScript string concatenation to Jinja2
            message = self._js_to_jinja(log_expr)

            tasks.append(
                {
                    "name": f"Log: {display_name}",
                    "ansible.builtin.debug": {"msg": message},
                }
            )

        return tasks

    def _extract_validations(self, script: str, display_name: str) -> list[dict[str, Any]]:
        """Extract throw statements and convert to assert tasks."""
        tasks = []
        # Match: if (condition) { throw "message"; } with multiline support
        throw_pattern = r'if\s*\(\s*(.+?)\s*\)\s*\{\s*throw\s+["\'](.+?)["\']\s*;\s*\}'

        for match in re.finditer(throw_pattern, script, re.DOTALL | re.MULTILINE):
            condition = match.group(1).strip()
            error_msg = match.group(2).strip()

            # Convert condition to Ansible (negate it for assert)
            ansible_condition = self._negate_condition(condition)

            tasks.append(
                {
                    "name": f"Validate: {error_msg[:50]}",
                    "ansible.builtin.assert": {
                        "that": ansible_condition,
                        "fail_msg": error_msg,
                    },
                }
            )

        return tasks

    def _extract_assignments(self, script: str, display_name: str) -> list[dict[str, Any]]:
        """Extract variable assignments and convert to set_fact tasks."""
        tasks = []
        # Match: varName = expression; (not inside if/throw blocks)
        # First, remove throw blocks to avoid matching inside them
        script_without_throws = re.sub(
            r"if\s*\([^)]+\)\s*\{\s*throw[^}]+\}", "", script, flags=re.DOTALL
        )

        # Match assignments
        assignment_pattern = r"^(\w+)\s*=\s*(.+?);$"

        for match in re.finditer(assignment_pattern, script_without_throws, re.MULTILINE):
            var_name = match.group(1)
            expression = match.group(2).strip()

            # Skip if it's part of System.log
            full_match = match.group(0)
            if "System.log" in full_match:
                continue
            if "throw" in expression:
                continue

            # Convert expression to Jinja2
            jinja_expr = self._js_to_jinja(expression)

            tasks.append(
                {
                    "name": f"Set {var_name} (from {display_name})",
                    "ansible.builtin.set_fact": {var_name: jinja_expr},
                }
            )

        return tasks

    def _js_to_jinja(self, js_expr: str) -> str:
        """
        Convert JavaScript expression to Jinja2.

        Handles common patterns:
        - === → ==
        - !== → !=
        - String concatenation → Jinja2
        - Variables → {{ var }}
        """
        # Remove quotes for simple string literals
        if js_expr.startswith('"') and js_expr.endswith('"'):
            content = js_expr[1:-1]
            # Check if it contains variable concatenation
            if " + " in js_expr:
                # Complex concatenation - convert to Jinja2
                return self._convert_string_concat(js_expr)
            else:
                # Simple string
                return content

        # Convert boolean comparisons
        expr = js_expr.replace("===", "==").replace("!==", "!=")

        # Wrap in Jinja2 template if it looks like an expression
        if any(op in expr for op in ["==", "!=", ">", "<", "&&", "||"]):
            expr = expr.replace("&&", "and").replace("||", "or")
            return f"{{{{ {expr} }}}}"

        # Simple variable or literal
        if expr in ["true", "false"]:
            return expr.capitalize()

        return f"{{{{ {expr} }}}}"

    def _convert_string_concat(self, js_expr: str) -> str:
        """Convert JavaScript string concatenation to Jinja2."""
        # Simple approach: replace + with Jinja2 concatenation
        # "text" + var + "more" → "text {{ var }} more"

        # Remove outer quotes
        expr = js_expr.strip()
        if expr.startswith('"') and expr.endswith('"'):
            expr = expr[1:-1]

        # Split by + and rebuild
        parts = [p.strip().strip('"') for p in expr.split("+")]
        result_parts = []

        for part in parts:
            if part.startswith('"') or part.endswith('"'):
                # String literal
                result_parts.append(part.strip('"'))
            else:
                # Variable
                result_parts.append(f"{{{{ {part} }}}}")

        return " ".join(result_parts)

    def _negate_condition(self, condition: str) -> str:
        """
        Negate a JavaScript condition for assert.

        If script has: if (x > 16) { throw ... }
        Assert needs: that: x <= 16
        """
        condition = condition.strip()

        # Handle simple comparisons
        negations = {
            ">": "<=",
            "<": ">=",
            ">=": "<",
            "<=": ">",
            "===": "!=",
            "!==": "==",
            "==": "!=",
            "!=": "==",
        }

        for op, neg_op in negations.items():
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    # Convert to Ansible/Jinja2
                    return f"{left} {neg_op} {right}"

        # Fallback: wrap in not
        return f"not ({condition})"

    def _detect_integration_calls(self, script: str, item: WorkflowItem) -> list[dict[str, Any]]:
        """
        Detect vRO integration calls and translate to Ansible tasks.

        Uses allowlist-based matching from integration mappings. Only matches
        when we have high confidence (explicit mapping exists).

        DOES NOT match common JS patterns like:
        - System.log(...)
        - Math.*
        - vm.powerOffVM_Task()

        Args:
            script: JavaScript code to analyze
            item: WorkflowItem for context

        Returns:
            List of Ansible task dictionaries (modules or adapter stubs)
        """
        if not self.integration_mappings:
            return []

        tasks = []
        detected_integrations = []

        # Build allowlist of object.method patterns from mappings
        for integration_name, methods in self.integration_mappings.items():
            for method_name, mapping in methods.items():
                match_config = mapping.get("match", {})

                # Pattern 1: Explicit object.method matching
                if "object" in match_config and "method" in match_config:
                    obj_name = match_config["object"]
                    method = match_config["method"]

                    # Build regex pattern for this specific call
                    # Matches: ObjectName.methodName(...) but not System.log, Math.*, etc.
                    # Use DOTALL to match arguments that span multiple lines
                    pattern = rf"\b{re.escape(obj_name)}\.{re.escape(method)}\s*\((.*?)\)"

                    for match in re.finditer(pattern, script, re.DOTALL):
                        args = match.group(1)
                        detected_integrations.append(
                            {
                                "integration": integration_name,
                                "method": method_name,
                                "mapping": mapping,
                                "args": args,
                                "evidence": match.group(0),
                            }
                        )

                # Pattern 2: Contains patterns (e.g., RESTHost, RESTRequest)
                elif "contains_any" in match_config:
                    patterns = match_config["contains_any"]
                    for pattern in patterns:
                        if pattern in script:
                            # Extract the full statement for evidence
                            # Look for the line containing the pattern
                            lines = script.split("\n")
                            evidence_lines = [line for line in lines if pattern in line]
                            evidence = evidence_lines[0] if evidence_lines else pattern

                            detected_integrations.append(
                                {
                                    "integration": integration_name,
                                    "method": method_name,
                                    "mapping": mapping,
                                    "args": "",  # Contains-based matches don't extract args
                                    "evidence": evidence,
                                }
                            )
                            break  # Only match once per method

        # Generate tasks for detected integrations
        for detection in detected_integrations:
            task = self._generate_integration_task(detection, item)
            tasks.append(task)

        return tasks

    def _generate_integration_task(
        self, detection: dict[str, Any], item: WorkflowItem
    ) -> dict[str, Any]:
        """
        Generate Ansible task for detected integration call.

        Generates either:
        1. A fully mapped Ansible module task
        2. A DECISION REQUIRED stub if profile keys are missing

        Args:
            detection: Detected integration info with mapping
            item: WorkflowItem for context

        Returns:
            Ansible task dictionary
        """
        integration = detection["integration"]
        method = detection["method"]
        mapping = detection["mapping"]
        args = detection["args"]
        evidence = detection["evidence"]

        ansible_config = mapping.get("ansible", {})
        module = ansible_config.get("module")
        params = ansible_config.get("params", {})
        register = ansible_config.get("register")
        requires_profile = mapping.get("requires_profile", [])

        # Parse arguments (simple arg0, arg1, arg2 substitution for v1)
        parsed_args = self._parse_args(args)

        # Substitute {arg0}, {arg1}, etc. in params
        substituted_params = self._substitute_params(params, parsed_args)

        # Build the task
        task_name = f"{integration.capitalize()}: {method.replace('_', ' ').title()}"

        # Check if this requires profile configuration
        if requires_profile:
            # Generate DECISION REQUIRED stub
            profile_keys_str = "\n      ".join(requires_profile)
            task = {
                "name": f"DECISION REQUIRED - {task_name}",
                "ansible.builtin.fail": {"msg": f"""Integration detected: {integration}
Missing required profile configuration:
      {profile_keys_str}

Evidence: {item.display_name} - {evidence.strip()}

Action required:
1. Configure profile keys in profile.yml
2. Implement adapter stub if needed
3. Re-run translation

See: intent/recommendations.md for guidance
"""},
                "tags": ["decision_required", "integration", integration],
            }
        else:
            # Generate fully mapped task
            task = {
                "name": task_name,
                module: substituted_params,
            }

            if register:
                task["register"] = register

        return task

    def _parse_args(self, args_str: str) -> list[str]:
        """
        Parse JavaScript function arguments.

        Simple v1 implementation: split by comma, strip whitespace.

        Args:
            args_str: Argument string from function call

        Returns:
            List of argument strings
        """
        if not args_str.strip():
            return []

        # Simple comma split (doesn't handle nested calls, but good enough for v1)
        args = [arg.strip() for arg in args_str.split(",")]
        return args

    def _substitute_params(self, params: dict[str, Any], args: list[str]) -> dict[str, Any]:
        """
        Substitute {arg0}, {arg1}, etc. in parameter template.

        Args:
            params: Parameter template from mapping
            args: Parsed argument values

        Returns:
            Parameters with substitutions applied
        """
        import copy
        from typing import cast

        # Deep copy params to avoid modifying the original
        result = copy.deepcopy(params)

        # Recursively substitute in nested dictionaries
        def substitute_recursive(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: substitute_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_recursive(item) for item in obj]
            elif isinstance(obj, str):
                # Substitute {argN} with actual values
                for i, arg in enumerate(args):
                    placeholder = f"{{arg{i}}}"
                    if placeholder in obj:
                        # Clean up the argument value
                        arg_clean = arg.strip().strip('"').strip("'")
                        obj = obj.replace(placeholder, arg_clean)

                # Substitute {url}, {method}, etc. with Jinja2 variables
                jinja_vars = ["url", "method", "headers", "body"]
                for var in jinja_vars:
                    placeholder = f"{{{var}}}"
                    if placeholder == obj:  # Exact match
                        return f"{{{{ {var} }}}}"
                    elif placeholder in obj:  # Partial match
                        obj = obj.replace(placeholder, f"{{{{ {var} }}}}")

                return obj
            else:
                return obj

        return cast(dict[str, Any], substitute_recursive(result))

    def _extract_error_handling(self, script: str) -> dict[str, Any] | None:
        """
        Detect try/catch/finally blocks in JavaScript.

        Args:
            script: JavaScript code to analyze

        Returns:
            Dictionary with try_block, catch_var, catch_block, finally_block
            or None if no error handling found
        """
        # Find the start of try block
        try_match = re.search(r"\btry\s*\{", script)
        if not try_match:
            return None

        # Extract blocks by counting braces
        try_start = try_match.end()
        try_block, try_end = self._extract_block_content(script, try_start)

        # Look for catch block
        catch_match = re.search(r"\bcatch\s*\((\w+)\)\s*\{", script[try_end:])
        if not catch_match:
            return None

        catch_var = catch_match.group(1)
        catch_start = try_end + catch_match.end()
        catch_block, catch_end = self._extract_block_content(script, catch_start)

        # Look for optional finally block
        finally_match = re.search(r"\bfinally\s*\{", script[catch_end:])
        finally_block = None
        if finally_match:
            finally_start = catch_end + finally_match.end()
            finally_block, _ = self._extract_block_content(script, finally_start)

        return {
            "try_block": try_block.strip(),
            "catch_var": catch_var,
            "catch_block": catch_block.strip(),
            "finally_block": finally_block.strip() if finally_block else None,
        }

    def _extract_block_content(self, script: str, start_pos: int) -> tuple[str, int]:
        """
        Extract the content of a brace-delimited block by counting braces.

        Args:
            script: Full script text
            start_pos: Position right after the opening brace

        Returns:
            Tuple of (block_content, end_position)
        """
        brace_count = 1
        pos = start_pos

        while pos < len(script) and brace_count > 0:
            char = script[pos]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
            pos += 1

        # Extract content between braces
        block_content = script[start_pos : pos - 1]
        return block_content, pos

    def _translate_error_handling(
        self, error_handling: dict[str, Any], item: WorkflowItem
    ) -> list[dict[str, Any]]:
        """
        Translate try/catch/finally to Ansible block/rescue/always.

        Args:
            error_handling: Parsed error handling structure from _extract_error_handling
            item: WorkflowItem for context

        Returns:
            List containing a single block/rescue/always task structure
        """
        # Translate try block
        try_tasks = self._translate_script_fragment(error_handling["try_block"], item)

        # Generate rescue tasks from catch block
        rescue_tasks = self._generate_rescue_tasks(
            error_handling["catch_block"], error_handling["catch_var"], item
        )

        # Translate finally block if present
        always_tasks = []
        if error_handling["finally_block"]:
            always_tasks = self._translate_script_fragment(error_handling["finally_block"], item)
            # If finally block didn't translate to any tasks, add a comment task
            if not always_tasks:
                always_tasks = [
                    {
                        "name": "Cleanup (from finally block)",
                        "ansible.builtin.debug": {
                            "msg": "Finally block present but no translatable tasks"
                        },
                    }
                ]

        # Build block/rescue/always structure
        block_task = {
            "name": f"Execute with error handling: {item.display_name}",
            "block": try_tasks,
        }

        if rescue_tasks:
            block_task["rescue"] = rescue_tasks

        if always_tasks:
            block_task["always"] = always_tasks

        return [block_task]

    def _translate_script_fragment(
        self, script_fragment: str, item: WorkflowItem
    ) -> list[dict[str, Any]]:
        """
        Translate a script fragment (without checking for error handling).

        This is used to translate try/catch/finally block contents.

        Args:
            script_fragment: JavaScript code fragment
            item: WorkflowItem for context

        Returns:
            List of Ansible task dictionaries
        """
        tasks = []

        # Detect and translate integration calls
        integration_tasks = self._detect_integration_calls(script_fragment, item)
        tasks.extend(integration_tasks)

        # Extract logging
        log_tasks = self._extract_logging(script_fragment, item.display_name)
        tasks.extend(log_tasks)

        # Extract validations (but skip if this is a catch block with throw)
        validation_tasks = self._extract_validations(script_fragment, item.display_name)
        tasks.extend(validation_tasks)

        # Extract assignments
        assignment_tasks = self._extract_assignments(script_fragment, item.display_name)
        tasks.extend(assignment_tasks)

        return tasks

    def _generate_rescue_tasks(
        self, catch_block: str, catch_var: str, item: WorkflowItem
    ) -> list[dict[str, Any]]:
        """
        Generate rescue tasks from catch block.

        Args:
            catch_block: JavaScript catch block code
            catch_var: Name of exception variable (e.g., 'e' in catch(e))
            item: WorkflowItem for context

        Returns:
            List of rescue tasks including rollback logic
        """
        rescue_tasks = []

        # Add error logging task
        rescue_tasks.append(
            {
                "name": "Log error",
                "ansible.builtin.debug": {
                    "msg": f"Error in {item.display_name}: {{{{ ansible_failed_result.msg }}}}"
                },
            }
        )

        # Translate catch block content (rollback logic)
        catch_tasks = self._translate_script_fragment(catch_block, item)
        rescue_tasks.extend(catch_tasks)

        # Check if catch block re-raises the exception
        if "throw" in catch_block:
            rescue_tasks.append(
                {
                    "name": "Re-raise error after rollback",
                    "ansible.builtin.fail": {"msg": "{{ ansible_failed_result.msg }}"},
                }
            )

        return rescue_tasks


def translate_workflow_to_ansible(
    workflow_file: Path, locking_backend: str = "redis", locking_enabled: bool = True
) -> list[dict[str, Any]]:
    """
    Translate vRealize workflow to Ansible tasks.

    Args:
        workflow_file: Path to vRealize workflow XML file
        locking_backend: Backend for distributed locking (redis, consul, file)
        locking_enabled: Whether to generate locking tasks for LockingSystem calls

    Returns:
        List of Ansible task dictionaries

    Example:
        >>> tasks = translate_workflow_to_ansible(Path("workflow.xml"))
        >>> for task in tasks:
        ...     print(task["name"])
    """
    parser = WorkflowParser()
    translator = JavaScriptToAnsibleTranslator(
        locking_backend=locking_backend, locking_enabled=locking_enabled
    )

    # Parse workflow
    items = parser.parse_file(workflow_file)

    # Translate each item
    all_tasks = []
    for item in items:
        # Check for approval workflow items
        if _is_approval_item(item):
            task = translator.translate_approval_interaction(item)
            all_tasks.append(task)
        # Check for email notification items
        elif _is_email_item(item):
            task = translator.translate_email_notification(item)
            all_tasks.append(task)
        # Regular script-based items
        elif item.script:
            tasks = translator.translate_script(item.script, item)
            all_tasks.extend(tasks)
        elif item.item_type == "decision":
            # Decision nodes become conditional task execution
            # The condition is in the script
            pass  # Handled by when: clauses on subsequent tasks

    return all_tasks


def _is_approval_item(item: WorkflowItem) -> bool:
    """Check if workflow item represents an approval interaction."""
    if item.item_type == "interaction":
        return True

    # Check for approval keywords in display name or script
    if item.display_name and "approval" in item.display_name.lower():
        return True

    if item.script and "approval" in item.script.lower():
        # Look for patterns like "request approval" or "approvalDecision"
        approval_patterns = [
            r"request\s+approval",
            r"approval\s*(decision|request|granted)",
            r"approver",
        ]
        return any(re.search(pattern, item.script, re.IGNORECASE) for pattern in approval_patterns)

    return False


def _is_email_item(item: WorkflowItem) -> bool:
    """Check if workflow item represents an email notification."""
    if item.item_type == "email":
        return True

    # Check for email/notification keywords
    if item.display_name:
        email_keywords = ["email", "notify", "notification", "send mail"]
        if any(keyword in item.display_name.lower() for keyword in email_keywords):
            return True

    if item.script:
        email_patterns = [
            r"send\s+email",
            r"notify\s+(owner|user)",
            r"email\s*(to|subject|body)",
            r"notification",
        ]
        return any(re.search(pattern, item.script, re.IGNORECASE) for pattern in email_patterns)

    return False
