# Testing Guide: NSX → OVN-Kubernetes MultiNetworkPolicy Feature

## Overview

Testing this feature happens at **4 levels**:
1. **Unit Tests** - Individual components (correlation, policy generation)
2. **Integration Tests** - Full pipeline (analysis → correlation → generation)
3. **Manual Testing** - Using demo NSX workflows
4. **Kubernetes Validation** - Deploying generated policies to OpenShift/K8s cluster

---

## Level 1: Unit Tests (Development Phase)

### What You're Testing
Individual functions work correctly in isolation.

### Setup
```bash
cd /Users/tsanders/Workspace/ops-translate

# Install dev dependencies if not already installed
pip install -r requirements-dev.txt

# Run all unit tests
pytest tests/ -v --cov=ops_translate

# Run specific test files
pytest tests/test_nsx_correlation.py -v
pytest tests/test_multinetworkpolicy.py -v
```

### Key Test Files

**File: `tests/test_nsx_correlation.py`**
- Tests correlation engine detection strategies
- Validates confidence scoring
- Tests edge cases (no segments, no rules, ambiguous matches)

**File: `tests/test_multinetworkpolicy.py`**
- Tests MultiNetworkPolicy YAML generation
- Validates OVN-Kubernetes API compliance
- Tests annotation and label generation

### Running Unit Tests with Coverage
```bash
# Run with coverage report
pytest tests/ --cov=ops_translate.generate --cov-report=html

# View coverage report
open htmlcov/index.html

# Expected coverage:
# - nsx_correlation.py: >85%
# - multinetworkpolicy.py: >85%
```

---

## Level 2: Integration Tests (Pipeline Validation)

### What You're Testing
End-to-end pipeline: vRealize XML → analysis → correlation → MultiNetworkPolicy YAML.

### Test File

**File: `tests/integration/test_multinetworkpolicy_workflow.py`**

9 integration test cases covering:
1. End-to-end correlation and generation
2. MultiNetworkPolicy YAML structure validation
3. Correlation report content verification
4. NetworkPolicy filtering (primary vs secondary)
5. Confidence scoring validation
6. Segment metadata extraction
7. README generation
8. No segments fallback behavior
9. No rules handling

### Running Integration Tests
```bash
# Run all integration tests
pytest tests/integration/test_multinetworkpolicy_workflow.py -v

# Run specific test
pytest tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_end_to_end_correlation_and_generation -v

# Run with detailed output
pytest tests/integration/test_multinetworkpolicy_workflow.py -v -s
```

### Expected Results
```
============================= test session starts ==============================
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_end_to_end_correlation_and_generation PASSED [ 11%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_multinetworkpolicy_yaml_structure PASSED [ 22%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_correlation_report_content PASSED [ 33%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_networkpolicy_filtering PASSED [ 44%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_confidence_scoring PASSED [ 55%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_segment_metadata_extraction PASSED [ 66%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_readme_generation PASSED [ 77%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_no_segments_fallback PASSED [ 88%]
tests/integration/test_multinetworkpolicy_workflow.py::TestMultiNetworkPolicyWorkflow::test_no_rules_handling PASSED [100%]

============================== 9 passed in 0.38s ===============================
```

---

## Level 3: Manual Testing with Demo Workflows

### What You're Testing
Real-world workflow with actual NSX analysis data.

### Test Using Demo Script

The project includes a demo script that automatically tests the MultiNetworkPolicy feature:

```bash
cd /Users/tsanders/Workspace/ops-translate

# Run demo script (creates test workspace, generates policies)
./demo.sh

# The demo script:
# 1. Creates test-multinetpolicy-workspace/test-mnp/
# 2. Generates mock NSX analysis data
# 3. Runs the generation pipeline
# 4. Shows generated outputs
```

### Manual Test Steps

```bash
# Initialize test workspace
ops-translate init test-mnp-manual
cd test-mnp-manual

# Create mock NSX analysis data
mkdir -p intent
cat > intent/analysis.vrealize.json <<'EOF'
{
  "source_file": "test-workflow.xml",
  "nsx_operations": {
    "segments": [
      {
        "name": "Web-Tier-VLAN100",
        "location": "workflow.xml:24",
        "confidence": 0.95,
        "evidence": "nsxClient.createSegment({displayName: 'Web-Tier-VLAN100', vlanIds: [100], subnets: ['10.10.100.0/24']})"
      },
      {
        "name": "DB-Tier-VLAN200",
        "location": "workflow.xml:45",
        "confidence": 0.95,
        "evidence": "nsxClient.createSegment({displayName: 'DB-Tier-VLAN200', vlanIds: [200], subnets: ['10.10.200.0/24']})"
      }
    ],
    "firewall_rules": [
      {
        "name": "Allow-Web-to-DB",
        "location": "workflow.xml:81",
        "confidence": 0.95,
        "evidence": "nsxClient.createFirewallRule({segment: 'Web-Tier-VLAN100', sources: ['web'], destinations: ['db'], services: ['MySQL']})"
      },
      {
        "name": "Allow-Internet",
        "location": "workflow.xml:102",
        "confidence": 0.95,
        "evidence": "nsxClient.createFirewallRule({sources: ['any'], destinations: ['internet'], services: ['HTTPS']})"
      }
    ]
  }
}
EOF

# Run generation
ops-translate generate --profile lab

# Verify outputs
tree output/
```

