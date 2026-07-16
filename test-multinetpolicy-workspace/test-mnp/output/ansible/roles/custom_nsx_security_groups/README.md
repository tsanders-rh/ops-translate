# Custom Nsx Security Groups Role

## Component

**Name:** NSX Security Groups
**Type:** nsx_security_groups
**Classification:** BLOCKED
**Owner:** SecOps

## Why Not Auto-Translatable

NSX Security Groups support dynamic membership based on VM tags, network properties, and complex criteria. Kubernetes uses label selectors which are fundamentally different. Auto-translation cannot safely map dynamic NSX group membership to static label selectors without NetOps/SecOps review.

## Recommended Ansible Approach

Define a Kubernetes label taxonomy that represents security zones and application tiers. Use Ansible to apply labels to workloads based on the NSX group membership criteria. Reference labels in NetworkPolicy selectors.

## OpenShift/Kubernetes Primitives

- `Pod Labels`
- `Namespace Labels`
- `NetworkPolicy podSelector/namespaceSelector`

## Implementation Steps

1. Document NSX security group membership rules and criteria
2. Design Kubernetes label taxonomy (e.g., security.zone, app.tier)
3. Map NSX group membership to label assignments
4. Create Ansible tasks to label namespaces and workloads
5. Update NetworkPolicy to reference label selectors
6. Require NetOps/SecOps sign-off on label taxonomy and policy mapping

## Required Inputs

- `security_groups`: List of NSX security groups with membership rules
- `label_taxonomy`: Proposed Kubernetes label schema
- `workload_inventory`: List of workloads and their security requirements

## Testing & Validation

Validate label assignments match intended security group membership. Test NetworkPolicy enforcement with labeled pods. Review with SecOps to ensure security boundaries are maintained. Document any gaps in enforcement compared to NSX.

## References

- https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/
- https://docs.openshift.com/container-platform/latest/networking/network_policy/about-network-policy.html

## Evidence

**Location:** nsx-multinetwork-test

## References

- [Gap Analysis Report](../../../intent/gaps.md)
- [OpenShift Documentation](https://docs.openshift.com/)
- [KubeVirt Documentation](https://kubevirt.io/user-guide/)
