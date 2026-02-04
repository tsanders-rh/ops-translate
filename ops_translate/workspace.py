"""
Workspace management for ops-translate.
"""
from pathlib import Path
from typing import Dict, Any
import yaml


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

    def load_config(self) -> Dict[str, Any]:
        """Load workspace configuration."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file) as f:
            return yaml.safe_load(f)
