# NSX Policy API Parser Implementation Plan

**Date**: 2026-07-18
**Author**: Todd Sanders
**Status**: Planning
**Target Delivery**: 3-4 weeks

---

## Executive Summary

Add NSX Policy API JSON export support to ops-translate to enable migration of NSX firewall rules to OpenShift MultiNetworkPolicy for customers who cannot provide vRealize Orchestrator workflows.

**Business Driver**: Active customer engagement needs to migrate 1268 NSX firewall rules to Kubernetes MultiNetworkPolicies.

**Current State**: ops-translate only supports vRealize Orchestrator workflow XML
**Target State**: Support both vRealize XML and NSX Policy API JSON inputs

---

## Customer Context

**Source**: Red Hat Consulting engagement via @rspazzol (Slack)

**Customer Environment**:
- NSX Policy API export: 220k line JSON file
- 540 Security Policies
- 1268 Firewall Rules
- 2 IDS Policies (cannot be translated - known gap)
- Target platform: OpenShift with OVN-Kubernetes CNI

**Customer Need**:
- Automated translation of NSX firewall rules → MultiNetworkPolicy
- Preserve network segmentation during VMware → OpenShift migration
- Reduce manual migration effort (weeks → hours)

**Timeline**: Active engagement - needs solution ASAP (POC quality acceptable)

---

## Problem Statement

### Current Limitations

1. **Input Format Gap**
   - Current: vRealize Orchestrator workflow XML only
   - Customer has: NSX Policy API JSON export
   - No parser exists for NSX Policy API format

2. **Scale Untested**
   - Current testing: 5-10 rules
   - Customer needs: 1268 rules
   - Correlation engine performance at scale unknown

3. **IDS Rules**
   - Customer has IDS rules (intrusion detection)
   - Kubernetes has no IDS equivalent
   - Need clear handling strategy

### Requirements

**Functional Requirements**:
- Parse NSX Policy API JSON export format
- Extract SecurityPolicy objects and rules
- Detect and flag IdsSecurityPolicy objects (cannot translate)
- Resolve object references (Groups, Services, Segments)
- Handle incomplete exports gracefully (missing references)
- Map to existing correlation engine format
- Support group-based scoping → Kubernetes label selectors

**Non-Functional Requirements**:
- Handle 1268+ rules efficiently
- Process 220k+ line JSON files
- Provide clear error messages for parse failures
- Document non-translatable items (IDS rules)
- Maintain backward compatibility with vRealize parser

**Success Criteria**:
- ✓ Parse customer's 220k line export successfully
- ✓ Extract all 1268 firewall rules
- ✓ Flag 2 IDS policies as non-translatable with guidance
- ✓ Generate valid MultiNetworkPolicy YAML
- ✓ Correlation engine processes rules correctly
- ✓ 80%+ of rules translate without manual intervention

---

## Technical Approach

### Architecture Design

**Principle**: Add NSX Policy API as pluggable input adapter, reuse existing correlation and generation logic.

