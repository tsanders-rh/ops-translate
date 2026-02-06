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
from pathlib import Path
from typing import Any

from lxml import etree as ET

from ops_translate.exceptions import FileNotFoundError as OpsFileNotFoundError


def calculate_signal_counts(
    nsx_ops: dict[str, list], plugins: list, rest_calls: list
) -> dict[str, int]:
    """
    Calculate count of detection signals for summary.

    Args:
        nsx_ops: NSX operations dict with categories as keys
        plugins: List of custom plugin detections
        rest_calls: List of REST API call detections

    Returns:
        Dictionary with signal counts:
        - nsx_keywords: Total NSX operation detections across all categories
        - rest_calls: Number of REST API calls detected
        - plugin_refs: Number of custom plugin references

    Example:
        >>> nsx_ops = {"segments": [{"name": "seg1"}, {"name": "seg2"}],
        ...            "firewall_rules": [{"name": "fw1"}]}
        >>> plugins = [{"name": "plugin1"}]
        >>> rest_calls = [{"endpoint": "/api/v1"}]
        >>> calculate_signal_counts(nsx_ops, plugins, rest_calls)
        {'nsx_keywords': 3, 'rest_calls': 1, 'plugin_refs': 1}
    """
    return {
        "nsx_keywords": sum(len(ops) for ops in nsx_ops.values()),
        "rest_calls": len(rest_calls),
        "plugin_refs": len(plugins),
    }


def calculate_overall_confidence(nsx_ops: dict[str, list], plugins: list, rest_calls: list) -> str:
    """
    Calculate overall confidence rating based on average confidence scores.

    Aggregates confidence scores from all detections and returns a categorical
    rating: low, medium, or high.

    Confidence thresholds:
    - high: average >= 0.75
    - medium: average >= 0.50
    - low: average < 0.50

    Args:
        nsx_ops: NSX operations dict with confidence scores
        plugins: Custom plugin detections (typically high confidence)
        rest_calls: REST API call detections with confidence scores

    Returns:
        Confidence rating string: "low", "medium", or "high"

    Example:
        >>> nsx_ops = {"segments": [{"confidence": 0.9}, {"confidence": 0.85}]}
        >>> plugins = [{"name": "plugin1"}]  # Implicit 0.95 confidence
        >>> rest_calls = [{"confidence": 0.8}]
        >>> calculate_overall_confidence(nsx_ops, plugins, rest_calls)
        'high'
    """
    confidences = []

    # Collect NSX operation confidences
    for category, ops in nsx_ops.items():
        for op in ops:
            confidences.append(op.get("confidence", 0.5))

    # Plugins are typically high confidence (explicit references)
    for _ in plugins:
        confidences.append(0.95)

    # Collect REST call confidences
    for call in rest_calls:
        confidences.append(call.get("confidence", 0.5))

    # Calculate average confidence
    if not confidences:
        return "low"

    avg_confidence = sum(confidences) / len(confidences)

    # Categorize
    if avg_confidence >= 0.75:
        return "high"
    elif avg_confidence >= 0.50:
        return "medium"
    else:
        return "low"


def build_evidence_array(
    nsx_ops: dict[str, list], plugins: list, rest_calls: list
) -> list[dict[str, Any]]:
    """
    Build structured evidence array from all detections.

    Consolidates evidence from NSX operations, plugins, and REST calls into
    a unified array with node, snippet, and confidence information.

    Args:
        nsx_ops: NSX operations dict with evidence
        plugins: Custom plugin detections
        rest_calls: REST API call detections

    Returns:
        List of evidence dictionaries with keys:
        - node: Location/node where detection occurred
        - snippet: Code snippet or evidence text
        - confidence: Detection confidence score (0.0-1.0)
        - type: Type of detection (nsx, plugin, rest_call)

    Example:
        >>> nsx_ops = {"segments": [
        ...     {"location": "task1", "evidence": "nsxClient.create...", "confidence": 0.9}
        ... ]}
        >>> build_evidence_array(nsx_ops, [], [])
        [{'node': 'task1', 'snippet': 'nsxClient.create...', 'confidence': 0.9, 'type': 'nsx'}]
    """
    evidence = []

    # Add NSX operation evidence
    for category, ops in nsx_ops.items():
        for op in ops:
            evidence.append(
                {
                    "node": op.get("location", "unknown"),
                    "snippet": op.get("evidence", ""),
                    "confidence": op.get("confidence", 0.5),
                    "type": "nsx",
                    "category": category,
                }
            )

    # Add plugin evidence
    for plugin in plugins:
        evidence.append(
            {
                "node": plugin.get("location", "unknown"),
                "snippet": plugin.get("evidence", plugin.get("name", "")),
                "confidence": 0.95,  # Plugin references are high confidence
                "type": "plugin",
                "category": "custom_plugin",
            }
        )

    # Add REST call evidence
    for call in rest_calls:
        evidence.append(
            {
                "node": call.get("location", "unknown"),
                "snippet": call.get("evidence", call.get("endpoint", "")),
                "confidence": call.get("confidence", 0.5),
                "type": "rest_call",
                "category": call.get("call_type", "unknown"),
            }
        )

    # Sort by confidence (highest first)
    evidence.sort(key=lambda e: e["confidence"], reverse=True)

    return evidence


