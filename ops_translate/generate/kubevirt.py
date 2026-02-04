"""
KubeVirt VirtualMachine manifest generation.
"""

import yaml

from ops_translate.util.files import ensure_dir
from ops_translate.workspace import Workspace


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

    # Generate VM manifest
    vm_manifest = create_vm_manifest(profile_config, use_ai)

    # Write to file
    output_file = output_dir / "vm.yaml"
    with open(output_file, "w") as f:
        yaml.dump(vm_manifest, f, default_flow_style=False, sort_keys=False)


def create_vm_manifest(profile_config: dict, use_ai: bool) -> dict:
    """Create KubeVirt VirtualMachine manifest."""
    namespace = profile_config["default_namespace"]
    storage_class = profile_config["default_storage_class"]

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
                        "source": {"blank": {}},
                    },
                }
            ],
        },
    }

    return manifest