```
┌─────────────────────────────────────────────────────┐
│                    ops-translate                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Input Parsers (Pluggable)                          │
│  ┌──────────────────┐  ┌─────────────────────────┐ │
│  │ vRealize Parser  │  │ NSX Policy API Parser   │ │
│  │ (existing)       │  │ (NEW)                   │ │
│  │                  │  │                         │ │
│  │ .xml → Analysis  │  │ .json → Analysis        │ │
│  └────────┬─────────┘  └────────┬────────────────┘ │
│           │                     │                   │
│           └──────────┬──────────┘                   │
│                      ▼                               │
│           ┌──────────────────────┐                  │
│           │ Common Data Model    │                  │
│           │ AnalysisResult       │                  │
│           │ - firewall_rules     │                  │
│           │ - segments           │                  │
│           │ - ids_rules (flagged)│                  │
│           │ - gaps               │                  │
│           └──────────┬───────────┘                  │
│                      ▼                               │
│           ┌──────────────────────┐                  │
│           │ Correlation Engine   │                  │
│           │ (shared - no changes)│                  │
│           └──────────┬───────────┘                  │
│                      ▼                               │
│           ┌──────────────────────┐                  │
│           │ Output Generators    │                  │
│           │ (shared - no changes)│                  │
│           │ - MultiNetworkPolicy │                  │
│           │ - NetworkAttachment  │                  │
│           └──────────────────────┘                  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### File Structure

```
ops-translate/
├── src/ops_translate/
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract parser interface
│   │   ├── vrealize.py                # Existing - no changes
│   │   └── nsx_policy_api.py          # NEW
│   │
│   ├── models/
│   │   ├── nsx_policy/                # NEW
│   │   │   ├── __init__.py
│   │   │   ├── security_policy.py     # SecurityPolicy model
│   │   │   ├── ids_policy.py          # IdsSecurityPolicy model
│   │   │   ├── group.py               # Group model
│   │   │   ├── service.py             # Service model
│   │   │   └── segment.py             # Segment model (if available)
│   │   │
│   │   └── common.py                  # Shared AnalysisResult model
│   │
│   └── cli/
│       └── analyze.py                 # Update to auto-detect parser
│
├── tests/
│   ├── parsers/
│   │   └── test_nsx_policy_api.py     # NEW - parser tests
│   │
│   └── fixtures/
│       └── nsx_policy_api/            # NEW - test data
│           ├── sample_export.json     # Sanitized customer data
│           ├── security_policy.json   # Unit test samples
│           └── ids_policy.json
│
└── docs/
    ├── parsers/
    │   └── NSX_POLICY_API.md          # NEW - parser documentation
    │
    └── plans/
        └── NSX_POLICY_API_PARSER.md   # This document
```

### Data Model

**NSX Policy API Objects** (from Broadcom schema):

```python
# models/nsx_policy/security_policy.py

from pydantic import BaseModel
from typing import List, Optional

class SecurityRule(BaseModel):
    """NSX SecurityPolicy Rule"""
    id: str
    display_name: str
    resource_type: str
    rule_id: int
    sequence_number: int

    # Rule definition
    source_groups: List[str]          # ["ANY"] or ["/infra/.../groups/X"]
    destination_groups: List[str]
    services: List[str]                # ["ANY"] or ["/infra/services/HTTP"]
    scope: List[str]                   # Which segments/groups this applies to

    # Action and direction
    action: str                        # "ALLOW", "DROP", "REJECT"
    direction: str                     # "IN", "OUT", "IN_OUT"
    ip_protocol: str                   # "IPV4_IPV6", "IPV4", "IPV6"

    # Metadata
    logged: bool
    disabled: bool
    notes: Optional[str]
    sources_excluded: bool
    destinations_excluded: bool

class SecurityPolicy(BaseModel):
    """NSX SecurityPolicy containing multiple rules"""
    id: str
    display_name: str
    resource_type: str = "SecurityPolicy"
    path: str

    # Policy settings
    category: str                      # "Application", "Environment", etc.
    stateful: bool
    sequence_number: int

    # Rules
    children: List[dict]               # ChildSecurityRule objects

    # Metadata
    marked_for_delete: bool
    _create_time: Optional[int]
    _create_user: Optional[str]
    _last_modified_time: Optional[int]
    _last_modified_user: Optional[str]

class IdsSecurityPolicy(BaseModel):
    """IDS Policy - flagged as non-translatable"""
    id: str
    display_name: str
    resource_type: str = "IdsSecurityPolicy"
    path: str
    category: str = "ThreatRules"

    # IDS-specific
    children: List[dict]               # ChildIdsRule objects

    # Metadata
    sequence_number: int
    marked_for_delete: bool

class Group(BaseModel):
    """NSX Group definition"""
    id: str
    display_name: str
    resource_type: str = "Group"
    path: str

    # Group membership
    expression: Optional[List[dict]]   # Membership criteria

class Service(BaseModel):
    """NSX Service definition"""
    id: str
    display_name: str
    resource_type: str = "Service"
    path: str

    # Service definition
    service_entries: List[dict]        # Port/protocol definitions
```

**Common Output Model** (existing - no changes):

```python
# models/common.py

class AnalysisResult(BaseModel):
    """Shared output format from all parsers"""
    firewall_rules: List[FirewallRule]
    segments: List[NetworkSegment]
    ids_rules: List[IdsRule]           # Flagged for documentation
    gaps: List[Gap]
    metadata: dict