def analyze_vrealize_workflow(workflow_file: Path) -> dict[str, Any]:
    """
    Analyze a vRealize workflow for external dependencies.

    Args:
        workflow_file: Path to vRealize workflow XML file

    Returns:
        Dictionary containing analysis results with keys:
        - source_file: Path to the analyzed workflow file
        - signals: Signal counts dict with nsx_keywords, rest_calls, plugin_refs
        - confidence: Overall confidence rating ("low", "medium", or "high")
        - evidence: Array of evidence dicts with node, snippet, confidence, type
        - nsx_operations: NSX-T operations detected (detailed dict by category)
        - custom_plugins: Custom plugins referenced (detailed list)
        - rest_api_calls: External REST API calls (detailed list)
        - complexity_score: Overall complexity rating (0-100)
        - has_external_dependencies: Boolean flag for any external dependencies

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
        # Parse XML with lxml (supports line number tracking via sourceline)
        tree = ET.parse(str(workflow_file))
        root = tree.getroot()

        # Extract namespace if present for proper XPath queries
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML in {workflow_file}: {e}")

    # Detect various external dependencies (pass filename for location tracking)
    nsx_ops = detect_nsx_operations(root, namespace, workflow_file)
    plugins = detect_custom_plugins(root, namespace)
    rest_calls = detect_rest_calls(root, namespace)

    # Calculate complexity score
    complexity = calculate_complexity(nsx_ops, plugins, rest_calls)

    # Build structured signal output
    signals = calculate_signal_counts(nsx_ops, plugins, rest_calls)
    confidence = calculate_overall_confidence(nsx_ops, plugins, rest_calls)
    evidence = build_evidence_array(nsx_ops, plugins, rest_calls)

    return {
        "source_file": str(workflow_file),
        "signals": signals,
        "confidence": confidence,
        "evidence": evidence,
        "nsx_operations": nsx_ops,
        "custom_plugins": plugins,
        "rest_api_calls": rest_calls,
        "complexity_score": complexity,
        "has_external_dependencies": bool(nsx_ops or plugins or rest_calls),
    }


def calculate_detection_confidence(match_type: str, context: str, pattern: str = "") -> float:
    """
    Calculate confidence score for a detection based on multiple signals.

    Confidence scoring logic:
    - API call patterns (nsxClient.createX): High confidence (0.85-0.95)
    - Object type keywords (Segment, FirewallRule): Medium confidence (0.5-0.7)
    - Generic keywords (nsx, tier1): Low confidence (0.3-0.5)
    - Boosts applied for supporting evidence in context

    Args:
        match_type: Type of match - "api_call", "object_type", or "keyword"
        context: Surrounding text context for the match
        pattern: The specific pattern that was matched

    Returns:
        Confidence score between 0.0 and 0.95 (never 100% certain with heuristics)

    Example:
        >>> calculate_detection_confidence("api_call", "nsxClient.createSegment()", "createSegment")
        0.9
        >>> calculate_detection_confidence("keyword", "tier1 gateway config", "tier1")
        0.35
    """
    # Base confidence by match type
    if match_type == "api_call":
        confidence = 0.9  # High confidence for explicit API calls
    elif match_type == "object_type":
        confidence = 0.6  # Medium confidence for object type names
    elif match_type == "keyword":
        confidence = 0.3  # Low confidence for generic keywords
    else:
        confidence = 0.5  # Default medium confidence

    # Context-based boosts (max +0.15 total)
    context_lower = context.lower()

    # Boost if nsxClient is present
    if "nsxclient" in context_lower:
        confidence += 0.05

    # Boost if create/update/delete verbs present
    if any(verb in context_lower for verb in ["create", "update", "delete", "configure"]):
        confidence += 0.05

    # Boost if nsx API path pattern present
    if re.search(r"nsx[/-]api[/-]v\d", context_lower):
        confidence += 0.05

    # Slight boost for multiple NSX-related terms
    nsx_terms = ["segment", "firewall", "gateway", "tier", "transport", "overlay"]
    term_count = sum(1 for term in nsx_terms if term in context_lower)
    if term_count >= 2:
        confidence += 0.03

    # Cap at 0.95 (never 100% certain with heuristics)
    return min(confidence, 0.95)


def detect_nsx_operations(
    root: ET.Element, namespace: str = "", workflow_file: Path | None = None
) -> dict[str, list[dict[str, Any]]]:
    """
    Detect NSX-T operations in vRealize workflow.

    Searches for NSX-specific keywords, API calls, and object types in:
    - Script content (JavaScript within <script> tags)
    - Workflow item names and types
    - Parameter names and descriptions

    Args:
        root: Root element of parsed vRealize workflow XML
        namespace: XML namespace prefix (e.g., "{http://vmware.com/vco/workflow}")
        workflow_file: Path to workflow file for location tracking (optional)

    Returns:
        Dictionary mapping NSX operation categories to detected instances.
        Each instance includes: name, location, confidence, evidence.

    Example result:
        {
            "segments": [
                {
                    "name": "Create Web Tier Segment",
                    "location": "workflow.xml:32",
                    "confidence": 0.95,
                    "evidence": "Found API call: nsxClient.createSegment()"
                }
            ],
            "firewall_rules": [...],
        }
    """
    # Get filename for location reporting
    filename = workflow_file.name if workflow_file else "workflow.xml"
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
                    parent: Any = script_elem
                    while parent is not None and parent.tag != "workflow-item":
                        parent = parent.getparent() if hasattr(parent, "getparent") else None

                    # Get location with line number (lxml provides sourceline)
                    location = "unknown"
                    if parent is not None:
                        line_num = parent.sourceline if hasattr(parent, "sourceline") else None
                        if line_num:
                            location = f"{filename}:{line_num}"
                        elif "name" in parent.attrib:
                            # Fallback to name if line number not available
                            location = f"{filename}:{parent.attrib['name']}"
                    elif hasattr(script_elem, "sourceline") and script_elem.sourceline:
                        # Use script element's line if no parent
                        location = f"{filename}:{script_elem.sourceline}"

                    # Determine match type for confidence calculation
                    if "nsxClient" in pattern:
                        match_type = "api_call"
                    elif pattern[0].isupper():  # CamelCase object types
                        match_type = "object_type"
                    else:
                        match_type = "keyword"

                    # Calculate confidence based on match type and context
                    confidence = calculate_detection_confidence(match_type, context, pattern)

                    nsx_ops[category].append(
                        {
                            "name": pattern,
                            "location": location,
                            "confidence": confidence,
                            "evidence": (
                                f"Pattern match: {match.group()} in context ({location}): "
                                f"...{context}..."
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
                    # Use item name/type as context for confidence calculation
                    context = f"{item_name} {item_type}".strip()

                    # Name-based matches are typically keywords or object types
                    if "nsxClient" in pattern:
                        match_type = "api_call"
                    elif pattern[0].isupper():
                        match_type = "object_type"
                    else:
                        match_type = "keyword"

                    # Calculate confidence (will be lower due to less context)
                    confidence = calculate_detection_confidence(match_type, context, pattern)

                    # Get location with line number from lxml
                    line_num = item.sourceline if hasattr(item, "sourceline") else None
                    if line_num:
                        location = f"{filename}:{line_num}"
                    else:
                        # Fallback to item name if line number not available
                        location = f"{filename}:{item_name or 'unknown'}"

                    nsx_ops[category].append(
                        {
                            "name": item_name or item_type,
                            "location": location,
                            "confidence": confidence,
                            "evidence": (
                                f"Workflow item name/type contains NSX keyword ({location}): "
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

                # Skip standard vCenter objects and common vRO built-ins
                standard_objects = [
                    "vmFolder",
                    "resourcePool",
                    "datacenter",
                    "cluster",
                    "host",
                    "datastore",
                    "network",
                    "vm",
                    "spec",
                    "config",
                    "Server",
                    "Properties",
                    "JSON",
                    "console",
                ]
                if plugin_name in standard_objects:
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
    Detect external REST API calls with structured endpoint and method extraction.

    Identifies REST operations that interact with external systems and extracts:
    - HTTP method (GET, POST, PUT, DELETE, PATCH)
    - Endpoint URL (if present)
    - Call type (restClient, fetch, XMLHttpRequest, vRO REST objects)

    Args:
        root: Root element of parsed vRealize workflow XML
        namespace: XML namespace prefix

    Returns:
        List of detected REST calls with metadata including:
        - endpoint: URL if detected, otherwise "unknown"
        - method: HTTP method if detected, otherwise "UNKNOWN"
        - call_type: Type of REST call (restClient, fetch, etc.)
        - confidence: Confidence score (0.0-0.95)
        - evidence: Supporting code snippet

    Example result:
        [
            {
                "endpoint": "https://api.example.com/v1/resources",
                "method": "POST",
                "call_type": "restClient",
                "location": "workflow-item[@name='callAPI']",
                "confidence": 0.9,
                "evidence": "REST call: restClient.post('https://...')"
            }
        ]
    """
    rest_calls = []
    script_tag = f"{namespace}script" if namespace else "script"

    for script_elem in root.iter(script_tag):
        script_text = script_elem.text or ""

        # Pattern 1: restClient.METHOD(url, ...) - highest confidence
        rest_client_pattern = r'restClient\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)'
        for match in re.finditer(rest_client_pattern, script_text, re.IGNORECASE):
            method, endpoint = match.groups()
            start = max(0, match.start() - 30)
            end = min(len(script_text), match.end() + 30)
            context = script_text[start:end].strip()

            rest_calls.append(
                {
                    "endpoint": endpoint,
                    "method": method.upper(),
                    "call_type": "restClient",
                    "location": "script-block",
                    "confidence": 0.9,  # High confidence - explicit REST client call
                    "evidence": f"restClient call: ...{context}...",
                }
            )

        # Pattern 2: fetch(url, options) - medium-high confidence
        fetch_pattern = (
            r'fetch\s*\(\s*["\']([^"\']+)["\'](?:,\s*\{[^}]*method\s*:\s*["\'](\w+)["\'])?'
        )
        for match in re.finditer(fetch_pattern, script_text, re.IGNORECASE):
            endpoint = match.group(1)
            method = match.group(2).upper() if match.group(2) else "GET"  # Default to GET
            start = max(0, match.start() - 30)
            end = min(len(script_text), match.end() + 30)
            context = script_text[start:end].strip()

            rest_calls.append(
                {
                    "endpoint": endpoint,
                    "method": method,
                    "call_type": "fetch",
                    "location": "script-block",
                    "confidence": 0.85,  # High confidence for fetch calls
                    "evidence": f"fetch call: ...{context}...",
                }
            )

        # Pattern 3: XMLHttpRequest - medium confidence
        xhr_pattern = r'XMLHttpRequest.*?\.open\s*\(\s*["\'](\w+)["\']\s*,\s*["\']([^"\']+)'
        for match in re.finditer(xhr_pattern, script_text, re.IGNORECASE | re.DOTALL):
            method, endpoint = match.groups()
            start = max(0, match.start() - 20)
            end = min(len(script_text), match.end() + 20)
            context = script_text[start:end].strip()

            rest_calls.append(
                {
                    "endpoint": endpoint,
                    "method": method.upper(),
                    "call_type": "XMLHttpRequest",
                    "location": "script-block",
                    "confidence": 0.8,  # Medium-high confidence
                    "evidence": f"XHR call: ...{context}...",
                }
            )

        # Pattern 4: vRO REST objects (RESTHost/RESTOperation) - low-medium confidence
        vro_rest_pattern = r"(RESTHost|RESTOperation)"
        for match in re.finditer(vro_rest_pattern, script_text, re.IGNORECASE):
            start = max(0, match.start() - 40)
            end = min(len(script_text), match.end() + 40)
            context = script_text[start:end].strip()

            # Try to extract URL from context if present
            url_match = re.search(r'https?://[^\s"\']+', context)
            endpoint = url_match.group(0) if url_match else "unknown"

            rest_calls.append(
                {
                    "endpoint": endpoint,
                    "method": "UNKNOWN",
                    "call_type": "vRO_REST",
                    "location": "script-block",
                    "confidence": 0.6,  # Lower confidence - less specific
                    "evidence": f"vRO REST object: ...{context}...",
                }
            )

        # Pattern 5: Standalone URLs (lowest confidence - might not be REST calls)
        # Only include if not already matched by other patterns
        url_pattern = r'https?://[^\s"\'<>]+'
        for match in re.finditer(url_pattern, script_text):
            url = match.group(0)

            # Skip if this URL was already captured by a higher-confidence pattern
            if any(call["endpoint"] == url for call in rest_calls):
                continue

            start = max(0, match.start() - 40)
            end = min(len(script_text), match.end() + 40)
            context = script_text[start:end].strip()

            rest_calls.append(
                {
                    "endpoint": url,
                    "method": "UNKNOWN",
                    "call_type": "url_reference",
                    "location": "script-block",
                    "confidence": 0.4,  # Low confidence - might just be a string
                    "evidence": f"URL reference: ...{context}...",
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
                    endpoint_display = (
                        call["endpoint"]
                        if call["endpoint"] != "unknown"
                        else "(endpoint not extracted)"
                    )
                    f.write(f"- **{call['method']}** {endpoint_display}\n")
                    f.write(f"  - Call type: {call.get('call_type', 'unknown')}\n")
                    f.write(f"  - Confidence: {call['confidence']:.0%}\n")
                    f.write(f"  - Evidence: {call['evidence']}\n\n")
        else:
            f.write("## No External Dependencies\n\n")
            f.write("This workflow appears to use only standard vRealize operations ")
            f.write("and should be fully translatable to OpenShift-native equivalents.\n\n")
