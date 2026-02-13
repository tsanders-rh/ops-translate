"""
Tests for effort metrics calculation and integration heatmap generation.
"""

from ops_translate.report.html import _calculate_effort_metrics, _generate_integration_heatmap


class TestEffortMetricsCalculation:
    """Tests for effort metrics calculation."""

    def test_empty_analysis_returns_zero_metrics(self):
        """Test that empty analysis data returns all zeros."""
        result = _calculate_effort_metrics(None, None)

        assert result["estate_summary"]["total_workflows"] == 0
        assert result["estate_summary"]["total_lines_of_code"] == 0
        assert result["estate_summary"]["external_integrations"] == 0
        assert result["estate_summary"]["approval_gates"] == 0
        assert result["effort_buckets"]["ready_now"] == 0
        assert result["effort_buckets"]["moderate"] == 0
        assert result["effort_buckets"]["complex"] == 0
        assert result["cost_drivers"] == []
        assert result["integration_heatmap"] == []

    def test_estate_summary_calculation(self):
        """Test estate summary metrics calculation."""
        analysis_data = {
            "total_workflows": 5,
            "workflows": {
                "workflow1": {
                    "classification": "automatable",
                    "total_tasks": 10,
                    "blocked_tasks": 0,
                    "adapter_tasks": 0,
                },
                "workflow2": {
                    "classification": "partial",
                    "total_tasks": 15,
                    "blocked_tasks": 0,
                    "adapter_tasks": 5,
                },
                "workflow3": {
                    "classification": "blocked",
                    "total_tasks": 20,
                    "blocked_tasks": 3,
                    "adapter_tasks": 0,
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        assert result["estate_summary"]["total_workflows"] == 5
        # Total tasks: 10 + 15 + 20 = 45, estimated at 20 lines per task = 900
        assert result["estate_summary"]["total_lines_of_code"] == 900

    def test_effort_bucket_classification_automatable(self):
        """Test that workflows with low scores are classified as ready."""
        analysis_data = {
            "total_workflows": 2,
            "workflows": {
                "simple_workflow": {
                    "classification": "automatable",
                    "total_tasks": 5,
                    "blocked_tasks": 0,
                    "adapter_tasks": 0,
                },
                "another_simple": {
                    "classification": "automatable",
                    "total_tasks": 3,
                    "blocked_tasks": 0,
                    "adapter_tasks": 0,
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # Both workflows should be ready (score 0)
        assert result["effort_buckets"]["ready_now"] == 2
        assert result["effort_buckets"]["moderate"] == 0
        assert result["effort_buckets"]["complex"] == 0

    def test_effort_bucket_classification_moderate(self):
        """Test that workflows with moderate scores are classified correctly."""
        analysis_data = {
            "total_workflows": 1,
            "workflows": {
                "moderate_workflow": {
                    "classification": "partial",
                    "total_tasks": 10,
                    "blocked_tasks": 0,
                    "adapter_tasks": 1,
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # Partial classification = +2, 1 adapter task = +1, total = 3 (moderate)
        assert result["effort_buckets"]["ready_now"] == 0
        assert result["effort_buckets"]["moderate"] == 1
        assert result["effort_buckets"]["complex"] == 0

    def test_effort_bucket_classification_complex(self):
        """Test that workflows with high scores are classified as complex."""
        analysis_data = {
            "total_workflows": 1,
            "workflows": {
                "complex_workflow": {
                    "classification": "blocked",
                    "total_tasks": 10,
                    "blocked_tasks": 2,
                    "adapter_tasks": 0,
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # Blocked classification = +4, 2 blocked tasks = +4, total = 8 (complex)
        assert result["effort_buckets"]["ready_now"] == 0
        assert result["effort_buckets"]["moderate"] == 0
        assert result["effort_buckets"]["complex"] == 1

    def test_cost_drivers_calculation(self):
        """Test cost drivers percentage calculation."""
        analysis_data = {
            "total_workflows": 10,
            "workflows": {
                f"workflow{i}": {
                    "classification": "blocked" if i < 5 else "automatable",
                    "total_tasks": 10,
                    "blocked_tasks": 1 if i < 5 else 0,
                    "adapter_tasks": 1 if i < 7 else 0,
                }
                for i in range(10)
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # 5 out of 10 are blocked = 50%
        # 7 out of 10 have adapters = 70%
        assert len(result["cost_drivers"]) > 0

        # Find the config decisions driver
        config_driver = next(
            (d for d in result["cost_drivers"] if "configuration decisions" in d["label"]), None
        )
        assert config_driver is not None
        assert config_driver["percentage"] == 50

        # Find the integrations driver
        integration_driver = next(
            (d for d in result["cost_drivers"] if "external integrations" in d["label"]), None
        )
        assert integration_driver is not None
        assert integration_driver["percentage"] == 70

    def test_integration_detection_from_gaps(self):
        """Test external integration detection from gaps data."""
        analysis_data = {
            "total_workflows": 1,
            "workflows": {
                "workflow1": {
                    "classification": "blocked",
                    "total_tasks": 5,
                    "blocked_tasks": 1,
                    "adapter_tasks": 0,
                },
            },
        }

        gaps_data = {
            "components": [
                {
                    "component_type": "servicenow_integration",
                    "classification": "BLOCKED",
                },
                {
                    "component_type": "nsx_firewall",
                    "classification": "PARTIAL",
                },
                {
                    "component_type": "approval_gate",
                    "classification": "SUPPORTED",
                },
            ],
        }

        result = _calculate_effort_metrics(analysis_data, gaps_data)

        # Should detect ITSM and NSX integrations
        assert result["estate_summary"]["external_integrations"] == 2
        # Should detect approval gate
        assert result["estate_summary"]["approval_gates"] == 1


class TestIntegrationHeatmap:
    """Tests for integration heatmap generation."""

    def test_empty_workflows_returns_empty_heatmap(self):
        """Test that empty workflows return empty heatmap."""
        result = _generate_integration_heatmap({}, None)
        assert result == []

    def test_workflow_without_integrations_not_included(self):
        """Test that workflows without integrations are not in heatmap."""
        workflows = {
            "simple_workflow": {
                "classification": "automatable",
                "blocker_details": [],
            },
        }

        result = _generate_integration_heatmap(workflows, None)
        assert result == []

    def test_servicenow_integration_detection(self):
        """Test ServiceNow/ITSM integration detection."""
        workflows = {
            "incident_workflow": {
                "classification": "blocked",
                "blocker_details": [
                    {
                        "task": "BLOCKED - ServiceNow integration",
                        "message": "Missing profile.itsm configuration",
                    },
                ],
            },
        }

        result = _generate_integration_heatmap(workflows, None)

        assert len(result) == 1
        assert result[0]["workflow"] == "incident_workflow"
        assert result[0]["integrations"]["ITSM"] is True
        assert result[0]["integrations"]["Approval"] is False

    def test_nsx_integration_detection(self):
        """Test NSX firewall integration detection."""
        workflows = {
            "firewall_workflow": {
                "classification": "blocked",
                "blocker_details": [
                    {
                        "task": "BLOCKED - NSX firewall rule",
                        "message": "NSX-T configuration required",
                    },
                ],
            },
        }

        result = _generate_integration_heatmap(workflows, None)

        assert len(result) == 1
        assert result[0]["integrations"]["NSX"] is True

    def test_approval_integration_detection(self):
        """Test approval gate detection."""
        workflows = {
            "approval_workflow": {
                "classification": "blocked",
                "blocker_details": [
                    {
                        "task": "BLOCKED - Approval gate",
                        "message": "Approval configuration needed",
                    },
                ],
            },
        }

        result = _generate_integration_heatmap(workflows, None)

        assert len(result) == 1
        assert result[0]["integrations"]["Approval"] is True

    def test_multiple_integrations_per_workflow(self):
        """Test detection of multiple integrations in one workflow."""
        workflows = {
            "complex_workflow": {
                "classification": "blocked",
                "blocker_details": [
                    {
                        "task": "BLOCKED - ServiceNow",
                        "message": "ITSM integration required",
                    },
                    {
                        "task": "BLOCKED - NSX firewall",
                        "message": "Firewall rules needed",
                    },
                    {
                        "task": "BLOCKED - Approval gate",
                        "message": "Approval required",
                    },
                ],
            },
        }

        result = _generate_integration_heatmap(workflows, None)

        assert len(result) == 1
        assert result[0]["integrations"]["ITSM"] is True
        assert result[0]["integrations"]["NSX"] is True
        assert result[0]["integrations"]["Approval"] is True
        assert result[0]["integrations"]["DNS"] is False

    def test_storage_integration_detection(self):
        """Test storage/datastore integration detection."""
        workflows = {
            "storage_workflow": {
                "classification": "blocked",
                "blocker_details": [
                    {
                        "task": "BLOCKED - Storage tier mapping",
                        "message": "Datastore mapping required",
                    },
                ],
            },
        }

        result = _generate_integration_heatmap(workflows, None)

        assert len(result) == 1
        assert result[0]["integrations"]["Storage"] is True

    def test_ad_integration_detection(self):
        """Test Active Directory integration detection."""
        workflows = {
            "ad_workflow": {
                "classification": "blocked",
                "blocker_details": [
                    {
                        "task": "BLOCKED - AD user creation",
                        "message": "ActiveDirectory configuration needed",
                    },
                ],
            },
        }

        result = _generate_integration_heatmap(workflows, None)

        assert len(result) == 1
        assert result[0]["integrations"]["AD"] is True


class TestEffortScoring:
    """Tests for effort scoring heuristic."""

    def test_scoring_blocked_classification(self):
        """Test that blocked classification adds significant points."""
        analysis_data = {
            "total_workflows": 1,
            "workflows": {
                "blocked_workflow": {
                    "classification": "blocked",
                    "total_tasks": 5,
                    "blocked_tasks": 0,
                    "adapter_tasks": 0,
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # Blocked classification alone should make it complex (score = 4)
        assert result["effort_buckets"]["complex"] == 1

    def test_scoring_partial_classification(self):
        """Test that partial classification adds moderate points."""
        analysis_data = {
            "total_workflows": 1,
            "workflows": {
                "partial_workflow": {
                    "classification": "partial",
                    "total_tasks": 5,
                    "blocked_tasks": 0,
                    "adapter_tasks": 0,
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # Partial classification should make it moderate (score = 2)
        assert result["effort_buckets"]["moderate"] == 1

    def test_scoring_blocked_tasks(self):
        """Test that blocked tasks add significant points."""
        analysis_data = {
            "total_workflows": 1,
            "workflows": {
                "workflow_with_blockers": {
                    "classification": "automatable",
                    "total_tasks": 10,
                    "blocked_tasks": 3,
                    "adapter_tasks": 0,
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # 3 blocked tasks = +6 points (complex)
        assert result["effort_buckets"]["complex"] == 1

    def test_scoring_adapter_tasks_capped(self):
        """Test that adapter task scoring is capped at +2."""
        analysis_data = {
            "total_workflows": 1,
            "workflows": {
                "many_adapters": {
                    "classification": "automatable",
                    "total_tasks": 20,
                    "blocked_tasks": 0,
                    "adapter_tasks": 10,  # Many adapters
                },
            },
        }

        result = _calculate_effort_metrics(analysis_data, None)

        # Even with 10 adapter tasks, cap at +2 (moderate bucket)
        assert result["effort_buckets"]["moderate"] == 1
