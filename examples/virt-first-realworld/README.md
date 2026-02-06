# Virt-First Migration Scenario: Acme Financial Services

## Customer Profile

**Organization:** Acme Financial Services
**Industry:** Financial Services / Banking
**Size:** Mid-market (2,000 employees)
**Current Infrastructure:** VMware vSphere 7.0 with NSX-T, vRealize Orchestrator, PowerCLI automation
**Migration Driver:** Cost optimization, modernization roadmap, reduce VMware licensing costs
**Timeline:** 18-24 month phased migration

## Current State

Acme Financial Services operates a mixed VMware environment that has evolved organically over 5+ years:

### Infrastructure Components

1. **vRealize Orchestrator (vRO)** - Used by the Platform Engineering team for:
   - Production VM provisioning with governance workflows
   - NSX-based micro-segmentation for web applications
   - Database tier provisioning (legacy workflow from 2019)
   - Automated load balancer configuration

2. **PowerCLI Scripts** - Used by Infrastructure Operations team for:
   - Day-to-day VM provisioning (faster for simple cases)
   - Snapshot management and backup coordination
   - Ad-hoc environment creation (dev/test)
   - Database VM deployments (newer standard, conflicts with legacy vRO)

3. **NSX-T Integration** - Security and networking:
   - Distributed firewall rules for tier-based isolation (web/app/db)
   - Security groups for environment segregation
   - Load balancers for web tier applications
   - Overlay segments for application networks

### Organizational Reality

The drift and inconsistencies in this environment are **intentional and realistic**:

- **Team Silos**: Platform Engineering owns vRealize, Infrastructure Ops owns PowerCLI
- **Evolution Over Time**: Standards have changed (16GB RAM → 32GB RAM for databases)
- **Legacy Baggage**: A 2019 database workflow is marked "DO NOT MODIFY" and still in production
- **Tooling Preferences**: Ops team finds PowerCLI faster for simple tasks, Platform team prefers vRO for governance
- **Naming Conflicts**: Different teams use different conventions (vmName vs vm_name, cost-center vs CostCenter)
- **Type Mismatches**: PowerCLI uses strict enums and integers, vRO uses flexible strings and numbers

This is **not poor practice** - this is reality in organizations with:
- Multiple teams with different tooling expertise
- Years of organic growth without centralized automation governance
- Legacy workflows that work and are risky to change
- Migration from manual → semi-automated → fully automated over time

## Migration Strategy: Virt-First Approach

Acme has chosen a **virt-first** migration strategy (also called "lift-and-shift-then-modernize"):

### Phase 1: OpenShift Virtualization (Months 1-12)
- Migrate existing VM workloads to KubeVirt on OpenShift
- Maintain VM-based architecture initially
- Reduce VMware licensing costs immediately
- Learn OpenShift platform with familiar VM paradigm
- **Goal**: 70% of VMs migrated to OpenShift Virtualization by month 12

### Phase 2: Container-Native Transformation (Months 13-24)
- Refactor suitable workloads to containers
- Re-platform stateless applications (web tier first)
- Modernize CI/CD pipelines
- Adopt cloud-native patterns incrementally

### Why Virt-First?

1. **Risk Mitigation**: Smaller change increments, easier rollback
2. **Skills Development**: Operations team learns OpenShift gradually
3. **Business Continuity**: Applications keep running with minimal changes
4. **Cost Optimization**: Immediate savings from reduced VMware licensing
5. **Pragmatic**: Transformation is a journey, not a one-time event

## What This Scenario Contains

### Input Files

#### vRealize Orchestrator Workflows (4 workflows)

1. **`provision-vm-with-nsx-firewall.workflow.xml`** (NSX-heavy)
   - Provisions VM and configures NSX security groups
   - Creates tier-based firewall rules (web/app/db isolation)
   - **Expected Analysis**: NSX security groups → BLOCKED or PARTIAL

2. **`provision-web-app-with-nsx-lb.workflow.xml`** (NSX-heavy)
   - Creates NSX overlay segment
   - Provisions multiple web tier VMs
   - Configures NSX load balancer pool and virtual server
   - **Expected Analysis**: NSX segments and LB → PARTIAL (NetworkPolicy limited alternative)

