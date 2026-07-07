"""
Unified artifact generation using LLM or templates.
"""

import json
import logging
import re
from pathlib import Path

from rich.console import Console

from ops_translate.llm import get_provider
from ops_translate.util.files import ensure_dir, write_text
from ops_translate.workspace import Workspace

console = Console()
logger = logging.getLogger(__name__)

# Get project root to find prompts
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _generate_role_stubs_from_gaps(workspace: Workspace):
    """
    Generate role stubs for MANUAL/BLOCKED components from gap analysis.

    This is called after AI generation to add role stubs that AI can't create.
    """
    from ops_translate.generate.ansible import _create_manual_role_stub
    from ops_translate.report.loaders import ReportDataLoader, ReportFileLocator

    output_dir = workspace.root / "output/ansible"

    # Load gap analysis and recommendations data
    locator = ReportFileLocator(workspace)
    loader = ReportDataLoader()

    gaps_data = None
    if gaps_file := locator.gaps_file():
        gaps_data = loader.load_json(gaps_file)

    recommendations_data = None
    if recs_file := locator.recommendations_file():
        recommendations_data = loader.load_json(recs_file)

    if not gaps_data:
        return

    # Generate role stubs for MANUAL/BLOCKED components
    for component in gaps_data.get("components", []):
        if component.get("level") in ["BLOCKED", "MANUAL"]:
            _create_manual_role_stub(output_dir, component, workspace, recommendations_data)
            comp_name = component.get("name", "unknown")
            console.print(f"[dim]  Generated role stub for: {comp_name}[/dim]")


def _generate_network_policies(workspace: Workspace, segment_mapping=None):
    """
    Generate Kubernetes NetworkPolicy manifests from detected NSX firewall rules.

    Reads analysis.vrealize.json to find NSX firewall rules and generates
    corresponding NetworkPolicy YAML files with limitation warnings.

    Args:
        workspace: Workspace containing analysis data
        segment_mapping: Optional SegmentRuleMapping to filter segment-specific rules.
                        If provided, only rules for the primary network are generated.
    """
    import json

    from ops_translate.generate.networkpolicy import generate_network_policies

    # Find analysis file (check intent/ directory first, then runs/)
    analysis_file = workspace.root / "intent" / "analysis.vrealize.json"
    if not analysis_file.exists():
        # Fallback to runs directory for backwards compatibility
        runs_dir = workspace.root / "runs"
        if runs_dir.exists():
            run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            for run_dir in run_dirs:
                potential_file = run_dir / "analysis.vrealize.json"
                if potential_file.exists():
                    analysis_file = potential_file
                    break

    if analysis_file.exists():
        # Load analysis data
        with open(analysis_file) as f:
            analysis = json.load(f)

        # Extract NSX firewall rules
        nsx_ops = analysis.get("nsx_operations", {})
        firewall_rules = nsx_ops.get("firewall_rules", [])
        distributed_firewall = nsx_ops.get("distributed_firewall", [])

        # Combine both types of firewall rules
        all_firewall_rules = firewall_rules + distributed_firewall

        if not all_firewall_rules:
            # No firewall rules detected
            return

        # Filter to primary network rules only if segment mapping provided
        if segment_mapping and segment_mapping.primary_network_rules:
            # Only generate policies for rules assigned to primary network
            primary_rule_names = set(segment_mapping.primary_network_rules)
            all_firewall_rules = [
                r for r in all_firewall_rules if r.get("name") in primary_rule_names
            ]

            if not all_firewall_rules:
                # No primary network rules to generate
                console.print(
                    "[dim]All firewall rules assigned to secondary networks "
                    "(MultiNetworkPolicy)[/dim]"
                )
                return

            console.print(
                f"[dim]Generating NetworkPolicy for {len(all_firewall_rules)} "
                f"primary network rule(s)[/dim]"
            )

        # Get workflow name from source file
        source_file = analysis.get("source_file", "workflow")
        workflow_name = Path(source_file).stem

        # Generate NetworkPolicy manifests
        policies = generate_network_policies(all_firewall_rules, workflow_name)

        if not policies:
            # No policies could be generated
            return

        # Write NetworkPolicy files
        output_dir = workspace.root / "output/network-policies"
        output_dir.mkdir(parents=True, exist_ok=True)

        for filename, content in policies.items():
            policy_file = output_dir / filename
            policy_file.write_text(content)

        # Generate README
        readme_content = _generate_networkpolicy_readme()
        (output_dir / "README.md").write_text(readme_content)

        # Print success message
        console.print(
            f"[green]✓ Generated {len(policies)} NetworkPolicy manifest(s): "
            f"output/network-policies/[/green]"
        )
        console.print(
            "[yellow]⚠ Review limitations in YAML comments before deployment[/yellow]"
        )

        return  # Found analysis and generated policies


