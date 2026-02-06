"""
Unit tests for classification system.

Tests the translatability classification framework including levels, migration paths,
classified components, classifier discovery, and summary generation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ops_translate.intent.classify import (
    ClassifiedComponent,
    MigrationPath,
    TranslatabilityLevel,
    classify_components,
    discover_classifiers,
    generate_classification_summary,
)


class TestTranslatabilityLevel:
    """Tests for TranslatabilityLevel enum."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert TranslatabilityLevel.SUPPORTED.value == "SUPPORTED"
        assert TranslatabilityLevel.PARTIAL.value == "PARTIAL"
        assert TranslatabilityLevel.BLOCKED.value == "BLOCKED"
        assert TranslatabilityLevel.MANUAL.value == "MANUAL"

    def test_str_representation(self):
        """Test string representation of levels."""
        assert str(TranslatabilityLevel.SUPPORTED) == "SUPPORTED"
        assert str(TranslatabilityLevel.PARTIAL) == "PARTIAL"
        assert str(TranslatabilityLevel.BLOCKED) == "BLOCKED"
        assert str(TranslatabilityLevel.MANUAL) == "MANUAL"

    def test_emoji_property(self):
        """Test emoji representations."""
        assert TranslatabilityLevel.SUPPORTED.emoji == "✅"
        assert TranslatabilityLevel.PARTIAL.emoji == "⚠️"
        assert TranslatabilityLevel.BLOCKED.emoji == "🚫"
        assert TranslatabilityLevel.MANUAL.emoji == "👷"

    def test_severity_property(self):
        """Test severity scores for sorting."""
        assert TranslatabilityLevel.SUPPORTED.severity == 0
        assert TranslatabilityLevel.PARTIAL.severity == 1
        assert TranslatabilityLevel.BLOCKED.severity == 2
        assert TranslatabilityLevel.MANUAL.severity == 3

        # Verify ordering
        levels = [
            TranslatabilityLevel.MANUAL,
            TranslatabilityLevel.SUPPORTED,
            TranslatabilityLevel.BLOCKED,
            TranslatabilityLevel.PARTIAL,
        ]
        sorted_levels = sorted(levels, key=lambda l: l.severity)
        assert sorted_levels == [
            TranslatabilityLevel.SUPPORTED,
            TranslatabilityLevel.PARTIAL,
            TranslatabilityLevel.BLOCKED,
            TranslatabilityLevel.MANUAL,
        ]


