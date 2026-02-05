"""
Workspace management for ops-translate.
"""

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import ValidationError, validate

# Get project root to find schema
PROJECT_ROOT = Path(__file__).parent.parent


class Workspace:
    """Manages the ops-translate workspace structure and configuration."""

    REQUIRED_DIRS = [
        "input/powercli",
        "input/vrealize",
        "intent",
        "mapping",
        "output/ansible",
        "output/kubevirt",
        "runs",
    ]

    DEFAULT_CONFIG = {
        "llm": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "api_key_env": "OPS_TRANSLATE_LLM_API_KEY",
            "rate_limit_delay": 1.0,  # seconds between API calls
        },
        "profiles": {
            "lab": {
                "default_namespace": "virt-lab",
                "default_network": "lab-network",
                "default_storage_class": "nfs",
            },
            "prod": {
                "default_namespace": "virt-prod",
                "default_network": "prod-network",
                "default_storage_class": "ceph-rbd",
            },
        },
    }

    def __init__(self, root: Path):
        self.root = Path(root)
        self.config_file = self.root / "ops-translate.yaml"

    def initialize(self) -> None:
        """Initialize workspace directory structure and config."""
        # Create directories
        for dir_path in self.REQUIRED_DIRS:
            (self.root / dir_path).mkdir(parents=True, exist_ok=True)

        # Write default config
        with open(self.config_file, "w") as f:
            yaml.dump(self.DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)

    def load_config(self) -> dict[str, Any]:
        """Load and validate workspace configuration."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file) as f:
            config = yaml.safe_load(f)

        if config is None:
            raise ValueError(f"Config file is empty: {self.config_file}")

        if not isinstance(config, dict):
            raise ValueError(f"Invalid config file: expected dict, got {type(config).__name__}")

        # Validate against schema
        self._validate_config_schema(config)

        return config

    def _validate_config_schema(self, config: dict) -> None:
        """Validate config against JSON schema."""
        schema_file = PROJECT_ROOT / "schema/config.schema.json"
        if not schema_file.exists():
            # Schema not found - warn but continue (backward compatibility)
            return

        schema = json.loads(schema_file.read_text())
        try:
            validate(instance=config, schema=schema)
        except ValidationError as e:
            raise ValueError(
                f"Configuration validation failed:\n"
                f"  {e.message}\n"
                f"  Path: {'.'.join(str(p) for p in e.path)}"
            ) from e