def _generate_networkpolicy_readme() -> str:
    """Generate README for NetworkPolicy output directory."""
    return """# NetworkPolicy Manifests

This directory contains Kubernetes NetworkPolicy manifests generated from NSX-T
Distributed Firewall rules detected in vRealize workflows.

## Important Limitations

**NetworkPolicy is not a complete replacement for NSX-T Distributed Firewall.**

### Supported Features
- ✅ Layer 3/4 traffic filtering (IP, port, protocol)
- ✅ Pod-to-pod communication control
- ✅ Ingress and egress rules
- ✅ CIDR-based source/destination selectors

### Unsupported Features (NSX-only)
- ❌ Layer 7 application-aware filtering
- ❌ FQDN-based rules
- ❌ Time-based rules
- ❌ User/group-based authentication
- ❌ Connection tracking and stateful inspection
- ❌ IDS/IPS integration

## Before Deployment

1. **Read YAML comments** - Each generated manifest includes specific limitations
2. **Test in dev/lab** - Validate policies don't break existing traffic
3. **Consider alternatives** for advanced features:
   - **Calico NetworkPolicy** - FQDN, global policies, deny rules
   - **Cilium** - L7 policies, observability, eBPF-based filtering
   - **Istio** - Application-layer (L7) service mesh policies

## Deployment

```bash
# Review policies
cat *.yaml

# Apply to cluster
kubectl apply -f output/network-policies/

# Verify
kubectl get networkpolicies -n default
```

## Migration Strategy

For complex NSX environments, consider a hybrid approach:
- Use NetworkPolicy for basic L3/L4 filtering
- Keep NSX for advanced features (L7, FQDN, IDS/IPS)
- Gradually migrate as CNI capabilities mature

## Additional Resources

- [Kubernetes NetworkPolicy Docs](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Calico NetworkPolicy](https://docs.tigera.io/calico/latest/network-policy/)
- [Cilium Network Policy](https://docs.cilium.io/en/stable/security/policy/)
"""


def _correlate_segments_and_rules(workspace: Workspace):
    """
    Correlate NSX segments with firewall rules to determine network scope.

    Uses the NSXCorrelationEngine to analyze which firewall rules apply to
    specific segments (secondary networks) vs. primary network.

    Returns:
        SegmentRuleMapping or None if correlation fails or no data
    """
    import json

    from ops_translate.generate.nsx_correlation import NSXCorrelationEngine

    # Find analysis file (check intent/ directory first, then runs/)
    analysis_file = workspace.root / "intent" / "analysis.vrealize.json"
    if not analysis_file.exists():
        # Fallback to runs directory for backwards compatibility
        runs_dir = workspace.root / "runs"
        if runs_dir.exists():
            run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            for run_dir in run_dirs:
                potential_file = run_dir / "analysis.vrealize.json"
                if potential_file.exists():
                    analysis_file = potential_file
                    break

    if analysis_file.exists():
        # Load analysis data
        with open(analysis_file) as f:
            analysis = json.load(f)

        # Extract NSX operations
        nsx_ops = analysis.get("nsx_operations", {})
        segments = nsx_ops.get("segments", [])
        firewall_rules = nsx_ops.get("firewall_rules", [])
        distributed_firewall = nsx_ops.get("distributed_firewall", [])

        # Combine both types of firewall rules
        all_firewall_rules = firewall_rules + distributed_firewall

        if not all_firewall_rules:
            # No firewall rules to correlate
            return None

        # Run correlation engine
        engine = NSXCorrelationEngine()
        mapping = engine.correlate_rules_to_segments(all_firewall_rules, segments)

        # Log correlation results
        console.print("[dim]Correlation results:[/dim]")
        console.print(
            f"[dim]  - Primary network rules: {len(mapping.primary_network_rules)}[/dim]"
        )
        console.print(
            f"[dim]  - Segments with rules: {len(mapping.segment_mappings)}[/dim]"
        )

        for seg_name, seg_mapping in mapping.segment_mappings.items():
            console.print(
                f"[dim]    • {seg_name}: {len(seg_mapping.firewall_rules)} rules "
                f"(confidence: {seg_mapping.correlation_confidence:.2f})[/dim]"
            )

        return mapping

    return None


