"""
PowerCLI script to Ansible tasks translation.

Parses PowerCLI scripts into structured statements and translates them to
Ansible tasks using KubeVirt and Kubernetes modules.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ops_translate.generate.workflow_to_ansible import AnsibleTask
from ops_translate.models.profile import ProfileSchema


@dataclass
class PowerCLIStatement:
    """Represents a parsed PowerCLI statement."""

    line_number: int
    raw_text: str
    statement_type: str  # param | assignment | cmdlet | control_flow | comment
    category: str  # context | lookup | mutation | integration | gate | control_flow

    # Cmdlet-specific
    cmdlet: str | None = None
    parameters: dict[str, str] = field(default_factory=dict)
    piped_to: str | None = None

    # Control flow
    condition: str | None = None
    control_type: str | None = None  # if | throw | write-warning

    # Integration detection
    integration_type: str | None = None
    integration_evidence: str | None = None


class PowerCLIScriptParser:
    """Parse PowerCLI scripts into structured statements."""

    def __init__(self):
        """Initialize the parser."""
        self.statements: list[PowerCLIStatement] = []

    def parse_file(self, script_file: Path) -> list[PowerCLIStatement]:
        """
        Parse PowerCLI script into statements.

        Returns statements in source order (sequential, unlike vRO graphs).

        Args:
            script_file: Path to PowerCLI .ps1 script

        Returns:
            List of parsed PowerCLIStatement objects
        """
        self.statements = []
        content = script_file.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            stmt = self._parse_statement(line, line_num)
            if stmt:
                self.statements.append(stmt)

        return self.statements

    def _parse_statement(self, line: str, line_num: int) -> PowerCLIStatement | None:
        """Parse single line into statement."""
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            return None

        # Comments
        if stripped.startswith("#"):
            return PowerCLIStatement(
                line_number=line_num,
                raw_text=line,
                statement_type="comment",
                category="control_flow",
            )

        # Param blocks - for now, categorize as context
        if stripped.startswith("Param"):
            return PowerCLIStatement(
                line_number=line_num,
                raw_text=line,
                statement_type="param",
                category="context",
            )

        # Control flow: if statements
        if_match = re.match(r"^\s*if\s*\((.*)\)", stripped)
        if if_match:
            return PowerCLIStatement(
                line_number=line_num,
                raw_text=line,
                statement_type="control_flow",
                category="control_flow",
                condition=if_match.group(1),
                control_type="if",
            )

        # Control flow: throw statements (validation gates)
        throw_match = re.match(r'^\s*throw\s+"(.*)"', stripped)
        if throw_match:
            return PowerCLIStatement(
                line_number=line_num,
                raw_text=line,
                statement_type="control_flow",
                category="gate",
                control_type="throw",
            )

        # Variable assignment
        assignment_match = re.match(r"^\$(\w+)\s*=\s*(.+)", stripped)
        if assignment_match:
            var_name = assignment_match.group(1)
            value = assignment_match.group(2).strip()
            return PowerCLIStatement(
                line_number=line_num,
                raw_text=line,
                statement_type="assignment",
                category="context",
                parameters={"variable": var_name, "value": value},
            )

        # Cmdlet invocation
        cmdlet_match = re.match(r"^([\w-]+)\s+(.*)", stripped)
        if cmdlet_match:
            cmdlet = cmdlet_match.group(1)
            params_str = cmdlet_match.group(2)

            # Parse parameters
            params = self._parse_cmdlet_parameters(params_str)

            # Check for pipe
            piped_to = None
            if "|" in params_str:
                pipe_split = params_str.split("|")
                piped_to = pipe_split[1].strip().split()[0]

            stmt = PowerCLIStatement(
                line_number=line_num,
                raw_text=line,
                statement_type="cmdlet",
                category="mutation",  # Default, will be recategorized
                cmdlet=cmdlet,
                parameters=params,
                piped_to=piped_to,
            )

            # Categorize and detect integrations
            self._categorize_statement(stmt)
            self._detect_integration(stmt)

            return stmt

        # Unrecognized statement
        return None

    def _parse_cmdlet_parameters(self, params_str: str) -> dict[str, str]:
        """Parse PowerCLI cmdlet parameters."""
        params = {}

        # Remove piped portion
        if "|" in params_str:
            params_str = params_str.split("|")[0]

        # Match -ParamName Value patterns, handling quoted and unquoted values
        # Pattern: -ParamName followed by either "quoted value" or unquoted value
        param_pattern = r'-(\w+)\s+(?:"([^"]*)"|(\$?\w+))'
        for match in re.finditer(param_pattern, params_str):
            param_name = match.group(1)
            # Group 2 is quoted value, group 3 is unquoted value
            param_value = match.group(2) if match.group(2) is not None else match.group(3)
            params[param_name] = param_value

        return params

    def _categorize_statement(self, stmt: PowerCLIStatement) -> None:
        """Categorize as context/lookup/mutation/integration/gate/control_flow."""
        # Gate - validations
        if stmt.control_type == "throw":
            stmt.category = "gate"
            return

        # Context - variable assignments
        if stmt.statement_type == "assignment" and not stmt.cmdlet:
            stmt.category = "context"
            return

        # Integration - special cmdlets
        if stmt.cmdlet in ["New-TagAssignment", "New-Snapshot", "New-NetworkAdapter"]:
            stmt.category = "integration"
            return

        # Lookup - Get-* cmdlets
        if stmt.cmdlet and stmt.cmdlet.startswith("Get-"):
            stmt.category = "lookup"
            return

        # Mutation - New-*, Set-*, Start-*, Stop-*, Remove-*
        mutation_prefixes = ["New-", "Set-", "Start-", "Stop-", "Remove-"]
        if stmt.cmdlet and any(stmt.cmdlet.startswith(p) for p in mutation_prefixes):
            stmt.category = "mutation"
            return

        # Default: mutation
        stmt.category = "mutation"

    def _detect_integration(self, stmt: PowerCLIStatement) -> None:
        """Detect integration type (tagging/snapshot/network/nsx)."""
        if not stmt.cmdlet:
            return

        # Tagging
        if stmt.cmdlet == "New-TagAssignment":
            stmt.integration_type = "tagging"
            tag_value = stmt.parameters.get("Tag", "")
            stmt.integration_evidence = f"New-TagAssignment -Tag \"{tag_value}\""
            return

        # Snapshots
        if stmt.cmdlet == "New-Snapshot":
            stmt.integration_type = "snapshot"
            stmt.integration_evidence = "New-Snapshot"
            return

        # Network adapters
        if stmt.cmdlet == "New-NetworkAdapter":
            stmt.integration_type = "network"
            network_name = stmt.parameters.get("NetworkName", "")
            stmt.integration_evidence = f"New-NetworkAdapter -NetworkName \"{network_name}\""
            return


class PowerShellToAnsibleTranslator:
    """Translate PowerShell/PowerCLI statements to Ansible tasks."""

    def __init__(self, profile: ProfileSchema | None = None):
        """
        Initialize translator.

        Args:
            profile: Optional ProfileSchema for profile-driven decisions
        """
        self.profile = profile
        self.cmdlet_mappings = self._load_cmdlet_mappings()

    def _load_cmdlet_mappings(self) -> dict:
        """Load cmdlet mappings from YAML file."""
        mappings_file = Path(__file__).parent / "powercli_cmdlet_mappings.yaml"
        if not mappings_file.exists():
            return {}

        with open(mappings_file) as f:
            return yaml.safe_load(f) or {}

    def translate_statements(
        self, statements: list[PowerCLIStatement]
    ) -> list[AnsibleTask]:
        """Translate parsed statements to Ansible tasks."""
        tasks = []

        # Track control flow context
        in_if_block = False
        current_condition = None

        for stmt in statements:
            # Handle control flow
            if stmt.statement_type == "control_flow":
                if stmt.control_type == "if":
                    in_if_block = True
                    current_condition = stmt.condition
                    continue
                elif stmt.control_type == "throw":
                    task = self._translate_validation(stmt, current_condition)
                    if task:
                        tasks.append(task)
                    in_if_block = False
                    current_condition = None
                    continue

            # Skip comments and param blocks
            if stmt.statement_type in ["comment", "param"]:
                continue

            # Translate based on category
            if stmt.category == "context" and stmt.statement_type == "assignment":
                task = self._translate_assignment(stmt)
                if task:
                    tasks.append(task)

            elif stmt.category == "mutation" and stmt.cmdlet:
                task = self._translate_cmdlet(stmt)
                if task:
                    tasks.append(task)

            elif stmt.category == "integration" and stmt.cmdlet:
                task = self._translate_integration(stmt)
                if task:
                    tasks.append(task)

            elif stmt.category == "lookup" and stmt.cmdlet:
                task = self._translate_lookup(stmt)
                if task:
                    tasks.append(task)

        return tasks

    def _translate_assignment(self, stmt: PowerCLIStatement) -> AnsibleTask | None:
        """Translate variable assignment to set_fact task."""
        var_name = stmt.parameters.get("variable", "unknown")
        value = stmt.parameters.get("value", "")

        # Clean up value (remove quotes if string literal)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        # Convert to snake_case
        ansible_var = var_name.lower()

        return AnsibleTask(
            name=f"Set {ansible_var}",
            module="ansible.builtin.set_fact",
            module_args={ansible_var: value},
            tags=["context"],
        )

    def _translate_validation(
        self, stmt: PowerCLIStatement, condition: str | None
    ) -> AnsibleTask | None:
        """Translate throw/validation to assert task."""
        if not condition:
            return None

        # Extract error message from throw statement
        throw_match = re.search(r'throw\s+"(.*)"', stmt.raw_text)
        error_msg = throw_match.group(1) if throw_match else "Validation failed"

        # Negate the condition (if condition TRUE, we throw, so assert it's FALSE)
        negated_condition = self._negate_condition(condition)

        return AnsibleTask(
            name=f"Validate {error_msg.split()[0].lower()}",
            module="ansible.builtin.assert",
            module_args={"that": [negated_condition], "fail_msg": error_msg},
            tags=["gate", "validation"],
        )

    def _negate_condition(self, condition: str) -> str:
        """Negate a PowerShell condition for assert."""
        # Convert PowerShell operators to Ansible/Jinja2
        condition = condition.replace("$", "")

        # Handle comparison operators
        if "-gt" in condition:
            return condition.replace("-gt", "<=")
        elif "-ge" in condition:
            return condition.replace("-ge", "<")
        elif "-lt" in condition:
            return condition.replace("-lt", ">=")
        elif "-le" in condition:
            return condition.replace("-le", ">")
        elif "-eq" in condition:
            return condition.replace("-eq", "!=")
        elif "-ne" in condition:
            return condition.replace("-ne", "==")

        # Default: just negate with 'not'
        return f"not ({condition})"

    def _translate_cmdlet(self, stmt: PowerCLIStatement) -> AnsibleTask | None:
        """Translate PowerCLI cmdlet to Ansible task."""
        cmdlet = stmt.cmdlet

        # Try to find mapping
        for category_mappings in self.cmdlet_mappings.values():
            for mapping_key, mapping in category_mappings.items():
                if mapping["match"]["cmdlet"] == cmdlet:
                    return self._apply_cmdlet_mapping(stmt, mapping)

        # No mapping found - create placeholder
        return AnsibleTask(
            name=f"TODO: Translate {cmdlet}",
            module="ansible.builtin.debug",
            module_args={"msg": f"Not yet implemented: {cmdlet}"},
            tags=["todo"],
        )

    def _apply_cmdlet_mapping(
        self, stmt: PowerCLIStatement, mapping: dict
    ) -> AnsibleTask:
        """Apply cmdlet mapping to create Ansible task."""
        module = mapping["ansible"]["module"]
        params_template = mapping["ansible"]["params"]

        # Substitute parameters
        params = {}
        for param_key, param_value in params_template.items():
            # Replace {ParamName} with actual values
            if isinstance(param_value, str) and "{" in param_value:
                # Handle templates like "{Name}" or "{MemoryGB}Gi"
                result = param_value
                # Find all {ParamName} patterns
                import re as param_re
                for match in param_re.finditer(r'\{(\w+)\}', param_value):
                    powercli_param = match.group(1)
                    actual_value = stmt.parameters.get(powercli_param, "")

                    # Convert to Ansible variable if starts with $
                    if actual_value.startswith("$"):
                        var_name = actual_value[1:].lower()
                        result = result.replace(match.group(0), f"{{{{ {var_name} }}}}")
                    else:
                        result = result.replace(match.group(0), actual_value)
                params[param_key] = result
            else:
                params[param_key] = param_value

        # Generate task name
        cmdlet_action = stmt.cmdlet.replace("-", " ").lower()
        entity_param = stmt.parameters.get("Name") or stmt.parameters.get("VM") or ""
        if entity_param.startswith("$"):
            entity_var = entity_param[1:].lower()
            task_name = f"{cmdlet_action.capitalize()} {{{{ {entity_var} }}}}"
        else:
            task_name = cmdlet_action.capitalize()

        tags = mapping.get("tags", [mapping.get("category", "mutation")])
        if not isinstance(tags, list):
            tags = [tags]

        return AnsibleTask(
            name=task_name,
            module=module,
            module_args=params,
            tags=tags,
        )

    def _translate_integration(self, stmt: PowerCLIStatement) -> AnsibleTask:
        """Translate integration cmdlet to adapter call or module."""
        cmdlet = stmt.cmdlet

        # Tagging
        if cmdlet == "New-TagAssignment":
            return self._translate_tagging(stmt)

        # Snapshot
        if cmdlet == "New-Snapshot":
            return self._translate_snapshot(stmt)

        # Network adapter (profile-driven)
        if cmdlet == "New-NetworkAdapter":
            return self._translate_network_adapter(stmt)

        # Unknown integration
        return AnsibleTask(
            name=f"TODO: Integration {cmdlet}",
            module="ansible.builtin.debug",
            module_args={"msg": f"Integration not yet implemented: {cmdlet}"},
            tags=["todo", "integration"],
        )

    def _translate_tagging(self, stmt: PowerCLIStatement) -> AnsibleTask:
        """Translate New-TagAssignment to Kubernetes labels."""
        entity = stmt.parameters.get("Entity", "")
        tag = stmt.parameters.get("Tag", "")

        # Parse tag "Category:Value" format
        if ":" in tag:
            tag_key, tag_value = tag.split(":", 1)
            tag_key = tag_key.strip().lower()
            tag_value = tag_value.strip().lower()
        else:
            tag_key = "tag"
            tag_value = tag.strip().lower()

        # Convert entity to variable
        if entity.startswith("$"):
            entity_var = entity[1:].lower()
            entity_ref = f"{{{{ {entity_var} }}}}"
        else:
            entity_ref = entity

        return AnsibleTask(
            name=f"Apply {tag_key} label",
            module="kubernetes.core.k8s",
            module_args={
                "state": "patched",
                "kind": "VirtualMachine",
                "name": entity_ref,
                "namespace": "{{ target_namespace }}",
                "definition": {"metadata": {"labels": {tag_key: tag_value}}},
            },
            tags=["integration", "tagging"],
        )

    def _translate_snapshot(self, stmt: PowerCLIStatement) -> AnsibleTask:
        """Translate New-Snapshot to VolumeSnapshot."""
        name = stmt.parameters.get("Name", "")
        vm = stmt.parameters.get("VM", "")

        # Convert parameters to variables
        if name.startswith("$"):
            name_ref = f"{{{{ {name[1:].lower()} }}}}"
        else:
            name_ref = name

        if vm.startswith("$"):
            vm_ref = f"{{{{ {vm[1:].lower()} }}}}"
        else:
            vm_ref = vm

        return AnsibleTask(
            name=f"Create snapshot {name_ref}",
            module="kubevirt.core.kubevirt_vm_snapshot",
            module_args={
                "state": "present",
                "name": name_ref,
                "vm_name": vm_ref,
                "namespace": "{{ target_namespace }}",
            },
            tags=["integration", "snapshot"],
        )

    def _translate_network_adapter(self, stmt: PowerCLIStatement) -> AnsibleTask:
        """Translate New-NetworkAdapter (profile-driven)."""
        # Check if profile has network_security configured
        if self.profile and self.profile.network_security:
            # Generate NAD adapter call
            network_name = stmt.parameters.get("NetworkName", "")
            vm = stmt.parameters.get("VM", "")

            if vm.startswith("$"):
                vm_ref = f"{{{{ {vm[1:].lower()} }}}}"
            else:
                vm_ref = vm

            return AnsibleTask(
                name=f"Attach network adapter to {vm_ref}",
                module="ansible.builtin.include_role",
                module_args={
                    "name": "../../adapters/nsx/create_segment",
                    "vars": {"vm_name": vm_ref, "network_name": network_name},
                },
                tags=["integration", "network"],
            )
        else:
            # BLOCKED stub
            evidence = stmt.integration_evidence or "New-NetworkAdapter"
            return AnsibleTask(
                name="BLOCKED - Network adapter creation requires configuration",
                module="ansible.builtin.fail",
                module_args={
                    "msg": f"""BLOCKED: Network Adapter Creation

This script requires network adapter creation.
Configure profile.network_security to proceed.

Evidence: {evidence}

TO FIX: Add to profile.yml:
  network_security:
    model: networkpolicy

Then re-run: ops-translate generate --profile <profile>"""
                },
                tags=["blocked", "network"],
            )

    def _translate_lookup(self, stmt: PowerCLIStatement) -> AnsibleTask | None:
        """Translate Get-* cmdlets to k8s_info lookups."""
        cmdlet = stmt.cmdlet

        if cmdlet == "Get-VM":
            name = stmt.parameters.get("Name", "")
            if name.startswith("$"):
                name_ref = f"{{{{ {name[1:].lower()} }}}}"
            else:
                name_ref = name

            return AnsibleTask(
                name=f"Get VM info for {name_ref}",
                module="kubernetes.core.k8s_info",
                module_args={
                    "kind": "VirtualMachine",
                    "name": name_ref,
                    "namespace": "{{ target_namespace }}",
                },
                tags=["lookup", "vm"],
            )

        # Generic Get cmdlet
        return AnsibleTask(
            name=f"Lookup {cmdlet}",
            module="ansible.builtin.debug",
            module_args={"msg": f"TODO: Implement {cmdlet}"},
            tags=["lookup", "todo"],
        )
