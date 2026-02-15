"""
Analyze PowerCLI scripts for external dependencies.

This module detects external dependencies in PowerCLI scripts that may
not be fully translatable to OpenShift-native equivalents, including:
- NSX cmdlets (security groups, firewall rules, load balancers, etc.)
- VMware vCenter cmdlets
- REST API calls
- External system integrations

Analysis is performed offline without LLM assistance using pattern matching.
"""

import re
from pathlib import Path
from typing import Any


def calculate_signal_counts(
    vmware_ops: dict[str, list], nsx_ops: dict[str, list], rest_calls: list
) -> dict[str, int]:
    """
    Calculate count of detection signals for summary.

    Args:
        vmware_ops: VMware cmdlet detections dict with categories as keys
        nsx_ops: NSX operation detections dict with categories as keys
        rest_calls: List of REST API call detections

    Returns:
        Dictionary with signal counts:
        - vmware_cmdlets: Total VMware cmdlet detections
        - nsx_cmdlets: Total NSX cmdlet detections
        - rest_calls: Number of REST API calls detected
    """
    return {
        "vmware_cmdlets": sum(len(ops) for ops in vmware_ops.values()),
        "nsx_cmdlets": sum(len(ops) for ops in nsx_ops.values()),
        "rest_calls": len(rest_calls),
    }


def calculate_overall_confidence(
    vmware_ops: dict[str, list], nsx_ops: dict[str, list], rest_calls: list
) -> str:
    """
    Calculate overall confidence rating based on average confidence scores.

    Aggregates confidence scores from all detections and returns a categorical
    rating: low, medium, or high.

    Confidence thresholds:
    - high: average >= 0.75
    - medium: average >= 0.50
    - low: average < 0.50

    Args:
        vmware_ops: VMware cmdlet detections with confidence scores
        nsx_ops: NSX cmdlet detections with confidence scores
        rest_calls: REST API call detections with confidence scores

    Returns:
        Confidence rating string: "low", "medium", or "high"
    """
    confidences = []

    # Collect VMware cmdlet confidences
    for category, ops in vmware_ops.items():
        for op in ops:
            confidences.append(op.get("confidence", 0.5))

    # Collect NSX operation confidences
    for category, ops in nsx_ops.items():
        for op in ops:
            confidences.append(op.get("confidence", 0.5))

    # Collect REST call confidences
    for call in rest_calls:
        confidences.append(call.get("confidence", 0.5))

    # Calculate average confidence
    if not confidences:
        return "low"

    avg_confidence = sum(confidences) / len(confidences)

    if avg_confidence >= 0.75:
        return "high"
    elif avg_confidence >= 0.50:
        return "medium"
    else:
        return "low"


def build_evidence_array(
    vmware_ops: dict[str, list], nsx_ops: dict[str, list], rest_calls: list
) -> list[dict[str, Any]]:
    """
    Build unified evidence array from all detection categories.

    Args:
        vmware_ops: VMware cmdlet detections
        nsx_ops: NSX cmdlet detections
        rest_calls: REST API call detections

    Returns:
        List of evidence dicts with standardized format
    """
    evidence = []

    # VMware cmdlet evidence
    for category, ops in vmware_ops.items():
        for op in ops:
            evidence.append(
                {
                    "type": "vmware_cmdlet",
                    "category": category,
                    "cmdlet": op.get("cmdlet", "unknown"),
                    "location": op.get("location", "unknown"),
                    "line": op.get("line", 0),
                    "confidence": op.get("confidence", 0.5),
                    "snippet": op.get("evidence", ""),
                }
            )

    # NSX cmdlet evidence
    for category, ops in nsx_ops.items():
        for op in ops:
            evidence.append(
                {
                    "type": "nsx_cmdlet",
                    "category": category,
                    "cmdlet": op.get("cmdlet", "unknown"),
                    "location": op.get("location", "unknown"),
                    "line": op.get("line", 0),
                    "confidence": op.get("confidence", 0.5),
                    "snippet": op.get("evidence", ""),
                }
            )

    # REST call evidence
    for call in rest_calls:
        evidence.append(
            {
                "type": "rest_call",
                "endpoint": call.get("endpoint", "unknown"),
                "method": call.get("method", "UNKNOWN"),
                "location": call.get("location", "unknown"),
                "line": call.get("line", 0),
                "confidence": call.get("confidence", 0.5),
                "snippet": call.get("evidence", ""),
            }
        )

    return evidence


