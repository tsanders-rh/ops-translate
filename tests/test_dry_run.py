"""
Tests for enhanced dry-run validation.
"""

import pytest
import yaml

from ops_translate.intent.dry_run import (
    DryRunResult,
    generate_execution_plan,
    run_enhanced_dry_run,
    validate_intent_completeness,
    validate_profile_references,
    validate_resource_consistency,
)


class TestDryRunResult:
    """Tests for DryRunResult class."""

    def test_add_issue(self):
        """Test adding validation issues."""
        result = DryRunResult()
        result.add_issue("BLOCKING", "schema", "Test error", "test.yaml", "Fix it")

        assert len(result.issues) == 1
        assert result.issues[0].severity == "BLOCKING"
        assert result.issues[0].category == "schema"
        assert result.issues[0].message == "Test error"

    def test_add_step(self):
        """Test adding execution steps."""
        result = DryRunResult()
        result.add_step("Step 1")
        result.add_step("Step 2")

        assert len(result.steps) == 2
        assert result.steps[0] == "Step 1"

    def test_is_safe_to_proceed_with_blocking(self):
        """Test safety check with blocking issues."""
        result = DryRunResult()
        result.add_issue("BLOCKING", "schema", "Error")

        assert not result.is_safe_to_proceed()

    def test_is_safe_to_proceed_with_review_only(self):
        """Test safety check with only review issues."""
        result = DryRunResult()
        result.add_issue("REVIEW", "consistency", "Warning")

        assert result.is_safe_to_proceed()

    def test_has_review_items(self):
        """Test review items detection."""
        result = DryRunResult()
        result.add_issue("REVIEW", "consistency", "Warning")

        assert result.has_review_items()


class TestValidateIntentCompleteness:
    """Tests for intent completeness validation."""

    def test_missing_intent_section(self):
        """Test validation with missing intent section."""
        result = DryRunResult()
        intent_data = {"schema_version": 1}

        validate_intent_completeness(intent_data, result)

        assert len(result.issues) == 1
        assert result.issues[0].severity == "BLOCKING"
        assert "Missing 'intent' section" in result.issues[0].message

    def test_missing_workflow_name(self):
        """Test validation with missing workflow name."""
        result = DryRunResult()
        intent_data = {"intent": {}}

        validate_intent_completeness(intent_data, result)

        blocking = [i for i in result.issues if i.severity == "BLOCKING"]
        assert any("workflow_name" in i.message for i in blocking)

    def test_missing_workload_type(self):
        """Test validation with missing workload type."""
        result = DryRunResult()
        intent_data = {"intent": {"workflow_name": "test"}}

        validate_intent_completeness(intent_data, result)

        review = [i for i in result.issues if i.severity == "REVIEW"]
        assert any("workload_type" in i.message for i in review)

    def test_input_missing_type(self):
        """Test validation with input missing type."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "test",
                "inputs": {"vm_name": {"required": True}},
            }
        }

        validate_intent_completeness(intent_data, result)

        review = [i for i in result.issues if i.severity == "REVIEW"]
        assert any("missing type" in i.message for i in review)

    def test_required_input_with_default(self):
        """Test validation with required input that has default."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "test",
                "inputs": {"vm_name": {"type": "string", "required": True, "default": "vm1"}},
            }
        }

        validate_intent_completeness(intent_data, result)

        review = [i for i in result.issues if i.severity == "REVIEW"]
        assert any("required but has default" in i.message for i in review)

    def test_no_inputs_defined(self):
        """Test validation with no inputs."""
        result = DryRunResult()
        intent_data = {"intent": {"workflow_name": "test"}}

        validate_intent_completeness(intent_data, result)

        review = [i for i in result.issues if i.severity == "REVIEW"]
        assert any("No inputs defined" in i.message for i in review)


class TestValidateProfileReferences:
    """Tests for profile reference validation."""

    def test_profile_references_undefined_input(self):
        """Test profile referencing undefined input."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "inputs": {"cpu": {"type": "integer"}},
                "profiles": {"network": {"when": {"environment": "prod"}, "value": "prod-net"}},
            }
        }
        config = {"profiles": {}}

        validate_profile_references(intent_data, config, result)

        blocking = [i for i in result.issues if i.severity == "BLOCKING"]
        assert any("references undefined input" in i.message for i in blocking)

    def test_profile_references_valid_input(self):
        """Test profile with valid input reference."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "inputs": {"environment": {"type": "string"}},
                "profiles": {"network": {"when": {"environment": "prod"}, "value": "prod-net"}},
            }
        }
        config = {"profiles": {}}

        validate_profile_references(intent_data, config, result)

        blocking = [i for i in result.issues if i.severity == "BLOCKING"]
        assert len(blocking) == 0