def _generate_multi_network_policies(workspace: Workspace, segment_rule_mapping):
    """
    Generate OVN-Kubernetes MultiNetworkPolicy manifests for secondary networks.

    Args:
        workspace: Workspace containing analysis data
        segment_rule_mapping: SegmentRuleMapping from correlation engine

    Generates MultiNetworkPolicy YAML files for each segment with associated
    firewall rules, along with README and CORRELATION_REPORT.
    """
    import json

    from ops_translate.generate.multinetworkpolicy import generate_multi_network_policies

    if not segment_rule_mapping or not segment_rule_mapping.segment_mappings:
        return

    # Find analysis file (check intent/ directory first, then runs/)
    analysis_file = workspace.root / "intent" / "analysis.vrealize.json"
    if not analysis_file.exists():
        # Fallback to runs directory for backwards compatibility
        runs_dir = workspace.root / "runs"
        if runs_dir.exists():
            run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            for run_dir in run_dirs:
                potential_file = run_dir / "analysis.vrealize.json"
                if potential_file.exists():
                    analysis_file = potential_file
                    break

    if analysis_file.exists():
            # Load analysis data
            with open(analysis_file) as f:
                analysis = json.load(f)

            # Extract NSX firewall rules
            nsx_ops = analysis.get("nsx_operations", {})
            firewall_rules = nsx_ops.get("firewall_rules", [])
            distributed_firewall = nsx_ops.get("distributed_firewall", [])
            all_firewall_rules = firewall_rules + distributed_firewall

            # Get workflow name
            source_file = analysis.get("source_file", "workflow")
            workflow_name = Path(source_file).stem

            # Generate MultiNetworkPolicy for each segment
            output_dir = workspace.root / "output/multi-network-policies"
            output_dir.mkdir(parents=True, exist_ok=True)

            total_policies = 0
            for seg_name, seg_mapping in segment_rule_mapping.segment_mappings.items():
                # Convert SegmentMapping to dict for compatibility
                segment_dict = {
                    "segment_name": seg_mapping.segment_name,
                    "nad_name": seg_mapping.nad_name,
                    "firewall_rules": seg_mapping.firewall_rules,
                    "vlan_ids": seg_mapping.vlan_ids,
                    "subnets": seg_mapping.subnets,
                }

                # Generate policies for this segment
                policies = generate_multi_network_policies(
                    segment_dict, all_firewall_rules, workflow_name
                )

                # Write policy files
                for filename, content in policies.items():
                    policy_file = output_dir / filename
                    policy_file.write_text(content)
                    total_policies += 1

            # Generate README
            readme_content = _generate_multinetworkpolicy_readme()
            (output_dir / "README.md").write_text(readme_content)

            # Generate CORRELATION_REPORT
            report_content = _generate_correlation_report(segment_rule_mapping)
            (output_dir / "CORRELATION_REPORT.md").write_text(report_content)

            # Print success message
            console.print(
                f"[green]✓ Generated {total_policies} MultiNetworkPolicy manifest(s): "
                f"output/multi-network-policies/[/green]"
            )
            console.print(
                "[yellow]⚠ Review correlation report and YAML comments before deployment[/yellow]"
            )

            return  # Found analysis and generated policies


def _generate_multinetworkpolicy_readme() -> str:
    """Generate README for MultiNetworkPolicy output directory."""
    return """# MultiNetworkPolicy Manifests (OVN-Kubernetes)

This directory contains **OVN-Kubernetes MultiNetworkPolicy** manifests generated from NSX firewall rules that apply to **secondary networks** (NetworkAttachmentDefinitions).

## What is MultiNetworkPolicy?

MultiNetworkPolicy is a Kubernetes CRD provided by OVN-Kubernetes (OpenShift default CNI) that allows network policies to be scoped to specific secondary network interfaces, not just the primary pod network.

**Key Differences from Standard NetworkPolicy:**
- **API Group**: `k8s.cni.cncf.io/v1beta1` (not `networking.k8s.io/v1`)
- **Scope**: Applies to traffic on specific secondary network (via annotation)
- **Use Case**: VLANs, overlays, and other non-primary networks

## Generated Files

- **`*.yaml`**: MultiNetworkPolicy manifests (one per NSX firewall rule per segment)
- **`CORRELATION_REPORT.md`**: Explains how rules were mapped to segments
- **`README.md`**: This file

## How Correlation Works

NSX firewall rules are analyzed to determine which network segment (secondary network) they apply to:

1. **Direct Reference** (0.9 confidence) - Rule evidence contains segment name
2. **IP Range Overlap** (0.7 confidence) - Rule IPs in segment subnet
3. **VLAN Matching** (0.7 confidence) - Same VLAN ID
4. **Proximity** (0.4 confidence) - Same workflow location
5. **Default** - No correlation → goes to primary network (standard NetworkPolicy)

See `CORRELATION_REPORT.md` for details on each rule assignment.

## Prerequisites

Your cluster must have:
- **OVN-Kubernetes CNI** (OpenShift default - already installed!)
- **Multus CNI** for secondary network support
- **NetworkAttachmentDefinitions** (see `output/network-attachments/`)

## How to Use

### 1. Deploy NetworkAttachmentDefinitions First

```bash
kubectl apply -f output/network-attachments/
```

### 2. Deploy MultiNetworkPolicies

```bash
kubectl apply -f output/multi-network-policies/
```

### 3. Attach Pods to Secondary Networks

Pods must be annotated to use the secondary network:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  annotations:
    k8s.v1.cni.cncf.io/networks: web-tier-vlan100  # NAD name
spec:
  containers:
  - name: nginx
    image: nginx:latest
```

### 4. Verify Policy Application

```bash
# Check MultiNetworkPolicies
kubectl get multinetworkpolicy

# Describe specific policy
kubectl describe multinetworkpolicy web-tier-vlan100-allow-db
```

## Important Limitations

OVN-Kubernetes MultiNetworkPolicy shares the same limitations as standard NetworkPolicy:

- **L3/L4 only**: No L7 (HTTP/HTTPS) filtering. Consider Cilium for L7 support.
- **No FQDN**: Cannot filter by domain names. Consider Cilium for FQDN support.
- **No time-based rules**: Policies are always active.
- **No user/group policies**: Pod-based filtering only.

See YAML header comments for rule-specific limitations.

## Troubleshooting

**Policy not applying?**
- Ensure pod has `k8s.v1.cni.cncf.io/networks` annotation
- Verify NetworkAttachmentDefinition exists
- Check pod has secondary interface: `kubectl exec <pod> -- ip a`

**Traffic still blocked?**
- MultiNetworkPolicy is default-deny
- Ensure egress rules exist if needed
- Check for conflicting policies

## References

- [OVN-Kubernetes Documentation](https://github.com/ovn-org/ovn-kubernetes)
- [MultiNetworkPolicy Spec](https://github.com/k8snetworkplumbingwg/multi-networkpolicy)
- [OpenShift Virtualization Multi-Network](https://docs.openshift.com/container-platform/latest/virt/vm_networking/virt-connecting-vm-to-linux-bridge.html)
"""


