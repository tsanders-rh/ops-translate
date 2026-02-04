"""
Ansible playbook and role generation.
"""
from pathlib import Path
from ops_translate.workspace import Workspace
from ops_translate.util.files import write_text, ensure_dir
import yaml


def generate(workspace: Workspace, profile: str, use_ai: bool = False):
    """
    Generate Ansible playbook and role.

    Outputs:
    - output/ansible/site.yml
    - output/ansible/roles/provision_vm/tasks/main.yml
    - output/ansible/roles/provision_vm/defaults/main.yml
    - output/README.md
    """
    output_dir = workspace.root / "output/ansible"
    ensure_dir(output_dir)

    config = workspace.load_config()
    profile_config = config['profiles'][profile]

    # Generate site.yml playbook
    playbook_content = generate_playbook(profile)
    write_text(output_dir / "site.yml", playbook_content)

    # Generate role
    role_dir = output_dir / "roles/provision_vm"
    ensure_dir(role_dir / "tasks")
    ensure_dir(role_dir / "defaults")

    tasks_content = generate_tasks(profile_config, use_ai)
    write_text(role_dir / "tasks/main.yml", tasks_content)

    defaults_content = generate_defaults(profile_config)
    write_text(role_dir / "defaults/main.yml", defaults_content)

    # Generate README
    readme_content = generate_readme(profile)
    write_text(workspace.root / "output/README.md", readme_content)


def generate_playbook(profile: str) -> str:
    """Generate Ansible playbook."""
    playbook = [
        {
            'name': 'Provision KubeVirt VM',
            'hosts': 'localhost',
            'gather_facts': False,
            'roles': [
                'provision_vm'
            ]
        }
    ]

    return yaml.dump(playbook, default_flow_style=False, sort_keys=False)


def generate_tasks(profile_config: dict, use_ai: bool) -> str:
    """Generate Ansible tasks."""
    namespace = profile_config['default_namespace']
    storage_class = profile_config['default_storage_class']

    tasks = [
        {
            'name': 'Create KubeVirt VirtualMachine',
            'kubernetes.core.k8s': {
                'state': 'present',
                'definition': "{{ lookup('file', 'kubevirt/vm.yaml') | from_yaml }}"
            }
        },
        {
            'name': 'Wait for VM to be ready',
            'kubernetes.core.k8s_info': {
                'api_version': 'kubevirt.io/v1',
                'kind': 'VirtualMachine',
                'name': "{{ vm_name }}",
                'namespace': namespace
            },
            'register': 'vm_info',
            'until': "vm_info.resources | length > 0 and vm_info.resources[0].status.ready is defined",
            'retries': 30,
            'delay': 10
        }
    ]

    return yaml.dump(tasks, default_flow_style=False, sort_keys=False)


def generate_defaults(profile_config: dict) -> str:
    """Generate Ansible role defaults."""
    defaults = {
        'vm_name': 'example-vm',
        'namespace': profile_config['default_namespace'],
        'cpu_cores': 2,
        'memory': '4Gi',
        'storage_class': profile_config['default_storage_class'],
    }

    return yaml.dump(defaults, default_flow_style=False, sort_keys=False)


def generate_readme(profile: str) -> str:
    """Generate README for output artifacts."""
    return f"""# Generated Artifacts

This directory contains the generated Ansible and KubeVirt artifacts.

## Profile: {profile}

## Files

- `ansible/site.yml` - Main Ansible playbook
- `ansible/roles/provision_vm/` - Ansible role for VM provisioning
- `kubevirt/vm.yaml` - KubeVirt VirtualMachine manifest

## Usage

### Apply KubeVirt manifest directly:

```bash
kubectl apply -f kubevirt/vm.yaml
```

### Run Ansible playbook:

```bash
ansible-playbook ansible/site.yml -e vm_name=my-vm
```

## Requirements

- Ansible 2.9+
- kubernetes.core collection (`ansible-galaxy collection install kubernetes.core`)
- community.kubevirt collection (`ansible-galaxy collection install community.kubevirt`)
- kubectl configured with cluster access
- KubeVirt installed on target cluster

## Variables

See `ansible/roles/provision_vm/defaults/main.yml` for configurable variables.
"""
