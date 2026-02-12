"""
Tests for interview evidence formatting (Issue #55).

Tests that evidence from action scripts is properly displayed in interview questions.
"""

from pathlib import Path

from ops_translate.intent.classify import ClassifiedComponent, MigrationPath, TranslatabilityLevel
from ops_translate.intent.interview import (
    _api_call_questions,
    _approval_questions,
    _format_evidence_for_display,
    _nsx_firewall_questions,
    _nsx_segment_questions,
)


class TestFormatEvidence:
    """Tests for _format_evidence_for_display() helper function."""

    def test_format_evidence_for_action_script(self):
        """Test that evidence from action script shows 'Action' source type."""
        component = ClassifiedComponent(
            name="nsxClient.createFirewallRule",
            component_type="nsx_firewall_rules",
            level=TranslatabilityLevel.PARTIAL,
            reason="Test",
            openshift_equivalent="NetworkPolicy",
            migration_path=MigrationPath.PATH_A,
            evidence="Pattern match: nsxClient.createFirewallRule in context (action:com.acme.nsx/createFirewallRule): nsxClient.createFirewallRule({name: 'test'})",
            location="action:com.acme.nsx/createFirewallRule",
            recommendations=[],
        )

        result = _format_evidence_for_display(component)

        assert "Evidence detected:" in result
        assert "Source: Action (com.acme.nsx/createFirewallRule)" in result

    def test_format_evidence_for_workflow_script(self):
        """Test that evidence from workflow shows 'Workflow' source type."""
        component = ClassifiedComponent(
            name="Create Firewall Rule",
            component_type="nsx_firewall_rules",
            level=TranslatabilityLevel.PARTIAL,
            reason="Test",
            openshift_equivalent="NetworkPolicy",
            migration_path=MigrationPath.PATH_A,
            evidence="Workflow item name/type contains NSX keyword (workflow.xml:67): Create Firewall Rule",
            location="workflow.xml:67",
            recommendations=[],
        )

        result = _format_evidence_for_display(component)

        assert "Evidence detected:" in result
        assert "Source: Workflow (workflow.xml:67)" in result

    def test_format_evidence_extracts_pattern(self):
        """Test that pattern is extracted from evidence string."""
        component = ClassifiedComponent(
            name="nsxClient.createSegment",
            component_type="nsx_segments",
            level=TranslatabilityLevel.PARTIAL,
            reason="Test",
            openshift_equivalent="NetworkAttachmentDefinition",
            migration_path=MigrationPath.PATH_A,
            evidence="Pattern match: nsxClient.createSegment in context (action:com.acme.nsx/createSegment): var segment = nsxClient.createSegment({name: 'web-tier'})",
            location="action:com.acme.nsx/createSegment",
            recommendations=[],
        )

        result = _format_evidence_for_display(component)

        assert "Pattern: nsxClient.createSegment" in result

    def test_format_evidence_extracts_snippet(self):
        """Test that code snippet is extracted and displayed."""
        component = ClassifiedComponent(
            name="nsxClient.createFirewallRule",
            component_type="nsx_firewall_rules",
            level=TranslatabilityLevel.PARTIAL,
            reason="Test",
            openshift_equivalent="NetworkPolicy",
            migration_path=MigrationPath.PATH_A,
            evidence="Pattern match: nsxClient.createFirewallRule in context (action:com.acme.nsx/createFirewallRule): var rule = nsxClient.createFirewallRule({sources: ['10.0.0.0/8'], destinations: ['192.168.0.0/16']})",
            location="action:com.acme.nsx/createFirewallRule",
            recommendations=[],
        )

        result = _format_evidence_for_display(component)

        assert "Code:" in result
        assert "var rule = nsxClient.createFirewallRule" in result

    def test_format_evidence_truncates_long_snippet(self):
        """Test that code snippet is truncated if too long (>100 chars)."""
        long_snippet = "var segment = nsxClient.createSegment({name: 'web-tier', vlan: 100, subnet: '10.1.1.0/24', gateway: '10.1.1.1', dns: ['10.1.1.2', '10.1.1.3']})"
        component = ClassifiedComponent(
            name="nsxClient.createSegment",
            component_type="nsx_segments",
            level=TranslatabilityLevel.PARTIAL,
            reason="Test",
            openshift_equivalent="NetworkAttachmentDefinition",
            migration_path=MigrationPath.PATH_A,
            evidence=f"Pattern match: nsxClient.createSegment in context (action:com.acme.nsx/createSegment): {long_snippet}",
            location="action:com.acme.nsx/createSegment",
            recommendations=[],
        )

        result = _format_evidence_for_display(component)

        # Should be truncated to 100 chars (97 + "...")
        assert "Code:" in result
        assert "..." in result
        # Extract the code line
        code_line = [line for line in result.split("\n") if "Code:" in line][0]
        # Check that the code part is <= 103 chars ("  • Code: " = 10 chars prefix)
        assert len(code_line) <= 113  # 10 (prefix) + 100 (code) + 3 (...)

    def test_format_evidence_handles_missing_evidence(self):
        """Test that function returns empty string when no evidence."""
        component = ClassifiedComponent(
            name="Some Component",
            component_type="test",
            level=TranslatabilityLevel.SUPPORTED,
            reason="Test",
            openshift_equivalent=None,
            migration_path=MigrationPath.PATH_A,
            evidence=None,  # No evidence
            location="test.xml",
            recommendations=[],
        )

        result = _format_evidence_for_display(component)

        assert result == ""

    def test_format_evidence_fallback_format(self):
        """Test fallback formatting for non-standard evidence strings."""
        component = ClassifiedComponent(
            name="Custom Component",
            component_type="custom",
            level=TranslatabilityLevel.PARTIAL,
            reason="Test",
            openshift_equivalent=None,
            migration_path=MigrationPath.PATH_A,
            evidence="This is a non-standard evidence format that doesn't match the pattern",
            location="workflow.xml:100",
            recommendations=[],
        )

        result = _format_evidence_for_display(component)

        assert "Evidence detected:" in result
        assert "This is a non-standard evidence format" in result


