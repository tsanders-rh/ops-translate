"""
Parse and index vRealize Orchestrator (vRO) actions.

Actions are reusable JavaScript functions that workflows call by fully-qualified
name (fqname). This module provides deterministic parsing of action XML files
to extract metadata, input parameters, and script content.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from lxml import etree  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class ActionDef:
    """
    Definition of a vRO action.

    Represents a parsed vRO action XML file with extracted metadata,
    input parameters, and JavaScript source code.
    """

    fqname: str  # Fully-qualified name: com.acme.nsx/createFirewallRule
    name: str  # Action name: createFirewallRule
    module: str  # Module path: com.acme.nsx
    script: str  # JavaScript source code
    inputs: list[dict[str, str | None]]  # Input parameters
    result_type: str | None  # Return type
    description: str | None  # Action description
    source_path: Path  # Path to .action.xml file
    version: str | None  # Action version
    sha256: str  # Hash of script content


@dataclass
class ActionIndex:
    """
    Index of all actions in a vRO bundle.

    Provides fast lookup by fqname and filtering by module.
    """

    actions: dict[str, ActionDef]  # fqname -> ActionDef

    def get(self, fqname: str) -> ActionDef | None:
        """
        Get action by fully-qualified name.

        Args:
            fqname: Fully-qualified action name (e.g., "com.acme.nsx/createFirewallRule")

        Returns:
            ActionDef if found, None otherwise

        Example:
            >>> index.get("com.acme.nsx/createFirewallRule")
            ActionDef(fqname='com.acme.nsx/createFirewallRule', ...)
        """
        return self.actions.get(fqname)

    def find_by_module(self, module: str) -> list[ActionDef]:
        """
        Get all actions in a specific module.

        Args:
            module: Module path (e.g., "com.acme.nsx")

        Returns:
            List of ActionDef objects in the module

        Example:
            >>> index.find_by_module("com.acme.nsx")
            [ActionDef(fqname='com.acme.nsx/createFirewallRule', ...),
             ActionDef(fqname='com.acme.nsx/createSegment', ...)]
        """
        return [action for action in self.actions.values() if action.module == module]

    def __len__(self) -> int:
        """Return number of actions in index."""
        return len(self.actions)

    def __contains__(self, fqname: str) -> bool:
        """Check if action exists in index."""
        return fqname in self.actions


def parse_action_xml(action_file: Path) -> ActionDef:
    """
    Parse vRO action XML file into ActionDef.

    Extracts metadata, input parameters, and JavaScript source code from
    a vRO action XML file. Handles both dunes-script-module and action XML formats.

    Args:
        action_file: Path to .action.xml file

    Returns:
        ActionDef with parsed action metadata and script

    Raises:
        ValueError: If XML is malformed or required fields missing

    Example:
        >>> action = parse_action_xml(Path("actions/com.acme.nsx/createFirewallRule.action.xml"))
        >>> action.fqname
        'com.acme.nsx/createFirewallRule'
        >>> len(action.inputs)
        3
    """
    tree = etree.parse(str(action_file))
    root = tree.getroot()

    # Remove namespace for easier parsing
    for elem in root.iter():
        if elem.tag and "}" in str(elem.tag):
            elem.tag = elem.tag.split("}", 1)[1]

    # Detect XML format and extract metadata accordingly
    if root.tag == "dunes-script-module":
        # dunes-script-module format (standard vRO export)
        name = root.get("name")
        fqn = root.get("fqn") or _extract_fqname_from_path(action_file)
        result_type = root.get("result-type")
        version = root.get("version")

        # Extract description
        desc_elem = root.find("description")
        description = desc_elem.text if desc_elem is not None and desc_elem.text else None

        # Extract input parameters from <param> elements
        inputs = []
        for param in root.findall("param"):
            param_name = param.get("n")
            param_type = param.get("t")

            # Extract parameter description
            param_desc_elem = param.find("description")
            param_desc = (
                param_desc_elem.text
                if param_desc_elem is not None and param_desc_elem.text
                else None
            )

            inputs.append({"name": param_name, "type": param_type, "description": param_desc})

    elif root.tag == "action":
        # action format (alternative export format)
        # Always use filename-based FQN to match workflow call syntax
        fqn = _extract_fqname_from_path(action_file)

        # Extract name from filename (last part of FQN)
        name = fqn.split("/")[-1] if "/" in fqn else fqn

        # Extract description
        desc_elem = root.find("description")
        description = desc_elem.text if desc_elem is not None and desc_elem.text else None

        # Extract version
        version = root.get("version")

        # Extract result type from output
        result_type = None
        output_elem = root.find("output")
        if output_elem is not None:
            output_param = output_elem.find("param")
            if output_param is not None:
                result_type = output_param.get("type")

        # Extract input parameters
        inputs = []
        input_elem = root.find("input")
        if input_elem is not None:
            for param in input_elem.findall("param"):
                param_name = param.get("name")
                param_type = param.get("type")

                # Extract parameter description
                param_desc_elem = param.find("description")
                param_desc = (
                    param_desc_elem.text
                    if param_desc_elem is not None and param_desc_elem.text
                    else None
                )

                inputs.append({"name": param_name, "type": param_type, "description": param_desc})
    else:
        raise ValueError(f"Unknown action XML format: root tag is {root.tag}")

    # Extract script (common for both formats)
    script_elem = root.find("script")
    if script_elem is None or script_elem.text is None:
        raise ValueError(f"Action {name} has no script content in {action_file}")

    script = script_elem.text.strip()

    # Compute script hash for change detection
    script_hash = hashlib.sha256(script.encode()).hexdigest()

    # Extract module from fqn
    if "/" in fqn:
        module, action_name = fqn.rsplit("/", 1)
    else:
        module = ""
        action_name = fqn

    return ActionDef(
        fqname=fqn,
        name=name or action_name,
        module=module,
        script=script,
        inputs=inputs,
        result_type=result_type,
        description=description,
        source_path=action_file,
        version=version,
        sha256=script_hash,
    )


def _extract_fqname_from_path(action_file: Path) -> str:
    """
    Extract fully-qualified name from file path.

    Fallback method when fqn attribute is not present in XML.

    Args:
        action_file: Path to action XML file

    Returns:
        Fully-qualified action name

    Example:
        actions/com.acme.nsx/createFirewallRule.action.xml
        -> com.acme.nsx/createFirewallRule

        actions/utils/helper.action.xml
        -> utils/helper
    """
    parts = action_file.parts

    if "actions" in parts:
        actions_idx = parts.index("actions")
        relative_parts = parts[actions_idx + 1 :]

        # Module path + action name
        if len(relative_parts) > 1:
            module = ".".join(relative_parts[:-1])
            action_name = relative_parts[-1].replace(".action.xml", "")
            return f"{module}/{action_name}"
        else:
            return relative_parts[0].replace(".action.xml", "")

    return action_file.stem


def build_action_index(manifest: dict[str, Any]) -> ActionIndex:
    """
    Build ActionIndex from vRO bundle manifest.

    Parses all action files listed in the manifest and creates an index
    for fast lookup by fqname.

    Args:
        manifest: Bundle manifest from vrealize.import_vrealize_bundle()

    Returns:
        ActionIndex with all successfully parsed actions

    Example:
        >>> manifest = import_vrealize_bundle(bundle_path, workspace)
        >>> index = build_action_index(manifest)
        >>> len(index)
        42
    """
    actions = {}
    errors = []

    for action_entry in manifest.get("actions", []):
        action_file = Path(action_entry["absolute_path"])

        try:
            action_def = parse_action_xml(action_file)
            actions[action_def.fqname] = action_def
        except Exception as e:
            # Log warning but don't crash import
            error_msg = (
                f"Failed to parse action {action_file.name}: {e}. "
                "Action will not be available for resolution."
            )
            logger.warning(error_msg)
            errors.append({"file": str(action_file), "error": str(e)})
            continue

    if errors:
        logger.info(f"Successfully indexed {len(actions)} actions, {len(errors)} failed")

    return ActionIndex(actions=actions)


def save_action_index(action_index: ActionIndex, output_file: Path) -> None:
    """
    Save ActionIndex to JSON file.

    Args:
        action_index: ActionIndex to save
        output_file: Path to output JSON file

    Example:
        >>> save_action_index(index, workspace.root / "input/vrealize/action-index.json")
    """
    # Convert to serializable format
    index_data = {
        "actions": {
            fqname: {
                "fqname": action.fqname,
                "name": action.name,
                "module": action.module,
                "script": action.script,
                "inputs": action.inputs,
                "result_type": action.result_type,
                "description": action.description,
                "source_path": str(action.source_path),
                "version": action.version,
                "sha256": action.sha256,
            }
            for fqname, action in action_index.actions.items()
        },
        "count": len(action_index.actions),
        "indexed_at": datetime.now().isoformat(),
    }

    # Ensure parent directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    output_file.write_text(json.dumps(index_data, indent=2))


def load_action_index(index_file: Path) -> ActionIndex | None:
    """
    Load ActionIndex from JSON file.

    Args:
        index_file: Path to action-index.json file

    Returns:
        ActionIndex if file exists and is valid, None otherwise

    Example:
        >>> index = load_action_index(workspace.root / "input/vrealize/action-index.json")
        >>> if index:
        ...     action = index.get("com.acme.nsx/createFirewallRule")
    """
    if not index_file.exists():
        return None

    try:
        index_data = json.loads(index_file.read_text())
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse action index: {e}")
        return None

    actions = {}
    for fqname, action_data in index_data.get("actions", {}).items():
        actions[fqname] = ActionDef(
            fqname=action_data["fqname"],
            name=action_data["name"],
            module=action_data["module"],
            script=action_data["script"],
            inputs=action_data["inputs"],
            result_type=action_data.get("result_type"),
            description=action_data.get("description"),
            source_path=Path(action_data["source_path"]),
            version=action_data.get("version"),
            sha256=action_data["sha256"],
        )

    return ActionIndex(actions=actions)
