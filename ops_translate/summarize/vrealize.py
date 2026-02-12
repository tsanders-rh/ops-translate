"""
vRealize Orchestrator workflow summarizer (no AI).
Parses workflow XML exports to detect inputs, decisions, approvals, etc.

Also supports importing vRO export bundles (.package, .zip, directory)
containing workflows, actions, and configuration elements.
"""

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from defusedxml import ElementTree  # type: ignore[import-untyped]


def summarize(xml_file: Path) -> str:
    """
    Summarize a vRealize workflow XML.

    Returns a markdown-formatted summary string.

    This function wraps summarize_with_actions() for backward compatibility.
    """
    return summarize_with_actions(xml_file, action_index=None)


def summarize_with_actions(xml_file: Path, action_index: Any = None) -> str:
    """
    Summarize a vRealize workflow XML including resolved action scripts.

    Args:
        xml_file: Path to workflow XML file
        action_index: Optional ActionIndex for action resolution

    Returns:
        Markdown-formatted summary string
    """
    try:
        tree = ElementTree.parse(xml_file)
        root = tree.getroot()
    except ElementTree.ParseError:
        return "**Error:** Unable to parse XML"

    if root is None:
        return "**Error:** Empty XML document"

    summary = []

    # Extract workflow display name (with namespace handling)
    # Try with namespace first
    ns = {"vco": "http://vmware.com/vco/workflow"}
    display_name = root.findtext(".//vco:display-name", namespaces=ns)
    if not display_name:
        # Try without namespace
        display_name = root.findtext(".//display-name")
    if not display_name:
        # Try alternative name
        display_name = root.findtext(".//displayName")
    if not display_name:
        display_name = root.findtext(".//vco:displayName", namespaces=ns)
    if display_name:
        summary.append(f"**Workflow:** {display_name}")

    # Extract inputs
    inputs = extract_inputs(root)
    if inputs:
        summary.append("\n**Inputs:**")
        for inp in inputs:
            summary.append(f"- `{inp['name']}` ({inp['type']})")

    # NEW: Action resolution and integration detection
    if action_index is not None:
        from ops_translate.translate.vrealize_workflow import WorkflowParser
        from ops_translate.analyze.vrealize import (
            detect_nsx_operations,
            detect_custom_plugins,
            detect_rest_calls,
            detect_nsx_patterns_in_script,
            merge_nsx_operations,
        )

        # Parse workflow with action resolution
        parser = WorkflowParser(action_index=action_index)
        items = parser.parse_file(xml_file)

        # Collect all scripts (workflow + actions)
        all_nsx_ops: dict[str, list] = {}
        all_plugins = []
        all_rest_calls = []
        action_count = 0
        unresolved_count = 0

        for item in items:
            # Analyze workflow script
            if item.script:
                nsx_ops = detect_nsx_operations(root, item.script)
                all_nsx_ops = merge_nsx_operations(all_nsx_ops, nsx_ops)

                plugins = detect_custom_plugins(root, item.script)
                all_plugins.extend(plugins)

                rest = detect_rest_calls(root, item.script)
                all_rest_calls.extend(rest)

            # Analyze resolved action scripts
            for action in item.resolved_actions:
                action_count += 1
                if action.script:
                    # Detect NSX in action script
                    action_nsx = detect_nsx_patterns_in_script(
                        action.script, f"action:{action.fqname}"
                    )
                    all_nsx_ops = merge_nsx_operations(all_nsx_ops, action_nsx)

                    # Note: detect_custom_plugins() and detect_rest_calls() require XML root
                    # For action scripts, we only detect NSX operations via detect_nsx_patterns_in_script()
                    # TODO: Extract script-based plugin/REST detection logic for action scripts

            unresolved_count += len(item.unresolved_actions)

        # Add integration findings to summary
        if action_count > 0 or unresolved_count > 0:
            summary.append(f"\n**Actions:** {action_count} resolved")
            if unresolved_count > 0:
                summary.append(f"  ⚠️  {unresolved_count} unresolved")

        if all_nsx_ops:
            summary.append("\n**NSX-T Operations:**")
            for category, ops in sorted(all_nsx_ops.items()):
                category_name = category.replace("_", " ").title()
                summary.append(f"- {category_name}: {len(ops)} detected")

        if all_plugins:
            # Get unique plugin names and sort
            unique_plugins = sorted({p["plugin_name"] for p in all_plugins})
            summary.append(f"\n**Custom Plugins:** {', '.join(unique_plugins)}")

        if all_rest_calls:
            summary.append(f"\n**REST API Calls:** {len(all_rest_calls)} detected")

    # Existing simple detections (keep for backward compatibility)
    if detect_approval(root):
        summary.append("\n**Approval Semantics:** Detected")

    if detect_environment_branching(root):
        summary.append("\n**Environment Branching:** Detected")

    if detect_tagging(root):
        summary.append("\n**Tagging/Metadata:** Present")

    if detect_network_storage(root):
        summary.append("\n**Network/Storage Selection:** Present")

    return "\n".join(summary) if summary else "No detectable features"


