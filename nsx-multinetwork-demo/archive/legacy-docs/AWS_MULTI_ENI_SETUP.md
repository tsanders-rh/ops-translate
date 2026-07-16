# AWS Multi-ENI Setup Guide for Multi-Network Demo

**Goal**: Enable multi-network pod communication on your existing AWS OpenShift cluster by adding secondary ENIs.

**Time Required**: 2-3 hours
**Cost**: ~$5-10/month for additional ENIs
**Difficulty**: Medium (requires AWS console + OpenShift knowledge)

---

## Prerequisites

- ✅ Existing OpenShift cluster on AWS (your tsanders-virt-demo cluster)
- ✅ AWS Console access with EC2 permissions
- ✅ Cluster admin access (`oc` CLI configured)
- ✅ 2 worker nodes minimum

---

## Architecture Overview

### Current State
```
Worker Node (ip-10-0-27-4.ec2.internal)
├── enp126s0 (10.0.27.4) - Primary NIC
│   ├── Used by OVN-Kubernetes
│   └── Cannot use for secondary networks
```

### Target State
```
Worker Node (ip-10-0-27-4.ec2.internal)
├── enp126s0 (10.0.27.4) - Primary NIC (OVN)
├── eth1 (10.10.100.x) - Secondary ENI for Web Tier
├── eth2 (10.10.150.x) - Secondary ENI for App Tier
└── eth3 (10.10.200.x) - Secondary ENI for DB Tier
```

---

## Step 1: Create VPC Subnets (15 minutes)

### 1.1 Find Your VPC

```bash
# Get cluster VPC ID
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*tsanders-virt-demo*" \
  --query 'Reservations[0].Instances[0].VpcId' \
  --output text
```

Save the VPC ID (e.g., `vpc-0123456789abcdef0`)

### 1.2 Get Availability Zone

```bash
# Get worker node AZ
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*tsanders-virt-demo-worker*" \
  --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' \
  --output text
```

### 1.3 Create Subnets (AWS Console)

**Navigate to**: VPC → Subnets → Create subnet

Create 3 new subnets:

| Name | CIDR | AZ | Purpose |
|------|------|-----|---------|
| nsx-demo-web-tier | 10.10.100.0/24 | (your AZ) | Web Tier VLAN 100 |
| nsx-demo-app-tier | 10.10.150.0/24 | (your AZ) | App Tier VLAN 150 |
| nsx-demo-db-tier | 10.10.200.0/24 | (your AZ) | DB Tier VLAN 200 |

**Important**:
- Use the same VPC as your cluster
- Use the same AZ as your worker nodes
- Ensure CIDRs don't overlap with existing subnets (10.0.0.0/19)

---

## Step 2: Create Security Group (10 minutes)

### 2.1 Create Security Group

**Navigate to**: EC2 → Security Groups → Create security group

**Settings**:
- Name: `nsx-demo-secondary-networks`
- VPC: (your cluster VPC)
- Description: "Allow inter-pod communication on secondary networks"

**Inbound Rules**:
| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| All traffic | All | All | 10.10.0.0/16 | Allow all traffic between secondary networks |
| All traffic | All | All | sg-xxxxx (this SG) | Allow traffic within same SG |

**Outbound Rules**:
| Type | Protocol | Port Range | Destination | Description |
|------|----------|-------------|-------------|-------------|
| All traffic | All | All | 0.0.0.0/0 | Allow all outbound |

Save the security group ID (e.g., `sg-0123456789abcdef0`)

---

## Step 3: Attach ENIs to Worker Nodes (20 minutes)

### 3.1 Get Worker Node Instance IDs

