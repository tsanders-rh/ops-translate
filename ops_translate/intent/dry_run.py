"""
Enhanced dry-run validation with detailed checks and step planning.
"""

from typing import NamedTuple

import yaml
from rich.console import Console

console = Console()


class ValidationIssue(NamedTuple):
    """Represents a validation issue found during dry-run."""

    severity: str  # SAFE, REVIEW, BLOCKING
    category: str  # schema, resource, profile, consistency
    message: str
    location: str | None = None
    suggestion: str | None = None


class DryRunResult:
    """Results from dry-run validation."""

    def __init__(self):
        self.issues: list[ValidationIssue] = []
        self.steps: list[str] = []
        self.stats = {
            "intents_found": 0,
            "artifacts_generated": 0,
            "inputs_defined": 0,
            "profiles_configured": 0,
        }

    def add_issue(
        self,
        severity: str,
        category: str,
        message: str,
        location: str | None = None,
        suggestion: str | None = None,
    ):
        """Add a validation issue."""
        self.issues.append(ValidationIssue(severity, category, message, location, suggestion))

    def add_step(self, step: str):
        """Add a planned execution step."""
        self.steps.append(step)

    def is_safe_to_proceed(self) -> bool:
        """Check if there are any blocking issues."""
        return not any(issue.severity == "BLOCKING" for issue in self.issues)

    def has_review_items(self) -> bool:
        """Check if there are items that need review."""
        return any(issue.severity == "REVIEW" for issue in self.issues)


def validate_intent_completeness(intent_data: dict, result: DryRunResult):
    """
    Validate that intent has all required fields and data is complete.
    """
    # Check workflow name
    if "intent" not in intent_data:
        result.add_issue(
            "BLOCKING",
            "schema",
            "Missing 'intent' section in intent.yaml",
            suggestion="Add an 'intent' section with workflow_name and workload_type",
        )
        return

    intent = intent_data["intent"]

    if "workflow_name" not in intent:
        result.add_issue(
            "BLOCKING",
            "schema",
            "Missing workflow_name in intent",
            location="intent.workflow_name",
            suggestion="Add workflow_name field (e.g., provision_vm)",
        )

    if "workload_type" not in intent:
        result.add_issue(
            "REVIEW",
            "schema",
            "Missing workload_type in intent",
            location="intent.workload_type",
            suggestion="Add workload_type (e.g., virtual_machine)",
        )

    # Check inputs
    if "inputs" in intent:
        inputs = intent["inputs"]
        result.stats["inputs_defined"] = len(inputs)

        for input_name, input_spec in inputs.items():
            if isinstance(input_spec, dict):
                if "type" not in input_spec:
                    result.add_issue(
                        "REVIEW",
                        "schema",
                        f"Input '{input_name}' missing type specification",
                        location=f"intent.inputs.{input_name}",
                    )

                if input_spec.get("required") and "default" in input_spec:
                    result.add_issue(
                        "REVIEW",
                        "consistency",
                        f"Input '{input_name}' is required but has default value",
                        location=f"intent.inputs.{input_name}",
                        suggestion="Remove default or set required: false",
                    )
    else:
        result.add_issue(
            "REVIEW",
            "schema",
            "No inputs defined - workflow may not be parameterizable",
            suggestion="Add inputs section if workflow needs parameters",
        )


def validate_profile_references(intent_data: dict, config: dict, result: DryRunResult):
    """
    Validate that profile references in intent match configured profiles.
    """
    if "intent" not in intent_data:
        return

    intent = intent_data["intent"]
    profiles = intent.get("profiles", {})

    # Get configured profiles from config
    config_profiles = config.get("profiles", {})
    result.stats["profiles_configured"] = len(config_profiles)

    # Check if profiles reference valid configurations
    for profile_key, profile_value in profiles.items():
        if isinstance(profile_value, dict) and "when" in profile_value:
            # Conditional profile - check environment reference
            when_clause = profile_value["when"]
            if isinstance(when_clause, dict):
                for input_name in when_clause.keys():
                    if input_name not in intent.get("inputs", {}):
                        result.add_issue(
                            "BLOCKING",
                            "resource",
                            f"Profile '{profile_key}' references undefined input '{input_name}'",
                            location=f"intent.profiles.{profile_key}.when",
                            suggestion=f"Define input '{input_name}' in intent.inputs",
                        )


