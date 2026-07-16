# Multi-Network Solution for AWS OpenShift Cluster

**Date**: 2026-07-09
**Problem**: Bridge CNI with isolated bridges doesn't work on AWS (no VLAN support)
**Solution**: Use ipvlan L3 mode for proper multi-network support

---

## Why Bridge CNI Failed

### Issues Identified:
1. **Isolated Bridges**: Each NAD created a separate Linux bridge (br-vlan100, br-vlan150, br-vlan200)
2. **No Inter-Bridge Routing**: Bridges couldn't communicate even with iptables FORWARD rules
3. **L2 Connectivity Broken**: Pods couldn't even ping their bridge gateway
4. **AWS VLAN Incompatibility**: AWS doesn't support VLAN trunking between EC2 instances

### Root Cause:
- Bridge CNI expects physical VLAN infrastructure
- On AWS, each EC2 instance is isolated - no Layer 2 connectivity across nodes
- Even on same node, bridge setup was broken (policy DROP in FORWARD chain, possible CNI plugin issues)

---

## Solution: ipvlan L3 Mode

### Why ipvlan L3?

**Advantages**:
- ✅ No bridge creation needed - simpler setup
- ✅ Works on single physical interface (ens5 on AWS)
- ✅ Automatic routing between different subnets
- ✅ Layer 3 routing matches AWS network model
- ✅ Better performance (no bridge overhead)
- ✅ Works across nodes in same VPC

**How it works**:
1. All secondary networks use the same physical interface (ens5)
2. Each network gets its own subnet (10.244.100.0/24, 10.244.150.0/24, etc.)
3. ipvlan L3 mode automatically routes between subnets
4. No gateway IPs needed - routing is handled by ipvlan

---

## Network Design

### Original NSX Subnets (from workflow):
- Web tier: 10.10.100.0/24 (VLAN 100)
- App tier: 10.10.150.0/24 (VLAN 150)
- DB tier: 10.10.200.0/24 (VLAN 200)

### New AWS-Compatible Subnets:
- Web tier: 10.244.100.0/24 (ipvlan L3)
- App tier: 10.244.150.0/24 (ipvlan L3)
- DB tier: 10.244.200.0/24 (ipvlan L3)

**Note**: We use 10.244.0.0/16 to avoid conflicts with:
- OpenShift pod network: 10.128.0.0/14
- OpenShift service network: 172.30.0.0/16
- AWS VPC: 10.0.0.0/19

---

## Deployment Steps

### 1. Delete Old Bridge-Based NADs

```bash
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml delete nad -n virt-lab web-tier-vlan100 app-tier-vlan150 db-tier-vlan200
```

### 2. Deploy New ipvlan L3 NADs

```bash
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml apply -f nad-aws-ipvlan-l3-working.yaml
```

### 3. Restart Pods to Get New Network Interfaces

```bash
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml delete pods -n virt-lab --all
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml apply -f test-pods-demo.yaml  # or your pod definitions
```

### 4. Verify Connectivity

```bash
# Get pod IPs
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab web-server -- ip addr show net1
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab app-server -- ip addr show net1
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab db-server -- ip addr show net1

# Test connectivity
WEB_IP=$(oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab web-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
APP_IP=$(oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab app-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
DB_IP=$(oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab db-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)

# Ping from web to app
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab web-server -- ping -c 2 $APP_IP

# Ping from app to db
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml exec -n virt-lab app-server -- ping -c 2 $DB_IP
```

---

## Important Notes

### Interface Name
The NADs use `"master": "ens5"` assuming AWS EC2 instances. If your nodes use a different interface, update the NADs:

```bash
# Check interface name on your nodes
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml debug node/ip-10-0-27-4.ec2.internal -- chroot /host ip link show

# Common interface names:
# - AWS: ens5, eth0
# - Bare metal: eth1, eno1, ens3
```

### Subnet Changes
The subnets were changed from 10.10.x.0/24 to 10.244.x.0/24 because:
- AWS VPC uses 10.0.0.0/19
- OpenShift uses 10.128.0.0/14
- We need non-overlapping space

If you need to keep the original 10.10.x.0/24 subnets, ensure they're routable in your VPC.

### MultiNetworkPolicy Compatibility
The existing MultiNetworkPolicies should work without changes - they use pod selectors and port numbers, which are independent of the CNI plugin type.

---

## Expected Results

After deploying ipvlan L3 NADs:

### ✅ Working:
- Pods get secondary network interfaces (net1)
- IPs allocated from correct subnets (10.244.100.x, 10.244.150.x, 10.244.200.x)
- Pods can ping each other on secondary networks
- MultiNetworkPolicies can enforce rules
- Cross-node communication works (same VPC)

### ⚠️ Limitations:
- No gateway IP (ipvlan L3 is routed, not bridged)
- Requires all nodes in same VPC subnet
- Cannot communicate with external VLANs (no VLAN tagging)

---

## Testing MultiNetworkPolicy Enforcement

Once connectivity works, test that policies are enforced:

```bash
# Should succeed: web -> app on ports 80,443
oc exec -n virt-lab web-server -- curl -s -o /dev/null -w "%{http_code}\n" http://$APP_IP:8080

# Should fail: web -> db (no policy allows this)
oc exec -n virt-lab web-server -- timeout 3 nc -zv $DB_IP 3306

# Should succeed: app -> db on port 3306
oc exec -n virt-lab app-server -- timeout 3 nc -zv $DB_IP 3306
```

---

## Alternative: macvlan Bridge Mode

If ipvlan L3 doesn't work, try macvlan bridge mode:

```yaml
spec:
  config: |-
    {
      "cniVersion": "0.3.1",
      "type": "macvlan",
      "master": "ens5",
      "mode": "bridge",
      "ipam": {
        "type": "host-local",
        "subnet": "10.244.100.0/24",
        "rangeStart": "10.244.100.10",
        "rangeEnd": "10.244.100.250"
      }
    }
```

macvlan requires promiscuous mode, which may need AWS EC2 settings changes.

---

## Troubleshooting

### Pods fail to start with "Link not found"
- Check interface name (`ens5` vs `eth0`)
- Verify interface exists: `oc debug node/... -- chroot /host ip link show`

### Pods start but can't communicate
- Check if ipvlan kernel module is loaded: `lsmod | grep ipvlan`
- Verify routes in pod: `oc exec ... -- ip route show`
- Check MultiNetworkPolicy isn't blocking: `oc get multi-networkpolicy -n virt-lab`

### Cross-node communication fails
- Ensure both nodes are in same VPC subnet
- Check AWS security groups allow traffic on 10.244.0.0/16
- Verify VPC route table includes 10.244.0.0/16

---

## Success Criteria

- [ ] All 3 NADs deploy successfully
- [ ] All 3 pods have net1 interface with correct IP
- [ ] Pods can ping each other on secondary networks
- [ ] MultiNetworkPolicy blocks unauthorized traffic
- [ ] MultiNetworkPolicy allows authorized traffic

---

**Next Steps**: Deploy the ipvlan L3 NADs and test connectivity!
