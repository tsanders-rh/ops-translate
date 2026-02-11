"""
KubeVirt VirtualMachine manifest generation.
"""

import yaml
from rich.console import Console

from ops_translate.util.files import ensure_dir
from ops_translate.workspace import Workspace

console = Console()


def generate(workspace: Workspace, profile: str, use_ai: bool = False):
    """
    Generate KubeVirt VirtualMachine manifest.

    Outputs:
    - output/kubevirt/vm.yaml
    """
    output_dir = workspace.root / "output/kubevirt"
    ensure_dir(output_dir)

    config = workspace.load_config()
    profile_config = config["profiles"][profile]

    # Load intent to check for vm_source
    intent_file = workspace.root / "intent/intent.yaml"
    vm_source = None
    if intent_file.exists():
        with open(intent_file) as f:
            intent_data = yaml.safe_load(f)
            if intent_data and "intent" in intent_data:
                vm_source = intent_data["intent"].get("vm_source")

    # Generate VM manifest
    vm_manifest = create_vm_manifest(profile_config, vm_source, use_ai)

    # Write to file
    output_file = output_dir / "vm.yaml"
    with open(output_file, "w") as f:
        yaml.dump(vm_manifest, f, default_flow_style=False, sort_keys=False)


def create_vm_manifest(profile_config: dict, vm_source: dict | None, use_ai: bool) -> dict:
    """Create KubeVirt VirtualMachine manifest."""
    namespace = profile_config["default_namespace"]
    storage_class = profile_config["default_storage_class"]

    # Determine the data volume source based on vm_source and template mappings
    source_spec = _get_source_spec(vm_source, profile_config)

    manifest = {
        "apiVersion": "kubevirt.io/v1",
        "kind": "VirtualMachine",
        "metadata": {
            "name": "example-vm",
            "namespace": namespace,
            "labels": {"app": "example-vm", "managed-by": "ops-translate"},
        },
        "spec": {
            "running": False,
            "template": {
                "metadata": {"labels": {"kubevirt.io/vm": "example-vm"}},
                "spec": {
                    "domain": {
                        "cpu": {"cores": 2},
                        "resources": {"requests": {"memory": "4Gi"}},
                        "devices": {
                            "disks": [
                                {"name": "rootdisk", "disk": {"bus": "virtio"}},
                                {"name": "cloudinitdisk", "disk": {"bus": "virtio"}},
                            ],
                            "interfaces": [{"name": "default", "masquerade": {}}],
                        },
                    },
                    "networks": [{"name": "default", "pod": {}}],
                    "volumes": [
                        {"name": "rootdisk", "dataVolume": {"name": "example-vm-root"}},
                        {
                            "name": "cloudinitdisk",
                            "cloudInitNoCloud": {
                                # Empty cloud-init config
                                "userDataBase64": "I2Nsb3VkLWNvbmZpZwp1c2VyczogW10K"
                            },
                        },
                    ],
                },
            },
            "dataVolumeTemplates": [
                {
                    "metadata": {"name": "example-vm-root"},
                    "spec": {
                        "pvc": {
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {"requests": {"storage": "30Gi"}},
                            "storageClassName": storage_class,
                        },
                        "source": source_spec,
                    },
                }
            ],
        },
    }

    return manifest


def _get_source_spec(vm_source: dict | None, profile_config: dict) -> dict:
    """
    Generate CDI source spec based on vm_source and template mappings.

    Args:
        vm_source: vm_source from intent (type, name, description)
        profile_config: Profile configuration with template_mappings

    Returns:
        dict: CDI source specification (registry, pvc, http, or blank)
    """
    # Default to blank if no vm_source specified
    if not vm_source:
        return {"blank": {}}

    source_type = vm_source.get("type", "blank")
    source_name = vm_source.get("name")

    # If blank, return early
    if source_type == "blank":
        return {"blank": {}}

    # Look up template mapping in profile config
    template_mappings = profile_config.get("template_mappings", {})

    # Try to find a mapping for this template/image
    mapping = None
    if source_name and source_name in template_mappings:
        mapping = template_mappings[source_name]

    # If no mapping found, warn and default to blank
    if not mapping:
        if source_name:
            console.print(
                f"[yellow]Warning: No template mapping found for '{source_name}'. "
                f"Add mapping in profile config to use actual image.[/yellow]"
            )
            console.print(
                f"[dim]  Example: template_mappings:\n"
                f"    {source_name}: registry:quay.io/containerdisks/centos:8[/dim]"
            )
        return {"blank": {}}

    # Parse mapping format: "registry:url", "pvc:name", "http:url", or "blank"
    if mapping == "blank":
        return {"blank": {}}
    elif mapping.startswith("registry:"):
        url = mapping[len("registry:") :]
        return {"registry": {"url": url}}
    elif mapping.startswith("pvc:"):
        pvc_spec = mapping[len("pvc:") :]
        # Support "pvc:name" or "pvc:namespace/name"
        if "/" in pvc_spec:
            namespace, name = pvc_spec.split("/", 1)
            return {"pvc": {"name": name, "namespace": namespace}}
        else:
            return {"pvc": {"name": pvc_spec}}
    elif mapping.startswith("http:"):
        url = mapping[len("http:") :]
        return {"http": {"url": url}}
    else:
        # Unknown format, warn and default to blank
        console.print(
            f"[yellow]Warning: Invalid mapping format for '{source_name}': {mapping}[/yellow]"
        )
        console.print("[dim]  Valid formats: registry:url, pvc:name, http:url, or blank[/dim]")
        return {"blank": {}}
