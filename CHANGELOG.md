# Changelog

All notable changes to ops-translate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

#### Ansible Role Skeleton Generation (Issue #58)
- Automated Ansible role directory structure creation for imported workflows
- Role generation for both vRealize Orchestrator workflows and PowerCLI scripts
- Metadata extraction from workflow XML and PowerCLI script parameters
- Automatic generation of:
  - `tasks/main.yml` - Main task file with translated tasks or skeleton
  - `defaults/main.yml` - Default variables from workflow inputs/parameters
  - `meta/main.yml` - Ansible Galaxy metadata
  - `README.md` - Role documentation with implementation status
- Idempotent regeneration support
- Graceful fallback role creation on metadata extraction failure
- Integration with `ops-translate generate` command

#### vRealize Workflow to Ansible Task Translation (Issue #59)
- Deterministic translation of vRO workflows to Ansible tasks
- `WorkflowParser` class for parsing vRO XML workflows
- `JavaScriptToAnsibleTranslator` class for translating workflow items
- Integration detection via allowlist-based pattern matching:
  - NSX integration (logicalSwitch, logicalRouter, securityGroup)
  - ServiceNow integration (RESTHost, sys_id, incident)
  - ITSM integration (ticketCreate, approvalRequest)
- Topological sorting of workflow items by execution dependencies
- Profile-driven adapter generation for integrations
- BLOCKED stub generation with detailed guidance when profile incomplete
- Translation of vRO scriptable tasks to equivalent Ansible modules
- Integration with role generation (`_generate_vrealize_role`)

#### PowerCLI Script to Ansible Task Translation (Issue #60)
- Deterministic translation of PowerCLI scripts to Ansible tasks
- New `ops_translate/translate/` module with:
  - `powercli_script.py` - PowerCLI parser and translator
  - `powercli_cmdlet_mappings.yaml` - Cmdlet-to-module mappings
  - `vrealize_workflow.py` - vRO workflow translator
  - `vro_integration_mappings.yaml` - vRO integration mappings
- `PowerCLIScriptParser` class for parsing .ps1 files:
  - Sequential statement parsing (line-by-line execution order)
  - Parameter extraction with support for quoted strings and variables
  - Statement categorization (context, lookup, mutation, integration, gate)
  - Integration detection (tagging, snapshot, network, NSX)
- `PowerShellToAnsibleTranslator` class for translation:
  - Cmdlet-to-module mapping with parameter substitution
  - PowerShell variable to Jinja2 template conversion (`$VMName` → `{{ vmname }}`)
  - Profile-driven network adapter translation
  - BLOCKED stub generation for missing profile configuration
- Supported cmdlet mappings:
  - VM operations: `New-VM`, `Start-VM`, `Stop-VM`, `Set-VM`, `Remove-VM`
  - Lookups: `Get-VM`
  - Integrations: `New-TagAssignment` (→ labels), `New-Snapshot` (→ VolumeSnapshot)
  - Network: `New-NetworkAdapter` (profile-driven)
  - Control flow: `if/throw` (→ assert), variable assignment (→ set_fact)
- Parameter substitution patterns:
  - Simple: `{ParamName}` → parameter value
  - With suffix: `{MemoryGB}Gi` → `"8Gi"`
  - Variables: `$VMName` → `{{ vmname }}`
- Integration with role generation (`_generate_powercli_role`)

#### Automatic Path Selection
- **Zero-configuration workflow** - Automatically selects Direct Translation or Intent-Based generation
- Added `_create_minimal_translation_profile()` helper function:
  - Auto-generates ProfileSchema from workspace config
  - No `--translation-profile` file required for simple cases
  - Falls back to minimal config (namespace, API URL from workspace)
- Updated `generate_all()` with auto-detection logic:
  - Checks for PowerCLI `.ps1` files in `input/powercli/`
  - Checks for vRealize `.xml` files in `input/vrealize/`
  - Checks for `intent/intent.yaml`
- Decision tree:
  1. Has source files + no intent.yaml → **Direct Translation** (no LLM)
  2. Has intent.yaml → **Intent-Based Generation** (LLM optional)
  3. Has `--translation-profile` → **Explicit Direct Translation**
  4. Has nothing → **Helpful error** with import guidance
- **Improved user experience:**
  - Simple workflow: `import` → `generate` (no intermediate steps!)
  - No LLM required for standard PowerCLI cmdlets
  - Automatic profile creation from workspace settings
  - Clear messaging about which path is being used
- Console output shows selected path:
  - "Using direct translation (deterministic, no LLM required)"
  - "Using intent-based generation (AI-assisted)"

