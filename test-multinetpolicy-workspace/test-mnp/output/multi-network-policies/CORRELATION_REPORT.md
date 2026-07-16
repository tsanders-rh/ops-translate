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
- **Correlation Confidence**: 0.95
- **Firewall Rules**: 1

| Rule Name | Evidence |
|-----------|----------|
| `Allow-App-to-DB` | Rule evidence contains segment name 'App-Tier-VLAN150' |

### Segment: DB-Tier-VLAN200

- **NetworkAttachmentDefinition**: `default/db-tier-vlan200`
- **VLAN IDs**: 200
- **Subnets**: 10.10.200.0/24
- **Correlation Confidence**: 0.95
- **Firewall Rules**: 1

| Rule Name | Evidence |
|-----------|----------|
| `Allow-DB-Backup` | Rule evidence contains segment name 'DB-Tier-VLAN200' |

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