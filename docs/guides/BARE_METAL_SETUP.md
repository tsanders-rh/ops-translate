# Bare Metal OpenShift Setup for NSX MultiNetworkPolicy Demo

**Target Environment**: Virtualized or bare metal OpenShift with VLAN-capable networking
**Use Case**: Demonstrating NSX-to-Kubernetes translation with actual VLAN segmentation

---

## Prerequisites

- Multi-node OpenShift cluster on bare metal or VMs
- Hypervisor/network supporting VLAN trunking (KVM, VMware, OpenStack, etc.)
- Secondary network interface on worker nodes (eth1, ens3, etc.)
- VLANs 100, 150, 200 available on upstream network

---

## Network Infrastructure Setup

### Option A: KVM/libvirt

**1. Create trunk network definition**:
```xml
<!-- /tmp/vlan-trunk.xml -->
<network>
  <name>vlan-trunk</name>
  <forward mode='bridge'/>
  <bridge name='br-trunk'/>
  <virtualport type='openvswitch'/>
  <portgroup name='trunk-all'>
    <vlan trunk='yes'>
      <tag id='100'/>
      <tag id='150'/>
      <tag id='200'/>
    </vlan>
  </portgroup>
</network>
```

**2. Define and start**:
```bash
virsh net-define /tmp/vlan-trunk.xml
virsh net-start vlan-trunk
virsh net-autostart vlan-trunk
```

**3. Attach to worker VMs**:
```bash
# For each worker VM
virsh attach-interface worker-1 network vlan-trunk --model virtio --config --live
```

### Option B: VMware

**1. Create port group** for each VLAN:
- VLAN 100: Port group "NSX-Web-Tier-100"
- VLAN 150: Port group "NSX-App-Tier-150"
- VLAN 200: Port group "NSX-DB-Tier-200"

**2. Add network adapter** to each worker VM:
- VM Settings → Add Hardware → Network Adapter
- Connect to appropriate port group
- VLAN tagging: Enabled (guest)

### Option C: OpenStack

```bash
# Create provider networks for each VLAN
openstack network create --provider-network-type vlan \
  --provider-physical-network physnet1 \
  --provider-segment 100 nsx-web-tier

openstack network create --provider-network-type vlan \
  --provider-physical-network physnet1 \
  --provider-segment 150 nsx-app-tier

openstack network create --provider-network-type vlan \
  --provider-physical-network physnet1 \
  --provider-segment 200 nsx-db-tier

# Create subnets
openstack subnet create --network nsx-web-tier \
  --subnet-range 10.10.100.0/24 nsx-web-subnet

# Attach to worker instances
openstack server add network worker-1 nsx-web-tier
```

---

## Worker Node Configuration

On **each OpenShift worker node**, create VLAN interfaces:

### Method 1: NetworkManager (RHEL/CentOS/Fedora)

```bash
# SSH to each worker node
ssh core@worker-1.example.com

# Become root
sudo -i

# Create VLAN 100
nmcli connection add type vlan \
  con-name vlan100 \
  dev eth1 \
  id 100

# Don't assign IP (Multus will handle it)
nmcli connection modify vlan100 \
  ipv4.method disabled \
  ipv6.method disabled

# Bring up interface
nmcli connection up vlan100

# Repeat for VLANs 150 and 200
nmcli connection add type vlan con-name vlan150 dev eth1 id 150
nmcli connection modify vlan150 ipv4.method disabled ipv6.method disabled
nmcli connection up vlan150

nmcli connection add type vlan con-name vlan200 dev eth1 id 200
nmcli connection modify vlan200 ipv4.method disabled ipv6.method disabled
nmcli connection up vlan200

# Verify
ip link show | grep vlan
# Should see: eth1.100@eth1, eth1.150@eth1, eth1.200@eth1
```

### Method 2: Manual (ip command)

```bash
# Create VLAN interfaces
ip link add link eth1 name eth1.100 type vlan id 100
ip link add link eth1 name eth1.150 type vlan id 150
ip link add link eth1 name eth1.200 type vlan id 200

# Bring up interfaces
ip link set eth1.100 up
ip link set eth1.150 up
ip link set eth1.200 up

# Verify
ip -d link show | grep vlan
```

**Make persistent** (add to `/etc/sysconfig/network-scripts/` or `/etc/network/interfaces`).

### Method 3: MachineConfig (OpenShift Native)

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: worker
  name: 99-worker-vlan-interfaces
