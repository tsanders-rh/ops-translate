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

    # Detect VM templates/images
    templates = detect_vm_templates(content)
    if templates:
        summary.append("\n**VM Templates/Images:**")
        for template in templates:
            summary.append(f"- {template['type']}: `{template['name']}`")

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


def detect_vm_templates(content: str) -> list[dict[str, str]]:
    """
    Detect VM templates and images in PowerCLI scripts.

    Returns list of dicts with 'type' and 'name' keys.
    """
    templates = []

    # Detect New-VM -Template parameter
    # Pattern: New-VM ... -Template "TemplateName" or -Template $Variable
    template_pattern = r'New-VM[^;]*?-Template\s+["\']([^"\']+)["\']'
    for match in re.finditer(template_pattern, content, re.IGNORECASE):
        template_name = match.group(1)
        templates.append({"type": "Template", "name": template_name})

    # Also check for variable-based templates
    template_var_pattern = r"New-VM[^;]*?-Template\s+\$(\w+)"
    for match in re.finditer(template_var_pattern, content, re.IGNORECASE):
        var_name = match.group(1)
        # Try to find where the variable is set
        var_value_pattern = rf'\${var_name}\s*=\s*["\']([^"\']+)["\']'
        var_match = re.search(var_value_pattern, content, re.IGNORECASE)
        if var_match:
            template_name = var_match.group(1)
            templates.append({"type": "Template", "name": template_name})
        else:
            templates.append({"type": "Template", "name": f"${var_name} (variable)"})

    # Detect Import-VApp -Source parameter (OVA/OVF imports)
    # Pattern: Import-VApp -Source "path/to/file.ova"
    import_pattern = r'Import-VApp[^;]*?-Source\s+["\']([^"\']+)["\']'
    for match in re.finditer(import_pattern, content, re.IGNORECASE):
        source_path = match.group(1)
        # Determine type from extension
        if source_path.lower().endswith(".ova"):
            source_type = "OVA"
        elif source_path.lower().endswith(".ovf"):
            source_type = "OVF"
        else:
            source_type = "Image"
        templates.append({"type": source_type, "name": source_path})

    # Detect Clone-VM (cloning from existing VM)
    clone_pattern = r'Clone-VM[^;]*?-VM\s+["\']([^"\']+)["\']'
    for match in re.finditer(clone_pattern, content, re.IGNORECASE):
        vm_name = match.group(1)
        templates.append({"type": "Clone", "name": vm_name})

    return templates
