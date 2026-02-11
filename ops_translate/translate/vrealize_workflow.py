"""
vRealize workflow-to-Ansible translator.

Parses vRealize Orchestrator workflow XML and translates workflow items
into executable Ansible tasks.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
        display_name = display_elem.text if display_elem is not None else name

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
    """

    def translate_script(self, script: str, item: WorkflowItem) -> list[dict[str, Any]]:
        """
        Translate JavaScript script to Ansible tasks.

        Args:
            script: JavaScript code from workflow item
            item: WorkflowItem containing the script

        Returns:
            List of Ansible task dictionaries
        """
        tasks = []

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


def translate_workflow_to_ansible(workflow_file: Path) -> list[dict[str, Any]]:
    """
    Translate vRealize workflow to Ansible tasks.

    Args:
        workflow_file: Path to vRealize workflow XML file

    Returns:
        List of Ansible task dictionaries

    Example:
        >>> tasks = translate_workflow_to_ansible(Path("workflow.xml"))
        >>> for task in tasks:
        ...     print(task["name"])
    """
    parser = WorkflowParser()
    translator = JavaScriptToAnsibleTranslator()

    # Parse workflow
    items = parser.parse_file(workflow_file)

    # Translate each item
    all_tasks = []
    for item in items:
        if item.script:
            tasks = translator.translate_script(item.script, item)
            all_tasks.extend(tasks)
        elif item.item_type == "decision":
            # Decision nodes become conditional task execution
            # The condition is in the script
            pass  # Handled by when: clauses on subsequent tasks

    return all_tasks