spec:
  config:
    ignition:
      version: 3.2.0
    storage:
      files:
      - path: /etc/NetworkManager/dispatcher.d/20-vlan-setup
        mode: 0755
        contents:
          inline: |
            #!/bin/bash
            # Create VLAN interfaces on eth1
            nmcli connection add type vlan con-name vlan100 dev eth1 id 100 || true
            nmcli connection modify vlan100 ipv4.method disabled ipv6.method disabled
            nmcli connection up vlan100 || true

            nmcli connection add type vlan con-name vlan150 dev eth1 id 150 || true
            nmcli connection modify vlan150 ipv4.method disabled ipv6.method disabled
            nmcli connection up vlan150 || true

            nmcli connection add type vlan con-name vlan200 dev eth1 id 200 || true
            nmcli connection modify vlan200 ipv4.method disabled ipv6.method disabled
            nmcli connection up vlan200 || true
```

Apply:
```bash
oc apply -f vlan-machineconfig.yaml
# Nodes will reboot to apply changes
```

---

## Configure Generated NetworkAttachmentDefinitions

### Option A: Manual Edit

Edit the generated NADs in `output/network-attachments/`:

```bash
cd output/network-attachments/

# Edit each NAD file
vi web-tier-vlan100.yaml
```

**Find and replace**:
```yaml
# BEFORE (generated with TODOs):
spec:
  config: |-
    {
      "cniVersion": "0.3.1",
      "type": "macvlan",
      "master": "TODO: Specify parent interface (e.g., eth1, ens3)",
      "vlan": 100,
      "mode": "bridge",
      "ipam": {
        "type": "whereabouts",
        "range": "TODO: Configure subnet CIDR (e.g., 10.10.10.0/24)",
        "range_start": "TODO: Start IP (e.g., 10.10.10.10)",
        "range_end": "TODO: End IP (e.g., 10.10.10.250)",
        "gateway": "TODO: Gateway IP (e.g., 10.10.10.1)"
      }
    }

# AFTER (configured for bare metal):
spec:
  config: |-
    {
      "cniVersion": "0.3.1",
      "type": "macvlan",
      "master": "eth1.100",              # ← VLAN interface you created
      "mode": "bridge",
      "ipam": {
        "type": "whereabouts",
        "range": "10.10.100.0/24",       # ← From NSX analysis (intent/analysis.vrealize.json)
        "rangeStart": "10.10.100.10",
        "rangeEnd": "10.10.100.250",
        "gateway": "10.10.100.1"
      }
    }
```

Repeat for `app-tier-vlan150.yaml` and `db-tier-vlan200.yaml`.

### Option B: Automated Script

```bash
#!/bin/bash
# configure-nads-bare-metal.sh

# Get NSX subnet info from analysis
WEB_SUBNET=$(jq -r '.nsx_operations.segments[] | select(.segment_name == "Web-Tier-VLAN100") | .subnets[0]' ../intent/analysis.vrealize.json)
APP_SUBNET=$(jq -r '.nsx_operations.segments[] | select(.segment_name == "App-Tier-VLAN150") | .subnets[0]' ../intent/analysis.vrealize.json)
DB_SUBNET=$(jq -r '.nsx_operations.segments[] | select(.segment_name == "DB-Tier-VLAN200") | .subnets[0]' ../intent/analysis.vrealize.json)

