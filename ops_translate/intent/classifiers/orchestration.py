"""
Orchestration complexity classifier for vRealize migrations.

Detects complex orchestration patterns like nested decision trees, loops,
sub-workflow invocations, and error handling that require refactoring from
procedural to declarative automation.
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


class OrchestrationClassifier(BaseClassifier):
    """
    Classifier for orchestration complexity in vRealize workflows.

    vRealize workflows often contain procedural orchestration logic (loops,
    conditionals, sub-workflows) that doesn't map directly to declarative
    Kubernetes/Ansible patterns. This classifier identifies complexity levels.

    Detection Patterns:
    - Nested decision trees
    - Loop constructs (for-each, while)
    - Sub-workflow invocations
    - Complex error handling / exception branches
    - State machines

    Classification Rules:
    - Simple conditionals → SUPPORTED (Ansible when clauses)
    - Moderate loops → PARTIAL (refactor to Ansible loops)
    - Complex orchestration → MANUAL (requires redesign)

    Example:
        >>> classifier = OrchestrationClassifier()
        >>> components = classifier.classify_from_intent(intent_data)
    """

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "orchestration"

    @property
    def priority(self) -> int:
        """Orchestration classifier runs with medium priority."""
        return 30

    def can_classify(self, analysis: dict[str, Any]) -> bool:
        """
        Check if this analysis contains vRealize orchestration patterns.

        Args:
            analysis: Must contain 'source_type' == 'vrealize' and intent data

        Returns:
            True if this is vRealize data with orchestration indicators
        """
        if analysis.get("source_type") != "vrealize":
            return False

        intent_file = analysis.get("intent_file")
        if not intent_file or not Path(intent_file).exists():
            return False

        with open(intent_file) as f:
            data = yaml.safe_load(f)

        if not data or "intent" not in data:
            return False

        intent = data["intent"]
        return self._has_orchestration_patterns(intent)

    def classify(self, analysis: dict[str, Any]) -> list[ClassifiedComponent]:
        """
        Classify orchestration components from extracted intent.

        Args:
            analysis: Dict with 'intent_file' path to intent YAML

        Returns:
            List of ClassifiedComponent instances for orchestration patterns
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
        self, intent: dict[str, Any], location: str = "orchestration"
    ) -> list[ClassifiedComponent]:
        """
        Classify orchestration components from normalized intent structure.

        Args:
            intent: Normalized intent dict
            location: Source file identifier for evidence

        Returns:
            List of classified orchestration components
        """
        components: list[ClassifiedComponent] = []

        if not self._has_orchestration_patterns(intent):
            return components

        complexity = self._assess_complexity(intent)

        if complexity == "high":
            components.append(
                ClassifiedComponent(
                    name="Complex Orchestration Logic",
                    component_type="orchestration_complex",
                    level=TranslatabilityLevel.MANUAL,
                    reason=(
                        "Complex procedural orchestration (nested decisions, loops, "
                        "sub-workflows) requires refactoring into declarative automation"
                    ),
                    openshift_equivalent="Refactored Ansible playbooks or custom operator",
                    migration_path=MigrationPath.PATH_C,
                    location=location,
                    recommendations=[
                        "Review workflow logic with automation architect",
                        "Identify declarative alternatives to procedural steps",
                        "Consider breaking into smaller, focused playbooks",
                        "Evaluate custom operator for complex state management",
                        "Document business logic requirements",
                    ],
                )
            )
        elif complexity == "medium":
            components.append(
                ClassifiedComponent(
                    name="Moderate Orchestration Logic",
                    component_type="orchestration_moderate",
                    level=TranslatabilityLevel.PARTIAL,
                    reason=(
                        "Moderate orchestration complexity can be refactored to "
                        "Ansible loops, conditionals, and block structures"
                    ),
                    openshift_equivalent="Ansible when/loop/block constructs",
                    migration_path=MigrationPath.PATH_A,
                    location=location,
                    recommendations=[
                        "Refactor loops to Ansible loop constructs",
                        "Map conditionals to when clauses",
                        "Use block/rescue for error handling",
                        "Generate scaffolding with TODO markers",
                        "Test logic in dev environment",
                    ],
                )
            )

        return components

    def _has_orchestration_patterns(self, intent: dict[str, Any]) -> bool:
        """Check if intent contains orchestration complexity indicators."""
        # Check description for orchestration keywords
        description = str(intent.get("description", "")).lower()
        keywords = [
            "loop",
            "foreach",
            "while",
            "decision",
            "conditional",
            "sub-workflow",
            "workflow call",
            "error handling",
            "exception",
            "retry",
        ]

        if any(keyword in description for keyword in keywords):
            return True

        # Check workflow structure section if present
        if intent.get("workflow_structure"):
            return True

        # Check for control_flow section
        if intent.get("control_flow"):
            return True

        return False

    def _assess_complexity(self, intent: dict[str, Any]) -> str:
        """
        Assess orchestration complexity level.

        Returns:
            'low', 'medium', or 'high'
        """
        description = str(intent.get("description", "")).lower()
        control_flow = intent.get("control_flow", {})

        # High complexity indicators
        high_complexity_keywords = [
            "nested loop",
            "state machine",
            "complex decision",
            "multiple sub-workflows",
            "exception handling",
        ]

        if any(keyword in description for keyword in high_complexity_keywords):
            return "high"

        # Check control_flow structure
        if control_flow:
            has_loops = control_flow.get("loops") or "loop" in str(control_flow).lower()
            has_conditions = control_flow.get("conditions") or "if" in str(control_flow).lower()
            has_subworkflows = (
                control_flow.get("sub_workflows") or "call" in str(control_flow).lower()
            )

            # High: multiple complexity features
            if sum([has_loops, has_conditions, has_subworkflows]) >= 2:
                return "high"

            # Medium: single complexity feature
            if has_loops or has_conditions or has_subworkflows:
                return "medium"

        # Medium complexity indicators
        medium_complexity_keywords = ["loop", "foreach", "conditional", "sub-workflow"]

        if any(keyword in description for keyword in medium_complexity_keywords):
            return "medium"

        return "low"
