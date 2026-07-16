# AWS Test Environment Setup for NSX Multi-Network Demo

This directory contains everything needed to set up a test environment on AWS OpenShift clusters for demonstrating NSX MultiNetworkPolicy translation.

## Quick Start

```bash
# 1. Login to your OpenShift cluster
oc login https://api.your-cluster.example.com:6443

# 2. Run the setup script
cd nsx-multinetwork-demo
./setup-aws-test-environment.sh

# 3. Verify connectivity
oc exec -n virt-lab web-server -- ping -c 3 10.244.150.11
```

That's it! The script handles everything automatically.

---

## What Gets Created

### 1. Namespace
- **Name**: `virt-lab` (configurable via `NAMESPACE` env var)

### 2. Three Secondary Networks (NetworkAttachmentDefinitions)
- **web-tier-vlan100**: 10.244.100.0/24 (simulates NSX VLAN 100)
- **app-tier-vlan150**: 10.244.150.0/24 (simulates NSX VLAN 150)
- **db-tier-vlan200**: 10.244.200.0/24 (simulates NSX VLAN 200)

Technology: Bridge CNI with separate bridge per network

### 3. Three Test Pods
- **web-server**: nginx (10.244.100.11)
  - Labels: `app=websecuritygroup, tier=web`
- **app-server**: nginx (10.244.150.11)
  - Labels: `app=securitygroup, tier=app`
- **db-server**: postgres (10.244.200.11)
  - Labels: `app=dbsecuritygroup, tier=db`

### 4. Node Configuration
- iptables FORWARD rules on all worker nodes
- Allows traffic between secondary networks (10.244.0.0/16)

---

## Prerequisites

### Required

1. **OpenShift 4.12+** cluster running on AWS
   - Any AWS region/instance type works
   - Minimum 2 worker nodes recommended

2. **Cluster admin access**
   ```bash
   oc auth can-i create machineconfigs
   # Should return: yes
   ```

3. **MultiNetworkPolicy enabled** (one-time cluster configuration)
   ```bash
   # Check if enabled
   oc get network.operator.openshift.io cluster -o jsonpath='{.spec.useMultiNetworkPolicy}'
   # Should return: true

   # If not enabled, enable it:
   oc patch network.operator.openshift.io cluster --type=merge \
     -p '{"spec":{"useMultiNetworkPolicy":true}}'

   # Wait for network operator to finish updating (~2 minutes)
   oc wait --for=condition=Progressing=False --timeout=300s co/network

   # Verify OVN-Kubernetes pods are running
   oc get pods -n openshift-ovn-kubernetes -l app=ovnkube-node
   ```

4. **OpenShift CLI (oc)** installed locally
   - Download from: https://mirror.openshift.com/pub/openshift-v4/clients/ocp/

### Optional

- **ops-translate** installed (to generate MultiNetworkPolicy from NSX workflows)
  ```bash
  git clone https://github.com/tsanders-rh/ops-translate.git
  cd ops-translate
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .
  ```

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `setup-aws-test-environment.sh` | **Main setup script** - runs everything automatically |
| `nad-aws-bridge-test.yaml` | NetworkAttachmentDefinition configs (bridge CNI) |
| `test-pods-demo.yaml` | Test pod specifications |
| `AWS_TEST_ENVIRONMENT_SUMMARY.md` | Detailed environment documentation |
| `README-AWS-SETUP.md` | This file |

### Other Files (Historical/Alternative Approaches)
- `nad-aws-eni-*.yaml` - Attempts using actual AWS ENIs (complex, not recommended for testing)
- `nad-aws-macvlan.yaml` - Macvlan approach (requires AWS secondary IPs)
- `nad-aws-test-setup.yaml` - ipvlan L3 approach (requires IP forwarding)

**Use `nad-aws-bridge-test.yaml` - it's the simplest and most reliable approach for testing.**

---

## Manual Setup Steps

If you prefer to run commands manually instead of using the script:

### 1. Enable MultiNetworkPolicy (if not already enabled)
```bash
oc patch network.operator.openshift.io cluster --type=merge \
  -p '{"spec":{"useMultiNetworkPolicy":true}}'

oc wait --for=condition=Progressing=False --timeout=300s co/network
```

### 2. Create Namespace
```bash
oc create namespace virt-lab
```

### 3. Configure Worker Nodes
```bash
# Get worker node names
WORKER_NODES=$(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[*].metadata.name}')

# Configure iptables on each worker
for node in $WORKER_NODES; do
  echo "Configuring $node..."
  oc debug node/$node -- chroot /host bash -c \
    "iptables -I FORWARD 1 -s 10.244.0.0/16 -d 10.244.0.0/16 -j ACCEPT"
done
```

