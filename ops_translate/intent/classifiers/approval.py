"""
Approval and governance workflow classifier for vRealize migrations.

Detects approval tasks, governance workflows, and conditional approval paths that
require process redesign or custom integration when migrating to OpenShift.
"""

from pathlib import Path
from typing import Any

import yaml

from ops_translate.intent.classifiers.base import BaseClassifier
from ops_translate.intent.classify import (
    ClassifiedComponent,
    MigrationPath,
    TranslatabilityLevel,
)


class ApprovalClassifier(BaseClassifier):
    """
    Classifier for approval and governance workflows in vRealize.

    Approval logic is a core vRO orchestration feature with no direct
    OpenShift equivalent. This classifier detects approval patterns and
    recommends integration strategies.

    Detection Patterns:
    - Approval tasks in workflows
    - Conditional approval paths (environment-based, etc.)
    - Timeout/escalation logic
    - Multi-stage approval chains

    Classification Rules:
    - Simple approval → PARTIAL (requires custom integration)
    - Complex approval chains → MANUAL (requires process redesign)
    - Escalation logic → MANUAL (complex process)

    Example:
        >>> classifier = ApprovalClassifier()
        >>> components = classifier.classify_from_intent(intent_data)
    """

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "approval"

    @property
    def priority(self) -> int:
        """Approval classifier runs with medium-high priority."""
        return 20

    def can_classify(self, analysis: dict[str, Any]) -> bool:
        """
        Check if this analysis contains vRealize approval patterns.

        Args:
            analysis: Must contain 'source_type' == 'vrealize' and intent data

        Returns:
            True if this is vRealize data with approval indicators
        """
        if analysis.get("source_type") != "vrealize":
            return False

        # Check for intent file with approval indicators
        intent_file = analysis.get("intent_file")
        if not intent_file or not Path(intent_file).exists():
            return False

        # Load and check for approval patterns
        with open(intent_file) as f:
            data = yaml.safe_load(f)

        if not data or "intent" not in data:
            return False

        intent = data["intent"]

        # Check for approval indicators
        return self._has_approval_patterns(intent)

    def classify(self, analysis: dict[str, Any]) -> list[ClassifiedComponent]:
        """
        Classify approval components from extracted intent.

        Args:
            analysis: Dict with 'intent_file' path to intent YAML

        Returns:
            List of ClassifiedComponent instances for approval patterns
        """
        intent_file = analysis.get("intent_file")
        if not intent_file or not Path(intent_file).exists():
            return []

        with open(intent_file) as f:
            data = yaml.safe_load(f)

        if not data or "intent" not in data:
            return []

        intent = data["intent"]
        filename = Path(intent_file).stem.replace(".intent", "").replace(".workflow", "")

        return self.classify_from_intent(intent, location=filename)

    def classify_from_intent(
        self, intent: dict[str, Any], location: str = "approval"
    ) -> list[ClassifiedComponent]:
        """
        Classify approval components from normalized intent structure.

        Args:
            intent: Normalized intent dict
            location: Source file identifier for evidence

        Returns:
            List of classified approval components
        """
        components: list[ClassifiedComponent] = []

        governance = intent.get("governance", {})
        approval_config = governance.get("approval")

        if not approval_config and not self._has_approval_patterns(intent):
            return components

        # Determine complexity
        is_complex = self._is_complex_approval(intent, approval_config)

        if is_complex:
            # Complex approval requires process redesign
            components.append(
                ClassifiedComponent(
                    name="Complex Approval Workflow",
                    component_type="approval_complex",
                    level=TranslatabilityLevel.MANUAL,
                    reason=(
                        "Complex approval workflows with escalation, timeouts, or "
                        "multi-stage chains require process redesign and custom "
                        "operator development"
                    ),
                    openshift_equivalent="Custom operator or AAP workflow",
                    migration_path=MigrationPath.PATH_C,
                    location=location,
                    recommendations=[
                        "Review approval process with governance team",
                        "Consider simplifying approval chains",
                        "Evaluate Ansible Automation Platform workflows",
                        "May require custom Kubernetes operator",
                        "Document approval requirements in runbook",
                    ],
                )
            )
        else:
            # Simple approval can be scaffolded
            components.append(
                ClassifiedComponent(
                    name="Approval Workflow",
                    component_type="approval_simple",
                    level=TranslatabilityLevel.PARTIAL,
                    reason=(
                        "Approval logic requires custom integration with existing "
                        "approval systems (ServiceNow, Jira, AAP)"
                    ),
                    openshift_equivalent="AAP workflow or admission controller",
                    migration_path=MigrationPath.PATH_B,
                    location=location,
                    recommendations=[
                        "Integrate with existing approval system (ServiceNow, Jira, etc.)",
                        "Consider Ansible Automation Platform workflows",
                        "Evaluate Kubernetes admission controllers for policy enforcement",
                        "Generate scaffolding with TODO tasks for integration points",
                        "Document approval requirements",
                    ],
                )
            )

        return components

    def _has_approval_patterns(self, intent: dict[str, Any]) -> bool:
        """Check if intent contains approval indicators."""
        # Check governance.approval section
        if intent.get("governance", {}).get("approval"):
            return True

        # Check workflow description for approval keywords
        description = str(intent.get("description", "")).lower()
        approval_keywords = ["approval", "approve", "authorization", "governance", "gate"]
        if any(keyword in description for keyword in approval_keywords):
            return True

        # Check workflow name
        name = str(intent.get("name", "")).lower()
        if any(keyword in name for keyword in approval_keywords):
            return True

        return False

    def _is_complex_approval(
        self, intent: dict[str, Any], approval_config: dict[str, Any] | None
    ) -> bool:
        """Determine if approval workflow is complex."""
        if not approval_config:
            # If no explicit approval config, check for complexity indicators
            description = str(intent.get("description", "")).lower()
            complexity_keywords = ["escalation", "timeout", "multi-stage", "conditional approval"]
            return any(keyword in description for keyword in complexity_keywords)

        # Check approval config for complexity
        has_timeout = approval_config.get("timeout") is not None
        has_escalation = approval_config.get("escalation") is not None
        has_conditions = bool(approval_config.get("conditions"))

        return has_timeout or has_escalation or has_conditions