def _generate_correlation_report(segment_rule_mapping) -> str:
    """Generate correlation report explaining rule-to-segment assignments."""
    lines = [
        "# NSX Segment-to-Rule Correlation Report",
        "",
        "This report explains how NSX firewall rules were mapped to network segments (secondary networks).",
        "",
        "## Summary",
        "",
        f"- **Primary Network Rules**: {len(segment_rule_mapping.primary_network_rules)}",
        f"- **Segments with Rules**: {len(segment_rule_mapping.segment_mappings)}",
        "",
    ]

    # Primary network rules
    if segment_rule_mapping.primary_network_rules:
        lines.extend([
            "## Primary Network Rules",
            "",
            "These rules apply to the primary pod network (standard NetworkPolicy):",
            "",
        ])
        for rule_name in segment_rule_mapping.primary_network_rules:
            lines.append(f"- `{rule_name}`")
        lines.append("")

    # Segment-specific rules
    if segment_rule_mapping.segment_mappings:
        lines.extend([
            "## Secondary Network Rules (MultiNetworkPolicy)",
            "",
            "These rules were correlated to specific network segments:",
            "",
        ])

        for seg_name, seg_mapping in segment_rule_mapping.segment_mappings.items():
            lines.extend([
                f"### Segment: {seg_name}",
                "",
                f"- **NetworkAttachmentDefinition**: `default/{seg_mapping.nad_name}`",
                f"- **VLAN IDs**: {', '.join(map(str, seg_mapping.vlan_ids)) if seg_mapping.vlan_ids else 'N/A'}",
                f"- **Subnets**: {', '.join(seg_mapping.subnets) if seg_mapping.subnets else 'N/A'}",
                f"- **Correlation Confidence**: {seg_mapping.correlation_confidence:.2f}",
                f"- **Firewall Rules**: {len(seg_mapping.firewall_rules)}",
                "",
            ])

            if seg_mapping.firewall_rules:
                lines.append("| Rule Name | Evidence |")
                lines.append("|-----------|----------|")
                for i, rule_name in enumerate(seg_mapping.firewall_rules):
                    evidence = (
                        seg_mapping.correlation_evidence[i]
                        if i < len(seg_mapping.correlation_evidence)
                        else "N/A"
                    )
                    lines.append(f"| `{rule_name}` | {evidence} |")
                lines.append("")

    lines.extend([
        "## Correlation Methods",
        "",
        "The correlation engine uses multiple detection strategies:",
        "",
        "1. **Direct Reference** (0.90 confidence) - Rule evidence contains segment name",
        "2. **IP Range Overlap** (0.70 confidence) - Rule IPs fall within segment subnet",
        "3. **VLAN Matching** (0.70 confidence) - Same VLAN ID in rule and segment",
        "4. **Proximity Analysis** (0.40 confidence) - Same workflow location",
        "5. **Multi-Signal Boost** (+0.05 per additional signal, max +0.15)",
        "",
        "Rules with confidence ≥ 0.50 are assigned to segments. Lower confidence rules default to primary network.",
        "",
        "## Review Recommendations",
        "",
        "- **High Confidence (≥ 0.85)**: Likely correct, but review YAML comments",
        "- **Medium Confidence (0.65-0.84)**: Review carefully, validate IP ranges and VLANs",
        "- **Low Confidence (0.50-0.64)**: Manual review recommended",
        "",
        "For questions or issues with correlation, see the project documentation.",
    ])

    return "\n".join(lines)


