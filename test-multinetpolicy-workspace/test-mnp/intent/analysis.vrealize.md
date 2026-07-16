# vRealize Workflow Analysis Report

**Source**: /Users/tsanders/Workspace/ops-translate/test-multinetpolicy-workspace/test-mnp/input/vrealize/nsx-multinetwork-test.workflow.xml

**Complexity Score**: 100/100

## External Dependencies Detected

### NSX-T Operations

**Segments** (3 instances)

- **nsxClient\.createSegment** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:24`
  - Evidence: Pattern match: nsxClient.createSegment in context (nsx-multinetwork-test.workflow.xml:24): ...cme.nsx").getNSXClient();

      var webSegment = nsxClient.createSegment({
        displayName: "Web-Tier-VLAN100",...

- **nsxClient\.createSegment** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:43`
  - Evidence: Pattern match: nsxClient.createSegment in context (nsx-multinetwork-test.workflow.xml:43): ...cme.nsx").getNSXClient();

      var appSegment = nsxClient.createSegment({
        displayName: "App-Tier-VLAN150",...

- **nsxClient\.createSegment** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:62`
  - Evidence: Pattern match: nsxClient.createSegment in context (nsx-multinetwork-test.workflow.xml:62): ...acme.nsx").getNSXClient();

      var dbSegment = nsxClient.createSegment({
        displayName: "DB-Tier-VLAN200",...

**Firewall Rules** (10 instances)

- **nsxClient\.createFirewallRule** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:81`
  - Evidence: Pattern match: nsxClient.createFirewallRule in context (nsx-multinetwork-test.workflow.xml:81): ...e.nsx").getNSXClient();

      var webToAppRule = nsxClient.createFirewallRule({
        name: "Allow-Web-to-App",
        segme...

- **FirewallRule** (confidence: 70%)
  - Location: `nsx-multinetwork-test.workflow.xml:81`
  - Evidence: Pattern match: FirewallRule in context (nsx-multinetwork-test.workflow.xml:81): ...ient();

      var webToAppRule = nsxClient.createFirewallRule({
        name: "Allow-Web-to-App",
        segme...

- **nsxClient\.createFirewallRule** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:102`
  - Evidence: Pattern match: nsxClient.createFirewallRule in context (nsx-multinetwork-test.workflow.xml:102): ...me.nsx").getNSXClient();

      var appToDbRule = nsxClient.createFirewallRule({
        name: "Allow-App-to-DB",
        segmen...

- **FirewallRule** (confidence: 70%)
  - Location: `nsx-multinetwork-test.workflow.xml:102`
  - Evidence: Pattern match: FirewallRule in context (nsx-multinetwork-test.workflow.xml:102): ...lient();

      var appToDbRule = nsxClient.createFirewallRule({
        name: "Allow-App-to-DB",
        segmen...

- **nsxClient\.createFirewallRule** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:124`
  - Evidence: Pattern match: nsxClient.createFirewallRule in context (nsx-multinetwork-test.workflow.xml:124): ...e.nsx").getNSXClient();

      var dbBackupRule = nsxClient.createFirewallRule({
        name: "Allow-DB-Backup",
        segmen...

- **FirewallRule** (confidence: 70%)
  - Location: `nsx-multinetwork-test.workflow.xml:124`
  - Evidence: Pattern match: FirewallRule in context (nsx-multinetwork-test.workflow.xml:124): ...ient();

      var dbBackupRule = nsxClient.createFirewallRule({
        name: "Allow-DB-Backup",
        segmen...

- **nsxClient\.createFirewallRule** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:147`
  - Evidence: Pattern match: nsxClient.createFirewallRule in context (nsx-multinetwork-test.workflow.xml:147): ...).getNSXClient();

      var internetEgressRule = nsxClient.createFirewallRule({
        name: "Allow-Internet-Egress",...

- **FirewallRule** (confidence: 70%)
  - Location: `nsx-multinetwork-test.workflow.xml:147`
  - Evidence: Pattern match: FirewallRule in context (nsx-multinetwork-test.workflow.xml:147): ...;

      var internetEgressRule = nsxClient.createFirewallRule({
        name: "Allow-Internet-Egress",...

- **nsxClient\.createFirewallRule** (confidence: 95%)
  - Location: `nsx-multinetwork-test.workflow.xml:167`
  - Evidence: Pattern match: nsxClient.createFirewallRule in context (nsx-multinetwork-test.workflow.xml:167): ...m.acme.nsx").getNSXClient();

      var dnsRule = nsxClient.createFirewallRule({
        name: "Allow-DNS",
        sources: ["a...

- **FirewallRule** (confidence: 70%)
  - Location: `nsx-multinetwork-test.workflow.xml:167`
  - Evidence: Pattern match: FirewallRule in context (nsx-multinetwork-test.workflow.xml:167): ...NSXClient();

      var dnsRule = nsxClient.createFirewallRule({
        name: "Allow-DNS",
        sources: ["a...

### Custom Plugins

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...cme.nsx").getNSXClient();

      var webSegment = nsxClient.createSegment({
        displayName: "Web-Tier-VLAN100",...

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...cme.nsx").getNSXClient();

      var appSegment = nsxClient.createSegment({
        displayName: "App-Tier-VLAN150",...

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...acme.nsx").getNSXClient();

      var dbSegment = nsxClient.createSegment({
        displayName: "DB-Tier-VLAN200",...

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...e.nsx").getNSXClient();

      var webToAppRule = nsxClient.createFirewallRule({
        name: "Allow-Web-to-App",
        segmen...

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...me.nsx").getNSXClient();

      var appToDbRule = nsxClient.createFirewallRule({
        name: "Allow-App-to-DB",
        segment...

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...e.nsx").getNSXClient();

      var dbBackupRule = nsxClient.createFirewallRule({
        name: "Allow-DB-Backup",
        segment...

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...).getNSXClient();

      var internetEgressRule = nsxClient.createFirewallRule({
        name: "Allow-Internet-Egress",
        s...

- **nsxClient** (confidence: 75%)
  - Evidence: Plugin reference: ...m.acme.nsx").getNSXClient();

      var dnsRule = nsxClient.createFirewallRule({
        name: "Allow-DNS",
        sources: ["an...