def extract_inputs(root) -> list:
    """Extract workflow inputs."""
    inputs = []
    ns = {"vco": "http://vmware.com/vco/workflow"}

    # Try with namespace first
    for input_elem in root.findall(".//vco:input/vco:param", namespaces=ns):
        name = input_elem.get("name")
        type_ = input_elem.get("type") or "unknown"
        if name:
            inputs.append({"name": name, "type": type_})

    # Try without namespace
    if not inputs:
        for input_elem in root.findall(".//input/param"):
            name = input_elem.get("name")
            type_ = input_elem.get("type") or "unknown"
            if name:
                inputs.append({"name": name, "type": type_})

    # Alternative path
    if not inputs:
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


# Bundle import functions


def import_vrealize_bundle(source_path: Path, workspace_root: Path) -> dict[str, Any]:
    """
    Import vRealize bundle (single XML, directory, or .package/.zip).

    Determines bundle type and delegates to appropriate handler.

    Args:
        source_path: Path to file or directory to import
        workspace_root: Workspace root directory

    Returns:
        Manifest dict with discovered artifacts

    Raises:
        ValueError: If source type is unsupported or path is invalid
    """
    if not source_path.exists():
        raise ValueError(f"Path not found: {source_path}")

    if source_path.is_file():
        if source_path.suffix == ".xml":
            # Single workflow - backwards compatibility
            return _import_single_workflow(source_path, workspace_root)
        elif source_path.suffix in [".package", ".zip"]:
            # ZIP archive bundle
            return _import_package_bundle(source_path, workspace_root)
        else:
            raise ValueError(f"Unsupported file type: {source_path.suffix}")

    elif source_path.is_dir():
        # Directory bundle
        return _import_directory_bundle(source_path, workspace_root)

    else:
        raise ValueError(f"Invalid path: {source_path}")


def _import_single_workflow(xml_file: Path, workspace_root: Path) -> dict[str, Any]:
    """
    Import single workflow XML file (backwards compatibility).

    Args:
        xml_file: Path to workflow XML file
        workspace_root: Workspace root directory

    Returns:
        Manifest dict with single workflow
    """
    manifest = {
        "source_path": str(xml_file),
        "source_type": "vrealize_workflow",
        "import_timestamp": datetime.now().isoformat(),
        "sha256": _compute_file_hash(xml_file),
        "workflows": [
            {
                "path": xml_file.name,
                "absolute_path": str(xml_file.absolute()),
                "name": xml_file.stem,
                "sha256": _compute_file_hash(xml_file),
            }
        ],
        "actions": [],
        "configurations": [],
    }

    return manifest


def _import_package_bundle(package_file: Path, workspace_root: Path) -> dict[str, Any]:
    """
    Extract and import vRO .package/.zip bundle.

    Includes zip-slip protection to prevent path traversal attacks.

    Args:
        package_file: Path to .package or .zip file
        workspace_root: Workspace root directory

    Returns:
        Manifest dict with discovered artifacts

    Raises:
        ValueError: If archive contains unsafe paths
    """
    # Create extraction directory
    extract_dir = workspace_root / "input/vrealize/extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Extract archive with security validation
    with zipfile.ZipFile(package_file, "r") as zf:
        # Validate all paths before extraction (zip-slip protection)
        for member in zf.namelist():
            member_path = extract_dir / member

            # Ensure the extracted path is within extract_dir
            if not _is_safe_path(extract_dir, member_path):
                raise ValueError(f"Unsafe path in archive: {member}")

        # Extract safely
        zf.extractall(extract_dir)

    # Find the bundle directory
    # If there's a single top-level directory, use that
    # Otherwise, use the extraction directory itself
    bundle_dir = extract_dir
    top_level_items = list(extract_dir.iterdir())
    if len(top_level_items) == 1 and top_level_items[0].is_dir():
        # Single directory - likely the bundle root
        potential_bundle = top_level_items[0]
        # Check if it has bundle structure
        if (
            (potential_bundle / "workflows").exists()
            or (potential_bundle / "actions").exists()
            or (potential_bundle / "configurations").exists()
        ):
            bundle_dir = potential_bundle

    # Process extracted directory
    return _import_directory_bundle(bundle_dir, workspace_root)