def _generate_network_attachments(workspace: Workspace):
    """
    Generate Kubernetes NetworkAttachmentDefinition manifests from NSX segments.

    Reads analysis.vrealize.json to find NSX segments and generates
    corresponding NAD YAML files with CNI/IPAM configuration.
    """
    import json

    from ops_translate.generate.network_attachment import generate_network_attachments

    # Find analysis file (check intent/ directory first, then runs/)
    analysis_file = workspace.root / "intent" / "analysis.vrealize.json"
    if not analysis_file.exists():
        # Fallback to runs directory for backwards compatibility
        runs_dir = workspace.root / "runs"
        if runs_dir.exists():
            run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            for run_dir in run_dirs:
                potential_file = run_dir / "analysis.vrealize.json"
                if potential_file.exists():
                    analysis_file = potential_file
                    break

    if analysis_file.exists():
            # Load analysis data
            with open(analysis_file) as f:
                analysis = json.load(f)

            # Extract NSX segments
            nsx_ops = analysis.get("nsx_operations", {})
            segments = nsx_ops.get("segments", [])

            if not segments:
                # No segments detected
                return

            # Get workflow name from source file
            source_file = analysis.get("source_file", "workflow")
            workflow_name = Path(source_file).stem

            # Generate NetworkAttachmentDefinition manifests
            attachments = generate_network_attachments(segments, workflow_name)

            if not attachments:
                # No NADs could be generated
                return

            # Write NAD files
            output_dir = workspace.root / "output/network-attachments"
            output_dir.mkdir(parents=True, exist_ok=True)

            for filename, content in attachments.items():
                nad_file = output_dir / filename
                nad_file.write_text(content)

            # Generate README
            readme_content = _generate_nad_readme()
            (output_dir / "README.md").write_text(readme_content)

            # Print success message
            console.print(
                f"[green]✓ Generated {len(attachments)} NetworkAttachmentDefinition(s): "
                f"output/network-attachments/[/green]"
            )
            console.print(
                "[yellow]⚠ Review TODO comments and configure host network interfaces[/yellow]"
            )

            return  # Found analysis and generated NADs


def _generate_nad_readme() -> str:
    """Generate README for NetworkAttachmentDefinition output directory."""
    return """# NetworkAttachmentDefinition Manifests

This directory contains Kubernetes NetworkAttachmentDefinition (NAD) manifests
generated from NSX-T segments detected in vRealize workflows.

## Critical Prerequisites

### 1. Install Multus CNI

Multus is required for multi-network support in Kubernetes:

```bash
# Kubernetes (DaemonSet)
kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/master/deployments/multus-daemonset.yml

# OpenShift (via Operator)
# Multus is pre-installed on OpenShift 4.x
```

### 2. Install Whereabouts IPAM

For dynamic IP allocation:

```bash
kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/whereabouts/master/doc/daemonset-install.yaml
```

### 3. Configure Host Network Interfaces

Each NAD requires a parent network interface on cluster nodes:

```bash
# Verify interface exists on nodes
ip link show

# Example: Create VLAN interface
ip link add link eth1 name eth1.100 type vlan id 100
ip link set eth1.100 up
```

## NSX Features vs Kubernetes

| NSX Feature | Kubernetes Equivalent | Notes |
|-------------|----------------------|-------|
| VLAN Segments | macvlan CNI with VLAN ID | Requires host interface configuration |
| Overlay Segments | bridge CNI | Different encapsulation mechanism |
| DHCP Server | Whereabouts IPAM | Different lease management |
| L2 MAC Learning | Not available | Bridge mode provides basic L2 |
| ARP Suppression | Not available | Standard ARP used |
| QoS Policies | Network QoS CRD | Separate configuration required |
| Security Profiles | NetworkPolicy | Limited to L3/L4 filtering |

## Deployment Workflow

### 1. Review Generated NADs

```bash
# Check all TODO comments
grep -r "TODO" *.yaml

# Verify VLAN IDs match NSX configuration
# Validate subnet/gateway addresses
```

### 2. Configure Host Networking

On each cluster node:

```bash
# For VLAN 100 on eth1
ip link add link eth1 name eth1.100 type vlan id 100
ip link set eth1.100 up

# Make persistent (varies by OS)
# RHEL/CentOS: /etc/sysconfig/network-scripts/ifcfg-eth1.100
# Ubuntu: /etc/netplan/
```

### 3. Apply NADs to Cluster

```bash
# Apply all NADs
kubectl apply -f output/network-attachments/

# Verify
kubectl get network-attachment-definitions -n default
```

### 4. Test with Sample Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-multi-network
  annotations:
    k8s.v1.cni.cncf.io/networks: web-tier-vlan100
spec:
  containers:
  - name: test
    image: busybox
    command: ["sleep", "3600"]
```

```bash
kubectl apply -f test-pod.yaml

# Verify connectivity
kubectl exec test-multi-network -- ip addr
kubectl exec test-multi-network -- ping <gateway-ip>
```

## Troubleshooting

### Pod fails to start with "network error"

- Check Multus is installed: `kubectl get pods -n kube-system | grep multus`
- Verify NAD exists: `kubectl get network-attachment-definitions`
- Check node has parent interface: `kubectl debug node/<node> -- ip link`

### Pod gets IP but no connectivity

- Verify VLAN ID matches physical network: `ip -d link show`
- Check gateway is reachable from node: `ping <gateway>`
- Ensure firewall allows traffic on VLAN interface

### Whereabouts IPAM errors

- Check Whereabouts pods running: `kubectl get pods -n kube-system | grep whereabouts`
- Verify IP range is not exhausted: `kubectl describe network-attachment-definition`
- Check for IP conflicts with existing infrastructure

## Migration Considerations

- **Network downtime required** - Cannot live-migrate NSX segments
- **Plan maintenance window** for network reconfiguration
- **Test extensively** in non-production before production migration
- **Consider hybrid approach** - Keep NSX for complex scenarios, use NADs for simple L2
- **Update monitoring** - NSX network monitoring won't work for Multus networks

## Additional Resources

- [Multus CNI Documentation](https://github.com/k8snetworkplumbingwg/multus-cni)
- [Whereabouts IPAM](https://github.com/k8snetworkplumbingwg/whereabouts)
- [OpenShift Multiple Networks](https://docs.openshift.com/container-platform/latest/networking/multiple_networks/understanding-multiple-networks.html)
- [CNI Plugin Reference](https://www.cni.dev/plugins/current/)
"""