```

### Parser Implementation

**Core Parser Class**:

```python
# parsers/nsx_policy_api.py

import json
from typing import Dict, List, Optional
from pathlib import Path

from ops_translate.models.nsx_policy.security_policy import (
    SecurityPolicy, SecurityRule, IdsSecurityPolicy
)
from ops_translate.models.nsx_policy.group import Group
from ops_translate.models.nsx_policy.service import Service
from ops_translate.models.common import AnalysisResult, Gap

class NSXPolicyAPIParser:
    """Parser for NSX Policy API JSON exports"""

    def __init__(self, export_file: Path):
        self.export_file = export_file
        self.data = None

        # Object indexes for reference resolution
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.ids_policies: Dict[str, IdsSecurityPolicy] = {}
        self.groups: Dict[str, Group] = {}
        self.services: Dict[str, Service] = {}
        self.segments: Dict[str, dict] = {}

    def parse(self) -> AnalysisResult:
        """Main parsing entry point"""

        # 1. Load JSON export
        self._load_export()

        # 2. Build object indexes
        self._index_objects()

        # 3. Parse security policies
        firewall_rules = self._parse_security_policies()

        # 4. Parse IDS policies (flag as non-translatable)
        ids_rules = self._parse_ids_policies()

        # 5. Extract segments (if available)
        segments = self._extract_segments()

        # 6. Identify gaps and missing references
        gaps = self._identify_gaps()

        return AnalysisResult(
            firewall_rules=firewall_rules,
            segments=segments,
            ids_rules=ids_rules,
            gaps=gaps,
            metadata={
                'parser': 'nsx-policy-api',
                'export_file': str(self.export_file),
                'total_policies': len(self.security_policies),
                'total_rules': len(firewall_rules),
                'ids_policies': len(ids_rules),
            }
        )

    def _load_export(self):
        """Load and validate JSON export"""
        with open(self.export_file, 'r') as f:
            self.data = json.load(f)

        # Validate structure
        if not isinstance(self.data, list):
            raise ValueError("Expected JSON array of NSX policy objects")

    def _index_objects(self):
        """Build indexes of all objects for reference resolution"""

        for obj in self.data:
            resource_type = obj.get('resource_type')
            path = obj.get('path')

            if resource_type == 'SecurityPolicy':
                policy = SecurityPolicy(**obj)
                self.security_policies[path] = policy

            elif resource_type == 'IdsSecurityPolicy':
                policy = IdsSecurityPolicy(**obj)
                self.ids_policies[path] = policy

            elif resource_type == 'Group':
                group = Group(**obj)
                self.groups[path] = group

            elif resource_type == 'Service':
                service = Service(**obj)
                self.services[path] = service

            elif resource_type == 'Segment':
                self.segments[path] = obj

    def _parse_security_policies(self) -> List[FirewallRule]:
        """Extract firewall rules from SecurityPolicy objects"""

        rules = []

        for policy_path, policy in self.security_policies.items():
            # Extract rules from policy children
            for child in policy.children:
                if 'SecurityRule' in child:
                    rule_data = child['SecurityRule']
                    rule = SecurityRule(**rule_data)

                    # Convert to common FirewallRule format
                    firewall_rule = self._convert_to_firewall_rule(
                        rule, policy
                    )
                    rules.append(firewall_rule)

        return rules

    def _convert_to_firewall_rule(
        self,
        nsx_rule: SecurityRule,
        policy: SecurityPolicy
    ) -> FirewallRule:
        """Convert NSX SecurityRule to common FirewallRule format"""

        # Resolve group references
        source_groups = self._resolve_groups(nsx_rule.source_groups)
        dest_groups = self._resolve_groups(nsx_rule.destination_groups)

        # Resolve service references
        services = self._resolve_services(nsx_rule.services)

        # Resolve scope (which segments/groups rule applies to)
        scope = self._resolve_scope(nsx_rule.scope)

        return FirewallRule(
            id=nsx_rule.id,
            name=nsx_rule.display_name,
            source_groups=source_groups,
            destination_groups=dest_groups,
            services=services,
            scope=scope,
            action=nsx_rule.action,
            direction=nsx_rule.direction,
            sequence=nsx_rule.sequence_number,
            metadata={
                'policy_name': policy.display_name,
                'policy_category': policy.category,
                'nsx_rule_id': nsx_rule.rule_id,
                'stateful': policy.stateful,
            }
        )

    def _resolve_groups(self, group_refs: List[str]) -> List[str]:
        """Resolve group path references to group details"""

        if group_refs == ["ANY"]:
            return ["ANY"]

        resolved = []
        for ref in group_refs:
            if ref in self.groups:
                group = self.groups[ref]
                resolved.append({
                    'name': group.display_name,
                    'path': ref,
                    'expression': group.expression,
                })
            else:
                # Missing reference - log and use placeholder
                self._log_missing_reference('Group', ref)
                resolved.append({
                    'name': ref.split('/')[-1],  # Extract name from path
                    'path': ref,
                    'missing': True,
                })

        return resolved

    def _resolve_services(self, service_refs: List[str]) -> List[str]:
        """Resolve service path references to service definitions"""

        if service_refs == ["ANY"]:
            return ["ANY"]

        resolved = []
        for ref in service_refs:
            if ref in self.services:
                service = self.services[ref]
                resolved.append({
                    'name': service.display_name,
                    'path': ref,
                    'entries': service.service_entries,
                })
            else:
                # Missing reference - log and use placeholder
                self._log_missing_reference('Service', ref)
                resolved.append({
                    'name': ref.split('/')[-1],
                    'path': ref,
                    'missing': True,
                })

        return resolved

    def _resolve_scope(self, scope_refs: List[str]) -> List[str]:
        """Resolve scope references (which segments rule applies to)"""

        resolved = []
        for ref in scope_refs:
            # Could be group or segment
            if ref in self.groups:
                group = self.groups[ref]
                resolved.append({
                    'type': 'group',
                    'name': group.display_name,
                    'path': ref,
                })
            elif ref in self.segments:
                segment = self.segments[ref]
                resolved.append({
                    'type': 'segment',
                    'name': segment.get('display_name'),
                    'path': ref,
                })
            else:
                self._log_missing_reference('Scope', ref)
                resolved.append({
                    'type': 'unknown',
                    'name': ref.split('/')[-1],
                    'path': ref,
                    'missing': True,
                })

        return resolved

    def _parse_ids_policies(self) -> List[IdsRule]:
        """Parse IDS policies - flagged as non-translatable"""

        ids_rules = []

        for policy_path, policy in self.ids_policies.items():
            for child in policy.children:
                if 'IdsRule' in child:
                    rule_data = child['IdsRule']

                    ids_rules.append(IdsRule(
                        id=rule_data['id'],
                        name=rule_data['display_name'],
                        action=rule_data['action'],  # "DETECT"
                        scope=rule_data['scope'],
                        profiles=rule_data['ids_profiles'],
                        translatable=False,
                        reason="Kubernetes has no native IDS capability",
                        recommendation="Consider Falco, Tetragon, or enterprise security platform"
                    ))

        return ids_rules

    def _extract_segments(self) -> List[NetworkSegment]:
        """Extract network segments if available in export"""

        segments = []
        for path, segment_data in self.segments.items():
            segments.append(NetworkSegment(
                name=segment_data.get('display_name'),
                vlan=segment_data.get('vlan_ids', []),
                subnet=segment_data.get('subnets', []),
                path=path,
            ))

        return segments

    def _identify_gaps(self) -> List[Gap]:
        """Identify translation gaps and limitations"""

        gaps = []

        # Missing references
        if self.missing_references:
            gaps.append(Gap(
                type='missing_references',
                severity='warning',
                description=f"Export contains {len(self.missing_references)} missing object references",
                items=self.missing_references,
                impact="Rules referencing missing objects will use placeholder values",
                recommendation="Request complete export from NSX Manager"
            ))

        # IDS rules
        if self.ids_policies:
            gaps.append(Gap(
                type='ids_policies',
                severity='info',
                description=f"Found {len(self.ids_policies)} IDS policies that cannot be translated",
                items=[p.display_name for p in self.ids_policies.values()],
                impact="IDS functionality not preserved in Kubernetes",
                recommendation="Implement runtime security solution (Falco, Tetragon, etc.)"
            ))

        return gaps

    def _log_missing_reference(self, obj_type: str, path: str):
        """Track missing object references for gap reporting"""
        if not hasattr(self, 'missing_references'):
            self.missing_references = []

        self.missing_references.append({
            'type': obj_type,
            'path': path,
        })