### 4. Apply NetworkAttachmentDefinitions
```bash
oc apply -f nad-aws-bridge-test.yaml
```

### 5. Deploy Test Pods
```bash
oc apply -f test-pods-demo.yaml

# Wait for pods to be ready
oc wait --for=condition=ready pod --all -n virt-lab --timeout=90s
```

### 6. Verify Connectivity
```bash
# Test web → app
oc exec -n virt-lab web-server -- ping -c 3 10.244.150.11

# Test app → db
oc exec -n virt-lab app-server -- ping -c 3 10.244.200.11

# Test web → db
oc exec -n virt-lab web-server -- ping -c 3 10.244.200.11
```

---

## Using with ops-translate

Once the environment is set up, you can use it to test ops-translate output:

```bash
# 1. Setup ops-translate workspace
cd ~/demos
git clone https://github.com/tsanders-rh/ops-translate.git
cd ops-translate
source .venv/bin/activate

# 2. Initialize workspace
ops-translate init virt-lab && cd virt-lab

# 3. Add your NSX workflow XML to input/vrealize/
mkdir -p input/vrealize
# (copy your workflow XML here)

# 4. Analyze and translate
ops-translate analyze
ops-translate translate

# 5. Deploy generated NetworkAttachmentDefinitions and MultiNetworkPolicies
oc apply -f output/k8s/network-attachment-definitions.yaml
oc apply -f output/k8s/multi-network-policies.yaml

# 6. Recreate pods to pick up new policies
oc delete pods -n virt-lab --all
oc apply -f nsx-multinetwork-demo/test-pods-demo.yaml

# 7. Test policy enforcement
# (See DEMO_SCRIPT.md for testing procedures)
```

---

## Troubleshooting

### Pods stuck in ContainerCreating
```bash
# Check pod events
oc describe pod web-server -n virt-lab

# Common issues:
# - NetworkAttachmentDefinition not found: Apply nad-aws-bridge-test.yaml
# - CNI plugin error: Check network operator logs
```

### Connectivity tests fail
```bash
# 1. Check if pods have secondary interfaces
oc exec -n virt-lab web-server -- ip addr show net1

# 2. Check if bridges exist on host
NODE=$(oc get pod web-server -n virt-lab -o jsonpath='{.spec.nodeName}')
oc debug node/$NODE -- chroot /host ip link show | grep cni

# 3. Check iptables FORWARD rules
oc debug node/$NODE -- chroot /host iptables -L FORWARD -n -v | grep 10.244

# 4. Re-run iptables configuration
for node in $(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[*].metadata.name}'); do
  oc debug node/$node -- chroot /host iptables -I FORWARD 1 -s 10.244.0.0/16 -d 10.244.0.0/16 -j ACCEPT
done
```

### After node reboot
iptables rules are temporary and lost on reboot. Re-run:
```bash
./setup-aws-test-environment.sh
# Or manually configure iptables as shown above
```

### MultiNetworkPolicy not found
The setup script only creates networks and pods. MultiNetworkPolicies must be deployed separately:
```bash
# If you have them from a previous ops-translate run:
oc apply -f /path/to/multi-network-policies.yaml

# Or use the existing demo policies:
oc apply -f multi-networkpolicy-install.yaml
```

---

## Customization

### Use Different Namespace
```bash
export NAMESPACE=my-demo
./setup-aws-test-environment.sh
```

### Use Different Kubeconfig
```bash
export KUBECONFIG=~/Downloads/kubeconfig-my-cluster.yaml
./setup-aws-test-environment.sh
```

### Modify Network Subnets
Edit `nad-aws-bridge-test.yaml` and change the subnet ranges:
```yaml
"ipam": {
  "subnet": "10.250.100.0/24",  # Change this
  "rangeStart": "10.250.100.10",
  "rangeEnd": "10.250.100.250",
  "gateway": "10.250.100.1"
}
```

Then update iptables rules to match:
```bash
oc debug node/$NODE -- chroot /host iptables -I FORWARD 1 -s 10.250.0.0/16 -d 10.250.0.0/16 -j ACCEPT
```

---

## Cleanup

### Remove Everything
```bash
# Delete namespace (removes pods, NADs, policies)
oc delete namespace virt-lab

# Note: iptables rules will be lost on next node reboot
# To manually remove them now:
for node in $(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[*].metadata.name}'); do
  oc debug node/$node -- chroot /host iptables -D FORWARD -s 10.244.0.0/16 -d 10.244.0.0/16 -j ACCEPT
done
```