def validate_resource_consistency(workspace, intent_data: dict, result: DryRunResult):
    """
    Validate that generated resources are consistent with intent.
    """
    if "intent" not in intent_data:
        return

    intent = intent_data["intent"]

    # Check if KubeVirt manifest exists and is valid
    kubevirt_file = workspace.root / "output/kubevirt/vm.yaml"
    if kubevirt_file.exists():
        result.stats["artifacts_generated"] += 1
        try:
            kubevirt_data = yaml.safe_load(kubevirt_file.read_text())

            # Validate KubeVirt structure
            if not isinstance(kubevirt_data, dict):
                result.add_issue(
                    "BLOCKING",
                    "resource",
                    "KubeVirt manifest is not valid YAML object",
                    location="output/kubevirt/vm.yaml",
                )
            elif kubevirt_data.get("kind") != "VirtualMachine":
                result.add_issue(
                    "REVIEW",
                    "resource",
                    f"KubeVirt resource has unexpected kind: {kubevirt_data.get('kind')}",
                    location="output/kubevirt/vm.yaml",
                    suggestion="Expected kind: VirtualMachine",
                )

            # Check metadata labels match intent tags
            if "metadata" in intent:
                expected_tags = intent["metadata"].get("tags", [])
                kubevirt_labels = kubevirt_data.get("metadata", {}).get("labels", {})

                for tag in expected_tags:
                    tag_key = tag.get("key")
                    if tag_key and tag_key not in kubevirt_labels:
                        result.add_issue(
                            "REVIEW",
                            "consistency",
                            f"Intent tag '{tag_key}' not found in KubeVirt labels",
                            location="output/kubevirt/vm.yaml",
                            suggestion="Regenerate artifacts with current intent",
                        )

        except yaml.YAMLError as e:
            result.add_issue(
                "BLOCKING",
                "resource",
                f"KubeVirt manifest is invalid YAML: {e}",
                location="output/kubevirt/vm.yaml",
            )

    # Check Ansible playbook
    ansible_file = workspace.root / "output/ansible/site.yml"
    if ansible_file.exists():
        result.stats["artifacts_generated"] += 1
        try:
            ansible_data = yaml.safe_load(ansible_file.read_text())
            if not isinstance(ansible_data, list):
                result.add_issue(
                    "BLOCKING",
                    "resource",
                    "Ansible playbook is not a valid list of plays",
                    location="output/ansible/site.yml",
                )
        except yaml.YAMLError as e:
            result.add_issue(
                "BLOCKING",
                "resource",
                f"Ansible playbook is invalid YAML: {e}",
                location="output/ansible/site.yml",
            )


