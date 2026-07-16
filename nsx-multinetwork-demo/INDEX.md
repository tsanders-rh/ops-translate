# NSX Multi-Network Demo - File Index

This directory contains a complete test environment for demonstrating NSX to Kubernetes MultiNetworkPolicy translation.

## 🚀 Start Here

**New to this demo?** → [README-AWS-SETUP.md](README-AWS-SETUP.md)

**Quick setup?** → Run `./setup-aws-test-environment.sh`

**During demo?** → [QUICK-REFERENCE.md](QUICK-REFERENCE.md)

---

## 📁 File Organization

### Setup & Automation Scripts

| File | Purpose | When to Use |
|------|---------|-------------|
| **setup-aws-test-environment.sh** | Automated setup script | First time setup on new cluster |
| **cleanup-aws-test-environment.sh** | Cleanup script | When done with demo |

### Documentation

| File | Purpose | Audience |
|------|---------|----------|
| **README-AWS-SETUP.md** | Complete setup guide | Setting up new clusters |
| **QUICK-REFERENCE.md** | Command cheat sheet | During live demos |
| **AWS_TEST_ENVIRONMENT_SUMMARY.md** | Environment details | Understanding current setup |
| **DEMO_SCRIPT.md** | Full demo walkthrough | Preparing for demos |
| **MULTINETWORK_DEMO.md** | Detailed demo guide | Learning the full flow |
| **INDEX.md** | This file | Finding the right doc |

### Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| **nad-aws-bridge-test.yaml** | ✅ NetworkAttachmentDefinitions (WORKING) | Use this |
| **test-pods-demo.yaml** | Test pod specifications | Use this |
| **multi-networkpolicy-install.yaml** | Sample MultiNetworkPolicies | Reference |

### Historical/Alternative Approaches

| File | Purpose | Status |
|------|---------|--------|
| nad-aws-eni-final.yaml | ipvlan L2 with ENIs | ❌ Not working |
| nad-aws-eni-l2-fixed.yaml | ipvlan L2 with routes | ❌ Not working |
| nad-aws-eni-with-routes.yaml | ipvlan L3 with ENIs | ❌ Not working |
| nad-aws-macvlan.yaml | Macvlan with ENIs | ❌ Requires AWS config |
| nad-aws-test-setup.yaml | ipvlan L3 with br-ex | ❌ Requires IP forwarding |
| nad-aws-ipvlan-l3-working.yaml | ipvlan L3 local subnets | ⚠️ Alternative approach |
| AWS_MULTI_ENI_SETUP.md | ENI-based setup guide | ❌ Complex, not recommended |

**Recommendation**: Use `nad-aws-bridge-test.yaml` - it's the simplest and most reliable.

---

## 🎯 Common Workflows

### First Time Setup
1. Read: [README-AWS-SETUP.md](README-AWS-SETUP.md)
2. Run: `./setup-aws-test-environment.sh`
3. Verify: Check [AWS_TEST_ENVIRONMENT_SUMMARY.md](AWS_TEST_ENVIRONMENT_SUMMARY.md)

### Preparing for a Demo
1. Review: [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
2. Practice: Follow [MULTINETWORK_DEMO.md](MULTINETWORK_DEMO.md)
3. Keep handy: [QUICK-REFERENCE.md](QUICK-REFERENCE.md)

### Setting Up on New Cluster
1. Prerequisites: [README-AWS-SETUP.md#prerequisites](README-AWS-SETUP.md#prerequisites)
2. Run: `./setup-aws-test-environment.sh`
3. Test: Commands in [QUICK-REFERENCE.md](QUICK-REFERENCE.md)

### Troubleshooting
1. Check: [README-AWS-SETUP.md#troubleshooting](README-AWS-SETUP.md#troubleshooting)
2. Verify: [QUICK-REFERENCE.md#troubleshooting](QUICK-REFERENCE.md#troubleshooting)
3. Details: [AWS_TEST_ENVIRONMENT_SUMMARY.md](AWS_TEST_ENVIRONMENT_SUMMARY.md)

### Cleanup
1. Run: `./cleanup-aws-test-environment.sh`
2. Or: `oc delete namespace virt-lab`

---

## 📊 Architecture Overview

```
OpenShift on AWS
    ├── 3 Secondary Networks (bridge CNI)
    │   ├── web-tier-vlan100 (10.244.100.0/24)
    │   ├── app-tier-vlan150 (10.244.150.0/24)
    │   └── db-tier-vlan200 (10.244.200.0/24)
    │
    ├── 3 Test Pods
    │   ├── web-server (10.244.100.11)
    │   ├── app-server (10.244.150.11)
    │   └── db-server (10.244.200.11)
    │
    └── 3 MultiNetworkPolicies
        ├── web → app (ports 80, 443)
        ├── app → db (port 3306)
        └── backup → db (port 22)
```

---

## 🔗 Related Resources

### External Links
- [OpenShift MultiNetworkPolicy Docs](https://docs.openshift.com/container-platform/latest/networking/multiple_networks/configuring-multi-network-policy.html)
- [ops-translate GitHub](https://github.com/tsanders-rh/ops-translate)
- [Multus CNI](https://github.com/k8snetworkplumbingwg/multus-cni)

### Internal Links
- Main ops-translate: `../` (parent directory)
- Input workflows: `input/vrealize/` (if using ops-translate)
- Generated output: `output/k8s/` (if using ops-translate)

---

## 💡 Tips

- **Bookmark** [QUICK-REFERENCE.md](QUICK-REFERENCE.md) for fast access during demos
- **Print** [QUICK-REFERENCE.md](QUICK-REFERENCE.md) for offline reference
- **Script works on any cluster** - not just AWS (despite the name)
- **iptables rules** are temporary - persist across pod restarts but not node reboots
- **Use cleanup script** to remove everything cleanly

---

## 📝 Version History

| Date | Change | Files Affected |
|------|--------|----------------|
| 2026-07-10 | Initial AWS test setup scripts | setup-aws-test-environment.sh, nad-aws-bridge-test.yaml |
| 2026-07-10 | Added cleanup and documentation | cleanup-aws-test-environment.sh, README-AWS-SETUP.md |
| 2026-07-10 | Added quick reference | QUICK-REFERENCE.md, INDEX.md |

---

## ❓ Questions?

- **Setup issues?** → [README-AWS-SETUP.md#troubleshooting](README-AWS-SETUP.md#troubleshooting)
- **Demo questions?** → [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
- **Environment details?** → [AWS_TEST_ENVIRONMENT_SUMMARY.md](AWS_TEST_ENVIRONMENT_SUMMARY.md)
- **Quick commands?** → [QUICK-REFERENCE.md](QUICK-REFERENCE.md)

---

## 📦 Archived Files

Experimental and legacy files have been moved to the `archive/` directory.
These include:
- ENI-based approach scripts
- Experimental NAD configurations
- Legacy documentation

See `archive/README.md` for details.
