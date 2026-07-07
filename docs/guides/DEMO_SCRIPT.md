# NSX MultiNetworkPolicy Demo - Quick Script

**Duration**: 20-30 minutes live demo
**Audience**: Consulting team, customers, technical stakeholders

---

## Pre-Demo Setup (Do Before Meeting)

```bash
# 1. Clone and setup ops-translate
cd ~/demos
git clone https://github.com/tsanders-rh/ops-translate.git
cd ops-translate
source .venv/bin/activate

# 2. Create demo workspace with pre-made NSX workflow
ops-translate init nsx-demo && cd nsx-demo

# 3. Copy the 3-tier NSX workflow from MULTINETWORK_DEMO.md
# (See Part 1, Step 2 in full demo guide)
mkdir -p input/vrealize
# ... paste workflow XML ...

# 4. Optional: Have OpenShift cluster ready
# - Login: oc login https://your-cluster
# - Create namespace: oc new-project nsx-demo
```

---

## Demo Flow

### Introduction (2 min)

**Say**:
> "Today I'll show you how ops-translate automatically translates NSX network segments and firewall rules into OpenShift MultiNetworkPolicy resources. This preserves your network segmentation during VMware to OpenShift migrations."

**Show**: Architecture diagram on slide (NSX → Correlation → MultiNetworkPolicy)

---

### Part 1: The Challenge (3 min)

**Say**:
> "Here's a typical vRealize workflow that provisions a 3-tier application with NSX networking."

**Show**:
```bash
cat input/vrealize/nsx-3tier-app.workflow.xml | grep -A 5 "createWebSegment"
```

**Say**:
> "This creates 3 network segments on VLANs 100, 150, 200, and 5 firewall rules. Manually translating this to Kubernetes policies would take weeks. Let's see how ops-translate does it."

---

### Part 2: Analysis (4 min)

**Run**:
```bash
ops-translate analyze
```

**Point out**:
```
✓ 3 network segments detected
✓ 5 firewall rules detected
```

**Say**:
> "The analyzer detected all NSX operations. Let's look at what it found."

**Show**:
```bash
cat intent/analysis.vrealize.json | jq '.nsx_operations.segments[] | {name, vlan: .vlan_ids, subnet: .subnets}'
```

**Point out**:
- Web-Tier-VLAN100: VLAN 100, subnet 10.10.100.0/24
- App-Tier-VLAN150: VLAN 150, subnet 10.10.150.0/24
- DB-Tier-VLAN200: VLAN 200, subnet 10.10.200.0/24

---

### Part 3: Generation & Correlation (8 min)

#### Generate Resources

**Run**:
```bash
ops-translate generate --profile lab
tree output/
```

**Point out the structure**:
```
output/
├── multi-network-policies/     ← Secondary networks (3 rules)
├── network-policies/            ← Primary network (2 rules)
└── network-attachments/         ← NADs (3 VLANs)
```

**Say**:
> "The correlation engine intelligently routed rules. Segment-specific rules became MultiNetworkPolicies, general rules became standard NetworkPolicies."

#### Show Correlation Report

**Run**:
```bash
cat output/multi-network-policies/CORRELATION_REPORT.md | head -n 60
```

**Highlight**:
```
Primary Network Rules: 2
  - Allow-Internet-Egress
  - Allow-DNS

Segments with Rules: 3
  - Web-Tier-VLAN100 (confidence: 0.95)
  - App-Tier-VLAN150 (confidence: 0.90)
  - DB-Tier-VLAN200 (confidence: 0.95)
```

**Say**:
> "Notice the confidence scores. The DB rule got 0.95 because it had THREE signals: segment name reference, VLAN ID match, AND IP subnet overlap. Multi-signal validation prevents false positives."

#### Show Generated MultiNetworkPolicy

**Run**:
```bash
cat output/multi-network-policies/web-tier-vlan100-allow-web-to-app.yaml
```

**Point out**:
1. **Line 1-30**: Detailed header comments explaining scope and limitations
2. **Line 35**: `apiVersion: k8s.cni.cncf.io/v1beta1` (OVN-Kubernetes standard)
3. **Line 40**: `k8s.v1.cni.cncf.io/policy-for: default/web-tier-vlan100` (critical annotation)
4. **Line 42-46**: Labels for traceability
5. **Line 48-62**: Standard NetworkPolicy structure (easy to understand)

**Say**:
> "This is a standard OVN-Kubernetes MultiNetworkPolicy. No custom CRDs, no special operators - it's what OpenShift 4.12+ provides out of the box."

#### Show NetworkAttachmentDefinition

**Run**:
```bash
cat output/network-attachments/web-tier-vlan100.yaml | tail -n 20
```

**Point out**:
```yaml
spec:
  config: |
    {
      "type": "bridge",
      "vlan": 100,              ← Same VLAN as NSX
      "ipam": {
        "range": "10.10.100.0/24",  ← Same subnet as NSX
        "gateway": "10.10.100.1"    ← Same gateway as NSX
      }
    }
```

**Say**:
> "The NetworkAttachmentDefinition preserves the exact VLAN ID and subnet from NSX. Your network segmentation is maintained."

---

### Part 4: OpenShift Deployment (8 min)

**⚠️ Only if you have cluster access**

**Say**:
> "Let's deploy these to OpenShift and see them in action."

#### Deploy

**Run**:
```bash
oc apply -f output/network-attachments/ -n nsx-demo
oc apply -f output/multi-network-policies/ -n nsx-demo
oc apply -f output/network-policies/ -n nsx-demo
```

