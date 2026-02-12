# vRealize Bundle Import Examples

This directory demonstrates how to import vRealize Orchestrator (vRO) export bundles using ops-translate.

## Bundle Formats Supported

ops-translate supports three bundle formats:

1. **Single XML Workflow** (`.xml`) - Backwards compatible
2. **ZIP Archive** (`.package` or `.zip`) - vRO export archives
3. **Directory Bundle** - Extracted vRO export directory

## Bundle Structure

A vRO bundle has the following structure:

```
acme-corp-export/
├── workflows/
│   ├── vm-provisioning.workflow.xml
│   ├── approval-workflow.workflow.xml
│   └── network-config.workflow.xml
├── actions/
│   ├── com.acme.nsx/
│   │   ├── createFirewallRule.action.xml
│   │   └── createSegment.action.xml
│   ├── com.acme.servicenow/
│   │   └── createIncident.action.xml
│   └── com.acme.ipam/
│       └── getNextIP.action.xml
├── configurations/
│   └── config-elements.xml
└── manifest.txt (optional)
```

## Usage Examples

### Import Single Workflow (Backwards Compatible)

```bash
ops-translate import --source vrealize --file workflow.xml
```

This imports a single workflow XML file using the traditional method.

### Import Directory Bundle

```bash
ops-translate import --source vrealize --file /path/to/vro-export/
```

When the directory contains `workflows/`, `actions/`, or `configurations/` subdirectories, ops-translate automatically detects it as a bundle and imports all artifacts.

### Import .package File

```bash
ops-translate import --source vrealize --file acme-corp-export.package
```

The `.package` file is a ZIP archive. ops-translate will:
1. Extract the archive safely (with zip-slip protection)
2. Discover all workflows, actions, and configurations
3. Generate a manifest with metadata and SHA256 hashes

### Import .zip File

```bash
ops-translate import --source vrealize --file vro-bundle.zip
```

Works the same as `.package` files.

## Generated Manifest

After importing a bundle, ops-translate generates a manifest at `input/vrealize/manifest.json`:

```json
{
  "source_path": "/path/to/acme-corp-export.package",
  "source_type": "vrealize_bundle",
  "import_timestamp": "2026-02-12T12:00:00",
  "sha256": "abc123...",
  "workflows": [
    {
      "path": "workflows/vm-provisioning.workflow.xml",
      "absolute_path": "/workspace/input/vrealize/extracted/workflows/vm-provisioning.workflow.xml",
      "name": "vm-provisioning",
      "sha256": "def456..."
    }
  ],
  "actions": [
    {
      "path": "actions/com.acme.nsx/createFirewallRule.action.xml",
      "absolute_path": "/workspace/input/vrealize/extracted/actions/com.acme.nsx/createFirewallRule.action.xml",
      "fqname": "com.acme.nsx/createFirewallRule",
      "sha256": "ghi789..."
    }
  ],
  "configurations": [
    {
      "path": "configurations/config-elements.xml",
      "absolute_path": "/workspace/input/vrealize/extracted/configurations/config-elements.xml",
      "sha256": "jkl012..."
    }
  ]
}
```

## Manifest Fields

### Workflows
- `path`: Relative path within the bundle
- `absolute_path`: Full filesystem path
- `name`: Workflow name (extracted from filename)
- `sha256`: File integrity hash

### Actions
- `path`: Relative path within the bundle
- `absolute_path`: Full filesystem path
- `fqname`: Fully-qualified action name (e.g., `com.acme.nsx/createFirewallRule`)
- `sha256`: File integrity hash

### Configurations
- `path`: Relative path within the bundle
- `absolute_path`: Full filesystem path
- `sha256`: File integrity hash

## Security Features

ops-translate includes **zip-slip protection** to prevent malicious archives from extracting files outside the workspace:

```bash
# This will be rejected with an error
ops-translate import --source vrealize --file malicious.zip
# Error: Unsafe path in archive: ../../etc/passwd
```

All archive members are validated before extraction to ensure they resolve within the workspace directory.

## Action Indexing

When importing a bundle, ops-translate automatically parses and indexes all actions into `input/vrealize/action-index.json`:

```json
{
  "actions": {
    "com.acme.nsx/createFirewallRule": {
      "fqname": "com.acme.nsx/createFirewallRule",
      "name": "createFirewallRule",
      "module": "com.acme.nsx",
      "script": "var nsxClient = System.getModule(...);\n...",
      "inputs": [
        {"name": "ruleName", "type": "string", "description": "..."}
      ],
      "result_type": "any",
      "description": "Create NSX-T firewall rule",
      "sha256": "abc123..."
    }
  },
  "count": 42,
  "indexed_at": "2026-02-12T..."
}
```

**What's Indexed:**
- JavaScript source code from action scripts
- Input parameters with types and descriptions
- Return types
- Module organization
- SHA256 hashes for change detection

**Why Action Indexing Matters:**
- **Integration Detection**: Action scripts contain the real NSX, ServiceNow, IPAM integration logic
- **Action Resolution**: Workflows can reference actions by fully-qualified name
- **Signature Analysis**: Understand action inputs/outputs for better classification
- **Deterministic**: Pure text parsing, no AI required

## Benefits of Bundle Import

1. **Complete Export Support**: Import all workflows, actions, and configurations in one operation
2. **Action Indexing**: Automatically parses action scripts for integration detection
3. **Action Resolution**: Enables resolving action calls within workflows
4. **Traceability**: Manifest includes file hashes and paths for integrity verification
5. **Security**: Zip-slip protection prevents path traversal attacks
6. **Backwards Compatible**: Single XML workflow import still works

## Next Steps

After importing a bundle:

```bash
# Summarize the imported content
ops-translate summarize

# Analyze for dependencies and translatability
ops-translate analyze

# Generate OpenShift artifacts
ops-translate generate --profile lab
```

## Related Issues

- Issue #51: Support vRO export bundles (implemented)
- Issue #52: Parse and index vRO Actions (future)
- Issue #53: Resolve ActionCall nodes (future)
- Issue #54: Include action scripts in summarize (future)
