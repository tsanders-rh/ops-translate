"""
Decision Interview persistence and integration.

Handles loading, validation, and application of user decisions from
the Decision Interview tab to update component classifications.
"""

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)

# Get project root to find schema
PROJECT_ROOT = Path(__file__).parent.parent


class DecisionManager:
    """
    Manages decision interview responses and their application to classification.

    Attributes:
        workspace_root: Path to the workspace root directory
        decisions_file: Path to the decisions.yaml file
        _decisions_cache: Cached decisions dict for performance
    """

    def __init__(self, workspace_root: Path):
        """
        Initialize decision manager.

        Args:
            workspace_root: Path to workspace root
        """
        self.workspace_root = Path(workspace_root)
        self.decisions_dir = self.workspace_root / ".ops-translate"
        self.decisions_file = self.decisions_dir / "decisions.yaml"
        self._decisions_cache: dict[str, Any] | None = None

    def load_decisions(self) -> dict[str, Any] | None:
        """
        Load and validate decisions from workspace.

        Returns:
            Decisions dict if file exists and is valid, None otherwise

        Raises:
            ValueError: If decisions file is invalid or doesn't match schema
        """
        # Return cached decisions if available
        if self._decisions_cache is not None:
            return self._decisions_cache

        if not self.decisions_file.exists():
            logger.debug(f"No decisions file found at {self.decisions_file}")
            return None

        try:
            with open(self.decisions_file) as f:
                decisions = yaml.safe_load(f)

            if decisions is None:
                logger.warning(f"Decisions file is empty: {self.decisions_file}")
                return None

            if not isinstance(decisions, dict):
                raise ValueError(
                    f"Invalid decisions file: expected dict, got {type(decisions).__name__}"
                )

            # Validate against schema
            self._validate_decisions_schema(decisions)

            # Cache the decisions
            self._decisions_cache = decisions
            logger.info(f"Loaded decisions from {self.decisions_file}")

            return decisions

        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse decisions YAML: {e}") from e

    def _validate_decisions_schema(self, decisions: dict) -> None:
        """
        Validate decisions against JSON schema.

        Args:
            decisions: Decisions dict to validate

        Raises:
            ValueError: If validation fails
        """
        schema_file = PROJECT_ROOT / "schema/decisions.schema.json"
        if not schema_file.exists():
            logger.warning(
                f"Decisions schema file not found: {schema_file}. Skipping validation."
            )
            return

        schema = json.loads(schema_file.read_text())
        try:
            validate(instance=decisions, schema=schema)
        except ValidationError as e:
            raise ValueError(
                f"Decision validation failed:\n"
                f"  {e.message}\n"
                f"  Path: {'.'.join(str(p) for p in e.path)}"
            ) from e

    def save_decisions(self, decisions: dict[str, Any]) -> None:
        """
        Save decisions to workspace.

        Args:
            decisions: Decisions dict to save

        Raises:
            ValueError: If decisions don't match schema
        """
        # Validate before saving
        self._validate_decisions_schema(decisions)

        # Create decisions directory if needed
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

        # Write decisions file
        with open(self.decisions_file, "w") as f:
            yaml.dump(
                decisions,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        logger.info(f"Saved decisions to {self.decisions_file}")

        # Update cache
        self._decisions_cache = decisions

    def has_decisions(self) -> bool:
        """
        Check if workspace has decisions file.

        Returns:
            True if decisions file exists
        """
        return self.decisions_file.exists()

    def get_decision(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a specific decision value.

        Args:
            category: Decision category (security, firewall, governance, networking)
            key: Decision key within category
            default: Default value if decision not found

        Returns:
            Decision value or default
        """
        decisions = self.load_decisions()
        if not decisions:
            return default

        category_decisions = decisions.get("decisions", {}).get(category, {})
        return category_decisions.get(key, default)

    def apply_to_component(self, component: dict[str, Any]) -> dict[str, Any]:
        """
        Apply decisions to update a component's classification.

        This method checks if decisions can resolve BLOCKED/PARTIAL components
        and updates their level accordingly.

        Args:
            component: Component dict with level, component_type, etc.

        Returns:
            Updated component dict

        Example:
            >>> manager = DecisionManager(Path("/workspace"))
            >>> component = {"level": "BLOCKED", "component_type": "nsx-security-group"}
            >>> updated = manager.apply_to_component(component)
            >>> updated["level"]  # May now be "PARTIAL" or "READY" if decisions exist
        """
        decisions = self.load_decisions()
        if not decisions:
            return component

        # Make a copy to avoid mutating original
        updated = component.copy()
        comp_type = component.get("component_type", "").lower()
        current_level = component.get("level", "")

        # Only try to upgrade BLOCKED or PARTIAL components
        if current_level not in ["BLOCKED", "PARTIAL"]:
            return updated

        # Check for relevant decisions based on component type
        security_decisions = decisions.get("decisions", {}).get("security", {})
        firewall_decisions = decisions.get("decisions", {}).get("firewall", {})
        governance_decisions = decisions.get("decisions", {}).get("governance", {})
        networking_decisions = decisions.get("decisions", {}).get("networking", {})

        # NSX Security Groups → Check for label taxonomy decisions
        if "nsx" in comp_type and "group" in comp_type:
            if security_decisions.get("label_key") and security_decisions.get(
                "namespace_model"
            ):
                # Upgrade BLOCKED → PARTIAL (still need manual NetworkPolicy creation)
                if current_level == "BLOCKED":
                    updated["level"] = "PARTIAL"
                    updated["reason"] = (
                        "Label taxonomy defined via decisions - "
                        "manual NetworkPolicy creation required"
                    )

        # NSX Firewall → Check for firewall policy decisions
        elif "firewall" in comp_type:
            if firewall_decisions.get("egress_model"):
                if current_level == "BLOCKED":
                    updated["level"] = "PARTIAL"
                    updated["reason"] = (
                        "Firewall policy approach defined via decisions - "
                        "manual policy creation required"
                    )

        # Approval Workflows → Check for governance decisions
        elif "approval" in comp_type:
            if governance_decisions.get("approval_system"):
                if current_level == "BLOCKED":
                    updated["level"] = "PARTIAL"
                    updated["reason"] = (
                        "Approval system defined via decisions - "
                        "manual workflow configuration required"
                    )

        # Networking/Multi-NIC → Check for networking decisions
        elif "network" in comp_type or "nic" in comp_type:
            if networking_decisions.get("multinic_strategy") and networking_decisions.get(
                "vlan_mapping"
            ):
                if current_level == "PARTIAL":
                    # May be able to upgrade to SUPPORTED if mappings are complete
                    updated["level"] = "SUPPORTED"
                    updated["reason"] = "Network mapping defined via decisions"
                elif current_level == "BLOCKED":
                    updated["level"] = "PARTIAL"
                    updated["reason"] = "Network strategy defined via decisions"

        return updated

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of decisions made.

        Returns:
            Dict with counts of decisions by category
        """
        decisions = self.load_decisions()
        if not decisions:
            return {"has_decisions": False, "categories": {}}

        categories = decisions.get("decisions", {})
        summary = {
            "has_decisions": True,
            "categories": {},
        }

        for category, fields in categories.items():
            # Count non-empty fields
            filled_fields = sum(1 for v in fields.values() if v)
            summary["categories"][category] = {
                "total_fields": len(fields),
                "filled_fields": filled_fields,
                "completion_pct": int((filled_fields / len(fields)) * 100)
                if fields
                else 0,
            }

        return summary
