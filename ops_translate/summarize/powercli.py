"""
PowerCLI script summarizer (no AI).
Parses PowerCLI scripts to detect parameters, environment branching, tags, etc.
"""

import re
from pathlib import Path
from typing import Any


def summarize(ps_file: Path) -> str:
    """
    Summarize a PowerCLI script.

    Returns a markdown-formatted summary string.
    """
    content = ps_file.read_text()
    summary = []

    # Detect parameters
    params = extract_parameters(content)
    if params:
        summary.append("**Parameters:**")
        for param in params:
            summary.append(
                f"- `{param['name']}` ({param['type']})"
                + (" [required]" if param["required"] else "")
            )

    # Detect environment branching
    if detect_environment_branching(content):
        summary.append("\n**Environment Branching:** Detected (dev/prod)")

    # Detect tagging
    if detect_tagging(content):
        summary.append("\n**Tagging/Metadata:** Present")

    # Detect network/storage selection
    if detect_network_storage(content):
        summary.append("\n**Network/Storage Selection:** Present")

    return "\n".join(summary) if summary else "No detectable features"


def extract_parameters(content: str) -> list:
    """Extract param() block parameters."""
    params: list[dict[str, Any]] = []

    # Simple pattern matching for param blocks
    param_block_match = re.search(r"param\s*\((.*?)\)", content, re.DOTALL | re.IGNORECASE)
    if not param_block_match:
        return params

    param_block = param_block_match.group(1)

    # Extract individual parameters
    param_pattern = r"\[\s*Parameter.*?\]\s*\[(\w+)\]\s*\$(\w+)"
    for match in re.finditer(param_pattern, param_block, re.IGNORECASE):
        param_type = match.group(1)
        param_name = match.group(2)

        # Check if required (simplified)
        required = "Mandatory" in param_block

        params.append({"name": param_name, "type": param_type, "required": required})

    return params


def detect_environment_branching(content: str) -> bool:
    """Detect environment branching (dev/prod)."""
    patterns = [
        r'ValidateSet.*?["\']dev["\'].*?["\']prod["\']',
        r'\$environment\s*-eq\s*["\']prod["\']',
        r'\$environment\s*-eq\s*["\']dev["\']',
        r"if.*?\$env.*?prod",
    ]

    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    return False


def detect_tagging(content: str) -> bool:
    """Detect tagging operations."""
    patterns = [
        r"Tags\s*=",
        r"New-TagAssignment",
        r'@\(["\'].*?:.*?["\']',  # PowerShell array with key:value
    ]

    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    return False


def detect_network_storage(content: str) -> bool:
    """Detect network or storage profile selection."""
    patterns = [
        r"\$Network\s*=\s*if",
        r"\$Storage\s*=\s*if",
        r"Get-NetworkAdapter",
        r"New-NetworkAdapter",
        r"Get-Datastore",
        r"New-HardDisk",
    ]

    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    return False
