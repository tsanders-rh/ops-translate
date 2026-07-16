# MultiNetworkPolicy Manifests (OVN-Kubernetes)

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