class TestQuestionGeneratorsWithEvidence:
    """Tests that question generators include evidence in prompts."""

    def test_nsx_firewall_questions_include_evidence(self):
        """Test that NSX firewall questions include evidence in all prompts."""
        component = ClassifiedComponent(
            name="nsxClient.createFirewallRule",
            component_type="nsx_firewall_rules",
            level=TranslatabilityLevel.PARTIAL,
            reason="Firewall rules can be partially translated",
            openshift_equivalent="NetworkPolicy",
            migration_path=MigrationPath.PATH_A,
            evidence="Pattern match: nsxClient.createFirewallRule in context (action:com.acme.nsx/createFirewallRule): nsxClient.createFirewallRule({name: 'web-to-db'})",
            location="action:com.acme.nsx/createFirewallRule",
            recommendations=[],
        )

        questions = _nsx_firewall_questions(component)

        # Should have 3 questions
        assert len(questions) == 3

        # All questions should include evidence
        for question in questions:
            assert "Evidence detected:" in question["prompt"]
            assert "Source: Action (com.acme.nsx/createFirewallRule)" in question["prompt"]
            assert "Pattern: nsxClient.createFirewallRule" in question["prompt"]

    def test_nsx_segment_questions_include_evidence(self):
        """Test that NSX segment questions include evidence."""
        component = ClassifiedComponent(
            name="nsxClient.createSegment",
            component_type="nsx_segments",
            level=TranslatabilityLevel.PARTIAL,
            reason="Segments can be partially translated",
            openshift_equivalent="NetworkAttachmentDefinition",
            migration_path=MigrationPath.PATH_A,
            evidence="Pattern match: nsxClient.createSegment in context (action:com.acme.nsx/createSegment): var segment = nsxClient.createSegment({name: 'web-segment'})",
            location="action:com.acme.nsx/createSegment",
            recommendations=[],
        )

        questions = _nsx_segment_questions(component)

        # Should have 1 question
        assert len(questions) == 1

        # Question should include evidence
        assert "Evidence detected:" in questions[0]["prompt"]
        assert "Source: Action (com.acme.nsx/createSegment)" in questions[0]["prompt"]
        assert "Pattern: nsxClient.createSegment" in questions[0]["prompt"]

    def test_approval_questions_include_evidence(self):
        """Test that approval questions include evidence."""
        component = ClassifiedComponent(
            name="Approval Step",
            component_type="approval",
            level=TranslatabilityLevel.PARTIAL,
            reason="Approval requires custom integration",
            openshift_equivalent=None,
            migration_path=MigrationPath.PATH_B,
            evidence="Workflow item name/type contains approval keyword (workflow.xml:45): Wait for Approval",
            location="workflow.xml:45",
            recommendations=[],
        )

        questions = _approval_questions(component)

        # Should have 2 questions
        assert len(questions) == 2

        # All questions should include evidence
        for question in questions:
            assert "Evidence detected:" in question["prompt"]
            assert "Source: Workflow (workflow.xml:45)" in question["prompt"]

    def test_api_call_questions_include_evidence(self):
        """Test that API call questions include evidence."""
        component = ClassifiedComponent(
            name="REST API Call",
            component_type="rest_api_calls",
            level=TranslatabilityLevel.PARTIAL,
            reason="REST calls can be migrated to Ansible",
            openshift_equivalent="Ansible uri module",
            migration_path=MigrationPath.PATH_A,
            evidence="Pattern match: restClient.post in context (workflow.xml:78): var response = restClient.post('https://api.example.com/v1/resources', data)",
            location="workflow.xml:78",
            recommendations=[],
        )

        questions = _api_call_questions(component)

        # Should have 2 questions
        assert len(questions) == 2

        # All questions should include evidence
        for question in questions:
            assert "Evidence detected:" in question["prompt"]
            assert "Source: Workflow (workflow.xml:78)" in question["prompt"]
            assert "Pattern: restClient.post" in question["prompt"]

    def test_questions_without_evidence_are_backward_compatible(self):
        """Test that questions work gracefully when component has no evidence."""
        component = ClassifiedComponent(
            name="NSX Firewall",
            component_type="nsx_firewall_rules",
            level=TranslatabilityLevel.PARTIAL,
            reason="Test",
            openshift_equivalent="NetworkPolicy",
            migration_path=MigrationPath.PATH_A,
            evidence=None,  # No evidence
            location="unknown",
            recommendations=[],
        )

        questions = _nsx_firewall_questions(component)

        # Should still generate questions
        assert len(questions) == 3

        # Prompts should not have evidence section (just the question)
        for question in questions:
            assert "Evidence detected:" not in question["prompt"]
            # But should still have the base question text
            assert "?" in question["prompt"]