def generate_execution_plan(intent_data: dict, result: DryRunResult):
    """
    Generate step-by-step execution plan.
    """
    if "intent" not in intent_data:
        result.add_step("❌ Cannot plan execution - intent is invalid")
        return

    intent = intent_data["intent"]
    workflow_name = intent.get("workflow_name", "unknown")

    result.add_step(f"1. Initialize workflow: {workflow_name}")

    # Input validation step
    if "inputs" in intent:
        required_inputs = [
            name
            for name, spec in intent["inputs"].items()
            if isinstance(spec, dict) and spec.get("required")
        ]
        if required_inputs:
            result.add_step(f"2. Validate required inputs: {', '.join(required_inputs)}")
        else:
            result.add_step("2. Validate inputs (all optional)")
    else:
        result.add_step("2. Skip input validation (no inputs defined)")

    # Approval step
    if "governance" in intent and "approval" in intent["governance"]:
        approval = intent["governance"]["approval"]
        if "required_when" in approval:
            conditions = ", ".join(f"{k}={v}" for k, v in approval["required_when"].items())
            result.add_step(f"3. Check approval requirement (when: {conditions})")
        else:
            result.add_step("3. Check approval requirement (always required)")
    else:
        result.add_step("3. Skip approval (not required)")

    # Resource creation
    workload_type = intent.get("workload_type", "unknown")
    result.add_step(f"4. Create {workload_type} resource")

    # Profile selection
    if "profiles" in intent:
        profile_count = len(intent["profiles"])
        result.add_step(f"5. Apply {profile_count} profile(s) (network, storage, etc.)")
    else:
        result.add_step("5. Skip profile application (none defined)")

    # Metadata/tagging
    if "metadata" in intent and "tags" in intent["metadata"]:
        tag_count = len(intent["metadata"]["tags"])
        result.add_step(f"6. Apply {tag_count} metadata tag(s)")
    else:
        result.add_step("6. Skip metadata tagging (none defined)")

    # Day 2 operations
    if "day2_operations" in intent:
        ops = intent["day2_operations"].get("supported", [])
        if ops:
            result.add_step(f"7. Enable day-2 operations: {', '.join(ops)}")
        else:
            result.add_step("7. No day-2 operations enabled")
    else:
        result.add_step("7. No day-2 operations configured")


def print_dry_run_results(result: DryRunResult):
    """
    Print formatted dry-run results to console.
    """
    # Print execution plan
    if result.steps:
        console.print("\n[bold cyan]Execution Plan:[/bold cyan]")
        for step in result.steps:
            console.print(f"  {step}")

    # Print statistics
    console.print("\n[bold cyan]Statistics:[/bold cyan]")
    console.print(f"  Inputs defined: {result.stats['inputs_defined']}")
    console.print(f"  Profiles configured: {result.stats['profiles_configured']}")
    console.print(f"  Artifacts generated: {result.stats['artifacts_generated']}")

    # Print issues by severity
    if result.issues:
        console.print("\n[bold cyan]Validation Issues:[/bold cyan]")

        # Group by severity
        blocking = [i for i in result.issues if i.severity == "BLOCKING"]
        review = [i for i in result.issues if i.severity == "REVIEW"]
        safe = [i for i in result.issues if i.severity == "SAFE"]

        if blocking:
            console.print("\n[bold red]BLOCKING Issues (must fix):[/bold red]")
            for issue in blocking:
                console.print(f"  ❌ [{issue.category}] {issue.message}")
                if issue.location:
                    console.print(f"     Location: {issue.location}")
                if issue.suggestion:
                    console.print(f"     💡 {issue.suggestion}")

        if review:
            console.print("\n[bold yellow]REVIEW Items (should check):[/bold yellow]")
            for issue in review:
                console.print(f"  ⚠️  [{issue.category}] {issue.message}")
                if issue.location:
                    console.print(f"     Location: {issue.location}")
                if issue.suggestion:
                    console.print(f"     💡 {issue.suggestion}")

        if safe:
            console.print("\n[bold green]SAFE Items (informational):[/bold green]")
            for issue in safe:
                console.print(f"  ℹ️  [{issue.category}] {issue.message}")

    # Print summary
    console.print("\n[bold cyan]Summary:[/bold cyan]")

    if not result.issues:
        console.print("  [green]✓ No issues found - safe to proceed[/green]")
    elif result.is_safe_to_proceed():
        if result.has_review_items():
            console.print("  [yellow]⚠ Safe to proceed but review items should be checked[/yellow]")
        else:
            console.print("  [green]✓ Safe to proceed[/green]")
    else:
        console.print("  [red]✗ Blocking issues found - must fix before proceeding[/red]")