```bash
# List worker nodes
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*tsanders-virt-demo-worker*" \
  --query 'Reservations[*].Instances[*].[InstanceId,PrivateIpAddress,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

Note the instance IDs for your 2 worker nodes.

### 3.2 Create and Attach ENIs (AWS Console)

**For EACH worker node**, create 3 ENIs:

**Navigate to**: EC2 → Network Interfaces → Create network interface

**Web Tier ENI** (repeat for each worker):
- Description: `nsx-demo-web-tier-worker1`
- Subnet: `nsx-demo-web-tier` (10.10.100.0/24)
- Private IP: Auto-assign
- Security groups: `nsx-demo-secondary-networks`
- Click **Create**

**Attach to instance**:
1. Select the created ENI
2. Actions → Attach
3. Instance: (select worker node)
4. Device index: 1
5. Click **Attach**

**Repeat for**:
- App Tier: Subnet `nsx-demo-app-tier`, Device index 2
- DB Tier: Subnet `nsx-demo-db-tier`, Device index 3

**Result**: Each worker should have 4 ENIs total:
- eth0/enp126s0: Primary (10.0.x.x)
- eth1: Web tier (10.10.100.x)
- eth2: App tier (10.10.150.x)
- eth3: DB tier (10.10.200.x)

---

## Step 4: Configure ENIs on Worker Nodes (30 minutes)

### 4.1 Verify ENIs Are Visible

```bash
# SSH to worker node
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml debug node/ip-10-0-27-4.ec2.internal

# Inside debug pod
chroot /host bash
ip link show
```

You should see: `eth1`, `eth2`, `eth3` (or similar names)

### 4.2 Create NetworkManager Configurations

We need to ensure ENIs come up automatically. Create NM config for each ENI:

```bash
# Still in debug pod chroot
cat > /etc/NetworkManager/system-connections/eth1.nmconnection <<EOF
[connection]
id=eth1
type=ethernet
interface-name=eth1
autoconnect=true

[ipv4]
method=auto
EOF

chmod 600 /etc/NetworkManager/system-connections/eth1.nmconnection

# Repeat for eth2, eth3
```

### 4.3 Restart NetworkManager

```bash
systemctl restart NetworkManager
sleep 5
ip addr show eth1  # Should have IP from 10.10.100.0/24
ip addr show eth2  # Should have IP from 10.10.150.0/24
ip addr show eth3  # Should have IP from 10.10.200.0/24
```

### 4.4 Repeat for All Worker Nodes

Exit debug pod and repeat Steps 4.1-4.3 for each worker node.

---

## Step 5: Deploy Updated NetworkAttachmentDefinitions (10 minutes)

### 5.1 Create NADs for Secondary ENIs

Create file: `nad-aws-multi-eni.yaml`

```yaml
---
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: web-tier-vlan100
  namespace: virt-lab
  labels:
    translated-from: nsx-segment
    vlan-id: "100"
spec:
  config: |-
    {
      "cniVersion": "0.3.1",
      "type": "ipvlan",
      "master": "eth1",
      "mode": "l2",
      "ipam": {
        "type": "host-local",
        "subnet": "10.10.100.0/24",
        "rangeStart": "10.10.100.10",
        "rangeEnd": "10.10.100.250"
      }
    }
---
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: app-tier-vlan150
  namespace: virt-lab
  labels:
    translated-from: nsx-segment
    vlan-id: "150"
spec:
  config: |-
    {
      "cniVersion": "0.3.1",
      "type": "ipvlan",
      "master": "eth2",
      "mode": "l2",
      "ipam": {
        "type": "host-local",
        "subnet": "10.10.150.0/24",
        "rangeStart": "10.10.150.10",
        "rangeEnd": "10.10.150.250"
      }
    }
---
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: db-tier-vlan200
  namespace: virt-lab
  labels:
    translated-from: nsx-segment
    vlan-id: "200"
spec:
  config: |-
    {
      "cniVersion": "0.3.1",
      "type": "ipvlan",
      "master": "eth3",
      "mode": "l2",
      "ipam": {
        "type": "host-local",
        "subnet": "10.10.200.0/24",
        "rangeStart": "10.10.200.10",
        "rangeEnd": "10.10.200.250"
      }
    }
```

### 5.2 Deploy

```bash
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml delete pods -n virt-lab --all
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml apply -f nad-aws-multi-eni.yaml
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml apply -f test-pods-demo.yaml
```

---

## Step 6: Test Connectivity (15 minutes)

### 6.1 Wait for Pods

```bash
oc --kubeconfig ~/Downloads/kubeconfig-tsanders-virt-demo.yaml wait --for=condition=ready pod/web-server pod/app-server pod/db-server -n virt-lab --timeout=60s
```

### 6.2 Verify Secondary Interfaces

```bash
# Check web-server
oc exec -n virt-lab web-server -- ip addr show net1
# Should show IP from 10.10.100.0/24

