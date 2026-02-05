"""
Analyze vRealize Orchestrator workflows for external dependencies.

This module detects external dependencies in vRealize workflows that may
not be fully translatable to OpenShift-native equivalents, including:
- NSX-T operations (segments, firewall rules, security groups, etc.)
- Custom plugins
- REST API calls
- External system integrations

Analysis is performed offline without LLM assistance.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ops_translate.exceptions import FileNotFoundError as OpsFileNotFoundError


def analyze_vrealize_workflow(workflow_file: Path) -> dict[str, Any]:
    """
    Analyze a vRealize workflow for external dependencies.

    Args:
        workflow_file: Path to vRealize workflow XML file

    Returns:
        Dictionary containing analysis results with keys:
        - nsx_operations: NSX-T operations detected
        - plugins: Custom plugins referenced
        - rest_calls: External REST API calls
        - complexity_score: Overall complexity rating (0-100)
        - evidence: Supporting evidence for detections

    Raises:
        OpsFileNotFoundError: If workflow file doesn't exist
        ValueError: If workflow file is not valid XML

    Example:
        >>> result = analyze_vrealize_workflow(Path("workflow.xml"))
        >>> if result["nsx_operations"]:
        ...     print(f"Found NSX operations: {result['nsx_operations'].keys()}")
    """
    if not workflow_file.exists():
        raise OpsFileNotFoundError(str(workflow_file))

    try:
        tree = ET.parse(workflow_file)
        root = tree.getroot()

        # Extract namespace if present for proper XPath queries
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML in {workflow_file}: {e}")

    # Detect various external dependencies
    nsx_ops = detect_nsx_operations(root, namespace)
    plugins = detect_custom_plugins(root, namespace)
    rest_calls = detect_rest_calls(root, namespace)

    # Calculate complexity score
    complexity = calculate_complexity(nsx_ops, plugins, rest_calls)

    return {
        "source_file": str(workflow_file),
        "nsx_operations": nsx_ops,
        "custom_plugins": plugins,
        "rest_api_calls": rest_calls,
        "complexity_score": complexity,
        "has_external_dependencies": bool(nsx_ops or plugins or rest_calls),
    }


def detect_nsx_operations(root: ET.Element, namespace: str = "") -> dict[str, list[dict[str, Any]]]:
    """
    Detect NSX-T operations in vRealize workflow.

    Searches for NSX-specific keywords, API calls, and object types in:
    - Script content (JavaScript within <script> tags)
    - Workflow item names and types
    - Parameter names and descriptions

    Args:
        root: Root element of parsed vRealize workflow XML
        namespace: XML namespace prefix (e.g., "{http://vmware.com/vco/workflow}")

    Returns:
        Dictionary mapping NSX operation categories to detected instances.
        Each instance includes: name, location, confidence, evidence.

    Example result:
        {
            "segments": [
                {
                    "name": "Create Web Tier Segment",
                    "location": "workflow-item[@name='createSegment']",
                    "confidence": 0.95,
                    "evidence": "Found API call: nsxClient.createSegment()"
                }
            ],
            "firewall_rules": [...],
        }
    """
    nsx_ops: dict[str, list[dict[str, Any]]] = {
        "segments": [],
        "firewall_rules": [],
        "security_groups": [],
        "tier_gateways": [],
        "load_balancers": [],
        "nat_rules": [],
        "vpn": [],
        "distributed_firewall": [],
    }

    # NSX API patterns and keywords for each category
    patterns = {
        "segments": [
            r"nsxClient\.createSegment",
            r"nsxClient\.updateSegment",
            r"segment[-_]?id",
            r"LogicalSwitch",
            r"TransportZone",
        ],
        "firewall_rules": [
            r"nsxClient\.createFirewallRule",
            r"nsxClient\.updateFirewallRule",
            r"FirewallRule",
            r"SecurityPolicy",
        ],
        "security_groups": [
            r"nsxClient\.createSecurityGroup",
            r"nsxClient\.updateSecurityGroup",
            r"SecurityGroup",
            r"IPSet",
        ],
        "tier_gateways": [
            r"Tier[01]Gateway",
            r"nsxClient\.createGateway",
            r"EdgeGateway",
        ],
        "load_balancers": [
            r"LoadBalancer",
            r"nsxClient\.createLoadBalancer",
            r"VirtualServer",
            r"ServerPool",
        ],
        "nat_rules": [
            r"NatRule",
            r"nsxClient\.createNatRule",
            r"SNAT|DNAT",
        ],
        "vpn": [
            r"VPN",
            r"IPSecVPN",
            r"nsxClient\.createVPN",
        ],
        "distributed_firewall": [
            r"DistributedFirewall",
            r"DFW",
            r"L3Firewall",
        ],
    }

    # Search all script blocks
    script_tag = f"{namespace}script" if namespace else "script"
    for script_elem in root.iter(script_tag):
        script_text = script_elem.text or ""

        # Check each pattern category
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, script_text, re.IGNORECASE)
                for match in matches:
                    # Extract surrounding context for evidence
                    start = max(0, match.start() - 50)
                    end = min(len(script_text), match.end() + 50)
                    context = script_text[start:end].strip()

                    # Find parent workflow item for location
                    parent = script_elem
                    while parent is not None and parent.tag != "workflow-item":
                        parent = parent.getparent() if hasattr(parent, "getparent") else None

                    location = "unknown"
                    if parent is not None and "name" in parent.attrib:
                        location = f"workflow-item[@name='{parent.attrib['name']}']"

                    nsx_ops[category].append(
                        {
                            "name": pattern,
                            "location": location,
                            "confidence": 0.9,  # High confidence for API pattern match
                            "evidence": (
                                f"Pattern match: {match.group()} in context: " f"...{context}..."
                            ),
                        }
                    )

    # Search workflow item names and parameters
    workflow_item_tag = f"{namespace}workflow-item" if namespace else "workflow-item"
    for item in root.iter(workflow_item_tag):
        item_name = item.get("name", "")
        item_type = item.get("type", "")

        # Check item names against patterns
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, item_name, re.IGNORECASE) or re.search(
                    pattern, item_type, re.IGNORECASE
                ):
                    nsx_ops[category].append(
                        {
                            "name": item_name or item_type,
                            "location": f"workflow-item[@name='{item_name}']",
                            "confidence": 0.7,  # Lower confidence for name-based match
                            "evidence": (
                                f"Workflow item name/type contains NSX keyword: "
                                f"{item_name or item_type}"
                            ),
                        }
                    )

    # Return only categories with detections
    return {k: v for k, v in nsx_ops.items() if v}


def detect_custom_plugins(root: ET.Element, namespace: str = "") -> list[dict[str, Any]]:
    """
    Detect custom vRealize plugin usage.

    Identifies non-standard vRO plugins that may not have OpenShift equivalents.

    Args:
        root: Root element of parsed vRealize workflow XML
        namespace: XML namespace prefix

    Returns:
        List of detected plugin references with metadata

    Example result:
        [
            {
                "plugin_name": "com.vmware.library.vc.customPlugin",
                "location": "workflow-item[@name='callPlugin']",
                "confidence": 0.85,
                "evidence": "Plugin invocation: customPlugin.execute()"
            }
        ]
    """
    plugins = []

    # Known plugin patterns (excluding standard vRO plugins)
    # Standard plugins we skip: vCenter, vRA, basic scripting
    standard_plugins = {
        "com.vmware.library.vc",
        "com.vmware.library.vra",
        "com.vmware.library.workflow",
        "System",
    }

    # Look for plugin references in scripts
    script_tag = f"{namespace}script" if namespace else "script"
    for script_elem in root.iter(script_tag):
        script_text = script_elem.text or ""

        # Pattern: PluginModule.method() or plugin:method syntax
        plugin_patterns = [
            r"([a-zA-Z][a-zA-Z0-9_\.]+)\.[a-zA-Z][a-zA-Z0-9_]*\s*\(",  # Module.method()
            r"plugin:([a-zA-Z][a-zA-Z0-9_\.]+)",  # plugin:name
        ]

        for pattern in plugin_patterns:
            matches = re.finditer(pattern, script_text)
            for match in matches:
                plugin_name = match.group(1)

                # Skip if it's a standard plugin or JavaScript built-in
                if any(plugin_name.startswith(std) for std in standard_plugins):
                    continue
                if plugin_name in ["System", "Math", "Date", "String", "Array"]:
                    continue

                # Extract context
                start = max(0, match.start() - 50)
                end = min(len(script_text), match.end() + 50)
                context = script_text[start:end].strip()

                plugins.append(
                    {
                        "plugin_name": plugin_name,
                        "location": "script-block",
                        "confidence": 0.75,
                        "evidence": f"Plugin reference: ...{context}...",
                    }
                )

    return plugins


def detect_rest_calls(root: ET.Element, namespace: str = "") -> list[dict[str, Any]]:
    """
    Detect external REST API calls.

    Identifies REST operations that interact with external systems.

    Args:
        root: Root element of parsed vRealize workflow XML
        namespace: XML namespace prefix

    Returns:
        List of detected REST calls with metadata

    Example result:
        [
            {
                "endpoint": "https://api.example.com/v1/resources",
                "method": "POST",
                "location": "workflow-item[@name='callAPI']",
                "confidence": 0.9,
                "evidence": "REST call: restClient.post(url)"
            }
        ]
    """
    rest_calls = []

    # REST API patterns
    rest_patterns = [
        r"(https?://[^\s\"']+)",  # URLs
        r"RESTHost|RESTOperation",  # vRO REST objects
        r"restClient\.(get|post|put|delete|patch)",  # REST client calls
        r"fetch\s*\(",  # JavaScript fetch
        r"XMLHttpRequest",  # XHR
    ]

    script_tag = f"{namespace}script" if namespace else "script"
    for script_elem in root.iter(script_tag):
        script_text = script_elem.text or ""

        for pattern in rest_patterns:
            matches = re.finditer(pattern, script_text, re.IGNORECASE)
            for match in matches:
                # Extract context
                start = max(0, match.start() - 50)
                end = min(len(script_text), match.end() + 50)
                context = script_text[start:end].strip()

                rest_calls.append(
                    {
                        "endpoint": match.group(0) if pattern.startswith("(https?") else "unknown",
                        "method": "unknown",
                        "location": "script-block",
                        "confidence": 0.8,
                        "evidence": f"REST pattern: ...{context}...",
                    }
                )

    return rest_calls


def calculate_complexity(nsx_ops: dict[str, list], plugins: list, rest_calls: list) -> int:
    """
    Calculate overall complexity score for workflow translatability.

    Scoring:
    - Each NSX operation category: +15 points
    - Each plugin: +10 points
    - Each REST call: +5 points
    - Capped at 100

    Args:
        nsx_ops: Detected NSX operations by category
        plugins: Detected custom plugins
        rest_calls: Detected REST API calls

    Returns:
        Complexity score from 0 (simple, fully translatable) to 100 (very complex)

    Interpretation:
    - 0-20: Low complexity, likely fully translatable
    - 21-50: Medium complexity, may require manual steps
    - 51-80: High complexity, significant manual work needed
    - 81-100: Very high complexity, consider hybrid approach
    """
    score = 0

    # NSX operations contribute most to complexity
    score += len(nsx_ops) * 15

    # Custom plugins are also significant
    score += len(plugins) * 10

    # REST calls add moderate complexity
    score += len(rest_calls) * 5

    # Cap at 100
    return min(score, 100)


def write_analysis_report(analysis: dict[str, Any], output_dir: Path) -> None:
    """
    Write analysis results to both JSON and Markdown files.

    Creates:
    - analysis.vrealize.json: Machine-readable analysis data
    - analysis.vrealize.md: Human-readable analysis report

    Args:
        analysis: Analysis results from analyze_vrealize_workflow()
        output_dir: Directory to write analysis files (typically workspace/intent/)

    Side Effects:
        Writes two files to output_dir
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_file = output_dir / "analysis.vrealize.json"
    with open(json_file, "w") as f:
        json.dump(analysis, f, indent=2)

    # Write Markdown report
    md_file = output_dir / "analysis.vrealize.md"
    with open(md_file, "w") as f:
        f.write("# vRealize Workflow Analysis Report\n\n")
        f.write(f"**Source**: {analysis['source_file']}\n\n")
        f.write(f"**Complexity Score**: {analysis['complexity_score']}/100\n\n")

        if analysis["has_external_dependencies"]:
            f.write("## External Dependencies Detected\n\n")

            if analysis["nsx_operations"]:
                f.write("### NSX-T Operations\n\n")
                for category, operations in analysis["nsx_operations"].items():
                    category_title = category.replace("_", " ").title()
                    f.write(f"**{category_title}** ({len(operations)} instances)\n\n")
                    for op in operations:
                        f.write(f"- **{op['name']}** (confidence: {op['confidence']:.0%})\n")
                        f.write(f"  - Location: `{op['location']}`\n")
                        f.write(f"  - Evidence: {op['evidence']}\n\n")

            if analysis["custom_plugins"]:
                f.write("### Custom Plugins\n\n")
                for plugin in analysis["custom_plugins"]:
                    f.write(
                        f"- **{plugin['plugin_name']}** (confidence: {plugin['confidence']:.0%})\n"
                    )
                    f.write(f"  - Evidence: {plugin['evidence']}\n\n")

            if analysis["rest_api_calls"]:
                f.write("### REST API Calls\n\n")
                for call in analysis["rest_api_calls"]:
                    f.write(f"- **{call['endpoint']}**\n")
                    f.write(f"  - Evidence: {call['evidence']}\n\n")
        else:
            f.write("## No External Dependencies\n\n")
            f.write("This workflow appears to use only standard vRealize operations ")
            f.write("and should be fully translatable to OpenShift-native equivalents.\n\n")
