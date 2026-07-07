# End-to-End Demo: NSX → OVN-Kubernetes MultiNetworkPolicy

**For**: Consulting Team
**Duration**: 30-45 minutes
**Requirements**: ops-translate installed, OpenShift 4.12+ cluster (optional for deployment)

---

## Overview

This demo shows how ops-translate automatically translates NSX network segments and firewall rules into OVN-Kubernetes MultiNetworkPolicy resources for OpenShift, enabling network segmentation for migrated workloads.

**What You'll Learn**:
1. How to analyze vRealize workflows with NSX operations
2. How the correlation engine maps firewall rules to network segments
3. What MultiNetworkPolicy resources are generated
4. How to deploy and validate policies on OpenShift

**Customer Value**:
- Preserves NSX network segmentation in OpenShift
- Automates translation of complex NSX configurations
- Provides confidence scoring and detailed correlation reports
- Reduces manual policy creation from weeks to minutes

---

## Demo Scenario

**VMware Environment**:
- 3-tier application (Web, App, Database)
- Each tier on separate NSX segment (VLANs 100, 150, 200)
- NSX firewall rules controlling inter-tier traffic
- General internet/DNS rules for all tiers

**Migration Goal**:
- Preserve network segmentation in OpenShift
- Use MultiNetworkPolicy for secondary networks (VLANs)
- Use NetworkPolicy for primary pod network
- Maintain same security posture

---

## Architecture Diagram

### NSX Environment → OpenShift Translation

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           NSX NETWORK ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────┐         ┌──────────────────────┐         ┌──────────────────────┐
    │  Web-Tier-VLAN100    │         │  App-Tier-VLAN150    │         │  DB-Tier-VLAN200     │
    │  ════════════════    │         │  ════════════════    │         │  ═══════════════     │
    │  VLAN: 100           │         │  VLAN: 150           │         │  VLAN: 200           │
    │  Subnet:             │         │  Subnet:             │         │  Subnet:             │
    │  10.10.100.0/24      │         │  10.10.150.0/24      │         │  10.10.200.0/24      │
    │  Gateway:            │         │  Gateway:            │         │  Gateway:            │
    │  10.10.100.1         │         │  10.10.150.1         │         │  10.10.200.1         │
    └──────────┬───────────┘         └──────────┬───────────┘         └──────────┬───────────┘
               │                                │                                │
               │  Web VMs                       │  App VMs                       │  DB VMs
               │  (10.10.100.x)                 │  (10.10.150.x)                 │  (10.10.200.x)
               │                                │                                │
               └────────────────────────────────┴────────────────────────────────┘
                                                │
                                    ┌───────────▼──────────┐
                                    │   NSX Firewall       │
                                    │   ═════════════      │
                                    │  5 Rules:            │
                                    │  • Web → App (80,443)│
                                    │  • App → DB (3306)   │
                                    │  • DB → Backup (*)   │
                                    │  • Internet Egress   │
                                    │  • DNS (53)          │
                                    └──────────────────────┘


                                           ⬇ ⬇ ⬇
                               ops-translate analyze + generate
                                           ⬇ ⬇ ⬇


┌─────────────────────────────────────────────────────────────────────────────────┐
│                       OPENSHIFT / OVN-KUBERNETES                                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                    NetworkAttachmentDefinitions (NADs)                          │
│  ═══════════════════════════════════════════════════════════════════════       │
│                                                                                 │
│  web-tier-vlan100.yaml    app-tier-vlan150.yaml    db-tier-vlan200.yaml       │
│  ├─ VLAN: 100             ├─ VLAN: 150             ├─ VLAN: 200               │
│  ├─ IPAM: Whereabouts     ├─ IPAM: Whereabouts     ├─ IPAM: Whereabouts       │
│  └─ Range: 10.10.100.0/24 └─ Range: 10.10.150.0/24 └─ Range: 10.10.200.0/24   │
└─────────────────────────────────────────────────────────────────────────────────┘

                                           │
                                           ▼

┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Pod Deployment (with annotations)                            │
└─────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
  │   web-server     │         │   app-server     │         │   db-server      │
  │   ═══════════    │         │   ══════════     │         │   ═════════      │
  │  Annotations:    │         │  Annotations:    │         │  Annotations:    │
  │  networks:       │         │  networks:       │         │  networks:       │
  │  web-tier-vlan100│         │  app-tier-vlan150│         │  db-tier-vlan200 │
  │                  │         │                  │         │                  │
  │  ┌─────────────┐ │         │  ┌─────────────┐ │         │  ┌─────────────┐ │
  │  │ eth0 (prim) │ │         │  │ eth0 (prim) │ │         │  │ eth0 (prim) │ │
  │  │ net1 (VLAN) │ │         │  │ net1 (VLAN) │ │         │  │ net1 (VLAN) │ │
  │  │ 10.10.100.x │ │         │  │ 10.10.150.x │ │         │  │ 10.10.200.x │ │
  │  └─────────────┘ │         │  └─────────────┘ │         │  └─────────────┘ │
  └────────┬─────────┘         └────────┬─────────┘         └────────┬─────────┘
           │                            │                            │
           │                            │                            │
           └────────────┬───────────────┴───────────┬────────────────┘
                        │                           │
                        ▼                           ▼

┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│   MultiNetworkPolicy (Secondary)    │   │   NetworkPolicy (Primary)           │
│   ════════════════════════════      │   │   ════════════════════              │
│                                     │   │                                     │
│  web-tier-vlan100-allow-web-to-app  │   │  allow-internet-egress              │
│  • policy-for: web-tier-vlan100     │   │  • All pods → internet              │
│  • Web pods → App pods (80,443)     │   │                                     │
│                                     │   │  allow-dns                          │
│  app-tier-vlan150-allow-app-to-db   │   │  • All pods → DNS (53)              │
│  • policy-for: app-tier-vlan150     │   │                                     │
│  • App pods → DB pods (3306)        │   │                                     │
│                                     │   │                                     │
│  db-tier-vlan200-allow-db-backup    │   │                                     │
│  • policy-for: db-tier-vlan200      │   │                                     │
│  • DB pods → Backup server          │   │                                     │
└─────────────────────────────────────┘   └─────────────────────────────────────┘
     ▲                                         ▲
     │                                         │
     │    Applies to net1 interface            │    Applies to eth0 interface
     │    (secondary VLAN networks)            │    (primary pod network)
     │                                         │

┌─────────────────────────────────────────────────────────────────────────────────┐
│                          CORRELATION MAPPING                                    │
│  ═══════════════════════════════════════════════════════════════════════       │
│                                                                                 │
│  NSX Rule             Confidence   Target         Reason                       │
│  ─────────────────    ──────────   ─────────────  ─────────────────────────    │
│  Web → App (80,443)      0.95      Multi (VLAN100) Segment name + VLAN match   │
│  App → DB (3306)         0.90      Multi (VLAN150) Segment name + IP overlap   │
│  DB → Backup             0.95      Multi (VLAN200) Name + VLAN + IP (3 signals)│
│  Internet Egress         0.50      Primary Network No segment correlation      │
│  DNS (53)                0.50      Primary Network No segment correlation      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- ✅ **3 NSX segments** → 3 NetworkAttachmentDefinitions (secondary networks)
- ✅ **3 segment-specific rules** → 3 MultiNetworkPolicies (net1 interface)
- ✅ **2 general rules** → 2 NetworkPolicies (eth0 interface)
- ✅ **Correlation engine** intelligently routes rules based on evidence
- ✅ **Confidence scoring** ensures accurate mapping (0.90-0.95 for direct matches)

---

## Part 1: Setup and Import (5 minutes)

### Step 1: Initialize Workspace

```bash
# Navigate to ops-translate directory
cd /path/to/ops-translate

# Initialize demo workspace
ops-translate init nsx-multinetwork-demo
cd nsx-multinetwork-demo

# Verify workspace structure
tree -L 2
```

**Expected Output**:
```
.
├── input/
│   ├── powercli/
│   └── vrealize/
├── intent/
├── output/
└── ops-translate.yaml  ← Configuration file (profiles, LLM settings)
```

> **Tip**: You can customize environment profiles by editing `ops-translate.yaml`. The default `lab` and `prod` profiles can be modified or you can add custom profiles like `staging`, `dev`, etc. See the note in Step 5 for details.

### Step 2: Create Sample NSX Workflow

Create a realistic vRealize workflow that provisions a 3-tier application with NSX networking:

