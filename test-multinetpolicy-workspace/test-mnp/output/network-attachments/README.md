# NetworkAttachmentDefinition Manifests

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