def generate_all(
    workspace: Workspace,
    profile: str,
    use_ai: bool = False,
    output_format: str = "yaml",
    assume_existing_vms: bool = False,
    translation_profile=None,
):
    """
    Generate all artifacts (KubeVirt + Ansible) using AI or templates.

    Args:
        workspace: Workspace instance
        profile: Profile name (lab/prod)
        use_ai: If True, use LLM. If False, use templates.
        output_format: Output format (yaml, json, kustomize, argocd)
        assume_existing_vms: If True, assume VMs exist (MTV mode) - skip VM YAML generation
        translation_profile: ProfileSchema for deterministic Ansible adapter generation
    """
    if use_ai:
        generate_with_ai(
            workspace, profile, output_format, assume_existing_vms, translation_profile
        )
    else:
        generate_with_templates(
            workspace, profile, output_format, assume_existing_vms, translation_profile
        )


def generate_with_ai(
    workspace: Workspace,
    profile: str,
    output_format: str = "yaml",
    assume_existing_vms: bool = False,
    translation_profile=None,
):
    """
    Generate artifacts using LLM.

    Reads intent/intent.yaml and calls LLM to generate all artifacts.

    Args:
        workspace: Workspace instance
        profile: Profile name
        output_format: Output format
        assume_existing_vms: If True, skip VM YAML generation (MTV mode)
    """
    # Load config and initialize LLM
    config = workspace.load_config()
    llm = get_provider(config)

    if not llm.is_available():
        console.print("[yellow]Warning: LLM not available. Falling back to templates.[/yellow]")
        generate_with_templates(workspace, profile, output_format)
        return

    # Load intent
    intent_file = workspace.root / "intent/intent.yaml"
    if not intent_file.exists():
        # Check if we have NSX operations that can be generated without intent.yaml
        analysis_file = workspace.root / "intent/analysis.vrealize.json"
        has_nsx_operations = False
        if analysis_file.exists():
            try:
                analysis_data = json.load(analysis_file.open())
                nsx_ops = analysis_data.get("nsx_operations", {})
                has_segments = bool(nsx_ops.get("segments"))
                has_firewall_rules = bool(nsx_ops.get("firewall_rules"))
                has_nsx_operations = has_segments or has_firewall_rules
            except Exception:
                pass

        if has_nsx_operations:
            # NSX-only mode: fall back to templates which handle this case
            console.print("[dim]NSX operations detected. Using template-based generation for network policies.[/dim]")
            generate_with_templates(workspace, profile, output_format, assume_existing_vms, translation_profile)
            return
        else:
            console.print("[red]Error: intent/intent.yaml not found. Run 'intent extract' first.[/red]")
            return

    intent_yaml = intent_file.read_text()

    # Load profile config
    profile_config = config["profiles"][profile]

    # Load prompt template
    prompt_file = PROJECT_ROOT / "prompts/generate_artifacts.md"
    prompt_template = prompt_file.read_text()

    # Format profile config as YAML
    profile_yaml = f"""profile_name: {profile}
default_namespace: {profile_config["default_namespace"]}
default_network: {profile_config["default_network"]}
default_storage_class: {profile_config["default_storage_class"]}"""

    # Fill in prompt
    prompt = prompt_template.replace("{intent_yaml}", intent_yaml)
    prompt = prompt.replace("{profile_config}", profile_yaml)

    console.print("[dim]Calling LLM to generate artifacts (this may take a moment)...[/dim]")

    # Call LLM
    try:
        response = llm.generate(
            prompt,
            max_tokens=8192,
            temperature=0.0,  # Larger for multiple files
        )

        # Parse multi-file response
        files = parse_multifile_response(response)

        # Write each file
        for file_path, content in files.items():
            full_path = workspace.root / file_path
            ensure_dir(full_path.parent)
            write_text(full_path, content)
            console.print(f"[dim]  Generated: {file_path}[/dim]")

        if not files:
            console.print(
                "[yellow]Warning: No files extracted from LLM response. "
                "Falling back to templates.[/yellow]"
            )
            generate_with_templates(workspace, profile, output_format)
        else:
            # After AI generation, also generate role stubs for MANUAL/BLOCKED components
            _generate_role_stubs_from_gaps(workspace)

    except Exception as e:
        console.print(f"[red]Error calling LLM: {e}[/red]")
        console.print("[yellow]Falling back to template-based generation[/yellow]")
        generate_with_templates(workspace, profile, output_format)