class TestValidateResourceConsistency:
    """Tests for resource consistency validation."""

    def test_kubevirt_invalid_yaml(self, tmp_path):
        """Test validation with invalid KubeVirt YAML."""
        from ops_translate.workspace import Workspace

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        kubevirt_file = workspace.root / "output/kubevirt/vm.yaml"
        kubevirt_file.write_text("invalid: yaml: content:")

        result = DryRunResult()
        intent_data = {"intent": {}}

        validate_resource_consistency(workspace, intent_data, result)

        blocking = [i for i in result.issues if i.severity == "BLOCKING"]
        assert any("invalid YAML" in i.message for i in blocking)

    def test_kubevirt_wrong_kind(self, tmp_path):
        """Test validation with wrong KubeVirt kind."""
        from ops_translate.workspace import Workspace

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        kubevirt_file = workspace.root / "output/kubevirt/vm.yaml"
        kubevirt_file.write_text(yaml.dump({"kind": "Pod", "metadata": {}}))

        result = DryRunResult()
        intent_data = {"intent": {}}

        validate_resource_consistency(workspace, intent_data, result)

        review = [i for i in result.issues if i.severity == "REVIEW"]
        assert any("unexpected kind" in i.message for i in review)

    def test_missing_intent_tags_in_kubevirt(self, tmp_path):
        """Test validation when intent tags not in KubeVirt."""
        from ops_translate.workspace import Workspace

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        kubevirt_file = workspace.root / "output/kubevirt/vm.yaml"
        kubevirt_data = {"kind": "VirtualMachine", "metadata": {"labels": {}}}
        kubevirt_file.write_text(yaml.dump(kubevirt_data))

        result = DryRunResult()
        intent_data = {
            "intent": {"metadata": {"tags": [{"key": "env", "value_from": "environment"}]}}
        }

        validate_resource_consistency(workspace, intent_data, result)

        review = [i for i in result.issues if i.severity == "REVIEW"]
        assert any("not found in KubeVirt labels" in i.message for i in review)

    def test_ansible_invalid_structure(self, tmp_path):
        """Test validation with invalid Ansible structure."""
        from ops_translate.workspace import Workspace

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        ansible_file = workspace.root / "output/ansible/site.yml"
        ansible_file.write_text(yaml.dump({"not": "a list"}))

        result = DryRunResult()
        intent_data = {"intent": {}}

        validate_resource_consistency(workspace, intent_data, result)

        blocking = [i for i in result.issues if i.severity == "BLOCKING"]
        assert any("not a valid list" in i.message for i in blocking)


class TestGenerateExecutionPlan:
    """Tests for execution plan generation."""

    def test_basic_execution_plan(self):
        """Test basic execution plan generation."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "provision_vm",
                "workload_type": "virtual_machine",
            }
        }

        generate_execution_plan(intent_data, result)

        assert len(result.steps) > 0
        assert any("provision_vm" in step for step in result.steps)
        assert any("virtual_machine" in step for step in result.steps)

    def test_plan_with_required_inputs(self):
        """Test plan with required inputs."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "test",
                "inputs": {
                    "vm_name": {"type": "string", "required": True},
                    "cpu": {"type": "integer", "required": True},
                },
            }
        }

        generate_execution_plan(intent_data, result)

        assert any("vm_name" in step and "cpu" in step for step in result.steps)

    def test_plan_with_approval(self):
        """Test plan with approval requirement."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "test",
                "governance": {
                    "approval": {"required_when": {"environment": "prod"}}
                },
            }
        }

        generate_execution_plan(intent_data, result)

        assert any("approval" in step.lower() for step in result.steps)

    def test_plan_with_profiles(self):
        """Test plan with profiles."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "test",
                "profiles": {"network": "prod-net", "storage": "gold"},
            }
        }

        generate_execution_plan(intent_data, result)

        assert any("profile" in step.lower() for step in result.steps)

    def test_plan_with_metadata_tags(self):
        """Test plan with metadata tags."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "test",
                "metadata": {
                    "tags": [
                        {"key": "env", "value_from": "environment"},
                        {"key": "owner", "value_from": "owner_email"},
                    ]
                },
            }
        }

        generate_execution_plan(intent_data, result)

        assert any("tag" in step.lower() for step in result.steps)

    def test_plan_with_day2_operations(self):
        """Test plan with day-2 operations."""
        result = DryRunResult()
        intent_data = {
            "intent": {
                "workflow_name": "test",
                "day2_operations": {"supported": ["start", "stop", "reconfigure"]},
            }
        }

        generate_execution_plan(intent_data, result)

        assert any("day-2" in step.lower() for step in result.steps)


class TestRunEnhancedDryRun:
    """Tests for full dry-run execution."""

    def test_missing_intent_file(self, tmp_path):
        """Test dry-run with missing intent file."""
        from ops_translate.workspace import Workspace

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        config = {}
        is_safe, result = run_enhanced_dry_run(workspace, config)

        assert not is_safe
        assert any("Intent file not found" in i.message for i in result.issues)

    def test_successful_dry_run(self, tmp_path):
        """Test successful dry-run with valid intent."""
        from ops_translate.workspace import Workspace

        workspace = Workspace(tmp_path / "workspace")
        workspace.initialize()

        intent_file = workspace.root / "intent/intent.yaml"
        intent_data = {
            "schema_version": 1,
            "intent": {
                "workflow_name": "provision_vm",
                "workload_type": "virtual_machine",
                "inputs": {"vm_name": {"type": "string", "required": True}},
            },
        }
        intent_file.write_text(yaml.dump(intent_data))

        config = {"profiles": {"lab": {}}}
        is_safe, result = run_enhanced_dry_run(workspace, config)

        # Should be safe even with some review items
        assert result.stats["intents_found"] == 1
        assert len(result.steps) > 0