def _import_directory_bundle(bundle_dir: Path, workspace_root: Path) -> dict[str, Any]:
    """
    Import vRO bundle from directory structure.

    Discovers workflows, actions, and configurations from standard vRO export structure:
    - workflows/*.workflow.xml
    - actions/{module}/*.action.xml
    - configurations/*.xml

    Args:
        bundle_dir: Path to bundle directory
        workspace_root: Workspace root directory

    Returns:
        Manifest with discovered artifacts and metadata
    """
    manifest: dict[str, Any] = {
        "source_path": str(bundle_dir),
        "source_type": "vrealize_bundle",
        "import_timestamp": datetime.now().isoformat(),
        "workflows": [],
        "actions": [],
        "configurations": [],
        "sha256": _compute_dir_hash(bundle_dir),
    }

    # Discover workflows
    workflows_dir = bundle_dir / "workflows"
    if workflows_dir.exists():
        for workflow_file in workflows_dir.glob("**/*.workflow.xml"):
            manifest["workflows"].append(
                {
                    "path": str(workflow_file.relative_to(bundle_dir)),
                    "absolute_path": str(workflow_file.absolute()),
                    "name": workflow_file.stem.replace(".workflow", ""),
                    "sha256": _compute_file_hash(workflow_file),
                }
            )

    # Discover actions
    actions_dir = bundle_dir / "actions"
    if actions_dir.exists():
        for action_file in actions_dir.glob("**/*.action.xml"):
            manifest["actions"].append(
                {
                    "path": str(action_file.relative_to(bundle_dir)),
                    "absolute_path": str(action_file.absolute()),
                    "fqname": _extract_action_fqname(action_file, actions_dir),
                    "sha256": _compute_file_hash(action_file),
                }
            )

    # Discover configurations
    configs_dir = bundle_dir / "configurations"
    if configs_dir.exists():
        for config_file in configs_dir.glob("**/*.xml"):
            manifest["configurations"].append(
                {
                    "path": str(config_file.relative_to(bundle_dir)),
                    "absolute_path": str(config_file.absolute()),
                    "sha256": _compute_file_hash(config_file),
                }
            )

    # Build and save action index
    from ops_translate.summarize.vrealize_actions import (
        build_action_index,
        save_action_index,
    )

    action_index = build_action_index(manifest)
    action_index_file = workspace_root / "input/vrealize/action-index.json"
    save_action_index(action_index, action_index_file)

    # Add action index info to manifest
    manifest["action_index"] = {
        "count": len(action_index),
        "file": "input/vrealize/action-index.json",
    }

    # Write manifest to workspace (after action index is added)
    manifest_file = workspace_root / "input/vrealize/manifest.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest, indent=2))

    return manifest


# Helper functions


def _is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """
    Check if target_path resolves within base_dir (zip-slip protection).

    Prevents path traversal attacks in ZIP archives.

    Args:
        base_dir: Base directory that should contain the target
        target_path: Path to validate

    Returns:
        True if safe, False if path escapes base_dir
    """
    try:
        resolved = target_path.resolve()
        base_resolved = base_dir.resolve()
        return resolved.is_relative_to(base_resolved)
    except (ValueError, RuntimeError):
        return False


def _compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of file.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _compute_dir_hash(dir_path: Path) -> str:
    """
    Compute aggregate hash of directory contents.

    Creates deterministic hash based on all file paths and contents.

    Args:
        dir_path: Path to directory

    Returns:
        Hexadecimal SHA256 hash of directory contents
    """
    sha256 = hashlib.sha256()

    for file_path in sorted(dir_path.rglob("*")):
        if file_path.is_file():
            # Include relative path in hash for structure sensitivity
            sha256.update(str(file_path.relative_to(dir_path)).encode())
            sha256.update(_compute_file_hash(file_path).encode())

    return sha256.hexdigest()


def _extract_action_fqname(action_file: Path, actions_dir: Path) -> str:
    """
    Extract action fully-qualified name from file path.

    vRO actions are organized as: actions/{module}/{action}.action.xml
    FQN format: {module}/{action}

    Examples:
        actions/com.acme.nsx/createFirewallRule.action.xml
        -> com.acme.nsx/createFirewallRule

        actions/utils/helper.action.xml
        -> utils/helper

    Args:
        action_file: Path to action XML file
        actions_dir: Base actions directory

    Returns:
        Fully-qualified action name
    """
    try:
        # Get relative path from actions directory
        rel_path = action_file.relative_to(actions_dir)
        parts = rel_path.parts

        if len(parts) == 1:
            # Action directly in actions/ (no module)
            return rel_path.stem.replace(".action", "")
        else:
            # Module path + action name
            module = "/".join(parts[:-1])
            action_name = parts[-1].replace(".action.xml", "")
            return f"{module}/{action_name}"

    except ValueError:
        # Fallback if path is not relative to actions_dir
        return action_file.stem.replace(".action", "")