```

### CLI Integration

**Auto-detect parser based on file extension**:

```python
# cli/analyze.py

def analyze_command(input_file: Path, parser: Optional[str] = None):
    """Analyze NSX or vRealize input"""

    # Auto-detect parser if not specified
    if parser is None:
        if input_file.suffix == '.json':
            parser = 'nsx-policy-api'
        elif input_file.suffix == '.xml':
            parser = 'vrealize'
        else:
            raise ValueError(f"Cannot determine parser for {input_file.suffix}")

    # Load appropriate parser
    if parser == 'nsx-policy-api':
        from ops_translate.parsers.nsx_policy_api import NSXPolicyAPIParser
        parser_instance = NSXPolicyAPIParser(input_file)
    elif parser == 'vrealize':
        from ops_translate.parsers.vrealize import VRealizeParser
        parser_instance = VRealizeParser(input_file)
    else:
        raise ValueError(f"Unknown parser: {parser}")

    # Parse and analyze
    result = parser_instance.parse()

    # Continue with correlation engine...
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Goal**: Set up data models and basic parser structure

**Tasks**:
1. Create NSX Policy models using Pydantic
   - SecurityPolicy, SecurityRule
   - IdsSecurityPolicy, IdsRule
   - Group, Service, Segment
   - Reference Broadcom API schema documentation
   - Duration: 2 days

