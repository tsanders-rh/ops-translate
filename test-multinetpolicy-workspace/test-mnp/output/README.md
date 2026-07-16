# Generated Artifacts

This directory contains the generated Ansible and KubeVirt artifacts.

## Profile: lab

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