### Verification Checklist

**Check 1: MultiNetworkPolicy Generated**
```bash
cat output/multi-network-policies/web-tier-vlan100-allow-web-to-db.yaml

# Verify:
# ✓ apiVersion: k8s.cni.cncf.io/v1beta1
# ✓ kind: MultiNetworkPolicy
# ✓ annotations.k8s.v1.cni.cncf.io/policy-for: "default/web-tier-vlan100"
# ✓ spec.podSelector present
# ✓ spec.ingress rules present
# ✓ Header comments explain secondary network scope
```

**Check 2: Correlation Report**
```bash
cat output/multi-network-policies/CORRELATION_REPORT.md

# Verify:
# ✓ Lists "Web-Tier-VLAN100" segment
# ✓ Shows "Allow-Web-to-DB" rule mapped to it
# ✓ Confidence score shown (0.95)
# ✓ Evidence section explains correlation
# ✓ Primary network section lists "Allow-Internet"
```

**Check 3: Standard NetworkPolicy for Primary**
```bash
cat output/network-policies/allow-internet.yaml

# Verify:
# ✓ Standard Kubernetes NetworkPolicy (networking.k8s.io/v1)
# ✓ NOT MultiNetworkPolicy
# ✓ No network-attachment annotation
# ✓ Comment explains this is for primary network
```

**Check 4: NetworkAttachmentDefinitions**
```bash
cat output/network-attachments/web-tier-vlan100.yaml

# Verify:
# ✓ NetworkAttachmentDefinition with VLAN 100
# ✓ Subnet 10.10.100.0/24
# ✓ bridge CNI config
# ✓ whereabouts IPAM configured
```

---

## Level 4: OpenShift/Kubernetes Cluster Validation

### What You're Testing
Generated policies actually work in a real cluster with OVN-Kubernetes.

### Prerequisites

You need an OpenShift cluster (4.12+) OR Kubernetes cluster with:
- ✅ OVN-Kubernetes CNI installed
- ✅ Multus CNI installed
- ✅ Bridge CNI plugin (for VLAN support)

### OpenShift Setup (Recommended)

```bash
# Login to OpenShift cluster
oc login https://your-cluster-api:6443

# Verify OVN-Kubernetes is running
oc get pods -n openshift-ovn-kubernetes

# Verify Multus (pre-installed on OpenShift)
oc get pods -n openshift-multus
```

### Deploy Generated Resources

```bash
# From your test workspace
cd test-mnp-manual

# 1. Apply NetworkAttachmentDefinitions first
oc apply -f output/network-attachments/

# Verify NADs created
oc get network-attachment-definitions
# Expected:
# NAME                  AGE
# web-tier-vlan100      5s
# db-tier-vlan200       5s

# 2. Apply MultiNetworkPolicies
oc apply -f output/multi-network-policies/

# Verify MultiNetworkPolicies
oc get multinetworkpolicies
# Expected:
# NAME                               AGE
# web-tier-vlan100-allow-web-to-db   3s

# 3. Apply standard NetworkPolicies
oc apply -f output/network-policies/

# Verify standard policies
oc get networkpolicies
# Expected:
# NAME               POD-SELECTOR   AGE
# allow-internet     <all>          2s
```

### Create Test Pods

**File: `test-pods.yaml`**

```yaml
---
# Web tier pod with secondary network
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web
  annotations:
    k8s.v1.cni.cncf.io/networks: web-tier-vlan100
spec:
  containers:
  - name: nginx
    image: nginx:alpine
    command: ["/bin/sh", "-c", "sleep 3600"]

---
# Database pod with secondary network
apiVersion: v1
kind: Pod
metadata:
  name: db-server
  labels:
    app: database
  annotations:
    k8s.v1.cni.cncf.io/networks: web-tier-vlan100
spec:
  containers:
  - name: mysql
    image: mysql:8
    env:
    - name: MYSQL_ROOT_PASSWORD
      value: testpass
```

```bash
# Deploy test pods
oc apply -f test-pods.yaml

# Wait for pods to be ready
oc wait --for=condition=ready pod/web-server --timeout=60s
oc wait --for=condition=ready pod/db-server --timeout=60s

# Verify pods have secondary network interface
oc exec web-server -- ip addr show
# Expected:
# 1: lo: ...
# 2: eth0@if... (primary pod network)
# 3: net1@if... (secondary network - VLAN 100)
```