2. Create base parser class and structure
   - NSXPolicyAPIParser skeleton
   - JSON loading and validation
   - Object indexing logic
   - Duration: 1 day

3. Set up test fixtures
   - Extract anonymized samples from customer export
   - Create unit test samples (single policy, single rule, etc.)
   - Duration: 1 day

4. Write basic unit tests
   - Test JSON loading
   - Test object indexing
   - Test model validation
   - Duration: 1 day

**Deliverable**: Parser structure with models, can load and index objects

### Phase 2: Core Parsing (Week 2)

**Goal**: Parse SecurityPolicies and convert to common format

**Tasks**:
1. Implement SecurityPolicy parsing
   - Extract rules from policies
   - Convert to FirewallRule format
   - Duration: 2 days

2. Implement reference resolution
   - Resolve group references
   - Resolve service references
   - Resolve scope references
   - Handle missing references gracefully
   - Duration: 2 days

3. Implement IDS policy detection
   - Parse IdsSecurityPolicy objects
   - Flag as non-translatable
   - Generate recommendation text
   - Duration: 1 day

**Deliverable**: Parser extracts firewall rules and flags IDS policies

### Phase 3: Integration & Testing (Week 3)

**Goal**: Test against real customer data and integrate with correlation engine

**Tasks**:
1. Test against customer's 220k line export
   - Parse full export
   - Validate 1268 rules extracted
   - Identify any parse failures
   - Duration: 2 days

2. Integration with correlation engine
   - Ensure output format matches engine expectations
   - Test correlation logic with NSX Policy API data
   - Duration: 2 days

3. End-to-end testing
   - Parse → Correlate → Generate MultiNetworkPolicy
   - Validate generated YAML
   - Test deployment to OpenShift cluster
   - Duration: 1 day

**Deliverable**: Working end-to-end pipeline with customer data

### Phase 4: Documentation & Hardening (Week 4)

**Goal**: Production-ready with documentation

**Tasks**:
1. Error handling improvements
   - Better error messages
   - Graceful handling of edge cases
   - Validation checks
   - Duration: 2 days

2. Performance optimization
   - Profile with large exports
   - Optimize if needed for 1268+ rules
   - Duration: 1 day

3. Documentation
   - Parser usage guide
   - Input format documentation
   - Gap analysis documentation (IDS, missing refs)
   - Update main README
   - Duration: 2 days

**Deliverable**: Production-ready parser with documentation

---

## Testing Strategy

### Unit Tests

