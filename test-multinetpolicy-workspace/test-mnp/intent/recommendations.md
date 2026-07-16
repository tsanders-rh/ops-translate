# Expert-Guided Migration Recommendations

This document provides expert guidance for workflow components that cannot be safely auto-migrated.

**Important**: These are recommendations, not drop-in replacements. Each recommendation requires review, testing, and validation before production use.

## Summary

Total recommendations: 2

### By Team

- **NetOps**: 1 recommendation(s)
- **SecOps**: 1 recommendation(s)

---

## NSX Security Groups

**Component Type:** `nsx_security_group`  
**Owner:** SecOps  

### Why Not Auto-Translatable

NSX Security Groups support dynamic membership based on VM tags, network properties, and complex criteria. Kubernetes uses label selectors which are fundamentally different. Auto-translation cannot safely map dynamic NSX group membership to static label selectors without NetOps/SecOps review.

### Recommended Ansible Approach

Define a Kubernetes label taxonomy that represents security zones and application tiers. Use Ansible to apply labels to workloads based on the NSX group membership criteria. Reference labels in NetworkPolicy selectors.

### OpenShift/Kubernetes Primitives

- `Pod Labels`
- `Namespace Labels`
- `NetworkPolicy podSelector/namespaceSelector`

### Implementation Steps

1. Document NSX security group membership rules and criteria
2. Design Kubernetes label taxonomy (e.g., security.zone, app.tier)
3. Map NSX group membership to label assignments
4. Create Ansible tasks to label namespaces and workloads
5. Update NetworkPolicy to reference label selectors
6. Require NetOps/SecOps sign-off on label taxonomy and policy mapping

### Required Inputs

- `security_groups`: List of NSX security groups with membership rules
- `label_taxonomy`: Proposed Kubernetes label schema
- `workload_inventory`: List of workloads and their security requirements

### Testing & Validation

Validate label assignments match intended security group membership. Test NetworkPolicy enforcement with labeled pods. Review with SecOps to ensure security boundaries are maintained. Document any gaps in enforcement compared to NSX.

### References

- https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/
- https://docs.openshift.com/container-platform/latest/networking/network_policy/about-network-policy.html

### Ansible Scaffolding

A role stub has been generated at: `roles/custom_nsx_security_groups/`

---

## NSX Distributed Firewall

**Component Type:** `nsx_firewall`  
**Owner:** NetOps  

### Why Not Auto-Translatable

NSX Distributed Firewall provides L7 filtering, stateful inspection, and micro-segmentation features that cannot be directly mapped to Kubernetes NetworkPolicy. Auto-translation would lose critical security enforcement and create a false sense of equivalence.

### Recommended Ansible Approach

Use `kubernetes.core.k8s` module to create NetworkPolicy resources with an allow-list approach. For advanced requirements, consider Calico GlobalNetworkPolicy or OpenShift Egress Firewall.

### OpenShift/Kubernetes Primitives

- `NetworkPolicy (Kubernetes native)`
- `EgressFirewall (OpenShift)`
- `GlobalNetworkPolicy (Calico)`

### Implementation Steps

1. Analyze NSX firewall rules to extract source/destination patterns
2. Define Kubernetes label taxonomy for pod selectors
3. Create NetworkPolicy manifests with allow-list ingress/egress rules
4. Document unsupported features (L7, stateful inspection) for NetOps review
5. Test policies in dev environment with realistic traffic patterns
6. Implement monitoring for policy violations and denied connections

### Required Inputs

- `firewall_rules`: List of NSX firewall rules with source/dest/port/protocol
- `namespace`: Target namespace for NetworkPolicy
- `pod_labels`: Label selectors for affected pods

### Testing & Validation

Test with pod-to-pod traffic in dev cluster. Verify both allowed and denied traffic. Use `kubectl exec` to test connectivity between pods. Monitor CNI logs for policy enforcement. Compare behavior against NSX firewall logs to identify gaps.

### References

- https://docs.openshift.com/container-platform/latest/networking/network_policy/about-network-policy.html
- https://kubernetes.io/docs/concepts/services-networking/network-policies/
- https://docs.tigera.io/calico/latest/network-policy/

### Ansible Scaffolding

A role stub has been generated at: `roles/custom_nsx_firewall_migration/`

---
