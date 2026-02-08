"""
vRealize Orchestrator workflow summarizer (no AI).
Parses workflow XML exports to detect inputs, decisions, approvals, etc.
"""

from pathlib import Path

from defusedxml import ElementTree


def summarize(xml_file: Path) -> str:
    """
    Summarize a vRealize workflow XML.

    Returns a markdown-formatted summary string.
    """
    try:
        tree = ElementTree.parse(xml_file)
        root = tree.getroot()
    except ElementTree.ParseError:
        return "**Error:** Unable to parse XML"

    summary = []

    # Extract workflow display name
    display_name = root.findtext(".//display-name") or root.findtext(".//displayName")
    if display_name:
        summary.append(f"**Workflow:** {display_name}")

    # Extract inputs
    inputs = extract_inputs(root)
    if inputs:
        summary.append("\n**Inputs:**")
        for inp in inputs:
            summary.append(f"- `{inp['name']}` ({inp['type']})")

    # Detect approval
    if detect_approval(root):
        summary.append("\n**Approval Semantics:** Detected")

    # Detect environment branching
    if detect_environment_branching(root):
        summary.append("\n**Environment Branching:** Detected")

    # Detect tagging
    if detect_tagging(root):
        summary.append("\n**Tagging/Metadata:** Present")

    # Detect network/storage
    if detect_network_storage(root):
        summary.append("\n**Network/Storage Selection:** Present")

    return "\n".join(summary) if summary else "No detectable features"


def extract_inputs(root) -> list:
    """Extract workflow inputs."""
    inputs = []

    # Try multiple common XML paths for inputs
    for input_elem in root.findall(".//input"):
        name = input_elem.get("name") or input_elem.findtext("name")
        type_ = input_elem.get("type") or input_elem.findtext("type") or "unknown"

        if name:
            inputs.append({"name": name, "type": type_})

    # Alternative path
    for input_elem in root.findall(".//inputs/entry"):
        name = input_elem.get("key")
        type_ = input_elem.findtext("value/type") or "unknown"

        if name:
            inputs.append({"name": name, "type": type_})

    return inputs


def detect_approval(root) -> bool:
    """Detect approval-related elements."""
    # Check for approval keywords in element names or script content
    for elem in root.iter():
        if elem.tag and "approval" in elem.tag.lower():
            return True
        if elem.text and "approval" in elem.text.lower():
            return True
        if elem.attrib.get("name", "").lower().find("approval") != -1:
            return True

    return False


def detect_environment_branching(root) -> bool:
    """Detect environment branching logic."""
    # Look for decision elements or conditionals with environment keywords
    for elem in root.iter():
        if elem.tag and "decision" in elem.tag.lower():
            # Check for environment-related expressions
            expression = elem.get("expression", "") + elem.text or ""
            if any(env in expression.lower() for env in ["dev", "prod", "environment"]):
                return True

    return False


def detect_tagging(root) -> bool:
    """Detect tagging operations."""
    for elem in root.iter():
        text = (elem.text or "") + (elem.get("name", ""))
        if any(keyword in text.lower() for keyword in ["tag", "metadata", "customattribute"]):
            return True

    return False


def detect_network_storage(root) -> bool:
    """Detect network or storage operations."""
    for elem in root.iter():
        text = (elem.text or "") + (elem.get("name", ""))
        if any(
            keyword in text.lower() for keyword in ["network", "storage", "datastore", "portgroup"]
        ):
            return True

    return False