3. **`provision-vm-with-approval.workflow.xml`** (Governance)
   - Production approval workflow
   - Environment-based resource selection
   - Cost center validation and tagging
   - **Expected Analysis**: Approval logic → PARTIAL (requires custom integration)

4. **`old-db-provisioning-DO-NOT-MODIFY.workflow.xml`** (Legacy)
   - Hard-coded vCenter IP addresses and cluster names
   - Ignores memory input parameter (always forces 16GB)
   - Unclear variable names (temp1, temp2, temp3)
   - Comments like "Don't touch this - it works!"
   - **Expected Analysis**: Should extract intent but surface hardcoded values as technical debt

#### PowerCLI Scripts (4 scripts)

1. **`New-StandardVM.ps1`**
   - Standard VM provisioning with different naming than vRO (vm_name vs vmName)
   - Uses enum for Environment (Development/Staging/Production) vs vRO strings
   - Different tag schema (cost-center vs CostCenter)
   - **Conflicts**: Naming conventions, type definitions, metadata keys

2. **`Deploy-DatabaseVM.ps1`**
   - Newer DB standard (32GB RAM) conflicts with legacy vRO (16GB)
   - Different cluster and VLAN selection
   - Parameter name conflicts (db_name vs dbname)
   - **Conflicts**: Resource specifications, infrastructure topology, standards drift

3. **`Provision-WebTier.ps1`**
   - Uses traditional port groups, NOT NSX segments
   - Manual NSX configuration required (comments warn about this)
   - Type conflicts (int vs number)
   - **Conflicts**: NSX automation gap, network approach, parameter types

4. **`Manage-VMSnapshots.ps1`**
   - VM-level snapshot management
   - Different from storage-level snapshots
   - **Conflicts**: Snapshot strategy differences

### Expected Conflicts and Gaps

When you run `ops-translate` on this scenario, it should detect:

#### 1. Naming Convention Conflicts
```
CONFLICT: Different parameter names for same concept
  - vRealize: vmName, cpuCount, memoryGB, costCenter
  - PowerCLI: vm_name, cpu_cores, memory_gb, cost-center, CostCenter

Recommendation: Standardize on Kubernetes-style naming (vm_name, cpu_cores, memory_gb)
```

#### 2. Type Mismatches
```
CONFLICT: Environment parameter has inconsistent types
  - vRealize: string (accepts "prod", "dev", "staging")
  - PowerCLI New-StandardVM: enum (Development, Staging, Production)
  - PowerCLI Deploy-DatabaseVM: string (prod, dev, uat)

Recommendation: Define canonical enum values for OpenShift
```

#### 3. Resource Specification Drift
```
CONFLICT: Database VM memory specifications differ
  - Legacy vRO workflow: 16GB (hard-coded, ignores parameter)
  - PowerCLI script: 32GB (new standard)

Recommendation: Adopt 32GB standard for KubeVirt VMs
```

#### 4. NSX Translation Gaps
```
BLOCKED/PARTIAL: NSX features require alternatives
  - NSX Security Groups → NetworkPolicy (limited compared to NSX)
  - NSX Distributed Firewall → NetworkPolicy (less granular)
  - NSX Load Balancer → OpenShift Routes + Service (basic LB only)
  - NSX Segments → Multus CNI (requires additional setup)

Recommendation: Review NetworkPolicy limitations vs NSX micro-segmentation
```

#### 5. Metadata/Tagging Conflicts
```
CONFLICT: Inconsistent tag keys across sources
  - cost_center vs cost-center vs CostCenter
  - created-by vs ProvisionedBy vs ManagedBy
  - env vs Environment vs Env

Recommendation: Map to Kubernetes labels with standard keys
```

#### 6. Infrastructure Topology Drift
```
CONFLICT: Different cluster and network selections
  - vRO uses: PROD-DB-Cluster, VLAN_200
  - PowerCLI uses: PROD-DB-Cluster-New, VLAN-250-DB

Impact: Migration requires mapping diverse source topologies to OpenShift
```