```bash
mkdir -p input/vrealize
cat > input/vrealize/nsx-3tier-app.workflow.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://vmware.com/vco/workflow"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://vmware.com/vco/workflow http://vmware.com/vco/workflow/Workflow-v4.xsd"
          root-name="item1" object-name="workflow:name=nsx-3tier-app"
          id="12345678-1234-1234-1234-123456789012"
          version="1.0.0">

  <display-name>NSX 3-Tier Application Provisioning</display-name>
  <description>Provisions network segments and firewall rules for a 3-tier application</description>

  <!-- Web Tier Segment -->
  <workflow-item name="createWebSegment" type="task" out-name="item2">
    <display-name>Create Web Tier Segment</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating Web Tier network segment");

      var webSegment = nsxClient.createSegment({
        displayName: "Web-Tier-VLAN100",
        vlanIds: [100],
        subnets: ["10.10.100.0/24"],
        gateway: "10.10.100.1",
        description: "Web tier frontend network"
      });

      System.log("Web segment created: " + webSegment.id);
      ]]>
    </script>
  </workflow-item>

  <!-- App Tier Segment -->
  <workflow-item name="createAppSegment" type="task" out-name="item3">
    <display-name>Create App Tier Segment</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating Application Tier network segment");

      var appSegment = nsxClient.createSegment({
        displayName: "App-Tier-VLAN150",
        vlanIds: [150],
        subnets: ["10.10.150.0/24"],
        gateway: "10.10.150.1",
        description: "Application tier middleware network"
      });

      System.log("App segment created: " + appSegment.id);
      ]]>
    </script>
  </workflow-item>

  <!-- Database Tier Segment -->
  <workflow-item name="createDbSegment" type="task" out-name="item4">
    <display-name>Create Database Tier Segment</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating Database Tier network segment");

      var dbSegment = nsxClient.createSegment({
        displayName: "DB-Tier-VLAN200",
        vlanIds: [200],
        subnets: ["10.10.200.0/24"],
        gateway: "10.10.200.1",
        description: "Database tier backend network"
      });

      System.log("DB segment created: " + dbSegment.id);
      ]]>
    </script>
  </workflow-item>

  <!-- Firewall Rule: Web to App -->
  <workflow-item name="allowWebToApp" type="task" out-name="item5">
    <display-name>Allow Web to App Traffic</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating firewall rule: Web to App");

      var rule1 = nsxClient.createFirewallRule({
        name: "Allow-Web-to-App",
        segment: "Web-Tier-VLAN100",
        sources: ["web-security-group"],
        destinations: ["app-security-group"],
        services: ["HTTP", "HTTPS"],
        action: "ALLOW",
        direction: "INGRESS",
        description: "Allow web tier to communicate with app tier on HTTP/HTTPS"
      });

      System.log("Firewall rule created: " + rule1.id);
      ]]>
    </script>
  </workflow-item>

  <!-- Firewall Rule: App to DB -->
  <workflow-item name="allowAppToDb" type="task" out-name="item6">
    <display-name>Allow App to Database Traffic</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating firewall rule: App to Database");

      var rule2 = nsxClient.createFirewallRule({
        name: "Allow-App-to-DB",
        segment: "App-Tier-VLAN150",
        sources: ["app-security-group"],
        destinations: ["db-security-group"],
        destination: "10.10.200.50",
        services: ["MySQL"],
        action: "ALLOW",
        direction: "INGRESS",
        description: "Allow app tier to access database on MySQL port"
      });

      System.log("Firewall rule created: " + rule2.id);
      ]]>
    </script>
  </workflow-item>

  <!-- Firewall Rule: DB Backup -->
  <workflow-item name="allowDbBackup" type="task" out-name="item7">
    <display-name>Allow Database Backup</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating firewall rule: Database Backup");

      var rule3 = nsxClient.createFirewallRule({
        name: "Allow-DB-Backup",
        segment: "DB-Tier-VLAN200",
        vlan: 200,
        sources: ["backup-server"],
        destinations: ["db-security-group"],
        destination: "10.10.200.50",
        services: ["SSH"],
        action: "ALLOW",
        direction: "INGRESS",
        description: "Allow backup server to access database via SSH"
      });

      System.log("Firewall rule created: " + rule3.id);
      ]]>
    </script>
  </workflow-item>

  <!-- Firewall Rule: Internet Egress (No segment - primary network) -->
  <workflow-item name="allowInternetEgress" type="task" out-name="item8">
    <display-name>Allow Internet Egress</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating firewall rule: Internet Egress");

      var rule4 = nsxClient.createFirewallRule({
        name: "Allow-Internet-Egress",
        sources: ["any"],
        destinations: ["internet"],
        services: ["HTTP", "HTTPS"],
        action: "ALLOW",
        direction: "EGRESS",
        description: "Allow all workloads to access internet on HTTP/HTTPS"
      });

      System.log("Firewall rule created: " + rule4.id);
      ]]>
    </script>
  </workflow-item>

  <!-- Firewall Rule: DNS (No segment - primary network) -->
  <workflow-item name="allowDns" type="task" out-name="item9">
    <display-name>Allow DNS Queries</display-name>
    <script encoded="false">
      <![CDATA[
      System.log("Creating firewall rule: DNS");

      var rule5 = nsxClient.createFirewallRule({
        name: "Allow-DNS",
        sources: ["any"],
        destinations: ["dns-servers"],
        services: ["DNS"],
        action: "ALLOW",
        description: "Allow all workloads to perform DNS queries"
      });

      System.log("Firewall rule created: " + rule5.id);
      ]]>
    </script>
  </workflow-item>

  <presentation/>
</workflow>
EOF
```

