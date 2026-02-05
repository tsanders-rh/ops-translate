"""Configuration utility functions."""

from pathlib import Path


def get_llm_rate_limit_delay() -> float:
    """
    Get configured delay between LLM API calls.

    Returns:
        Delay in seconds (default: 1.0)

    This checks the workspace configuration for llm.rate_limit_delay.
    If not found or if there's an error loading the config, returns the default.
    """
    try:
        from ops_translate.workspace import Workspace

        ws = Workspace(Path.cwd())
        if ws.config_file.exists():
            config = ws.load_config()
            return float(config.get("llm", {}).get("rate_limit_delay", 1.0))
    except Exception:
        # If anything goes wrong, use default
        pass

    return 1.0  # Default: 1 second between API calls