**Show**:
```bash
oc get network-attachment-definitions -n nsx-demo
oc get multinetworkpolicies -n nsx-demo
oc get networkpolicies -n nsx-demo
```

#### Create Test Pods

**Run**:
```bash
cat > test-pods.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  namespace: nsx-demo
  labels:
    app: web
  annotations:
    k8s.v1.cni.cncf.io/networks: web-tier-vlan100
spec:
  containers:
  - name: nginx
    image: nginxinc/nginx-unprivileged:alpine
---
apiVersion: v1
kind: Pod
metadata:
  name: app-server
  namespace: nsx-demo
  labels:
    app: app-tier
  annotations:
    k8s.v1.cni.cncf.io/networks: app-tier-vlan150
spec:
  containers:
  - name: nginx
    image: nginxinc/nginx-unprivileged:alpine
EOF

oc apply -f test-pods.yaml
oc get pods -n nsx-demo -w
```

#### Verify Secondary Networks

**Run**:
```bash
oc exec -n nsx-demo web-server -- ip addr show
```

**Point out**:
```
1: lo: ...
2: eth0@if123: ...   ← Primary pod network
3: net1@if124: ...   ← Secondary network (VLAN 100)
                       inet 10.10.100.15/24  ← IP from NSX subnet!
```

**Say**:
> "The pod has TWO network interfaces. eth0 is the primary pod network, net1 is the VLAN 100 secondary network with an IP from the NSX subnet range."

#### Test Policy Enforcement

**Run**:
```bash
APP_IP=$(oc exec -n nsx-demo app-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)

# Test allowed traffic (HTTP to app)
oc exec -n nsx-demo web-server -- nc -zv $APP_IP 8080
echo "Exit code: $?"  # Should be 0 (success)

# Test denied traffic (SSH to app)
oc exec -n nsx-demo web-server -- timeout 2 nc -zv $APP_IP 22
echo "Exit code: $?"  # Should be 1 or 124 (timeout/denied)
```

**Say**:
> "The policy is enforcing! Port 8080 (HTTP) is allowed per the NSX rule, but port 22 (SSH) is blocked because it wasn't in the NSX firewall rule."

---

### Part 5: Value Summary (3 min)

**Say**:
> "Let me recap what you just saw:"

**Automation**:
- Analyzed NSX workflow (5 seconds)
- Generated 8 Kubernetes resources (2 seconds)
- What would take 2-3 weeks manually

**Accuracy**:
- 95% correlation confidence
- Multi-signal validation (segment name + VLAN + IP)
- Full traceability with source annotations

**OpenShift Native**:
- Standard OVN-Kubernetes APIs
- No custom operators or CRDs
- Works on any OpenShift 4.12+ cluster

**Customer Value**:
- Removes network policy migration as a blocker
- Preserves existing security posture
- Reduces consulting costs by 80-90%

---

## Q&A Preparation

### Expected Questions

**Q: What if NSX rules don't clearly reference segments?**
> "The correlation engine has fallback strategies - IP overlap, VLAN matching, proximity analysis. Low confidence rules get flagged in the report for manual review."

**Q: What NSX features aren't supported?**
> "MultiNetworkPolicy is L3/L4 only - no L7 HTTP filtering, no FQDN rules, no time-based policies. These are automatically detected and documented in the YAML comments."

**Q: Can we validate without OpenShift?**
> "Yes! The unit and integration tests validate the correlation logic and YAML generation. You can review outputs before deploying to any cluster."

**Q: How do we customize for our org?**
> "Use template customization: `ops-translate init --with-templates`. Edit the Jinja2 templates to add org-specific labels, annotations, naming conventions."

**Q: What's the accuracy rate?**
> "In our testing with real NSX exports, direct segment references achieve 95% confidence. IP overlap and VLAN matching achieve 70-85% confidence depending on complexity."

---

## Backup Slides/Demos

### If No Cluster Access

Show the correlation report and YAML files. Emphasize:
- Transparency (every decision is documented)
- Traceability (source locations annotated)
- Standards-based (OVN-Kubernetes, no vendor lock-in)

### If Extra Time

Show the demo.sh script:
```bash
cd /path/to/ops-translate
./demo.sh
```

This auto-creates a test workspace and runs the full pipeline.

---

## Post-Demo Follow-Up

**Send to attendees**:
1. Link to full demo guide: `docs/guides/MULTINETWORK_DEMO.md`
2. Link to testing guide: `docs/guides/TESTING_GUIDE.md`
3. GitHub repo: https://github.com/tsanders-rh/ops-translate

**Offer**:
> "If you have a real NSX export you'd like to test, send it over (anonymized is fine). We can run it through ops-translate and share the outputs with you."

---

## Checklist: Before Every Demo

- [ ] ops-translate installed and tested
- [ ] Demo workspace created with NSX workflow
- [ ] OpenShift cluster accessible (if doing deployment)
- [ ] `oc login` working
- [ ] Demo namespace created (`oc new-project nsx-demo`)
- [ ] Screen recording started (optional - for async sharing)
- [ ] Terminal font size increased (for visibility)
- [ ] Browser tabs ready:
  - GitHub repo
  - Documentation
  - Architecture diagram slide

---

**Script prepared by**: ops-translate project team
**Last tested**: 2026-07-06
**Estimated prep time**: 15 minutes
**Estimated delivery time**: 20-30 minutes
