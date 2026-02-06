# Demo Script: Virt-First Migration Scenario
## 2-3 Minute Talk Track

---

## Setup (Before Demo)

```bash
cd examples/virt-first-realworld
# Ensure clean state - remove any previous analysis
rm -rf .ops-translate/ ops-translate-report/
```

---

## Demo Flow

### Opening (15 seconds)

> "Let me show you how ops-translate helps with a real-world virt-first migration scenario. This is based on a mid-market financial services company migrating from VMware to OpenShift Virtualization."

**[SHOW: `examples/virt-first-realworld/` directory structure]**

```bash
tree -L 2 examples/virt-first-realworld/
```

---

### Context (30 seconds)

> "This customer has what most VMware shops have: **organic growth over 5+ years**."
>
> "They have **vRealize workflows** created by their Platform Engineering team..."

**[SHOW: vrealize/ directory]**

```bash
ls -1 vrealize/*.workflow.xml
```

> "...and **PowerCLI scripts** from their Infrastructure Ops team."

**[SHOW: powercli/ directory]**

```bash
ls -1 powercli/*.ps1
```

> "These tools have **different naming conventions, different standards, and drift**. That's normal. Let's see what ops-translate finds."

---

### Run Analysis (20 seconds)

**[RUN: ops-translate extract]**

```bash
ops-translate extract .
```

> "ops-translate extracts the **intent** from both vRealize XML and PowerCLI scripts, normalizes them, and analyzes migration readiness."

**[WAIT for completion - should take 10-20 seconds]**

---

### Show Report Overview (30 seconds)

**[OPEN: Report in browser]**

```bash
open ops-translate-report/index.html
```

> "Here's what it found. The migration readiness score is **MOSTLY_AUTOMATIC** - around 60-70% - which is realistic."
>
> **[POINT TO: Summary badges]**
>
> "We have **8-9 SUPPORTED** components like VM provisioning and compute resources - these translate cleanly to KubeVirt."
>
> "But we also have **4-6 PARTIAL** components - NSX features, approval workflows - that need manual work."
>
> "And **1-2 BLOCKED** items - NSX security groups that don't have direct OpenShift equivalents."

---

### Highlight Key Findings (45 seconds)

**[SCROLL TO: Component breakdown]**

> "Let's look at the details."
>
> **[POINT TO: Supported component - VM Provisioning]**
>
> "Simple VM provisioning? **Fully supported** - maps directly to KubeVirt VirtualMachine resources."
>
> **[POINT TO: Partial component - NSX Load Balancer]**
>
> "NSX load balancer? **Partial** - we can use OpenShift Routes and Services, but it's more limited than NSX. The report tells you exactly what's different."
>
> **[SCROLL TO: Conflicts section]**
>
> "Here's where it gets interesting - **conflicts and drift**."
>
> **[POINT TO: Naming conflicts]**
>
> "The vRealize workflows use `vmName` and `cpuCount`, but PowerCLI uses `vm_name` and `cpu_cores`. Different teams, different conventions."
>
> **[POINT TO: Resource drift]**
>
> "The legacy database workflow from 2019 uses 16GB RAM, but the newer PowerCLI standard is 32GB. ops-translate surfaces this and recommends standardizing."

---

### Call to Action (20 seconds)

> "The key insight: **This isn't a tool that just says 'yes you can migrate'**."
>
> "It gives you a **realistic assessment** with specific gaps, conflicts, and recommendations."
>
> "For this customer, they now know:
> - What they can automate (VM provisioning, compute, storage)
> - What needs manual work (NSX alternatives, approval integration)
> - What conflicts need resolution before migration
>
> "That's how you de-risk a virt-first migration."

---

## Alternative Flows

### If You Want to Deep Dive (Add 1-2 minutes)

**Show specific workflow:**

```bash
# Show the legacy workflow
cat vrealize/old-db-provisioning-DO-NOT-MODIFY.workflow.xml | grep -A 5 "temp1"
```

> "Look at this legacy workflow - hard-coded vCenter IPs, variable names like 'temp1', comments saying 'DO NOT MODIFY'. ops-translate still extracts the intent and shows you what it does, but flags the technical debt."

**Show PowerCLI conflict:**

```bash
# Show parameter differences
grep "Param" powercli/New-StandardVM.ps1 -A 10
grep "param name=" vrealize/provision-vm-with-approval.workflow.xml | head -5
```

> "Different teams, different naming. ops-translate catches all of this."

---

## Key Messages for Different Audiences

### For Sales/Marketing:
- "Real-world scenarios with real complexity"
- "Not just 'lift and shift' - surfaces real gaps and conflicts"
- "Actionable recommendations, not just 'good luck'"

### For Product Managers:
- "Handles multiple source types (vRealize + PowerCLI)"
- "Detects drift and conflicts across automation tools"
- "Provides migration readiness scoring with detail"

### For Engineers:
- "Extracts normalized intent from XML and PowerShell"
- "Classifies components by translatability (Supported/Partial/Blocked)"
- "LLM-powered extraction with manual override capability"

---

## Q&A Preparation

**Q: "Does this actually generate the KubeVirt manifests?"**
A: "Not yet - Phase 1 is analysis and gap detection. Phase 2 will be automated translation for SUPPORTED components."

**Q: "What if we have more tools - Terraform, Ansible?"**
A: "The architecture is pluggable. You can add new extractors for any IaC tool. The intent format is tool-agnostic."

**Q: "How does it handle NSX when there's no direct equivalent?"**
A: "It's honest - it says 'PARTIAL' or 'BLOCKED' and tells you why. For NSX micro-segmentation, it recommends NetworkPolicy but notes the limitations. Customers need to know that."

**Q: "What about the conflicts - does it auto-resolve them?"**
A: "No - it surfaces them and recommends a path forward. For example, if PowerCLI uses 32GB and vRealize uses 16GB, it'll suggest standardizing on 32GB, but you decide."

---

## Reset for Next Demo

```bash
# Clean up analysis results
rm -rf .ops-translate/ ops-translate-report/
```

---

## Timing Breakdown

- **Opening**: 15 sec
- **Context**: 30 sec
- **Run Analysis**: 20 sec
- **Show Report Overview**: 30 sec
- **Highlight Key Findings**: 45 sec
- **Call to Action**: 20 sec

**Total**: ~2:40 minutes

---

## Tips for Success

1. **Practice the flow** - know where to click in the report
2. **Have the report pre-generated** as backup (in case of network/LLM issues)
3. **Emphasize realism** - this is messy on purpose, like real customers
4. **Show the value** - specific recommendations, not vague "good luck"
5. **Be honest about gaps** - NSX doesn't have perfect equivalents, and that's okay