**What This Workflow Does**:
- Creates 3 NSX segments (Web, App, DB on VLANs 100, 150, 200)
- Creates 5 firewall rules:
  - 3 segment-specific rules (Web→App, App→DB, DB Backup)
  - 2 general rules (Internet, DNS) - no segment reference

---

## Part 2: Analysis and Intent Extraction (5 minutes)

### Step 3: Analyze the Workflow

ops-translate automatically detects NSX operations in vRealize workflows:

```bash
# Analyze to detect NSX operations
ops-translate analyze
```

**Note**: No need to run `import` since we created the file directly in `input/vrealize/`. The `import` command is only needed when copying files from outside the workspace.

**Expected Output**:
```
Analyzing automation for external dependencies...

Found 1 vRealize workflow(s) to analyze
Analyzing 1 changed file(s)

Analyzing nsx-3tier-app.workflow.xml...
  ⚠ nsx-3tier-app.workflow.xml: Found external dependencies

✓ Analysis reports written to intent/
  • analysis.vrealize.json - vRealize detection details
  • analysis.vrealize.md - Human-readable vRealize analysis
  • gaps.json - Classification data
  • gaps.md - Migration guidance

Gap Analysis Summary
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Classification           ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ ✅ Fully Supported       │     0 │
│ ⚠️ Partial Translation   │     8 │
│ 🎯 Expert-Guided         │     0 │
│ 🔧 Custom Implementation │     0 │
└──────────────────────────┴───────┘

Overall Assessment: Mostly Manual
```

**⚠️ IMPORTANT - Understanding "Partial Translation"**:

The "Partial Translation" status is **EXPECTED and CORRECT** for NSX operations. It does NOT mean the translation failed! Here's what it means:

- ✅ **Segments** → NetworkAttachmentDefinition (PARTIAL because you need to configure host network interfaces)
- ✅ **Firewall Rules** → NetworkPolicy/MultiNetworkPolicy (PARTIAL because OVN-Kubernetes is L3/L4 only, NSX has L7 features)

**What "Partial" REALLY Means**:
- ✅ YAMLs will be generated automatically
- ⚠️ You need to review limitations (documented in YAML comments)
- ⚠️ Some manual infrastructure setup required (VLAN interfaces on nodes)

**This is a SUCCESS** - all NSX operations were detected and will generate valid Kubernetes resources! The "Mostly Manual" message refers to infrastructure prerequisites, not translation failure.

### Step 4: Examine the Analysis

```bash
# View detected NSX operations
cat intent/analysis.vrealize.json | jq '.nsx_operations'
```

**Expected Output** (abbreviated):
```json
{
  "segments": [
    {
      "name": "Web-Tier-VLAN100",
      "location": "nsx-3tier-app.workflow.xml:24",
      "confidence": 0.95,
      "vlan_ids": [100],
      "subnets": ["10.10.100.0/24"],
      "gateway": "10.10.100.1",
      "evidence": "nsxClient.createSegment({displayName: 'Web-Tier-VLAN100', vlanIds: [100], subnets: ['10.10.100.0/24'], gateway: '10.10.100.1'})"
    },
    {
      "name": "App-Tier-VLAN150",
      "location": "nsx-3tier-app.workflow.xml:43",
      "confidence": 0.95,
      "vlan_ids": [150],
      "subnets": ["10.10.150.0/24"],
      "evidence": "..."
    },
    {
      "name": "DB-Tier-VLAN200",
      "location": "nsx-3tier-app.workflow.xml:62",
      "confidence": 0.95,
      "vlan_ids": [200],
      "subnets": ["10.10.200.0/24"],
      "evidence": "..."
    }
  ],
  "firewall_rules": [
    {
      "name": "Allow-Web-to-App",
      "location": "nsx-3tier-app.workflow.xml:81",
      "confidence": 0.95,
      "evidence": "nsxClient.createFirewallRule({name: 'Allow-Web-to-App', segment: 'Web-Tier-VLAN100', sources: ['web-security-group'], destinations: ['app-security-group'], services: ['HTTP', 'HTTPS'], action: 'ALLOW'})"
    },
    // ... 4 more rules
  ]
}
```

**Key Points**:
- ✅ All 3 segments detected with VLAN IDs and subnets
- ✅ All 5 firewall rules detected
- ✅ Evidence strings capture the original NSX API calls

---

## Part 3: Generation and Correlation (10 minutes)

### Step 5: Generate OpenShift Resources

```bash
# Generate all artifacts (correlation happens automatically)
ops-translate generate --profile lab

# View generated output structure
tree output/
```