def parse_multifile_response(response: str) -> dict:
    """
    Parse LLM response with multiple files.

    Expected format:
    FILE: path/to/file.yaml
    ---
    content here
    ---

    FILE: path/to/another.yaml
    ---
    more content
    ---

    Returns:
        dict: {file_path: content}
    """
    files = {}

    # Split by FILE: markers
    file_pattern = r"FILE:\s*([^\n]+)\n---\n(.*?)\n---"
    matches = re.findall(file_pattern, response, re.DOTALL)

    for file_path, content in matches:
        file_path = file_path.strip()
        content = content.strip()
        files[file_path] = content

    return files


def generate_with_templates(
    workspace: Workspace,
    profile: str,
    output_format: str = "yaml",
    assume_existing_vms: bool = False,
    translation_profile=None,
):
    """
    Generate artifacts using Jinja2 templates or direct generation.

    For standard YAML format, calls ansible.py and kubevirt.py directly to enable
    gap analysis integration. For other formats, uses Jinja2 templates.

    Args:
        workspace: Workspace instance
        profile: Profile name
        output_format: Output format
        assume_existing_vms: If True, skip VM YAML generation (MTV mode)
    """
    import yaml

    from ops_translate.generate import ansible, kubevirt
    from ops_translate.generate.formats import get_format_handler
    from ops_translate.util.templates import TemplateLoader, create_template_context

    # Load config and intent
    config = workspace.load_config()
    intent_file = workspace.root / "intent/intent.yaml"

    # Check if we can work with gaps.json instead of merged intent
    has_merged_intent = intent_file.exists()

    # Check if we have NSX operations that can be generated without intent.yaml
    analysis_file = workspace.root / "intent/analysis.vrealize.json"
    has_nsx_operations = False
    if analysis_file.exists():
        try:
            analysis_data = json.load(analysis_file.open())
            nsx_ops = analysis_data.get("nsx_operations", {})
            has_segments = bool(nsx_ops.get("segments"))
            has_firewall_rules = bool(nsx_ops.get("firewall_rules"))
            has_nsx_operations = has_segments or has_firewall_rules
        except Exception:
            pass

    # For YAML format, check if custom templates exist
    loader = TemplateLoader(workspace.root)
    has_custom_templates = loader.has_custom_templates()

    if output_format == "yaml" and not has_custom_templates:
        # Use direct generation to support gap analysis (only if no custom templates)
        # This path works without merged intent.yaml if gaps.json exists OR if we have NSX operations

        # Only generate Ansible/KubeVirt if we have merged intent (not NSX-only mode)
        skip_ansible_kubevirt = has_nsx_operations and not has_merged_intent

        if not skip_ansible_kubevirt:
            try:
                ansible.generate(
                    workspace,
                    profile,
                    use_ai=False,
                    assume_existing_vms=assume_existing_vms,
                    translation_profile=translation_profile,
                )
                if not assume_existing_vms:
                    kubevirt.generate(workspace, profile, use_ai=False)
                    console.print("[green]✓ KubeVirt manifest: output/kubevirt/vm.yaml[/green]")
                else:
                    console.print("[dim]Skipping VM YAML generation (--assume-existing-vms)[/dim]")
                console.print("[green]✓ Ansible playbook: output/ansible/site.yml[/green]")
                console.print("[green]✓ Ansible role: output/ansible/roles/provision_vm/[/green]")
                console.print("[green]✓ README: output/README.md[/green]")
            except Exception as e:
                if has_nsx_operations:
                    # If we have NSX operations, it's OK if Ansible/KubeVirt generation fails
                    console.print(f"[dim]Skipping Ansible/KubeVirt generation (NSX-only mode): {e}[/dim]")
                else:
                    # Otherwise, this is an error
                    raise
        else:
            console.print("[dim]Skipping Ansible/KubeVirt generation (NSX-only mode)[/dim]")

        # NSX network generation (works independently of intent.yaml)
        # Generate NetworkAttachmentDefinition manifests from NSX segments if detected
        try:
            _generate_network_attachments(workspace)
        except Exception as e:
            console.print(
                f"[yellow]⚠ Could not generate NetworkAttachmentDefinition "
                f"manifests: {e}[/yellow]"
            )

        # Correlate NSX segments with firewall rules to determine network scope
        segment_rule_mapping = None
        try:
            segment_rule_mapping = _correlate_segments_and_rules(workspace)
        except Exception as e:
            console.print(f"[yellow]⚠ Could not correlate segments and rules: {e}[/yellow]")

        # Generate MultiNetworkPolicy manifests for secondary networks
        if segment_rule_mapping and segment_rule_mapping.segment_mappings:
            try:
                _generate_multi_network_policies(workspace, segment_rule_mapping)
            except Exception as e:
                console.print(
                    f"[yellow]⚠ Could not generate MultiNetworkPolicy manifests: {e}[/yellow]"
                )

        # Generate NetworkPolicy manifests for primary network
        try:
            _generate_network_policies(workspace, segment_rule_mapping)
        except Exception as e:
            console.print(f"[yellow]⚠ Could not generate NetworkPolicy manifests: {e}[/yellow]")

        return

    # For other formats, we need merged intent.yaml
    if not has_merged_intent:
        console.print("[red]Error: intent/intent.yaml not found. Run 'intent merge' first.[/red]")
        console.print("[dim]Tip: For YAML format, you can skip merge if gaps.json exists[/dim]")
        return

    try:
        intent_data = yaml.safe_load(intent_file.read_text())
        if intent_data is None:
            console.print(f"[red]Error: {intent_file} is empty[/red]")
            return
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse {intent_file}: {e}")
        console.print(f"[red]Error: Invalid YAML in {intent_file}[/red]")
        console.print(f"[dim]{e}[/dim]")
        return

    profile_config = config["profiles"][profile]

    # Initialize template loader
    loader = TemplateLoader(workspace.root)

    # Show whether using custom or default templates
    if loader.has_custom_templates():
        console.print("[dim]Using custom templates from workspace[/dim]")
    else:
        console.print("[dim]Using default templates[/dim]")

    # Create template context
    context = create_template_context(intent_data, profile_config, profile)

    # Generate base YAML content
    content = {}

    # Generate KubeVirt manifest
    try:
        kubevirt_output = workspace.root / "output/kubevirt/vm.yaml"
        loader.render_template("kubevirt/vm.yaml.j2", context, kubevirt_output)
        content["kubevirt/vm.yaml"] = kubevirt_output.read_text()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not generate KubeVirt manifest: {e}[/yellow]")

    # Generate Ansible playbook
    try:
        playbook_output = workspace.root / "output/ansible/site.yml"
        loader.render_template("ansible/playbook.yml.j2", context, playbook_output)
        content["ansible/site.yml"] = playbook_output.read_text()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not generate Ansible playbook: {e}[/yellow]")

    # Generate Ansible role tasks
    try:
        role_tasks_output = workspace.root / "output/ansible/roles/provision_vm/tasks/main.yml"
        loader.render_template("ansible/role_tasks.yml.j2", context, role_tasks_output)
        content["ansible/roles/provision_vm/tasks/main.yml"] = role_tasks_output.read_text()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not generate Ansible role: {e}[/yellow]")

    # Apply output format
    if output_format != "yaml":
        try:
            format_handler = get_format_handler(output_format, workspace.root)
            format_handler.write(content, profile, context)

            # Print success messages based on format
            if output_format == "json":
                console.print("[green]✓ JSON manifests: output/json/[/green]")
            elif output_format in ("kustomize", "gitops"):
                console.print("[green]✓ Kustomize base: output/base/[/green]")
                console.print("[green]✓ Overlays: output/overlays/{dev,staging,prod}/[/green]")
            elif output_format == "argocd":
                console.print("[green]✓ ArgoCD applications: output/argocd/[/green]")
                console.print(
                    "[green]✓ Kustomize structure: output/base/ and output/overlays/[/green]"
                )
        except Exception as e:
            console.print(f"[yellow]⚠ Could not apply format {output_format}: {e}[/yellow]")
            return

    # Generate README
    generate_readme(workspace, profile, context)