class TestMigrationPath:
    """Tests for MigrationPath enum."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert MigrationPath.PATH_A.value == "PATH_A"
        assert MigrationPath.PATH_B.value == "PATH_B"
        assert MigrationPath.PATH_C.value == "PATH_C"

    def test_str_representation(self):
        """Test string representation of paths."""
        assert str(MigrationPath.PATH_A) == "PATH_A"
        assert str(MigrationPath.PATH_B) == "PATH_B"
        assert str(MigrationPath.PATH_C) == "PATH_C"

    def test_description_property(self):
        """Test human-readable descriptions."""
        assert MigrationPath.PATH_A.description == "OpenShift-native replacement"
        assert MigrationPath.PATH_B.description == "Hybrid approach (keep existing temporarily)"
        assert MigrationPath.PATH_C.description == "Custom specialist implementation"


class TestClassifiedComponent:
    """Tests for ClassifiedComponent NamedTuple."""

    def test_minimal_component(self):
        """Test creating component with minimal required fields."""
        component = ClassifiedComponent(
            name="Test Component",
            component_type="test_type",
            level=TranslatabilityLevel.SUPPORTED,
            reason="Test reason",
        )

        assert component.name == "Test Component"
        assert component.component_type == "test_type"
        assert component.level == TranslatabilityLevel.SUPPORTED
        assert component.reason == "Test reason"
        assert component.openshift_equivalent is None
        assert component.migration_path is None
        assert component.evidence is None
        assert component.location is None
        assert component.recommendations is None

    def test_full_component(self):
        """Test creating component with all fields populated."""
        component = ClassifiedComponent(
            name="NSX Segment",
            component_type="nsx_segment",
            level=TranslatabilityLevel.PARTIAL,
            reason="Can be replaced with NetworkAttachmentDefinition",
            openshift_equivalent="NetworkAttachmentDefinition (Multus CNI)",
            migration_path=MigrationPath.PATH_A,
            evidence="nsxClient.createSegment() at line 42",
            location="workflow.xml:42",
            recommendations=["Create NAD manifest", "Configure Multus", "Test networking"],
        )

        assert component.name == "NSX Segment"
        assert component.component_type == "nsx_segment"
        assert component.level == TranslatabilityLevel.PARTIAL
        assert component.openshift_equivalent == "NetworkAttachmentDefinition (Multus CNI)"
        assert component.migration_path == MigrationPath.PATH_A
        assert len(component.recommendations) == 3

    def test_to_dict(self):
        """Test dictionary serialization."""
        component = ClassifiedComponent(
            name="Test",
            component_type="test_type",
            level=TranslatabilityLevel.BLOCKED,
            reason="Test reason",
            migration_path=MigrationPath.PATH_C,
            recommendations=["Step 1", "Step 2"],
        )

        result = component.to_dict()

        assert result["name"] == "Test"
        assert result["component_type"] == "test_type"
        assert result["level"] == "BLOCKED"  # Enum converted to string
        assert result["reason"] == "Test reason"
        assert result["migration_path"] == "PATH_C"  # Enum converted to string
        assert result["openshift_equivalent"] is None
        assert result["recommendations"] == ["Step 1", "Step 2"]

    def test_to_dict_with_none_recommendations(self):
        """Test that None recommendations become empty list in dict."""
        component = ClassifiedComponent(
            name="Test",
            component_type="test_type",
            level=TranslatabilityLevel.SUPPORTED,
            reason="Test reason",
            recommendations=None,
        )

        result = component.to_dict()
        assert result["recommendations"] == []

    def test_requires_manual_work_property(self):
        """Test requires_manual_work property."""
        # SUPPORTED doesn't require manual work
        supported = ClassifiedComponent(
            name="Test",
            component_type="test",
            level=TranslatabilityLevel.SUPPORTED,
            reason="Fully supported",
        )
        assert not supported.requires_manual_work

        # PARTIAL, BLOCKED, MANUAL all require manual work
        partial = ClassifiedComponent(
            name="Test", component_type="test", level=TranslatabilityLevel.PARTIAL, reason="Partial"
        )
        assert partial.requires_manual_work

        blocked = ClassifiedComponent(
            name="Test", component_type="test", level=TranslatabilityLevel.BLOCKED, reason="Blocked"
        )
        assert blocked.requires_manual_work

        manual = ClassifiedComponent(
            name="Test", component_type="test", level=TranslatabilityLevel.MANUAL, reason="Manual"
        )
        assert manual.requires_manual_work

    def test_is_blocking_property(self):
        """Test is_blocking property."""
        # SUPPORTED and PARTIAL are not blocking
        supported = ClassifiedComponent(
            name="Test", component_type="test", level=TranslatabilityLevel.SUPPORTED, reason="OK"
        )
        assert not supported.is_blocking

        partial = ClassifiedComponent(
            name="Test", component_type="test",
            level=TranslatabilityLevel.PARTIAL, reason="OK"
        )
        assert not partial.is_blocking

        # BLOCKED and MANUAL are blocking
        blocked = ClassifiedComponent(
            name="Test", component_type="test", level=TranslatabilityLevel.BLOCKED, reason="Blocked"
        )
        assert blocked.is_blocking

        manual = ClassifiedComponent(
            name="Test", component_type="test", level=TranslatabilityLevel.MANUAL, reason="Manual"
        )
        assert manual.is_blocking


class TestDiscoverClassifiers:
    """Tests for classifier discovery."""

    def test_discover_nsx_classifier(self):
        """Test that NSX classifier is discovered."""
        classifiers = discover_classifiers()

        # Should find at least the NSX classifier
        assert len(classifiers) >= 1

        # Check that NSX classifier exists
        nsx_classifier = next((c for c in classifiers if c.name == "nsx"), None)
        assert nsx_classifier is not None
        assert hasattr(nsx_classifier, "priority")
        assert hasattr(nsx_classifier, "classify")
        assert hasattr(nsx_classifier, "can_classify")

    def test_classifiers_sorted_by_priority(self):
        """Test that classifiers are sorted by priority."""
        classifiers = discover_classifiers()

        if len(classifiers) > 1:
            # Verify sorting (lower priority number comes first)
            priorities = [c.priority for c in classifiers]
            assert priorities == sorted(priorities)

    def test_classifier_has_required_methods(self):
        """Test that discovered classifiers have required interface methods."""
        classifiers = discover_classifiers()

        # All classifiers should have required methods
        for classifier in classifiers:
            assert hasattr(classifier, "name")
            assert hasattr(classifier, "priority")
            assert hasattr(classifier, "can_classify")
            assert hasattr(classifier, "classify")
            assert callable(classifier.can_classify)
            assert callable(classifier.classify)


class TestClassifyComponents:
    """Tests for component classification."""

    def test_classify_with_nsx_operations(self):
        """Test classification of workflow with NSX operations."""
        analysis = {
            "nsx_operations": {
                "segments": [
                    {
                        "name": "createSegment",
                        "confidence": 0.9,
                        "evidence": "nsxClient.createSegment()",
                    }
                ],
                "firewall_rules": [
                    {
                        "name": "createFirewallRule",
                        "confidence": 0.85,
                        "evidence": "nsxClient.createFirewallRule()",
                    }
                ],
            },
            "signals": {"nsx_keywords": 5},
        }

        components = classify_components(analysis)

        # Should classify NSX operations
        assert len(components) >= 2

        # Check that components have required properties
        for component in components:
            assert component.name
            assert component.component_type
            assert component.level in TranslatabilityLevel
            assert component.reason

    def test_classify_with_no_classifiers(self):
        """Test that fallback to NSX classifier works when discovery fails."""
        analysis = {
            "nsx_operations": {
                "segments": [{"name": "seg1", "confidence": 0.9, "evidence": "test"}]
            },
            "signals": {"nsx_keywords": 1},
        }

        # Mock discover_classifiers to return empty list
        with patch("ops_translate.intent.classify.discover_classifiers") as mock_discover:
            mock_discover.return_value = []

            components = classify_components(analysis)

            # Should still work with fallback NSX classifier
            assert len(components) >= 1

    def test_classify_empty_analysis(self):
        """Test classification with no operations."""
        analysis = {
            "nsx_operations": {},
            "custom_plugins": [],
            "rest_api_calls": [],
            "signals": {"nsx_keywords": 0},
        }

        components = classify_components(analysis)

        # Should return empty list or only components that don't need operations
        assert isinstance(components, list)

    def test_components_sorted_by_severity(self):
        """Test that classified components are sorted by severity."""
        # Create mock classifier that returns components with different severity
        mock_classifier = MagicMock()
        mock_classifier.name = "test"
        mock_classifier.priority = 1
        mock_classifier.can_classify.return_value = True
        mock_classifier.classify.return_value = [
            ClassifiedComponent(
                name="Supported Component",
                component_type="test",
                level=TranslatabilityLevel.SUPPORTED,
                reason="OK",
            ),
            ClassifiedComponent(
                name="Blocked Component",
                component_type="test",
                level=TranslatabilityLevel.BLOCKED,
                reason="Not OK",
            ),
            ClassifiedComponent(
                name="Partial Component",
                component_type="test",
                level=TranslatabilityLevel.PARTIAL,
                reason="Somewhat OK",
            ),
        ]

        analysis = {"test": "data"}
        components = classify_components(analysis, classifiers=[mock_classifier])

        # Should be sorted: BLOCKED (severity 2), PARTIAL (1), SUPPORTED (0)
        # But reversed, so highest severity first
        assert components[0].level == TranslatabilityLevel.BLOCKED
        assert components[1].level == TranslatabilityLevel.PARTIAL
        assert components[2].level == TranslatabilityLevel.SUPPORTED


class TestGenerateClassificationSummary:
    """Tests for classification summary generation."""

    def test_summary_with_no_components(self):
        """Test summary generation with empty component list."""
        summary = generate_classification_summary([])

        assert summary["counts"]["SUPPORTED"] == 0
        assert summary["counts"]["PARTIAL"] == 0
        assert summary["counts"]["BLOCKED"] == 0
        assert summary["counts"]["MANUAL"] == 0
        assert summary["overall_assessment"] == "FULLY_TRANSLATABLE"

    def test_summary_counts(self):
        """Test that summary counts components correctly."""
        components = [
            ClassifiedComponent("c1", "t1", TranslatabilityLevel.SUPPORTED, "OK"),
            ClassifiedComponent("c2", "t2", TranslatabilityLevel.SUPPORTED, "OK"),
            ClassifiedComponent(
                "c3",
                "t3",
                TranslatabilityLevel.PARTIAL,
                "Partial",
                migration_path=MigrationPath.PATH_A,
            ),
            ClassifiedComponent("c4", "t4", TranslatabilityLevel.BLOCKED, "Blocked"),
            ClassifiedComponent("c5", "t5", TranslatabilityLevel.MANUAL, "Manual"),
        ]

        summary = generate_classification_summary(components)

        assert summary["counts"]["SUPPORTED"] == 2
        assert summary["counts"]["PARTIAL"] == 1
        assert summary["counts"]["BLOCKED"] == 1
        assert summary["counts"]["MANUAL"] == 1

    def test_overall_assessment_fully_translatable(self):
        """Test assessment when all components are SUPPORTED."""
        components = [
            ClassifiedComponent("c1", "t1", TranslatabilityLevel.SUPPORTED, "OK"),
            ClassifiedComponent("c2", "t2", TranslatabilityLevel.SUPPORTED, "OK"),
        ]

        summary = generate_classification_summary(components)
        assert summary["overall_assessment"] == "FULLY_TRANSLATABLE"

    def test_overall_assessment_requires_manual_work(self):
        """Test assessment when BLOCKED or MANUAL components exist."""
        components = [
            ClassifiedComponent("c1", "t1", TranslatabilityLevel.SUPPORTED, "OK"),
            ClassifiedComponent("c2", "t2", TranslatabilityLevel.BLOCKED, "Blocked"),
        ]

        summary = generate_classification_summary(components)
        assert summary["overall_assessment"] == "REQUIRES_MANUAL_WORK"

    def test_overall_assessment_mostly_automatic(self):
        """Test assessment with some PARTIAL components but not majority."""
        components = [
            ClassifiedComponent("c1", "t1", TranslatabilityLevel.SUPPORTED, "OK"),
            ClassifiedComponent("c2", "t2", TranslatabilityLevel.SUPPORTED, "OK"),
            ClassifiedComponent("c3", "t3", TranslatabilityLevel.PARTIAL, "Partial"),
        ]

        summary = generate_classification_summary(components)
        assert summary["overall_assessment"] == "MOSTLY_AUTOMATIC"

    def test_overall_assessment_mostly_manual(self):
        """Test assessment when PARTIAL components are majority."""
        components = [
            ClassifiedComponent("c1", "t1", TranslatabilityLevel.PARTIAL, "Partial"),
            ClassifiedComponent("c2", "t2", TranslatabilityLevel.PARTIAL, "Partial"),
            ClassifiedComponent("c3", "t3", TranslatabilityLevel.SUPPORTED, "OK"),
        ]

        summary = generate_classification_summary(components)
        assert summary["overall_assessment"] == "MOSTLY_MANUAL"

    def test_migration_path_counts(self):
        """Test that migration paths are counted correctly."""
        components = [
            ClassifiedComponent(
                "c1", "t1", TranslatabilityLevel.PARTIAL, "OK", migration_path=MigrationPath.PATH_A
            ),
            ClassifiedComponent(
                "c2", "t2", TranslatabilityLevel.PARTIAL, "OK", migration_path=MigrationPath.PATH_A
            ),
            ClassifiedComponent(
                "c3",
                "t3",
                TranslatabilityLevel.BLOCKED,
                "Blocked",
                migration_path=MigrationPath.PATH_B,
            ),
            ClassifiedComponent(
                "c4", "t4", TranslatabilityLevel.SUPPORTED, "OK", migration_path=None
            ),
        ]

        summary = generate_classification_summary(components)

        assert "migration_paths" in summary
        assert summary["migration_paths"]["PATH_A"] == 2
        assert summary["migration_paths"]["PATH_B"] == 1
        assert summary["migration_paths"]["NONE"] == 1