> **Note: What is `--profile lab`?**
>
> The profile parameter selects environment-specific defaults from your `ops-translate.yaml` configuration:
> - **`lab`**: Development/testing environment (namespace: `virt-lab`, storage: `nfs`)
> - **`prod`**: Production environment (namespace: `virt-prod`, storage: `ceph-rbd`)
>
> For NSX network resources, the profile mainly affects the namespace where policies are deployed. The network policies themselves (VLANs, firewall rules) come directly from the NSX workflow.
>
> **To customize profiles**, edit `ops-translate.yaml` in your workspace:
> ```bash
> # Add a custom staging profile
> vi ops-translate.yaml
> ```
> ```yaml
> profiles:
>   lab:
>     default_namespace: virt-lab
>     default_storage_class: nfs
>   staging:  # Add your custom profile
>     default_namespace: virt-staging
>     default_storage_class: ceph-rbd
>   prod:
>     default_namespace: virt-prod
>     default_storage_class: ceph-rbd
> ```
> See [USER_GUIDE.md - Profile Configuration](USER_GUIDE.md#profile-configuration) for all available options.

**Expected Output**:
```
output/
├── multi-network-policies/        # Secondary networks (OVN-Kubernetes)
│   ├── README.md
│   ├── CORRELATION_REPORT.md
│   ├── web-tier-vlan100-allow-web-to-app.yaml
│   ├── app-tier-vlan150-allow-app-to-db.yaml
│   └── db-tier-vlan200-allow-db-backup.yaml
├── network-policies/               # Primary network (standard K8s)
│   ├── README.md
│   ├── allow-internet-egress.yaml
│   └── allow-dns.yaml
└── network-attachments/            # NetworkAttachmentDefinitions
    ├── README.md
    ├── web-tier-vlan100.yaml
    ├── app-tier-vlan150.yaml
    └── db-tier-vlan200.yaml
```

**What Happened**:
1. **Correlation Engine** analyzed each firewall rule's evidence
2. **Smart Routing**:
   - Rules mentioning segments → MultiNetworkPolicy
   - General rules → NetworkPolicy
3. **Three output types** generated automatically

### Step 6: Review the Correlation Report

This is the key artifact that explains how the correlation engine mapped rules to segments:

```bash
cat output/multi-network-policies/CORRELATION_REPORT.md
```

**Expected Content**:

````markdown
# NSX Segment-to-Rule Correlation Report

This report explains how NSX firewall rules were mapped to network segments (secondary networks).

## Summary

- **Primary Network Rules**: 2
- **Segments with Rules**: 3

## Primary Network Rules

These rules apply to the primary pod network (standard NetworkPolicy):

- `Allow-Internet-Egress`
- `Allow-DNS`

## Secondary Network Rules (MultiNetworkPolicy)

These rules were correlated to specific network segments:

### Segment: Web-Tier-VLAN100

- **NetworkAttachmentDefinition**: `default/web-tier-vlan100`
- **VLAN IDs**: 100
- **Subnets**: 10.10.100.0/24
- **Correlation Confidence**: 0.95
- **Firewall Rules**: 1

| Rule Name | Evidence |
|-----------|----------|
| `Allow-Web-to-App` | Rule evidence contains segment name 'Web-Tier-VLAN100' |

### Segment: App-Tier-VLAN150

- **NetworkAttachmentDefinition**: `default/app-tier-vlan150`
- **VLAN IDs**: 150
- **Subnets**: 10.10.150.0/24
- **Correlation Confidence**: 0.90
- **Firewall Rules**: 1

| Rule Name | Evidence |
|-----------|----------|
| `Allow-App-to-DB` | Rule evidence contains segment name 'App-Tier-VLAN150'; IP overlap with subnet |

### Segment: DB-Tier-VLAN200

- **NetworkAttachmentDefinition**: `default/db-tier-vlan200`
- **VLAN IDs**: 200
- **Subnets**: 10.10.200.0/24
- **Correlation Confidence**: 0.95
- **Firewall Rules**: 1

| Rule Name | Evidence |
|-----------|----------|
| `Allow-DB-Backup` | Rule evidence contains segment name 'DB-Tier-VLAN200'; VLAN ID match (200); IP overlap with subnet (10.10.200.50) |

## Correlation Methods

The correlation engine uses multiple detection strategies:

1. **Direct Reference** (0.90 confidence) - Rule evidence contains segment name
2. **IP Range Overlap** (0.70 confidence) - Rule IPs fall within segment subnet
3. **VLAN Matching** (0.70 confidence) - Same VLAN ID in rule and segment
4. **Proximity Analysis** (0.40 confidence) - Same workflow location
5. **Multi-Signal Boost** (+0.05 per additional signal, max +0.15)

Rules with confidence ≥ 0.50 are assigned to segments. Lower confidence rules default to primary network.

## Review Recommendations

- **High Confidence (≥ 0.85)**: Likely correct, but review YAML comments
- **Medium Confidence (0.65-0.84)**: Review carefully, validate IP ranges and VLANs
- **Low Confidence (0.50-0.64)**: Manual review recommended

For questions or issues with correlation, see the project documentation.
````

**Customer Value Highlight**:
> "Notice how the DB rule got **0.95 confidence** because it had 3 signals: segment name, VLAN ID, and IP overlap. This multi-signal validation reduces false positives."

### Step 7: Examine a MultiNetworkPolicy

```bash
cat output/multi-network-policies/web-tier-vlan100-allow-web-to-app.yaml
```

**Expected Content**:

```yaml
---
# Generated from vRealize workflow NSX firewall rule
# Source rule: Allow-Web-to-App
# Location: nsx-3tier-app.workflow.xml:81
#
# NETWORK SCOPE: SECONDARY NETWORK
# Segment: Web-Tier-VLAN100
# NetworkAttachmentDefinition: default/web-tier-vlan100
# VLAN IDs: 100
# Subnets: 10.10.100.0/24
#
# This MultiNetworkPolicy applies ONLY to traffic on the secondary network
# (NetworkAttachmentDefinition: web-tier-vlan100) and does NOT affect traffic on
# the primary pod network or other secondary networks.
#
# IMPORTANT: Pods must be attached to the secondary network for this policy
# to apply. Add this annotation to pod metadata:
#   k8s.v1.cni.cncf.io/networks: web-tier-vlan100
#
# LIMITATIONS - READ BEFORE DEPLOYING:
# - NSX supports L7 application-aware filtering; MultiNetworkPolicy is L3/L4 only
# - NSX supports FQDN-based rules; MultiNetworkPolicy requires pod selectors or IP/CIDR
# - NSX supports time-based rules; MultiNetworkPolicy is always active
# - NSX supports user/group-based rules; MultiNetworkPolicy is pod-based only
# - Review and test thoroughly in dev environment before production
#
apiVersion: k8s.cni.cncf.io/v1beta1
kind: MultiNetworkPolicy
metadata:
  name: web-tier-vlan100-allow-web-to-app
  namespace: default
  annotations:
    k8s.v1.cni.cncf.io/policy-for: default/web-tier-vlan100
    source-location: nsx-3tier-app.workflow.xml:81
  labels:
    translated-from: nsx-firewall
    source-workflow: nsx-3tier-app
    network-scope: secondary
    network-attachment: web-tier-vlan100
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: app-tier
    ports:
    - protocol: TCP
      port: 80
    - protocol: TCP
      port: 443
```

**Key Points to Highlight**:
- ✅ **OVN-Kubernetes API**: `k8s.cni.cncf.io/v1beta1` (standard OpenShift CNI)
- ✅ **Critical Annotation**: `k8s.v1.cni.cncf.io/policy-for` links to NAD
- ✅ **Comprehensive Comments**: Explains scope, limitations, deployment requirements
- ✅ **Traceability**: Source location annotated
- ✅ **Standard NetworkPolicy structure**: Easy for users to understand

### Step 8: Examine a NetworkAttachmentDefinition

```bash
cat output/network-attachments/web-tier-vlan100.yaml
```

**Expected Content**:

```yaml
---
# NetworkAttachmentDefinition for NSX Segment: Web-Tier-VLAN100
# Source: nsx-3tier-app.workflow.xml:24
#
# This defines a secondary network interface for pods that need access to
# the Web-Tier-VLAN100 network segment.
#
# To attach a pod to this network, add this annotation to pod metadata:
#   k8s.v1.cni.cncf.io/networks: web-tier-vlan100
#
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: web-tier-vlan100
  namespace: default
  labels:
    translated-from: nsx-segment
    source-workflow: nsx-3tier-app
    vlan-id: "100"
spec:
  config: |
    {
      "cniVersion": "0.3.1",
      "name": "web-tier-vlan100",
      "type": "bridge",
      "vlan": 100,
      "ipam": {
        "type": "whereabouts",
        "range": "10.10.100.0/24",
        "range_start": "10.10.100.10",
        "range_end": "10.10.100.250",
        "gateway": "10.10.100.1"
      }
    }
```

**Key Points**:
- ✅ **VLAN Tagging**: Matches NSX segment VLAN 100
- ✅ **IP Management**: Uses Whereabouts IPAM (standard for OpenShift)
- ✅ **Subnet Preservation**: Same 10.10.100.0/24 as NSX
- ✅ **Bridge CNI**: Standard for VLAN-tagged networks

---

## Part 4: OpenShift Deployment (15 minutes)

**Prerequisites**:
- OpenShift 4.12+ cluster
- Cluster admin access
- `oc` CLI configured

### Step 9: Prepare the Cluster

```bash
# Login to OpenShift
oc login https://your-cluster-api:6443

# Create namespace for demo
oc new-project nsx-demo

# Verify OVN-Kubernetes is running
oc get pods -n openshift-ovn-kubernetes

# Verify Multus is available
oc get pods -n openshift-multus
```

### Step 10: Deploy NetworkAttachmentDefinitions

```bash
# Apply NADs first (other resources depend on them)
oc apply -f output/network-attachments/ -n nsx-demo

# Verify NADs created
oc get network-attachment-definitions -n nsx-demo
```

**Expected Output**:
```
NAME                  AGE
web-tier-vlan100      5s
app-tier-vlan150      5s
db-tier-vlan200       5s
```

### Step 11: Deploy MultiNetworkPolicies

```bash
# Apply MultiNetworkPolicies for secondary networks
oc apply -f output/multi-network-policies/ -n nsx-demo

# Verify policies created
oc get multinetworkpolicies -n nsx-demo
```

**Expected Output**:
```
NAME                                  AGE
web-tier-vlan100-allow-web-to-app     3s
app-tier-vlan150-allow-app-to-db      3s
db-tier-vlan200-allow-db-backup       3s
```

### Step 12: Deploy Standard NetworkPolicies

```bash
# Apply NetworkPolicies for primary network
oc apply -f output/network-policies/ -n nsx-demo

# Verify policies created
oc get networkpolicies -n nsx-demo
```

**Expected Output**:
```
NAME                      POD-SELECTOR   AGE
allow-internet-egress     <none>         2s
allow-dns                 <none>         2s
```

---

## Part 5: Testing and Validation (10 minutes)

### Step 13: Create Test Pods

Create pods attached to the secondary networks to test the policies:

```bash
cat > test-pods.yaml <<'EOF'
---
# Web tier pod with secondary network
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
    ports:
    - containerPort: 8080

---
# App tier pod with secondary network
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
  - name: app
    image: nginxinc/nginx-unprivileged:alpine
    ports:
    - containerPort: 8080

---
# Database pod with secondary network
apiVersion: v1
kind: Pod
metadata:
  name: db-server
  namespace: nsx-demo
  labels:
    app: database
  annotations:
    k8s.v1.cni.cncf.io/networks: db-tier-vlan200
spec:
  containers:
  - name: mysql
    image: mysql:8
    env:
    - name: MYSQL_ROOT_PASSWORD
      value: demo-password-123
    ports:
    - containerPort: 3306
EOF

# Deploy test pods
oc apply -f test-pods.yaml

# Wait for pods to be ready
oc wait --for=condition=ready pod/web-server -n nsx-demo --timeout=60s
oc wait --for=condition=ready pod/app-server -n nsx-demo --timeout=60s
oc wait --for=condition=ready pod/db-server -n nsx-demo --timeout=60s
```

### Step 14: Verify Secondary Network Interfaces

```bash
# Check web-server has secondary interface
oc exec -n nsx-demo web-server -- ip addr show

# You should see:
# 1: lo: <LOOPBACK,UP,LOWER_UP> ...
# 2: eth0@if123: <BROADCAST,MULTICAST,UP,LOWER_UP> ... (primary network)
# 3: net1@if124: <BROADCAST,MULTICAST,UP,LOWER_UP> ... (secondary network - VLAN 100)
```

**Get IP addresses**:
```bash
# Get secondary network IPs
WEB_SECONDARY=$(oc exec -n nsx-demo web-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
APP_SECONDARY=$(oc exec -n nsx-demo app-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)
DB_SECONDARY=$(oc exec -n nsx-demo db-server -- ip -4 addr show net1 | grep inet | awk '{print $2}' | cut -d/ -f1)

echo "Web Secondary IP (VLAN 100): $WEB_SECONDARY"
echo "App Secondary IP (VLAN 150): $APP_SECONDARY"
echo "DB Secondary IP (VLAN 200): $DB_SECONDARY"
```

**Expected Output**:
```
Web Secondary IP (VLAN 100): 10.10.100.15
App Secondary IP (VLAN 150): 10.10.150.20
DB Secondary IP (VLAN 200): 10.10.200.25
```

### Step 15: Test Network Policy Enforcement

**Test 1: Web → App (should be allowed on ports 80, 443)**
```bash
# Install curl in web pod
oc exec -n nsx-demo web-server -- apk add curl

# Test HTTP (port 80) - Should succeed
oc exec -n nsx-demo web-server -- curl -s -o /dev/null -w "%{http_code}\n" http://$APP_SECONDARY:8080
# Expected: 200 (or connection success)

# Test HTTPS (port 443) - Should succeed
oc exec -n nsx-demo web-server -- curl -sk -o /dev/null -w "%{http_code}\n" https://$APP_SECONDARY:8443
# Expected: Connection success (or 200 if HTTPS configured)
```

**Test 2: Web → App on different port (should be denied)**
```bash
# Test SSH (port 22) - Should timeout/fail
oc exec -n nsx-demo web-server -- timeout 3 nc -zv $APP_SECONDARY 22
# Expected: Connection timeout (policy only allows 80, 443)
```

**Test 3: App → DB on MySQL port (should be allowed)**
```bash
# Install mysql client in app pod
oc exec -n nsx-demo app-server -- apk add mysql-client

# Test MySQL connection (port 3306) - Should succeed
oc exec -n nsx-demo app-server -- timeout 5 nc -zv $DB_SECONDARY 3306
# Expected: Connection succeeded
```

**Test 4: Direct Web → DB (should be denied - no policy)**
```bash
# Test MySQL from web (no policy allowing this) - Should timeout
oc exec -n nsx-demo web-server -- timeout 3 nc -zv $DB_SECONDARY 3306
# Expected: Connection timeout (no policy allows web → db directly)
```

### Step 16: View Policy Verdicts (Optional - if network observability enabled)

```bash
# If using OpenShift network observability
oc get flows -n nsx-demo

# Or check pod logs for connection attempts
oc logs -n nsx-demo web-server --tail=20
```

---

## Part 6: Demo Talking Points

### For Technical Stakeholders

**1. Automation Value**:
> "What you just saw would typically take a network engineer 2-3 weeks to manually translate. ops-translate did it in seconds with 95% confidence."

**2. Accuracy and Traceability**:
> "Every generated policy includes source location annotations. If you need to trace a policy back to the original NSX rule, it's right there in the YAML."

**3. Confidence Scoring**:
> "The correlation engine uses multiple signals - not just segment names, but also IP ranges, VLAN IDs, and proximity analysis. Multi-signal correlation achieves 95% confidence."

**4. OpenShift Native**:
> "These are standard OVN-Kubernetes MultiNetworkPolicy resources. No custom CRDs, no special operators - just what OpenShift 4.12+ provides out of the box."

### For Business Stakeholders

**1. Migration Acceleration**:
> "Network policy migration is often a blocker for VMware to OpenShift migrations. This removes that blocker."

**2. Risk Reduction**:
> "The correlation report provides full transparency into what decisions were made and why. No black box - you can review every mapping."

**3. Cost Savings**:
> "For a typical enterprise with 50+ NSX segments, manual translation costs ~$50K-$100K in consulting time. This reduces that to hours of review time."

**4. Preserves Security Posture**:
> "Your network segmentation doesn't disappear during migration. It's translated and maintained in OpenShift."

---

## Part 7: Cleanup

```bash
# Delete test pods
oc delete pod web-server app-server db-server -n nsx-demo

# Delete policies
oc delete multinetworkpolicies --all -n nsx-demo
oc delete networkpolicies --all -n nsx-demo

# Delete NADs
oc delete network-attachment-definitions --all -n nsx-demo

# Delete namespace
oc delete project nsx-demo

# Clean up demo workspace (optional)
cd ..
rm -rf nsx-multinetwork-demo
```

---

## Appendix: Common Questions

### Q: What if NSX rules don't reference segment names?

**A**: The correlation engine uses fallback strategies:
1. IP range overlap (0.70 confidence)
2. VLAN ID matching (0.70 confidence)
3. Proximity in workflow (0.40 confidence)

If confidence is below 0.50, the rule goes to primary network (NetworkPolicy). The correlation report flags these for manual review.

### Q: What NSX features aren't supported?

**A**: MultiNetworkPolicy is L3/L4 only. Not supported:
- L7 application-aware filtering
- FQDN-based rules
- Time-based rules
- User/group-based rules

These are automatically detected and documented in generated YAML comments.

### Q: Can we customize the generated policies?

**A**: Yes! Use template customization:
```bash
ops-translate init my-project --with-templates
# Edit templates/multi-network-policies/policy.yaml.j2
```

### Q: How do we validate on clusters without real NSX VLANs?

**A**: For testing, you can:
1. Use macvlan instead of bridge CNI (no VLAN tagging required)
2. Use kind/minikube with simulated secondary networks
3. Test policy logic with different namespaces (simulate network isolation)

---

## Next Steps

1. **Try with your NSX export**: Get a real vRealize workflow export from your customer
2. **Customize templates**: Add org-specific labels, annotations
3. **Integrate with CI/CD**: Automate policy generation in migration pipeline
4. **Customer validation**: Run correlation report by customer's network team

---

## Resources

- **Full Documentation**: See `/docs/guides/` in ops-translate repo
- **Testing Guide**: `docs/guides/TESTING_GUIDE.md`
- **Architecture**: `docs/technical/ARCHITECTURE.md`
- **Support**: Open issues on GitHub

---

**Demo prepared by**: ops-translate project team
**Last updated**: 2026-07-06
**Version**: 1.0