# Check app-server
oc exec -n virt-lab app-server -- ip addr show net1
# Should show IP from 10.10.150.0/24

# Check db-server
oc exec -n virt-lab db-server -- ip addr show net1
# Should show IP from 10.10.200.0/24
```

### 6.3 Test Pod-to-Pod Connectivity

```bash
# Get IPs
WEB_IP=$(oc exec -n virt-lab web-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
APP_IP=$(oc exec -n virt-lab app-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
DB_IP=$(oc exec -n virt-lab db-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)

echo "Web: $WEB_IP"
echo "App: $APP_IP"
echo "DB: $DB_IP"

# Test connectivity
echo "Testing web → app:"
oc exec -n virt-lab web-server -- ping -c 3 $APP_IP

echo "Testing app → db:"
oc exec -n virt-lab app-server -- ping -c 3 $DB_IP

echo "Testing web → db:"
oc exec -n virt-lab web-server -- ping -c 3 $DB_IP
```

**Expected**: All pings should succeed! ✅

---

## Step 7: Test MultiNetworkPolicy Enforcement (20 minutes)

Your MultiNetworkPolicies should already be deployed. Now test that they actually enforce rules:

### 7.1 Verify Policies

```bash
oc get multi-networkpolicy -n virt-lab
```

Should show:
- `web-tier-vlan100-allow-web-to-app`
- `app-tier-vlan150-allow-app-to-db`
- `db-tier-vlan200-allow-db-backup`

### 7.2 Test Policy Enforcement

**Test 1: Allowed traffic (web → app on port 80)**
```bash
oc exec -n virt-lab web-server -- curl -s -o /dev/null -w "%{http_code}\n" http://$APP_IP:8080
# Should succeed (200 or connection)
```

**Test 2: Blocked traffic (web → db, no policy allows this)**
```bash
oc exec -n virt-lab web-server -- timeout 3 nc -zv $DB_IP 3306
# Should timeout/fail (blocked by policy)
```

**Test 3: Allowed traffic (app → db on port 3306)**
```bash
oc exec -n virt-lab app-server -- timeout 3 nc -zv $DB_IP 3306
# Should succeed
```

---

## Troubleshooting

### ENIs not showing up in OS

```bash
# Check if AWS recognized the attachment
aws ec2 describe-network-interfaces --filters "Name=attachment.instance-id,Values=i-xxxxx"

# Reboot worker node (drastic but effective)
aws ec2 reboot-instances --instance-ids i-xxxxx
```

### Pods fail with "Link not found"

Check interface names:
```bash
oc debug node/... -- chroot /host ip link show
```

Update NAD `master` field to match actual interface name (might be `ens6`, `ens7` instead of `eth1`, `eth2`)

### Connectivity works but MultiNetworkPolicy doesn't block

Check pod labels match policy selectors:
```bash
oc get pods -n virt-lab --show-labels
oc get multi-networkpolicy web-tier-vlan100-allow-web-to-app -o yaml
```

---

## Cost Estimation

- **ENIs**: $0.005/hour × 6 ENIs (3 per worker × 2 workers) = ~$2.16/month
- **Data transfer**: Minimal (internal VPC)
- **Total**: ~$5-10/month

**To clean up and avoid costs**: Detach and delete ENIs when not demoing.

---

## Success Criteria

- [ ] All worker nodes have 4 network interfaces
- [ ] All 3 NADs deploy successfully
- [ ] All 3 pods start with net1 interfaces
- [ ] Pods get IPs from correct subnets (10.10.x.0/24)
- [ ] Pod-to-pod ping works on secondary networks
- [ ] MultiNetworkPolicy blocks unauthorized traffic
- [ ] MultiNetworkPolicy allows authorized traffic

---

## Next Steps

Once working:
1. Document your demo flow
2. Take screenshots of working connectivity
3. Record video for future reference
4. Update your demo scripts

**You now have a production-like multi-network OpenShift setup!** 🎉