#### Documentation Updates
- New `docs/POWERCLI_MAPPINGS.md` - Comprehensive cmdlet mapping guide
- Updated `docs/ARCHITECTURE.md`:
  - Added Translate Module section with detailed architecture
  - Updated Generate Module section to mention role generation
  - Added Automatic Path Selection section with decision tree
  - Translation flow diagrams and component descriptions
  - Profile-driven decision documentation
- Updated `README.md`:
  - Added two translation paths (Direct Translation vs Intent Extraction)
  - Added Automatic Path Selection section with examples
  - Clarified when LLM is required vs optional
  - Updated architecture diagram
- Updated `docs/USER_GUIDE.md`:
  - Added 🚀 Automatic Path Selection section with table and examples
  - Clarified `generate` command output includes translated role tasks
  - Added role generation details for PowerCLI and vRO workflows
  - Documented when to use `--translation-profile`
- Updated `docs/TUTORIAL.md`:
  - Added note about automatic path selection in generate step
  - Added PowerCLI translation example showing before/after
  - Module mapping examples (New-VM → kubevirt_vm, etc.)
  - Variable conversion examples

### Changed

#### Module Organization
- Separated translation logic into dedicated `ops_translate/translate/` module
- Clear separation between deterministic translation (Translate Module) and LLM-based extraction (Extract/Generate modules)

#### Role Generation
- Enhanced `_generate_powercli_role()` to call PowerCLI translator
- Enhanced `_generate_vrealize_role()` to call vRO workflow translator
- Added profile parameter propagation through generation call chain
- Roles now contain translated tasks instead of skeleton placeholders for supported patterns

#### Test Coverage
- Added `tests/test_powercli_script_parser.py` (19 tests) - Parser tests
- Added `tests/test_powershell_to_ansible_translator.py` (15 tests) - Translator tests
- Added `tests/test_ansible_role_generation.py` (17 tests) - Role generation tests
- Enhanced `tests/test_e2e_ansible_project.py` with PowerCLI translation integration tests
- All tests passing (71 total test cases)

### Technical Details

#### Translation Architecture
- **Parser → Translator → AnsibleTask → YAML** pattern
- Reuses `AnsibleTask` dataclass and `generate_ansible_yaml()` from workflow_to_ansible.py
- Mapping files use YAML for easy extension and modification
- Profile-driven decisions with graceful degradation (BLOCKED stubs)

#### Key Design Principles
- **Deterministic**: Same input always produces identical output
- **Transparent**: Clear mapping files, no "black box" translation
- **Extensible**: Add new cmdlet mappings via YAML
- **Profile-Aware**: Adapts to target environment configuration
- **Graceful Degradation**: BLOCKED stubs with guidance when configuration missing

#### Performance
- No LLM required for common PowerCLI cmdlets and vRO patterns
- Fast, offline translation for supported patterns
- Instant regeneration (no API calls)

## [0.1.0] - 2026-02-12

### Initial Features
- PowerCLI script and vRealize workflow import
- Static pattern analysis and summarization
- LLM-based intent extraction
- Intent merging and validation
- KubeVirt manifest generation
- Ansible playbook generation (intent-based)
- Profile-based customization
- Migration readiness reporting
- Event-Driven Ansible (EDA) rulebook generation
- MTV (Migration Toolkit for Virtualization) mode
- Multi-profile support (lab, prod, etc.)
- Template-based generation (no-AI mode)

---

## Migration Guide

### For Users Upgrading from Earlier Versions

No breaking changes. New features are additive:

1. **PowerCLI Translation** - Automatically enabled when importing PowerCLI scripts
   - Standard cmdlets are now translated to Ansible tasks
   - No action required - works with existing `ops-translate generate` workflow

2. **vRO Workflow Translation** - Automatically enabled when importing vRO workflows
   - Common workflow patterns are translated to Ansible tasks
   - Integration detection identifies NSX, ServiceNow, ITSM patterns

3. **Profile Requirements** - Some integrations now require profile configuration:
   - Network adapters: Requires `profile.network_security.model`
   - Missing configuration generates BLOCKED stubs with fix instructions
   - See generated task comments for guidance

### Translation Paths

ops-translate now supports two translation approaches:

1. **Direct Translation** (New - Deterministic)
   - For: Standard PowerCLI cmdlets, common vRO patterns
   - Process: Parser → Mappings → Ansible tasks
   - LLM: Not required
   - Speed: Fast (milliseconds)

2. **Intent Extraction** (Existing - LLM-based)
   - For: Complex custom logic, multi-source merging
   - Process: LLM → intent.yaml → Templates → Ansible
   - LLM: Required for extraction
   - Flexibility: Handles all scenarios

Both paths are automatically used as appropriate during generation.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

Report issues at https://github.com/tsanders-rh/ops-translate/issues
