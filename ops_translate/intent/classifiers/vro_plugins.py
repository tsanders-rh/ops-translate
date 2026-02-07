"""
vRO/vRA-specific integrations classifier for vRealize migrations.

Detects platform-specific integrations like vRO plugins, vRA entities,
custom actions, and JavaScript scriptable tasks that are tied to the
vRealize platform and have no direct OpenShift equivalent.
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


class Vro_pluginsClassifier(BaseClassifier):
    """
    Classifier for vRO/vRA-specific platform integrations.

    vRealize workflows often use platform-specific features like:
    - vRO plugins (AD, SQL, HTTP-REST, etc.)
    - vRA entities (blueprints, resource actions)
    - Custom actions (JavaScript, Python)
    - Scriptable tasks

    These require alternative implementations in OpenShift/Ansible.

    Detection Patterns:
    - vRO plugin references
    - vRA catalog items / blueprints
    - JavaScript/Python scriptable tasks
    - Custom action invocations

    Classification Rules:
    - Standard plugins → PARTIAL (Ansible alternatives exist)
    - Custom plugins → MANUAL (requires custom implementation)
    - Scriptable tasks → PARTIAL (refactor to Ansible tasks)

    Example:
        >>> classifier = Vro_pluginsClassifier()
        >>> components = classifier.classify_from_intent(intent_data)
    """

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "vro_plugins"

    @property
    def priority(self) -> int:
        """vRO plugins classifier runs with lower priority."""
        return 40

    def can_classify(self, analysis: dict[str, Any]) -> bool:
        """
        Check if this analysis contains vRO/vRA platform integrations.

        Args:
            analysis: Must contain 'source_type' == 'vrealize' and intent data

        Returns:
            True if this is vRealize data with plugin/integration indicators
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
        return self._has_plugin_patterns(intent)

    def classify(self, analysis: dict[str, Any]) -> list[ClassifiedComponent]:
        """
        Classify vRO/vRA integration components from extracted intent.

        Args:
            analysis: Dict with 'intent_file' path to intent YAML

        Returns:
            List of ClassifiedComponent instances for platform integrations
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
        self, intent: dict[str, Any], location: str = "vro_plugins"
    ) -> list[ClassifiedComponent]:
        """
        Classify vRO/vRA integration components from normalized intent structure.

        Args:
            intent: Normalized intent dict
            location: Source file identifier for evidence

        Returns:
            List of classified integration components
        """
        components = []

        if not self._has_plugin_patterns(intent):
            return components

        # Check for integrations section
        integrations = intent.get("integrations", [])

        # Detect platform-specific integrations
        vro_integrations = [
            i
            for i in integrations
            if i.get("type") in ("vro_plugin", "vra_entity", "custom_action", "scriptable_task")
        ]

        if vro_integrations:
            # Check if these are standard or custom
            is_custom = any(
                i.get("type") == "custom_action"
                or "custom" in str(i.get("plugin_name", "")).lower()
                for i in vro_integrations
            )

            if is_custom:
                components.append(
                    ClassifiedComponent(
                        name="Custom vRO Integration",
                        component_type="vro_custom_integration",
                        level=TranslatabilityLevel.MANUAL,
                        reason=(
                            "Custom vRO plugins, actions, or scriptable tasks require "
                            "custom implementation in Ansible or as Kubernetes operators"
                        ),
                        openshift_equivalent="Custom Ansible module or Kubernetes operator",
                        migration_path=MigrationPath.PATH_C,
                        location=location,
                        recommendations=[
                            "Review custom plugin/action logic",
                            "Identify equivalent Ansible modules or APIs",
                            "Consider developing custom Ansible module",
                            "Evaluate Kubernetes operator pattern for complex integrations",
                            "Document integration requirements and dependencies",
                        ],
                    )
                )
            else:
                components.append(
                    ClassifiedComponent(
                        name="Standard vRO Plugin Integration",
                        component_type="vro_plugin_integration",
                        level=TranslatabilityLevel.PARTIAL,
                        reason=(
                            "Standard vRO plugin integrations (AD, SQL, HTTP) have "
                            "equivalent Ansible modules available"
                        ),
                        openshift_equivalent="Ansible modules (uri, ldap, mysql, etc.)",
                        migration_path=MigrationPath.PATH_A,
                        location=location,
                        recommendations=[
                            "Map vRO plugin calls to equivalent Ansible modules",
                            "Use uri module for HTTP-REST plugin",
                            "Use ldap/win modules for AD plugin",
                            "Use mysql/postgresql modules for database plugins",
                            "Generate scaffolding with TODO tasks for mapping",
                        ],
                    )
                )

        # Check description for scriptable task indicators
        description = str(intent.get("description", "")).lower()
        if "javascript" in description or "scriptable task" in description:
            if not any(c.component_type.startswith("vro_") for c in components):
                components.append(
                    ClassifiedComponent(
                        name="Scriptable Task",
                        component_type="vro_scriptable_task",
                        level=TranslatabilityLevel.PARTIAL,
                        reason=(
                            "JavaScript scriptable tasks need refactoring to "
                            "Ansible tasks or shell commands"
                        ),
                        openshift_equivalent="Ansible tasks or shell module",
                        migration_path=MigrationPath.PATH_B,
                        location=location,
                        recommendations=[
                            "Review JavaScript logic",
                            "Refactor to Ansible tasks where possible",
                            "Use shell/command module for simple scripts",
                            "Consider custom Ansible filter plugin for complex logic",
                            "Document any platform-specific dependencies",
                        ],
                    )
                )

        return components

    def _has_plugin_patterns(self, intent: dict[str, Any]) -> bool:
        """Check if intent contains vRO/vRA plugin indicators."""
        # Check integrations section
        integrations = intent.get("integrations", [])
        if any(
            i.get("type") in ("vro_plugin", "vra_entity", "custom_action", "scriptable_task")
            for i in integrations
        ):
            return True

        # Check description for plugin keywords
        description = str(intent.get("description", "")).lower()
        keywords = [
            "vro plugin",
            "vra entity",
            "custom action",
            "scriptable task",
            "javascript",
            "plugin:",
        ]

        return any(keyword in description for keyword in keywords)