### Test Network Policy Enforcement

```bash
# 1. Get pod IPs
WEB_PRIMARY=$(oc get pod web-server -o jsonpath='{.status.podIP}')
WEB_SECONDARY=$(oc exec web-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)

DB_PRIMARY=$(oc get pod db-server -o jsonpath='{.status.podIP}')
DB_SECONDARY=$(oc exec db-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)

echo "Web Primary: $WEB_PRIMARY"
echo "Web Secondary (VLAN 100): $WEB_SECONDARY"
echo "DB Primary: $DB_PRIMARY"
echo "DB Secondary (VLAN 100): $DB_SECONDARY"

# 2. Test connectivity on secondary network (should be allowed by MultiNetworkPolicy)
oc exec web-server -- nc -zv $DB_SECONDARY 3306
# Expected: Connection to 10.10.100.x 3306 port [tcp/mysql] succeeded!

# 3. Test connectivity on different port (should be denied)
oc exec web-server -- nc -zv -w 2 $DB_SECONDARY 22
# Expected: Connection timed out (policy only allows 3306)
```

### Verification Checklist (Kubernetes)

- [ ] NADs created successfully
- [ ] MultiNetworkPolicies applied without errors
- [ ] Pods have secondary network interfaces (net1)
- [ ] Pods get IPs from secondary network range (10.10.100.x)
- [ ] Traffic allowed per policy (web → db:3306)
- [ ] Traffic denied when not in policy (web → db:22)
- [ ] Standard NetworkPolicy applies to primary network

---

## Test Scenarios

### Scenario 1: Simple Migration (2-3 Segments)

**Customer Profile**: Small VMware deployment, straightforward network segmentation

**Test Data**:
- 2 segments (Web VLAN 100, DB VLAN 200)
- 5 firewall rules (3 segment-specific, 2 general)

**Expected Results**:
- 3 MultiNetworkPolicies
- 2 standard NetworkPolicies
- High correlation confidence (>0.85)

### Scenario 2: Complex Multi-Tier (10+ Segments)

**Customer Profile**: Large enterprise, many network zones

**Test Data**:
- 10+ segments (DMZ, Web, App, DB, Management, etc.)
- 40+ firewall rules (mixed segment-specific and general)

**Expected Results**:
- Correlation report shows clear mapping
- Some medium confidence scores (0.6-0.8) for IP overlap
- Performance: <5 seconds for generation

### Scenario 3: Edge Case (No Clear Correlation)

**Customer Profile**: NSX rules don't clearly reference segments

**Test Data**:
- 5 segments detected
- 20 firewall rules with no segment names in evidence

**Expected Results**:
- Most rules fall back to primary network (standard NetworkPolicy)
- Correlation report flags low confidence
- User warned to review mappings

---

## Performance Testing

### Load Testing

```bash
# Test with large NSX export
# 50 segments, 500 firewall rules

time ops-translate generate --profile lab

# Expected:
# - Generation time: <10 seconds
# - Memory usage: <500MB
# - All outputs generated correctly
```

### Regression Testing

```bash
# Ensure existing functionality still works
pytest tests/test_networkpolicy.py -v
pytest tests/test_network_attachment.py -v

# No failures should occur
```

---

## Summary: Testing Checklist

Before shipping this feature, ensure:

**Development Phase**:
- [x] Unit tests pass (>85% coverage)
- [x] Integration tests pass (9/9 tests)
- [x] Manual testing with demo workflows successful

**POC Validation**:
- [x] Tested with realistic NSX data (3+ segments, 5+ rules)
- [x] Correlation confidence acceptable (>0.85 for direct refs)
- [ ] YAML validated with oc/kubectl apply --dry-run
- [x] Documentation (README, CORRELATION_REPORT) clear

**Kubernetes Validation** (Optional for POC):
- [ ] Deployed to OpenShift cluster with OVN-Kubernetes
- [ ] Policies actually enforce as expected
- [ ] No regressions in existing features

---

## Tools & Resources

**Testing Tools**:
- `pytest` - Python testing framework
- `oc` / `kubectl` - Kubernetes CLI
- `yamllint` - YAML validation
- `jq` - JSON processing

**Useful Commands**:
```bash
# Quick syntax check
yamllint output/multi-network-policies/*.yaml

# Validate against Kubernetes schema
oc apply --dry-run=client -f output/multi-network-policies/

# Check NAD status
oc describe network-attachment-definitions web-tier-vlan100

# View pod network interfaces
oc exec <pod-name> -- ip addr show
```

---

## Questions or Issues?

Open an issue on GitHub with:
- Test scenario description
- Expected vs. actual results
- Relevant logs/outputs