**Parser component tests**:
```python
# tests/parsers/test_nsx_policy_api.py

def test_load_json_export():
    """Test loading valid JSON export"""
    parser = NSXPolicyAPIParser('fixtures/sample_export.json')
    parser._load_export()
    assert parser.data is not None

def test_index_security_policies():
    """Test indexing SecurityPolicy objects"""
    parser = NSXPolicyAPIParser('fixtures/sample_export.json')
    parser._load_export()
    parser._index_objects()
    assert len(parser.security_policies) > 0

def test_parse_security_rule():
    """Test parsing individual SecurityRule"""
    # ... test rule extraction and conversion

def test_resolve_group_references():
    """Test resolving group path to group object"""
    # ... test reference resolution

def test_missing_reference_handling():
    """Test graceful handling of missing references"""
    # ... test placeholder generation

def test_ids_policy_detection():
    """Test IDS policy flagging"""
    # ... test IDS detection and flagging
```

### Integration Tests

**End-to-end pipeline tests**:
```python
def test_parse_customer_export():
    """Test parsing full customer export (220k lines)"""
    parser = NSXPolicyAPIParser('fixtures/customer_export.json')
    result = parser.parse()

    assert len(result.firewall_rules) == 1268
    assert len(result.ids_rules) == 2
    assert result.metadata['total_policies'] == 540

def test_correlation_with_nsx_policy_data():
    """Test correlation engine with NSX Policy API data"""
    parser = NSXPolicyAPIParser('fixtures/customer_export.json')
    result = parser.parse()

    from ops_translate.correlation.engine import CorrelationEngine
    engine = CorrelationEngine()
    correlated = engine.correlate(result)

    # Validate correlation results
    assert len(correlated.multi_network_policies) > 0
```

### Validation Tests

**Output validation**:
```python
def test_generated_multinetworkpolicy_valid():
    """Test that generated YAML is valid Kubernetes manifest"""
    # Parse → Correlate → Generate
    # Validate YAML syntax
    # Validate against MultiNetworkPolicy schema

def test_deploy_to_openshift():
    """Test deploying generated policies to test cluster"""
    # Requires test cluster access
    # oc apply -f generated_policies/
    # Validate deployment succeeds
```

---

## Risks & Mitigations

### Risk 1: Incomplete Export Data

**Risk**: Customer export missing referenced objects (groups, services)
**Impact**: Cannot fully resolve rule references
**Probability**: High (Rydekull already mentioned this)

**Mitigation**:
- Detect missing references during parsing
- Use placeholder values with clear flagging
- Document in gaps report
- Request complete export if critical references missing

### Risk 2: Scale Performance

**Risk**: Correlation engine slow with 1268 rules
**Impact**: Poor user experience, long processing times
**Probability**: Medium

**Mitigation**:
- Profile early with customer data
- Optimize correlation algorithm if needed
- Consider batch processing for large exports
- Set realistic expectations (minutes, not seconds)

### Risk 3: NSX API Version Differences

**Risk**: Customer's NSX version has different schema
**Impact**: Parser fails or misses fields
**Probability**: Medium

**Mitigation**:
- Use Pydantic models with Optional fields
- Graceful handling of unknown fields
- Version detection in parser
- Document supported NSX versions

### Risk 4: IDS Rules Blocking Adoption

**Risk**: Customer rejects solution due to IDS gap
**Impact**: Project fails to deliver value
**Probability**: Medium

**Mitigation**:
- Address IDS gap proactively in documentation
- Provide clear alternative recommendations
- Position as "modern security approach"
- Offer to help evaluate Falco/Tetragon

### Risk 5: Correlation Logic Assumptions

**Risk**: vRealize-specific correlation logic doesn't work for NSX Policy API
**Impact**: Poor correlation results, manual work required
**Probability**: Low-Medium

**Mitigation**:
- Test correlation early with customer data
- May need NSX Policy API-specific correlation hints
- Validate correlation confidence scores
- Document correlation strategy differences

---

## Success Metrics

### Technical Metrics

- ✓ Parse 220k line export without errors
- ✓ Extract all 1268 firewall rules successfully
- ✓ Flag 2 IDS policies correctly
- ✓ Resolve 90%+ of object references
- ✓ Generate valid MultiNetworkPolicy YAML
- ✓ Processing time < 5 minutes for full export