def generate_readme(workspace: Workspace, profile: str, context: dict):
    """Generate README.md for output artifacts."""
    readme_content = f"""# Generated Artifacts

Generated by ops-translate from workflow: {context['intent'].get('workflow_name', 'unknown')}

## Profile: {profile}

Configuration:
- Namespace: {context['profile'].get('default_namespace', 'default')}
- Network: {context['profile'].get('default_network', 'pod-network')}
- Storage Class: {context['profile'].get('default_storage_class', 'standard')}

## Files

- `kubevirt/vm.yaml` - KubeVirt VirtualMachine manifest
- `ansible/site.yml` - Ansible playbook
- `ansible/roles/provision_vm/tasks/main.yml` - Ansible role tasks

## Usage

### Apply KubeVirt Manifest

```bash
kubectl apply -f output/kubevirt/vm.yaml
```

### Run Ansible Playbook

```bash
cd output/ansible
ansible-playbook site.yml
```

## Customization

To customize the generated artifacts, initialize your workspace with templates:

```bash
ops-translate init my-workspace --with-templates
```

Then edit the templates in `templates/` directory before running `generate`.
"""

    readme_file = workspace.root / "output/README.md"
    write_text(readme_file, readme_content)
    console.print(f"[dim]  Generated: {readme_file.relative_to(workspace.root)}[/dim]")
