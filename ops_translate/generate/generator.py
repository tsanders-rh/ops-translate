"""
Unified artifact generation using LLM or templates.
"""

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


def _generate_network_policies(workspace: Workspace):
    """
    Generate Kubernetes NetworkPolicy manifests from detected NSX firewall rules.

    Reads analysis.vrealize.json to find NSX firewall rules and generates
    corresponding NetworkPolicy YAML files with limitation warnings.
    """
    import json

    from ops_translate.generate.networkpolicy import generate_network_policies

    # Find the latest analysis file
    runs_dir = workspace.root / "runs"
    if not runs_dir.exists():
        return

    # Get the most recent run directory
    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_dirs:
        return

    # Look for analysis.vrealize.json in the latest run
    for run_dir in run_dirs:
        analysis_file = run_dir / "analysis.vrealize.json"
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


def _generate_network_attachments(workspace: Workspace):
    """
    Generate Kubernetes NetworkAttachmentDefinition manifests from NSX segments.

    Reads analysis.vrealize.json to find NSX segments and generates
    corresponding NAD YAML files with CNI/IPAM configuration.
    """
    import json

    from ops_translate.generate.network_attachment import generate_network_attachments

    # Find the latest analysis file
    runs_dir = workspace.root / "runs"
    if not runs_dir.exists():
        return

    # Get the most recent run directory
    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_dirs:
        return

    # Look for analysis.vrealize.json in the latest run
    for run_dir in run_dirs:
        analysis_file = run_dir / "analysis.vrealize.json"
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

    # For YAML format, check if custom templates exist
    loader = TemplateLoader(workspace.root)
    has_custom_templates = loader.has_custom_templates()

    if output_format == "yaml" and not has_custom_templates:
        # Use direct generation to support gap analysis (only if no custom templates)
        # This path works without merged intent.yaml if gaps.json exists
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

            # Generate NetworkPolicy manifests from NSX firewall rules if detected
            try:
                _generate_network_policies(workspace)
            except Exception as e:
                console.print(f"[yellow]⚠ Could not generate NetworkPolicy manifests: {e}[/yellow]")

            # Generate NetworkAttachmentDefinition manifests from NSX segments if detected
            try:
                _generate_network_attachments(workspace)
            except Exception as e:
                console.print(
                    f"[yellow]⚠ Could not generate NetworkAttachmentDefinition "
                    f"manifests: {e}[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]Error generating artifacts: {e}[/red]")
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
