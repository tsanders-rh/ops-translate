# NSX Multi-Network Demo - Quick Reference Card

## Setup (One-Time)

```bash
cd nsx-multinetwork-demo
./setup-aws-test-environment.sh
```

---

## Environment Details

| Component | Value |
|-----------|-------|
| **Namespace** | virt-lab |
| **Web Tier** | 10.244.100.0/24 (VLAN 100) |
| **App Tier** | 10.244.150.0/24 (VLAN 150) |
| **DB Tier** | 10.244.200.0/24 (VLAN 200) |

| Pod | IP | Labels |
|-----|-----|--------|
| **web-server** | 10.244.100.11 | app=websecuritygroup, tier=web |
| **app-server** | 10.244.150.11 | app=securitygroup, tier=app |
| **db-server** | 10.244.200.11 | app=dbsecuritygroup, tier=db |

---

## Essential Commands

### View Resources
```bash
# Everything
oc get network-attachment-definitions,pods,multi-networkpolicy -n virt-lab

# Networks only
oc get network-attachment-definitions -n virt-lab

# Policies only
oc get multi-networkpolicy -n virt-lab

# Pods with details
oc get pods -n virt-lab -o wide --show-labels
```

### Test Connectivity
```bash
# Web → App
oc exec -n virt-lab web-server -- ping -c 3 10.244.150.11

# App → DB
oc exec -n virt-lab app-server -- ping -c 3 10.244.200.11

# Web → DB
oc exec -n virt-lab web-server -- ping -c 3 10.244.200.11
```

### Inspect Pod Networks
```bash
# View secondary interface
oc exec -n virt-lab web-server -- ip addr show net1

# View routing table
oc exec -n virt-lab web-server -- ip route show

# View all interfaces
oc exec -n virt-lab web-server -- ip addr show
```

### Check Policy Details
```bash
# View policy YAML
oc get multi-networkpolicy web-tier-vlan100-allow-web-to-app -n virt-lab -o yaml

# List policies with their networks
oc get multi-networkpolicy -n virt-lab \
  -o custom-columns=NAME:.metadata.name,NETWORK:.metadata.annotations.'k8s\.v1\.cni\.cncf\.io/policy-for'
```

---

## Troubleshooting

### Pods Not Starting
```bash
# Check pod status
oc get pods -n virt-lab

# View pod events
oc describe pod web-server -n virt-lab

# Check NADs exist
oc get network-attachment-definitions -n virt-lab
```

### Connectivity Failed
```bash
# Re-apply iptables rules
NODES=$(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[*].metadata.name}')
for node in $NODES; do
  oc debug node/$node -- chroot /host iptables -I FORWARD 1 -s 10.244.0.0/16 -d 10.244.0.0/16 -j ACCEPT
done

# Check pod IPs
oc exec -n virt-lab web-server -- ip -4 addr show net1 | grep inet
```

### Recreate Pods
```bash
oc delete pods -n virt-lab --all
oc apply -f test-pods-demo.yaml
oc wait --for=condition=ready pod --all -n virt-lab --timeout=90s
```

---

## Cleanup

```bash
# Remove everything
./cleanup-aws-test-environment.sh

# Or manually
oc delete namespace virt-lab
```

---

## Demo Flow

1. **Show NSX workflow** → ops-translate input
2. **Run analysis** → `ops-translate analyze`
3. **Show translation** → `ops-translate translate`
4. **Deploy resources** → `oc apply -f output/k8s/`
5. **Test connectivity** → `oc exec ... ping ...`
6. **Show policies** → `oc get multi-networkpolicy`
7. **Demonstrate enforcement** → Test allowed/blocked traffic

---

## File Locations

```
nsx-multinetwork-demo/
├── setup-aws-test-environment.sh   ← Run this to setup
├── cleanup-aws-test-environment.sh ← Run this to cleanup
├── nad-aws-bridge-test.yaml        ← Network configs
├── test-pods-demo.yaml              ← Pod specs
├── README-AWS-SETUP.md              ← Full documentation
└── QUICK-REFERENCE.md               ← This file
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| "MultiNetworkPolicy not enabled" | `oc patch network.operator.openshift.io cluster --type=merge -p '{"spec":{"useMultiNetworkPolicy":true}}'` |
| Pods stuck in ContainerCreating | Check NADs exist: `oc get network-attachment-definitions -n virt-lab` |
| Ping timeout | Re-run iptables config (see Troubleshooting section) |
| After node reboot | Re-run `./setup-aws-test-environment.sh` |

---

## Prerequisites Checklist

- [ ] OpenShift 4.12+ on AWS
- [ ] Cluster admin access
- [ ] MultiNetworkPolicy enabled
- [ ] `oc` CLI installed
- [ ] Logged into cluster

---

## Quick Health Check

```bash
# All-in-one health check
oc get network-attachment-definitions,pods,multi-networkpolicy -n virt-lab && \
  echo "Testing connectivity..." && \
  oc exec -n virt-lab web-server -- ping -c 2 10.244.150.11 > /dev/null 2>&1 && \
  echo "✓ Environment is healthy" || echo "❌ Connectivity issue"
```