## How to Run This Scenario

### Prerequisites

```bash
# Install ops-translate
git clone https://github.com/tsanders-rh/ops-translate
cd ops-translate
pip install -e .

# Set up LLM access (optional but recommended)
export OPS_TRANSLATE_LLM_API_KEY="your-api-key"
```

### Run Analysis

```bash
# From the ops-translate repository root
ops-translate extract examples/virt-first-realworld/

# The tool will:
# 1. Extract intent from vRealize workflows (XML → normalized YAML)
# 2. Extract intent from PowerCLI scripts (PS1 → normalized YAML)
# 3. Classify components (SUPPORTED, PARTIAL, BLOCKED)
# 4. Detect conflicts and drift
# 5. Generate HTML report with migration paths
```

### Review Results

```bash
# Open the generated report
open examples/virt-first-realworld/ops-translate-report/index.html
```

### Expected Report Sections

1. **Migration Readiness Summary**
   - Overall translatability score: MOSTLY_AUTOMATIC (expect 60-75%)
   - Supported components: ~8-10 (VM provisioning, compute, basic networking)
   - Partial components: ~4-6 (NSX features, approval workflows, guest customization)
   - Blocked components: ~1-2 (NSX security groups, advanced NSX features)

2. **Component Analysis**
   - Detailed breakdown of each component type
   - OpenShift equivalents and migration paths
   - Recommendations for each component

3. **Conflicts and Drift**
   - Naming convention conflicts (at least 5 detected)
   - Type mismatches (at least 3 detected)
   - Resource specification drift (at least 2 detected)
   - Merge strategies recommended

4. **Migration Recommendations**
   - Prioritized migration paths
   - Manual steps required for NSX alternatives
   - Governance integration points (approval workflows)

## Success Criteria

This scenario is successful if `ops-translate` produces a report that:

1. ✅ Shows a realistic mix of SUPPORTED, PARTIAL, and BLOCKED components (not all green)
2. ✅ Surfaces naming conflicts between PowerCLI and vRealize
3. ✅ Identifies type mismatches (enum vs string, integer vs number)
4. ✅ Highlights NSX components as requiring alternatives
5. ✅ Detects drift in resource specifications (16GB vs 32GB)
6. ✅ Provides actionable recommendations for each gap
7. ✅ Shows migration readiness as MOSTLY_AUTOMATIC (not FULLY_TRANSLATABLE)

## Key Insights for Product Teams

This scenario demonstrates that **ops-translate must be opinionated yet realistic**:

### Must Surface Real Gaps
- Not everything can be fully automated (NSX → NetworkPolicy has real limitations)
- Legacy workflows have technical debt that needs visibility
- Drift is normal and needs to be detected and reconciled

### Must Provide Value to Practitioners
- Clear recommendations (not just "this is hard")
- Migration paths with concrete steps
- Prioritization guidance (what to fix first)

### Must Handle Real-World Messiness
- Multiple automation tools (vRO + PowerCLI)
- Inconsistent naming and types
- Organizational silos reflected in code
- Years of organic evolution

## Next Steps After Analysis

For a customer like Acme, the next steps after running ops-translate would be:

1. **Week 1-2**: Review report with stakeholders (Platform + Ops teams)
2. **Week 3-4**: Standardize naming conventions and types (create canonical schema)
3. **Week 5-6**: Pilot migration of 3-5 simple VMs (no NSX dependencies)
4. **Week 7-8**: Evaluate NetworkPolicy vs NSX gap, plan compensating controls
5. **Month 3**: Begin Phase 1 migrations (20% of VMs)
6. **Month 6**: Review and adjust based on lessons learned
7. **Month 12**: Complete 70% of VM migrations to OpenShift Virtualization
8. **Month 13+**: Begin Phase 2 container-native transformations

---

## Questions or Feedback?

This scenario is designed to be realistic and representative of mid-market VMware customers
pursuing virt-first migrations to OpenShift Virtualization.

If you find issues or have suggestions for making it more realistic, please open an issue
in the ops-translate repository.
