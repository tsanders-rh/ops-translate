# Generate Artifacts Prompt

You are an expert in Kubernetes, KubeVirt, Ansible, and OpenShift Virtualization. Your task is to generate production-ready artifacts for deploying and managing virtual machines on OpenShift based on a normalized operational intent model.

## Input
You will be provided with:
1. A normalized operational intent YAML (conforming to intent.schema.json)
2. A target profile (lab or prod) with configuration

## Task
Generate the following artifacts:

### 1. KubeVirt VirtualMachine Manifest
- File: `output/kubevirt/vm.yaml`
- A complete KubeVirt VirtualMachine resource definition
- Include all specs: CPU, memory, storage, network
- Apply appropriate labels and annotations from metadata
- Use profile-specific values (namespace, storage class, network)

### 2. Ansible Playbook
- File: `output/ansible/site.yml`
- Main playbook that orchestrates VM provisioning
- Should call the provision_vm role
- Include proper error handling
- Support check mode (--check)

### 3. Ansible Role - Tasks
- File: `output/ansible/roles/provision_vm/tasks/main.yml`
- Tasks to create the KubeVirt VM using k8s module
- Include pre-flight validation
- Apply tags/labels
- Handle conditional logic (environment-based profiles)

### 4. Ansible Role - Defaults
- File: `output/ansible/roles/provision_vm/defaults/main.yml`
- Default variable values extracted from intent
- Include all input parameters
- Profile-specific defaults

### 5. README
- File: `output/README.md`
- How to run the Ansible playbook
- Prerequisites (oc/kubectl, ansible, collections)
- Example invocations for different scenarios
- Troubleshooting tips

## Rules
1. **Generate valid, runnable code** - All YAML must be syntactically correct
2. **Use current best practices** - Follow Ansible and KubeVirt conventions (2024/2025)
3. **Include comments** - Explain non-obvious logic
4. **Handle conditionals** - Implement environment branching from intent
5. **Apply governance** - If approval is required, include a manual step with clear instructions
6. **Be defensive** - Validate inputs, provide helpful error messages
7. **Use profile values** - Replace generic values with profile-specific configuration

## Profile Configuration
```yaml
# Example profile passed to you
profile_name: lab
default_namespace: virt-lab
default_network: lab-network
default_storage_class: nfs
```

## Example Intent Input
```yaml
schema_version: 1
intent:
  workflow_name: provision_vm_with_governance
  workload_type: virtual_machine

  inputs:
    vm_name: { type: string, required: true }
    environment: { type: enum, values: [dev, prod], required: true }
    cpu: { type: integer, required: true, min: 1, max: 32 }
    memory_gb: { type: integer, required: true, min: 1, max: 256 }

  governance:
    approval:
      required_when:
        environment: prod

  profiles:
    network:
      when: { environment: prod }
      value: prod-network
    network_else: dev-network

  metadata:
    tags:
      - key: env
        value_from: environment
      - key: owner
        value_from: owner_email
```

## Expected Output Structure

You should output multiple files. Format your response as follows:

```
FILE: output/kubevirt/vm.yaml
---
<content here>
---

FILE: output/ansible/site.yml
---
<content here>
---

FILE: output/ansible/roles/provision_vm/tasks/main.yml
---
<content here>
---

FILE: output/ansible/roles/provision_vm/defaults/main.yml
---
<content here>
---

FILE: output/README.md
---
<content here>
---
```

## KubeVirt Example
```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: "{{ vm_name }}"
  namespace: virt-lab
  labels:
    env: "{{ environment }}"
spec:
  running: false
  template:
    metadata:
      labels:
        kubevirt.io/vm: "{{ vm_name }}"
    spec:
      domain:
        cpu:
          cores: {{ cpu }}
        memory:
          guest: "{{ memory_gb }}Gi"
        devices:
          disks:
            - name: rootdisk
              disk:
                bus: virtio
          interfaces:
            - name: default
              masquerade: {}
      networks:
        - name: default
          pod: {}
      volumes:
        - name: rootdisk
          persistentVolumeClaim:
            claimName: "{{ vm_name }}-root"
```

## Ansible Playbook Example
```yaml
---
- name: Provision Virtual Machine on OpenShift Virtualization
  hosts: localhost
  gather_facts: false
  roles:
    - provision_vm
```

## Ansible Tasks Example
```yaml
---
- name: Validate inputs
  assert:
    that:
      - vm_name is defined
      - environment in ['dev', 'prod']
      - cpu >= 1 and cpu <= 32
    fail_msg: "Invalid input parameters"

- name: Check for approval requirement
  debug:
    msg: "WARNING: Production deployment requires approval. Ensure approval is obtained before proceeding."
  when: environment == 'prod'

- name: Create KubeVirt VirtualMachine
  kubernetes.core.k8s:
    state: present
    definition: "{{ lookup('template', 'vm.yaml.j2') }}"
```

## Now Generate Artifacts

Intent:
{intent_yaml}

Profile:
{profile_config}

Remember: Generate complete, valid artifacts in the multi-file format specified above.