### Business Metrics

- ✓ 80%+ of rules translate automatically
- ✓ Clear documentation of non-translatable items
- ✓ Customer accepts POC as viable approach
- ✓ Reduces manual migration effort by 70%+

### Quality Metrics

- ✓ 90%+ unit test coverage for parser
- ✓ Integration tests pass with customer data
- ✓ Generated policies deploy successfully to OpenShift
- ✓ Documentation complete and clear

---

## Timeline Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| Phase 1: Foundation | Week 1 (5 days) | Parser structure with models |
| Phase 2: Core Parsing | Week 2 (5 days) | Parser extracts rules |
| Phase 3: Integration | Week 3 (5 days) | End-to-end pipeline working |
| Phase 4: Hardening | Week 4 (5 days) | Production-ready with docs |
| **Total** | **4 weeks** | **Production-ready NSX Policy API parser** |

**Critical Path**:
1. Data models (blocks everything else)
2. Core parsing logic (blocks integration)
3. Customer data testing (validates approach)
4. Documentation (required for handoff)

**Fast-track option** (POC in 2 weeks):
- Skip comprehensive error handling
- Minimal documentation
- Test with customer data only (skip edge cases)
- Accept "good enough" quality

---

## Open Questions

### For Rydekull/Customer

1. **Export Completeness**
   - Can you provide more complete export with all referenced objects?
   - Which objects are missing from current export?

2. **NSX Version**
   - What NSX version is the customer running?
   - Can you share NSX version from export metadata?

3. **IDS Requirements**
   - How critical is IDS to customer's security posture?
   - Is this a compliance requirement?
   - Open to alternative runtime security tools?

4. **Virtual Networks**
   - What does "virtual networks" mean? (Overlay vs VLAN-backed)
   - Do segments have VLAN IDs or are they pure overlay?

5. **Timeline**
   - What's the customer's deadline?
   - POC quality acceptable or need production-ready?

### For Internal Team

1. **Resource Allocation**
   - Who will implement this? (Todd solo or team?)
   - Can we dedicate 4 weeks to this?

2. **Prioritization**
   - Does this block other roadmap items?
   - Is this the top priority?

3. **Support Model**
   - Who supports this after delivery?
   - What's the handoff plan to consulting team?

---

## Appendix

### A. NSX Policy API Resources

- [Broadcom NSX-T REST API](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/)
- [NSX Policy API Guide](https://vdc-download.vmware.com/vmwb-repository/dcr-public/af1a1e22-c808-4d6a-9dc0-c165b103792b/17f86fee-6afa-4f9f-b007-5a63a592d132/NSX%20Policy%20API%20Guide.htm)
- [VMware NSX-T API Samples](https://github.com/vmware-samples/nsx-t/blob/master/API/PolicyAPI/04%20-%20Security%20Policy.rest)

### B. Related Issues

- [GitHub Issue #96](https://github.com/tsanders-rh/ops-translate/issues/96) - Customer request tracking

### C. Sample NSX Policy API Structure

```json
{
  "resource_type": "SecurityPolicy",
  "id": "POLICY_01",
  "display_name": "App-Tier-Policy",
  "category": "Application",
  "stateful": true,
  "children": [
    {
      "SecurityRule": {
        "id": "RULE_01",
        "display_name": "Allow-Web-To-App",
        "source_groups": ["/infra/domains/default/groups/WEB-TIER"],
        "destination_groups": ["/infra/domains/default/groups/APP-TIER"],
        "services": ["/infra/services/HTTP", "/infra/services/HTTPS"],
        "action": "ALLOW",
        "direction": "IN_OUT",
        "scope": ["/infra/domains/default/groups/APP-TIER"],
        "sequence_number": 10
      }
    }
  ]
}
```

### D. Customer Export Statistics

From Rydekull's environment:
- File size: 220k lines JSON
- Security Policies: 540
- Firewall Rules: 1268
- IDS Policies: 1
- IDS Rules: 2
- Notes: Not their largest environment, but "representative"

---

**Next Steps**:
1. Get approval for 4-week timeline
2. Request additional data from Rydekull (answers to open questions)
3. Begin Phase 1 implementation
4. Schedule weekly check-ins with consulting team
