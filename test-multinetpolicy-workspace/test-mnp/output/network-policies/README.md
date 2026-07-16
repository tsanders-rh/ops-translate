# NetworkPolicy Manifests

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