def detect_vmware_cmdlets(script_content: str, script_file: Path) -> dict[str, list]:
    """
    Detect VMware PowerCLI cmdlets in script content.

    Detects common VMware vCenter cmdlets including:
    - VM operations (New-VM, Set-VM, Get-VM, Remove-VM, Start-VM, Stop-VM)
    - Resource operations (Get-VMHost, Get-Datastore, Get-Cluster, Get-ResourcePool)
    - Network operations (Get-VirtualPortGroup, Get-VDSwitch)
    - Storage operations (Get-Datastore, New-Datastore)

    Args:
        script_content: PowerShell script content to analyze
        script_file: Path to script file for location tracking

    Returns:
        Dictionary with VMware cmdlet detections organized by category
    """
    vmware_ops = {
        "vm_lifecycle": [],
        "compute": [],
        "networking": [],
        "storage": [],
        "tagging": [],
    }

    # Split into lines for line number tracking
    lines = script_content.split("\n")

    # VM Lifecycle cmdlets
    vm_lifecycle_patterns = [
        r"\bNew-VM\b",
        r"\bSet-VM\b",
        r"\bGet-VM\b",
        r"\bRemove-VM\b",
        r"\bStart-VM\b",
        r"\bStop-VM\b",
        r"\bRestart-VM\b",
        r"\bSuspend-VM\b",
    ]

    # Compute cmdlets
    compute_patterns = [
        r"\bGet-VMHost\b",
        r"\bGet-Cluster\b",
        r"\bGet-ResourcePool\b",
        r"\bSet-VMHost\b",
        r"\bSet-Cluster\b",
    ]

    # Networking cmdlets
    networking_patterns = [
        r"\bGet-VirtualPortGroup\b",
        r"\bNew-VirtualPortGroup\b",
        r"\bGet-VDSwitch\b",
        r"\bGet-NetworkAdapter\b",
        r"\bNew-NetworkAdapter\b",
    ]

    # Storage cmdlets
    storage_patterns = [
        r"\bGet-Datastore\b",
        r"\bNew-Datastore\b",
        r"\bGet-HardDisk\b",
        r"\bNew-HardDisk\b",
    ]

    # Tagging cmdlets
    tagging_patterns = [
        r"\bNew-TagAssignment\b",
        r"\bGet-Tag\b",
        r"\bNew-Tag\b",
        r"\bSet-Annotation\b",
    ]

    # Detect patterns
    for line_num, line in enumerate(lines, 1):
        # VM Lifecycle
        for pattern in vm_lifecycle_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                vmware_ops["vm_lifecycle"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,  # High confidence - exact cmdlet match
                        "evidence": context,
                    }
                )

        # Compute
        for pattern in compute_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                vmware_ops["compute"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Networking
        for pattern in networking_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                vmware_ops["networking"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Storage
        for pattern in storage_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                vmware_ops["storage"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Tagging
        for pattern in tagging_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                vmware_ops["tagging"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

    return vmware_ops


def detect_nsx_cmdlets(script_content: str, script_file: Path) -> dict[str, list]:
    """
    Detect NSX-T cmdlets in PowerCLI scripts.

    Detects NSX-T cmdlets including:
    - Security groups (Get-NsxSecurityGroup, New-NsxSecurityGroup)
    - Firewall rules (Get-NsxFirewallRule, New-NsxFirewallRule)
    - Load balancers (Get-NsxLoadBalancer, New-NsxLoadBalancer)
    - Segments (Get-NsxSegment, New-NsxSegment)

    Args:
        script_content: PowerShell script content to analyze
        script_file: Path to script file for location tracking

    Returns:
        Dictionary with NSX cmdlet detections organized by category
    """
    nsx_ops = {
        "security_groups": [],
        "firewall_rules": [],
        "load_balancers": [],
        "segments": [],
        "tier_gateways": [],
        "other": [],
    }

    lines = script_content.split("\n")

    # NSX Security Groups
    security_group_patterns = [
        r"\bGet-NsxSecurityGroup\b",
        r"\bNew-NsxSecurityGroup\b",
        r"\bSet-NsxSecurityGroup\b",
        r"\bRemove-NsxSecurityGroup\b",
    ]

    # NSX Firewall Rules
    firewall_patterns = [
        r"\bGet-NsxFirewallRule\b",
        r"\bNew-NsxFirewallRule\b",
        r"\bSet-NsxFirewallRule\b",
        r"\bRemove-NsxFirewallRule\b",
    ]

    # NSX Load Balancers
    lb_patterns = [
        r"\bGet-NsxLoadBalancer\b",
        r"\bNew-NsxLoadBalancer\b",
        r"\bSet-NsxLoadBalancer\b",
        r"\bNew-NsxLoadBalancerPool\b",
        r"\bNew-NsxLoadBalancerVirtualServer\b",
    ]

    # NSX Segments
    segment_patterns = [
        r"\bGet-NsxSegment\b",
        r"\bNew-NsxSegment\b",
        r"\bSet-NsxSegment\b",
    ]

    # NSX Tier Gateways
    gateway_patterns = [
        r"\bGet-NsxTier0Gateway\b",
        r"\bGet-NsxTier1Gateway\b",
        r"\bNew-NsxTier1Gateway\b",
    ]

    # Generic NSX pattern (catch-all for other NSX cmdlets)
    generic_nsx_pattern = r"\b(Get|New|Set|Remove)-Nsx\w+\b"

    for line_num, line in enumerate(lines, 1):
        # Security Groups
        for pattern in security_group_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                nsx_ops["security_groups"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Firewall Rules
        for pattern in firewall_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                nsx_ops["firewall_rules"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Load Balancers
        for pattern in lb_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                nsx_ops["load_balancers"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Segments
        for pattern in segment_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                nsx_ops["segments"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Tier Gateways
        for pattern in gateway_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                cmdlet = match.group(0)
                context = line.strip()
                nsx_ops["tier_gateways"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.95,
                        "evidence": context,
                    }
                )

        # Generic NSX cmdlets (not already caught)
        match = re.search(generic_nsx_pattern, line, re.IGNORECASE)
        if match:
            cmdlet = match.group(0)
            # Check if we already caught this specific cmdlet
            already_detected = False
            for category in nsx_ops.values():
                if any(op["line"] == line_num for op in category):
                    already_detected = True
                    break

            if not already_detected:
                context = line.strip()
                nsx_ops["other"].append(
                    {
                        "cmdlet": cmdlet,
                        "location": str(script_file.name),
                        "line": line_num,
                        "confidence": 0.85,  # Slightly lower for generic catch-all
                        "evidence": context,
                    }
                )

    return nsx_ops


def _is_nsx_api_call(endpoint: str) -> tuple[bool, str | None]:
    """
    Check if endpoint is an NSX API call.

    Args:
        endpoint: URL or endpoint string

    Returns:
        Tuple of (is_nsx_api, nsx_version):
        - is_nsx_api: True if endpoint contains NSX API patterns
        - nsx_version: "NSX-V" for /api/2.0/, "NSX-T" for /policy/api/, None otherwise
    """
    if "/api/2.0/" in endpoint or "/api/v2.0/" in endpoint:
        return (True, "NSX-V")
    elif "/policy/api/" in endpoint or "/api/v1/policy" in endpoint:
        return (True, "NSX-T")
    return (False, None)


def detect_rest_calls(script_content: str, script_file: Path) -> list[dict[str, Any]]:
    """
    Detect external REST API calls in PowerCLI scripts.

    Detects:
    - Invoke-RestMethod
    - Invoke-WebRequest
    - curl
    - wget

    Also flags NSX API calls specifically:
    - NSX-V: /api/2.0/ or /api/v2.0/
    - NSX-T: /policy/api/ or /api/v1/policy

    Args:
        script_content: PowerShell script content to analyze
        script_file: Path to script file for location tracking

    Returns:
        List of detected REST calls with metadata including:
        - endpoint: URL if detected, otherwise "unknown"
        - method: HTTP method if detected, otherwise "UNKNOWN"
        - call_type: Type of REST call
        - nsx_api: True if NSX API call detected
        - nsx_version: "NSX-V" or "NSX-T" if NSX API, None otherwise
        - line: Line number
        - confidence: Confidence score (0.0-0.95)
        - evidence: Supporting code snippet
    """
    rest_calls = []
    lines = script_content.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Pattern 1: Invoke-RestMethod
        invoke_rest_pattern = r'Invoke-RestMethod\s+.*?(?:-Uri\s+)?["\']([^"\']+)["\']'
        match = re.search(invoke_rest_pattern, line, re.IGNORECASE)
        if match:
            endpoint = match.group(1)
            # Try to extract method
            method_match = re.search(r'-Method\s+["\']?(\w+)["\']?', line, re.IGNORECASE)
            method = method_match.group(1).upper() if method_match else "GET"

            # Check if this is an NSX API call
            is_nsx, nsx_version = _is_nsx_api_call(endpoint)
            confidence = 0.95 if is_nsx else 0.9  # Higher confidence for NSX API calls

            rest_calls.append(
                {
                    "endpoint": endpoint,
                    "method": method,
                    "call_type": "Invoke-RestMethod",
                    "nsx_api": is_nsx,
                    "nsx_version": nsx_version,
                    "location": str(script_file.name),
                    "line": line_num,
                    "confidence": confidence,
                    "evidence": line.strip(),
                }
            )

        # Pattern 2: Invoke-WebRequest
        invoke_web_pattern = r'Invoke-WebRequest\s+.*?(?:-Uri\s+)?["\']([^"\']+)["\']'
        match = re.search(invoke_web_pattern, line, re.IGNORECASE)
        if match:
            endpoint = match.group(1)
            method_match = re.search(r'-Method\s+["\']?(\w+)["\']?', line, re.IGNORECASE)
            method = method_match.group(1).upper() if method_match else "GET"

            # Check if this is an NSX API call
            is_nsx, nsx_version = _is_nsx_api_call(endpoint)
            confidence = 0.95 if is_nsx else 0.9  # Higher confidence for NSX API calls

            rest_calls.append(
                {
                    "endpoint": endpoint,
                    "method": method,
                    "call_type": "Invoke-WebRequest",
                    "nsx_api": is_nsx,
                    "nsx_version": nsx_version,
                    "location": str(script_file.name),
                    "line": line_num,
                    "confidence": confidence,
                    "evidence": line.strip(),
                }
            )

        # Pattern 3: curl
        curl_pattern = r'\bcurl\s+.*?["\']?(https?://[^\s"\']+)["\']?'
        match = re.search(curl_pattern, line, re.IGNORECASE)
        if match:
            endpoint = match.group(1)
            # Try to detect method flag
            method = "GET"
            if re.search(r"-X\s+POST", line, re.IGNORECASE):
                method = "POST"
            elif re.search(r"-X\s+PUT", line, re.IGNORECASE):
                method = "PUT"
            elif re.search(r"-X\s+DELETE", line, re.IGNORECASE):
                method = "DELETE"

            # Check if this is an NSX API call
            is_nsx, nsx_version = _is_nsx_api_call(endpoint)
            confidence = 0.9 if is_nsx else 0.85  # Higher confidence for NSX API calls

            rest_calls.append(
                {
                    "endpoint": endpoint,
                    "method": method,
                    "call_type": "curl",
                    "nsx_api": is_nsx,
                    "nsx_version": nsx_version,
                    "location": str(script_file.name),
                    "line": line_num,
                    "confidence": confidence,
                    "evidence": line.strip(),
                }
            )

    return rest_calls


def detect_risk_signals(script_content: str, script_file: Path) -> list[dict[str, Any]]:
    """
    Detect security and complexity risk signals in PowerCLI scripts.

    Detects:
    - Module imports (Import-Module)
    - Type loading (Add-Type)
    - Process execution (Start-Process)
    - SSH commands
    - Inline credentials (-Password, -Credential, hardcoded passwords)
    - Hardcoded endpoints (IP addresses, URLs)

    Args:
        script_content: PowerShell script content to analyze
        script_file: Path to script file for location tracking

    Returns:
        List of detected risk signals with metadata
    """
    risk_signals = []
    lines = script_content.split("\n")

    # Module imports
    module_pattern = r"\bImport-Module\s+([^\s;]+)"

    # Type loading
    type_pattern = r"\bAdd-Type\b"

    # Process execution
    process_pattern = r"\bStart-Process\b"

    # SSH commands
    ssh_pattern = r"\bssh\s+"

    # Credential patterns (case-insensitive)
    credential_patterns = [
        r'-Password\s+["\']([^"\']+)["\']',  # -Password "value"
        r"-Credential\s+",  # -Credential parameter
        r"ConvertTo-SecureString\s+",  # Secure string creation
        r'password\s*=\s*["\']([^"\']+)["\']',  # password = "value"
    ]

    # Hardcoded endpoint patterns
    endpoint_patterns = [
        r"\b(?:https?://)?(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?",  # IP addresses with optional port
        r'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s"\']*)?',  # URLs with protocol
        r"\b[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}\b",  # Bare domain names (e.g., vcenter.example.com)
    ]

    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith("#"):
            continue

        # Module imports
        match = re.search(module_pattern, line, re.IGNORECASE)
        if match:
            module_name = match.group(1)
            risk_signals.append(
                {
                    "type": "module_import",
                    "module": module_name,
                    "location": str(script_file.name),
                    "line": line_num,
                    "severity": "medium",
                    "confidence": 0.95,
                    "evidence": line.strip(),
                    "recommendation": f"Review module dependency: {module_name}",
                }
            )

        # Type loading
        if re.search(type_pattern, line, re.IGNORECASE):
            risk_signals.append(
                {
                    "type": "type_loading",
                    "location": str(script_file.name),
                    "line": line_num,
                    "severity": "high",
                    "confidence": 0.9,
                    "evidence": line.strip(),
                    "recommendation": "Add-Type may load external assemblies - review for security",
                }
            )

        # Process execution
        if re.search(process_pattern, line, re.IGNORECASE):
            risk_signals.append(
                {
                    "type": "process_execution",
                    "location": str(script_file.name),
                    "line": line_num,
                    "severity": "high",
                    "confidence": 0.9,
                    "evidence": line.strip(),
                    "recommendation": "Start-Process executes external commands - review for security",
                }
            )

        # SSH commands
        if re.search(ssh_pattern, line, re.IGNORECASE):
            risk_signals.append(
                {
                    "type": "ssh_command",
                    "location": str(script_file.name),
                    "line": line_num,
                    "severity": "medium",
                    "confidence": 0.85,
                    "evidence": line.strip(),
                    "recommendation": "SSH commands require external connectivity - manual review needed",
                }
            )

        # Credential patterns
        for pattern in credential_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # Redact actual credential values
                redacted_line = re.sub(r'(["\'][^"\']*["\'])', '"***REDACTED***"', line.strip())
                risk_signals.append(
                    {
                        "type": "inline_credential",
                        "location": str(script_file.name),
                        "line": line_num,
                        "severity": "high",
                        "confidence": 0.8,
                        "evidence": redacted_line,
                        "recommendation": "Inline credentials detected - use Azure Key Vault or secrets management",
                    }
                )
                break  # Only report once per line

        # Hardcoded endpoints
        for pattern in endpoint_patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                endpoint = match.group(0)
                risk_signals.append(
                    {
                        "type": "hardcoded_endpoint",
                        "endpoint": endpoint,
                        "location": str(script_file.name),
                        "line": line_num,
                        "severity": "low",
                        "confidence": 0.7,
                        "evidence": line.strip(),
                        "recommendation": f"Hardcoded endpoint '{endpoint}' - consider using configuration/environment variables",
                    }
                )

    return risk_signals


def calculate_complexity(
    vmware_ops: dict[str, list], nsx_ops: dict[str, list], rest_calls: list, risk_signals: list
) -> int:
    """
    Calculate migration complexity score (0-100).

    Weights:
    - VMware cmdlets: 1 point each (basic translation available)
    - NSX cmdlets: 5 points each (architectural complexity)
    - REST calls: 3 points each (custom integration)
    - Risk signals: 2 points each (security/complexity concerns)

    Args:
        vmware_ops: VMware cmdlet detections
        nsx_ops: NSX cmdlet detections
        rest_calls: REST API call detections
        risk_signals: Security/complexity risk signals

    Returns:
        Complexity score (0-100)
    """
    vmware_count = sum(len(ops) for ops in vmware_ops.values())
    nsx_count = sum(len(ops) for ops in nsx_ops.values())
    rest_count = len(rest_calls)
    risk_count = len(risk_signals)

    # Weighted scoring
    score = (vmware_count * 1) + (nsx_count * 5) + (rest_count * 3) + (risk_count * 2)

    # Cap at 100
    return min(score, 100)


def analyze_powercli_script(script_file: Path) -> dict[str, Any]:
    """
    Analyze a PowerCLI script for external dependencies and risk signals.

    Args:
        script_file: Path to PowerCLI (.ps1) script file

    Returns:
        Dictionary containing analysis results with keys:
        - source_file: Path to the analyzed script file
        - signals: Signal counts dict with vmware_cmdlets, nsx_cmdlets, rest_calls, risk_signals
        - confidence: Overall confidence rating ("low", "medium", or "high")
        - evidence: Array of evidence dicts with cmdlet, line, snippet, confidence, type
        - vmware_operations: VMware cmdlets detected (detailed dict by category)
        - nsx_operations: NSX cmdlets detected (detailed dict by category)
        - rest_api_calls: External REST API calls (detailed list)
        - risk_signals: Security/complexity risk signals (detailed list)
        - complexity_score: Overall complexity rating (0-100)
        - has_external_dependencies: Boolean flag for any external dependencies or risks

    Raises:
        FileNotFoundError: If script file doesn't exist
        ValueError: If script file cannot be read

    Example:
        >>> result = analyze_powercli_script(Path("provision.ps1"))
        >>> if result["nsx_operations"]:
        ...     print(f"Found NSX operations: {result['nsx_operations'].keys()}")
        >>> if result["risk_signals"]:
        ...     print(f"Found {len(result['risk_signals'])} risk signals")
    """
    if not script_file.exists():
        raise FileNotFoundError(f"Script file not found: {script_file}")

    try:
        with open(script_file, "r", encoding="utf-8") as f:
            script_content = f.read()
    except Exception as e:
        raise ValueError(f"Could not read script file {script_file}: {e}")

    # Detect various external dependencies
    vmware_ops = detect_vmware_cmdlets(script_content, script_file)
    nsx_ops = detect_nsx_cmdlets(script_content, script_file)
    rest_calls = detect_rest_calls(script_content, script_file)
    risk_signals = detect_risk_signals(script_content, script_file)

    # Calculate complexity score
    complexity = calculate_complexity(vmware_ops, nsx_ops, rest_calls, risk_signals)

    # Build structured signal output
    signals = calculate_signal_counts(vmware_ops, nsx_ops, rest_calls)
    signals["risk_signals"] = len(risk_signals)

    confidence = calculate_overall_confidence(vmware_ops, nsx_ops, rest_calls)
    evidence = build_evidence_array(vmware_ops, nsx_ops, rest_calls)

    # Check if there are any actual detections (not just empty category dicts)
    has_vmware = any(len(ops) > 0 for ops in vmware_ops.values())
    has_nsx = any(len(ops) > 0 for ops in nsx_ops.values())
    has_rest = len(rest_calls) > 0
    has_risk = len(risk_signals) > 0

    result = {
        "source_file": str(script_file),
        "signals": signals,
        "confidence": confidence,
        "evidence": evidence,
        "vmware_operations": vmware_ops,
        "nsx_operations": nsx_ops,
        "rest_api_calls": rest_calls,
        "risk_signals": risk_signals,
        "complexity_score": complexity,
        "has_external_dependencies": has_vmware or has_nsx or has_rest or has_risk,
    }

    return result
