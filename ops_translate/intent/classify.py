"""
Classification system for determining translatability of workflow components.

This module provides a framework for classifying workflow components based on
how well they can be translated from VMware automation to OpenShift-native
equivalents. It defines classification levels, migration paths, and utilities
for working with classified components.
"""

from enum import Enum
from typing import Any, NamedTuple


class TranslatabilityLevel(Enum):
    """
    Classification of how well a component can be translated to OpenShift.

    Levels:
        SUPPORTED: Full automatic translation to OpenShift-native equivalent
        PARTIAL: Can translate with limitations or manual configuration needed
        BLOCKED: Cannot translate automatically, requires manual implementation
        MANUAL: Complex custom logic requiring specialist review and implementation

    Examples:
        >>> level = TranslatabilityLevel.SUPPORTED
        >>> level.value
        'SUPPORTED'
        >>> TranslatabilityLevel.PARTIAL.name
        'PARTIAL'
    """

    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    MANUAL = "MANUAL"

    def __str__(self) -> str:
        """Return the string value for display."""
        return self.value

    @property
    def emoji(self) -> str:
        """Return an emoji representing this level for console output."""
        return {
            "SUPPORTED": "✅",
            "PARTIAL": "⚠️",
            "BLOCKED": "🚫",
            "MANUAL": "👷",
        }[self.value]

    @property
    def severity(self) -> int:
        """
        Return numeric severity for sorting (higher = more problematic).

        Returns:
            0 for SUPPORTED, 1 for PARTIAL, 2 for BLOCKED, 3 for MANUAL
        """
        return {
            "SUPPORTED": 0,
            "PARTIAL": 1,
            "BLOCKED": 2,
            "MANUAL": 3,
        }[self.value]


class MigrationPath(Enum):
    """
    Recommended migration path for components that aren't fully supported.

    Paths:
        PATH_A: OpenShift-native replacement available (e.g., NetworkPolicy for NSX firewall)
        PATH_B: Hybrid approach - keep existing system temporarily (e.g., continue using NSX)
        PATH_C: Custom implementation or specialist work required

    Usage:
        >>> path = MigrationPath.PATH_A
        >>> path.description
        'OpenShift-native replacement'
    """

    PATH_A = "PATH_A"
    PATH_B = "PATH_B"
    PATH_C = "PATH_C"

    def __str__(self) -> str:
        """Return the string value for display."""
        return self.value

    @property
    def description(self) -> str:
        """Return human-readable description of this migration path."""
        return {
            "PATH_A": "OpenShift-native replacement",
            "PATH_B": "Hybrid approach (keep existing temporarily)",
            "PATH_C": "Custom specialist implementation",
        }[self.value]