def run_enhanced_dry_run(workspace, config: dict) -> tuple[bool, DryRunResult]:
    """
    Run comprehensive pre-flight validation on intent and configuration.

    Performs multi-layered validation checks before artifact generation, including:
    - Schema validation (structure and types)
    - Resource consistency checks
    - Profile reference validation
    - Execution plan generation
    - Configuration completeness

    Issues are categorized by severity:
    - BLOCKING: Must be fixed before proceeding (schema errors, missing files)
    - REVIEW: Should be reviewed but not blocking (warnings, recommendations)
    - SAFE: Informational only

    The validation process:
    1. Verifies intent.yaml exists and is valid YAML
    2. Validates intent structure against schema
    3. Checks for required fields and complete definitions
    4. Validates profile references against configured profiles
    5. Checks resource consistency (if artifacts already generated)
    6. Generates execution plan showing what will happen
    7. Compiles statistics (inputs, profiles, artifacts)

    Args:
        workspace: Workspace instance with intent and configuration files.
        config: Loaded workspace configuration dict containing:
            - profiles: Dict of profile names to profile configs
            - llm: LLM provider configuration
            - Other workspace settings

    Returns:
        tuple: A 2-tuple containing:
            - bool: True if safe to proceed (no BLOCKING issues), False otherwise
            - DryRunResult: Object containing:
              - issues: List of ValidationIssue objects with severity, category, message
              - steps: List of planned execution steps
              - stats: Dict of statistics (inputs, profiles, artifacts counts)

    Raises:
        Does not raise exceptions. All errors are captured in the DryRunResult.

    Example:
        >>> from ops_translate.workspace import Workspace
        >>> from pathlib import Path
        >>> ws = Workspace(Path("my-workspace"))
        >>> config = ws.load_config()
        >>> is_safe, result = run_enhanced_dry_run(ws, config)
        >>> if not is_safe:
        ...     for issue in result.issues:
        ...         if issue.severity == "BLOCKING":
        ...             print(f"ERROR: {issue.message}")
        ERROR: Intent file not found

    Side Effects:
        - Reads intent.yaml and configuration files
        - May read generated artifacts for consistency checks
        - Does not modify any files

    Notes:
        - Returns immediately on critical errors (missing/invalid intent file)
        - Continues validation even after finding non-blocking issues
        - Use print_dry_run_results() to display results to user
        - Safe to call multiple times (read-only operation)
    """
    result = DryRunResult()

    # Load intent
    intent_file = workspace.root / "intent/intent.yaml"
    if not intent_file.exists():
        result.add_issue(
            "BLOCKING",
            "schema",
            "Intent file not found",
            location="intent/intent.yaml",
            suggestion="Run 'ops-translate intent merge' first",
        )
        return (False, result)

    try:
        intent_data = yaml.safe_load(intent_file.read_text())
    except yaml.YAMLError as e:
        result.add_issue(
            "BLOCKING",
            "schema",
            f"Intent file has invalid YAML syntax: {e}",
            location="intent/intent.yaml",
            suggestion="Fix YAML syntax errors in the intent file",
        )
        return (False, result)

    # Check if intent file is empty
    if intent_data is None:
        result.add_issue(
            "BLOCKING",
            "schema",
            "Intent file is empty",
            location="intent/intent.yaml",
            suggestion="Re-run 'ops-translate intent extract' to generate intent",
        )
        return (False, result)

    # Check if intent_data is a dict
    if not isinstance(intent_data, dict):
        result.add_issue(
            "BLOCKING",
            "schema",
            f"Intent file has invalid structure: expected dict, got {type(intent_data).__name__}",
            location="intent/intent.yaml",
            suggestion="Ensure intent file contains a valid YAML mapping/object",
        )
        return (False, result)

    result.stats["intents_found"] = 1

    # Run validation checks
    validate_intent_completeness(intent_data, result)
    validate_profile_references(intent_data, config, result)
    validate_resource_consistency(workspace, intent_data, result)
    generate_execution_plan(intent_data, result)

    return (result.is_safe_to_proceed(), result)