### Remove Only Pods (Keep NADs and Policies)
```bash
oc delete pods -n virt-lab --all
```

### Remove Only Policies (Keep Networks and Pods)
```bash
oc delete multi-networkpolicy -n virt-lab --all
```

---

## Making iptables Rules Permanent

The setup script creates **temporary** iptables rules that are lost on node reboot. For a permanent setup, create a MachineConfig:

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: worker
  name: 99-worker-secondary-network-forwarding
spec:
  config:
    ignition:
      version: 3.2.0
    systemd:
      units:
      - name: secondary-network-forwarding.service
        enabled: true
        contents: |
          [Unit]
          Description=Enable forwarding for secondary networks
          After=network-online.target
          Wants=network-online.target

          [Service]
          Type=oneshot
          ExecStart=/usr/sbin/iptables -I FORWARD 1 -s 10.244.0.0/16 -d 10.244.0.0/16 -j ACCEPT
          RemainAfterExit=yes

          [Install]
          WantedBy=multi-user.target
```

Apply with:
```bash
oc apply -f machineconfig-secondary-network-forwarding.yaml
```

⚠️ **WARNING**: This will trigger a rolling reboot of all worker nodes.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ OpenShift Worker Node                                        │
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ cni-web        │  │ cni-app        │  │ cni-db         │ │
│  │ (Linux Bridge) │  │ (Linux Bridge) │  │ (Linux Bridge) │ │
│  │ 10.244.100.1   │  │ 10.244.150.1   │  │ 10.244.200.1   │ │
│  │                │  │                │  │                │ │
│  │  ┌──────────┐  │  │  ┌──────────┐  │  │  ┌──────────┐  │ │
│  │  │web-server│  │  │  │app-server│  │  │  │db-server │  │ │
│  │  │ .100.11  │  │  │  │ .150.11  │  │  │  │ .200.11  │  │ │
│  │  │ net1     │  │  │  │ net1     │  │  │  │ net1     │  │ │
│  │  └────┬─────┘  │  │  └────┬─────┘  │  │  └────┬─────┘  │ │
│  └───────┼────────┘  └───────┼────────┘  └───────┼────────┘ │
│          │                   │                   │           │
│          └───────────────────┴───────────────────┘           │
│                              │                                │
│                    ┌─────────▼─────────┐                     │
│                    │ iptables FORWARD  │                     │
│                    │ 10.244.0.0/16 → OK│                     │
│                    └───────────────────┘                     │
│                                                               │
│  MultiNetworkPolicy Enforcement (OVN-Kubernetes)             │
│  - web → app: ports 80, 443                                  │
│  - app → db: port 3306                                       │
│  - backup → db: port 22                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## FAQ

**Q: Why use bridge CNI instead of actual AWS ENIs?**

A: Bridge CNI is simpler and sufficient for testing MultiNetworkPolicy functionality. It doesn't require AWS-specific configuration, secondary IPs, or ENI management. For production NSX migrations, you'd use actual VLANs/segments.

**Q: Can I use this on non-AWS OpenShift?**

A: Yes! This setup works on any OpenShift 4.12+ cluster (AWS, bare metal, VMware, etc.). The only AWS-specific part was the original attempt to use ENIs, which we abandoned.

**Q: Do I need separate ENIs for each network?**

A: No. This setup uses a single host interface (br-ex) with virtual bridges. It's purely for testing/demo purposes.

**Q: Will this work with actual NSX segments?**

A: The NetworkAttachmentDefinitions would need to be configured differently for actual NSX (using VLAN interfaces or NSX-T CNI). This setup simulates NSX behavior for testing policy translation.

**Q: How do I test with different workloads?**

A: Modify `test-pods-demo.yaml` to use your own container images and configurations. Just ensure pods have the correct labels and network annotations.

---

## Support

For issues or questions:
- Check `AWS_TEST_ENVIRONMENT_SUMMARY.md` for detailed environment info
- Review OpenShift logs: `oc logs -n openshift-ovn-kubernetes -l app=ovnkube-node`
- Check pod events: `oc describe pod -n virt-lab <pod-name>`

---

## Related Documentation

- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) - Demo walkthrough
- [MULTINETWORK_DEMO.md](MULTINETWORK_DEMO.md) - Full demo guide
- [AWS_TEST_ENVIRONMENT_SUMMARY.md](AWS_TEST_ENVIRONMENT_SUMMARY.md) - Environment details
- [AWS_MULTI_ENI_SETUP.md](AWS_MULTI_ENI_SETUP.md) - Alternative ENI-based approach