# Configure each NAD
for file in output/network-attachments/*.yaml; do
  # Skip README
  [[ "$file" == *"README"* ]] && continue

  # Replace TODOs with actual values
  sed -i \
    -e 's|"master": "TODO.*"|"master": "eth1.100"|g' \
    -e 's|"range": "TODO.*"|"range": "'"$WEB_SUBNET"'"|g' \
    -e 's|"range_start": "TODO.*"|"rangeStart": "10.10.100.10"|g' \
    -e 's|"range_end": "TODO.*"|"rangeEnd": "10.10.100.250"|g' \
    -e 's|"gateway": "TODO.*"|"gateway": "10.10.100.1"|g' \
    "$file"
done

echo "NADs configured for bare metal deployment"
```

---

## Install Whereabouts IPAM

Whereabouts provides dynamic IP allocation for secondary networks:

```bash
oc apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/whereabouts/master/doc/daemonset-install.yaml

# Verify installation
oc get pods -n kube-system | grep whereabouts
```

---

## Deploy and Test

### 1. Deploy NetworkAttachmentDefinitions

```bash
cd output/network-attachments/
oc apply -f . -n virt-lab

# Verify
oc get network-attachment-definitions -n virt-lab
```

### 2. Deploy MultiNetworkPolicies

```bash
cd ../multi-network-policies/
oc apply -f . -n virt-lab

# Verify
oc get multi-networkpolicy.k8s.cni.cncf.io -n virt-lab
```

### 3. Deploy NetworkPolicies

```bash
cd ../network-policies/
oc apply -f . -n virt-lab

# Verify
oc get networkpolicies -n virt-lab
```

### 4. Deploy Test Pods

```bash
cat > test-pods.yaml <<'EOF'
---
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  namespace: virt-lab
  labels:
    app: websecuritygroup
  annotations:
    k8s.v1.cni.cncf.io/networks: web-tier-vlan100
spec:
  containers:
  - name: nginx
    image: nginxinc/nginx-unprivileged:alpine
    ports:
    - containerPort: 80
    - containerPort: 443
---
apiVersion: v1
kind: Pod
metadata:
  name: app-server
  namespace: virt-lab
  labels:
    app: securitygroup
  annotations:
    k8s.v1.cni.cncf.io/networks: app-tier-vlan150
spec:
  containers:
  - name: nginx
    image: nginxinc/nginx-unprivileged:alpine
    ports:
    - containerPort: 80
    - containerPort: 443
---
apiVersion: v1
kind: Pod
metadata:
  name: db-server
  namespace: virt-lab
  labels:
    app: dbsecuritygroup
  annotations:
    k8s.v1.cni.cncf.io/networks: db-tier-vlan200
spec:
  containers:
  - name: postgres
    image: postgres:alpine
    env:
    - name: POSTGRES_PASSWORD
      value: demo123
    ports:
    - containerPort: 5432
EOF

oc apply -f test-pods.yaml

# Wait for pods to be ready
oc wait --for=condition=ready pod --all -n virt-lab --timeout=120s
```

### 5. Verify Secondary Networks

```bash
# Check web server has two interfaces
oc exec -n virt-lab web-server -- ip addr show

# Should see:
# 1: lo
# 2: eth0 (primary pod network - 10.128.x.x)
# 3: net1 (secondary network - 10.10.100.x)

# Get secondary IPs
WEB_IP=$(oc exec -n virt-lab web-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
APP_IP=$(oc exec -n virt-lab app-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
DB_IP=$(oc exec -n virt-lab db-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)

echo "Web: $WEB_IP (VLAN 100)"
echo "App: $APP_IP (VLAN 150)"
echo "DB:  $DB_IP (VLAN 200)"
```

### 6. Test Traffic and Policy Enforcement

```bash
# Test 1: Web → App on port 80 (SHOULD SUCCEED per NSX rule)
oc exec -n virt-lab web-server -- nc -zv $APP_IP 80

# Test 2: Web → App on port 443 (SHOULD SUCCEED per NSX rule)
oc exec -n virt-lab web-server -- nc -zv $APP_IP 443

# Test 3: Web → App on port 22 (SHOULD FAIL - not in NSX rule)
timeout 5 oc exec -n virt-lab web-server -- nc -zv $APP_IP 22 || echo "Blocked as expected"

# Test 4: Web → DB direct (SHOULD FAIL - no NSX rule for this path)
timeout 5 oc exec -n virt-lab web-server -- nc -zv $DB_IP 5432 || echo "Blocked as expected"
```

---

## Troubleshooting

### Pods stuck in ContainerCreating

```bash
# Check events
oc describe pod web-server -n virt-lab

# Common issues:
# 1. "Link not found" → VLAN interface doesn't exist on node
#    Fix: Create VLAN interfaces (see "Worker Node Configuration")

# 2. "No such device eth1" → Wrong parent interface name
#    Fix: Find correct interface with: ip link show

# 3. "Whereabouts IPAM error" → Whereabouts not installed
#    Fix: oc apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/whereabouts/master/doc/daemonset-install.yaml
```

### VLAN interfaces missing

```bash
# Check if interfaces exist
oc debug node/worker-1.example.com -- chroot /host ip link show | grep vlan

# If missing, create them
oc debug node/worker-1.example.com -- chroot /host nmcli connection add type vlan con-name vlan100 dev eth1 id 100
```

### MultiNetworkPolicy not enforcing

```bash
# Check if feature is enabled
oc get network.operator.openshift.io cluster -o jsonpath='{.spec.useMultiNetworkPolicy}'

# Should return: true
# If false, enable it:
oc patch network.operator.openshift.io cluster --type=merge \
  -p '{"spec":{"useMultiNetworkPolicy":true}}'
```

---

## Summary

This bare metal setup gives you:

✅ **True VLAN segmentation** (same as NSX)
✅ **MultiNetworkPolicy enforcement** on secondary networks
✅ **Realistic demo** for NSX-to-OpenShift migration
✅ **Production-ready configuration** customers can replicate

**Time to deploy**: 60-90 minutes (including OpenShift installation)

**Result**: **Complete, compelling demo** showing NSX network policies enforced on OpenShift with actual traffic testing!

---

## References

- [Multus CNI](https://github.com/k8snetworkplumbingwg/multus-cni)
- [Whereabouts IPAM](https://github.com/k8snetworkplumbingwg/whereabouts)
- [OpenShift Multiple Networks](https://docs.openshift.com/container-platform/latest/networking/multiple_networks/understanding-multiple-networks.html)
- [VLAN Configuration (RHEL)](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/configuring-vlan-tagging_configuring-and-managing-networking)