class ClassifiedComponent(NamedTuple):
    """
    A workflow component with translatability classification.

    Attributes:
        name: Component name or identifier
        component_type: Type of component (e.g., "nsx_segment", "firewall_rule")
        level: Translatability classification level
        reason: Human-readable explanation of the classification
        openshift_equivalent: OpenShift-native equivalent if available (None if BLOCKED/MANUAL)
        migration_path: Recommended migration approach (None if SUPPORTED)
        evidence: Supporting evidence from source analysis (e.g., code snippet)
        location: Where this component was found in source (e.g., file:line)
        recommendations: List of specific action items for migration

    Example:
        >>> component = ClassifiedComponent(
        ...     name="Web Tier Segment",
        ...     component_type="nsx_segment",
        ...     level=TranslatabilityLevel.PARTIAL,
        ...     reason="NSX segments can be replaced with Multus NetworkAttachmentDefinition",
        ...     openshift_equivalent="NetworkAttachmentDefinition (Multus CNI)",
        ...     migration_path=MigrationPath.PATH_A,
        ...     evidence="nsxClient.createSegment() in workflow-item[@name='createSegment']",
        ...     location="workflow.xml:45",
        ...     recommendations=[
        ...         "Create NAD manifest", "Configure Multus CNI", "Test pod networking"
        ...     ]
        ... )
    """

    name: str
    component_type: str
    level: TranslatabilityLevel
    reason: str
    openshift_equivalent: str | None = None
    migration_path: MigrationPath | None = None
    evidence: str | None = None
    location: str | None = None
    recommendations: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with enum values converted to strings
        """
        return {
            "name": self.name,
            "component_type": self.component_type,
            "level": self.level.value,
            "reason": self.reason,
            "openshift_equivalent": self.openshift_equivalent,
            "migration_path": self.migration_path.value if self.migration_path else None,
            "evidence": self.evidence,
            "location": self.location,
            "recommendations": self.recommendations or [],
        }

    @property
    def requires_manual_work(self) -> bool:
        """Return True if this component requires any manual intervention."""
        return self.level in (
            TranslatabilityLevel.PARTIAL,
            TranslatabilityLevel.BLOCKED,
            TranslatabilityLevel.MANUAL,
        )

    @property
    def is_blocking(self) -> bool:
        """Return True if this component prevents automatic translation."""
        return self.level in (TranslatabilityLevel.BLOCKED, TranslatabilityLevel.MANUAL)


def classify_components(
    analysis: dict[str, Any], classifiers: list[Any] | None = None
) -> list[ClassifiedComponent]:
    """
    Classify workflow components based on translatability.

    Takes analysis results (from analyze/vrealize.py) and applies classification
    logic using registered classifiers to determine how well each component can
    be translated to OpenShift.

    Args:
        analysis: Analysis results containing detected components
        classifiers: List of classifier instances to apply (defaults to [NSXClassifier()])

    Returns:
        List of ClassifiedComponent instances sorted by severity (worst first)

    Example:
        >>> from ops_translate.analyze.vrealize import analyze_vrealize_workflow
        >>> from ops_translate.intent.classifiers.nsx import NSXClassifier
        >>> analysis = analyze_vrealize_workflow(Path("workflow.xml"))
        >>> components = classify_components(analysis, [NSXClassifier()])
        >>> blocking = [c for c in components if c.is_blocking]
        >>> print(f"Found {len(blocking)} blocking components")
    """
    if classifiers is None:
        # Import here to avoid circular dependency
        from ops_translate.intent.classifiers.nsx import NSXClassifier

        classifiers = [NSXClassifier()]

    classified: list[ClassifiedComponent] = []

    # Apply each classifier
    for classifier in classifiers:
        classified.extend(classifier.classify(analysis))

    # Sort by severity (worst first), then by name
    classified.sort(key=lambda c: (c.level.severity, c.name), reverse=True)

    return classified


def generate_classification_summary(components: list[ClassifiedComponent]) -> dict[str, Any]:
    """
    Generate summary statistics for classified components.

    Args:
        components: List of classified components

    Returns:
        Dictionary with summary statistics including counts by level,
        overall translatability assessment, and recommendations

    Example:
        >>> summary = generate_classification_summary(components)
        >>> print(f"Translatability: {summary['overall_assessment']}")
        >>> print(f"Blocking issues: {summary['counts']['BLOCKED']}")
    """
    counts = {
        "SUPPORTED": 0,
        "PARTIAL": 0,
        "BLOCKED": 0,
        "MANUAL": 0,
    }

    for component in components:
        counts[component.level.value] += 1

    # Determine overall assessment
    total = len(components)
    if total == 0:
        assessment = "FULLY_TRANSLATABLE"
    elif counts["BLOCKED"] > 0 or counts["MANUAL"] > 0:
        assessment = "REQUIRES_MANUAL_WORK"
    elif counts["PARTIAL"] > total * 0.5:
        assessment = "MOSTLY_MANUAL"
    elif counts["PARTIAL"] > 0:
        assessment = "MOSTLY_AUTOMATIC"
    else:
        assessment = "FULLY_TRANSLATABLE"

    # Calculate migration path distribution
    path_counts = {"PATH_A": 0, "PATH_B": 0, "PATH_C": 0, "NONE": 0}
    for component in components:
        if component.migration_path:
            path_counts[component.migration_path.value] += 1
        else:
            path_counts["NONE"] += 1

    return {
        "total_components": total,
        "counts": counts,
        "overall_assessment": assessment,
        "migration_paths": path_counts,
        "requires_manual_work": any(c.requires_manual_work for c in components),
        "has_blocking_issues": any(c.is_blocking for c in components),
    }
