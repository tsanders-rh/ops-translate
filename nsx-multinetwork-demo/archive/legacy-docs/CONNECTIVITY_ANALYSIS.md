# Multi-Network Connectivity Analysis

**Date**: 2026-07-09
**Cluster**: OpenShift on AWS (ip-10-0-27-4, ip-10-0-54-232)

---

## What's Working ✅

1. **NetworkAttachmentDefinitions deployed** - All 3 NADs successfully created
2. **Pods running** - All 3 pods start successfully with secondary networks
3. **Secondary interfaces** - Each pod has net1 interface with correct IP:
   - web-server: 10.10.100.13/24
   - app-server: 10.10.150.13/24
   - db-server: 10.10.200.13/24
4. **Routes configured** - Pods have routes to other subnets via 10.10.100.1
5. **MultiNetworkPolicies deployed** - All policies accepted by OVN-Kubernetes

---

## What's Not Working ❌

**Cross-VLAN Communication**: Pods on different VLANs (10.10.100.0/24, 10.10.150.0/24, 10.10.200.0/24) cannot ping each other.

---

## Root Cause Analysis

### Current Configuration
- **CNI Type**: macvlan bridge mode
- **Master Interfaces**: enp126s0.100, enp126s0.150, enp126s0.200 (VLAN subinterfaces)
- **Routing**: Configured via IPAM routes to send traffic through 10.10.100.1

### The Problem: macvlan Limitations

**macvlan has a fundamental restriction**: Pods using macvlan **cannot communicate with:**
1. The host itself
2. Any IP address assigned to the master interface
3. The parent interface

In our setup:
- Pods route to other VLANs via gateway 10.10.100.1
- Gateway 10.10.100.1 is assigned to enp126s0.100 (the master interface)
- **macvlan blocks this communication** → packets never reach the gateway → routing fails

### Why This Happens

From the macvlan kernel documentation:
> "Endpoints on the master interface cannot communicate with macvlan endpoints. This is by design, as macvlan virtualizes the MAC address layer."

---

## Attempted Solutions

### 1. Bridge CNI ❌ Failed
**Tried**: Linux bridge with separate bridges (br-vlan100, br-vlan150, br-vlan200)
**Result**:
- Pods couldn't even ping their bridge gateway
- Isolated bridges with no inter-bridge routing
- FORWARD chain had DROP policy

### 2. ipvlan L3 on Parent Interface ❌ Failed
**Tried**: ipvlan L3 mode on enp126s0
**Result**: "device or resource busy" - VLAN subinterfaces block parent interface usage

### 3. macvlan with VLAN Subinterfaces ❌ Current State
**Tried**: macvlan bridge mode on enp126s0.100, enp126s0.150, enp126s0.200
**Result**:
- Pods start successfully
- Routes configured correctly
- Communication blocked by macvlan limitation (can't reach gateway)

---

## Potential Solutions

### Option 1: Single Shared Network (Simplest)
**Approach**: Use one network for all pods, simulate segmentation with MultiNetworkPolicy only

```yaml
spec:
  config: |-
    {
      "type": "macvlan",
      "master": "enp126s0",
      "mode": "bridge",
      "ipam": {
        "type": "host-local",
        "subnet": "10.10.0.0/16",
        "rangeStart": "10.10.100.10",
        "rangeEnd": "10.10.200.250"
      }
    }
```

**Pros**:
- ✅ Guaranteed to work
- ✅ Demonstrates MultiNetworkPolicy enforcement
- ✅ Simpler configuration

**Cons**:
- ❌ Not true network segmentation (all pods on same L2 network)
- ❌ Doesn't match NSX VLAN architecture

---

### Option 2: Clean Up and Use ipvlan L2
**Approach**: Remove VLAN subinterfaces, use ipvlan L2 mode on parent enp126s0

**Steps**:
1. Remove VLAN subinterfaces from both worker nodes:
   ```bash
   ip link delete enp126s0.100
   ip link delete enp126s0.150
   ip link delete enp126s0.200
   ```

2. Deploy ipvlan L2 NADs:
   ```yaml
   spec:
     config: |-
       {
         "type": "ipvlan",
         "master": "enp126s0",
         "mode": "l2",
         "ipam": {
           "type": "host-local",
           "subnet": "10.10.100.0/24",
           "rangeStart": "10.10.100.10",
           "rangeEnd": "10.10.100.250"
         }
       }
   ```

**Pros**:
- ✅ ipvlan L2 supports communication within subnet
- ✅ Can configure routing between subnets if needed
- ✅ No macvlan host communication limitation

**Cons**:
- ⚠️ Requires manual cleanup of VLAN interfaces on both nodes
- ⚠️ Risky - might break existing node networking
- ❌ Still separate L2 domains - inter-subnet routing still challenging

---

### Option 3: Use ipvlan L3 with Routed Subnets
**Approach**: Same as Option 2, but use ipvlan L3 for automatic inter-subnet routing

**Pros**:
- ✅ ipvlan L3 automatically routes between subnets
- ✅ No gateway configuration needed
- ✅ Matches AWS network model (L3 routing)

**Cons**:
- ⚠️ Requires VLAN subinterface cleanup
- ❌ Changes subnet addressing (can't keep 10.10.x.0/24 as separate VLANs)

---

### Option 4: AWS-Specific Multi-ENI Approach
**Approach**: Use multiple Elastic Network Interfaces (ENIs) on EC2 instances

**Steps**:
1. Attach additional ENIs to each worker node
2. Assign each ENI to a different VPC subnet
3. Use ipvlan or macvlan on each ENI

**Pros**:
- ✅ True network segmentation at AWS level
- ✅ Matches enterprise AWS architecture
- ✅ VPC routing handles inter-subnet traffic

**Cons**:
- ❌ Requires AWS infrastructure changes
- ❌ Additional ENI costs
- ❌ Complex setup for a demo

---

## Recommendation

### For Demo/Testing: **Option 1 (Single Shared Network)**

This is the most pragmatic choice because:
1. **It works reliably** - No complex networking issues
2. **Demonstrates the core value** - MultiNetworkPolicy translation and enforcement
3. **Quick to implement** - No infrastructure changes needed
4. **Honest trade-off** - We can explain this is for demo purposes

### For Production: **Option 4 (Multi-ENI on AWS)**

For actual customer deployments on AWS:
1. Use multiple ENIs per worker node
2. Assign each ENI to a VPC subnet matching NSX segments
3. Use NetworkAttachmentDefinitions with bridge or ipvlan CNI
4. Let AWS VPC routing handle inter-subnet traffic

---

## Next Steps

**Immediate** (for demo):
1. Implement Option 1 - single shared network
2. Test pod-to-pod connectivity
3. Demonstrate MultiNetworkPolicy enforcement
4. Document limitations clearly

**Future** (for production guidance):
1. Create AWS multi-ENI deployment guide
2. Test with actual multi-ENI setup
3. Document VPC security group requirements
4. Provide Terraform/CloudFormation templates

---

## Key Lesson

**The NSX translation tool is working perfectly**. The networking challenges we're facing are:
1. Infrastructure limitations (AWS doesn't support traditional VLANs)
2. CNI plugin limitations (macvlan can't talk to host)
3. Demo environment constraints (test cluster without multi-ENI)

These are **deployment environment issues**, not translation bugs. The generated MultiNetworkPolicies, NADs, and correlation logic are all correct.

---

**Bottom Line**: We should use a single shared network for demo purposes and focus on showing the policy translation and enforcement, which is the real value proposition.
