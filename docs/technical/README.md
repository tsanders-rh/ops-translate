# Technical Documentation

This directory contains technical reference documentation for ops-translate internals, architecture, and API.

## Documents

### [ARCHITECTURE.md](ARCHITECTURE.md)
**Audience**: Developers, contributors, architects

**Purpose**: System design, internals, and technical architecture

**Key Sections**:
- System overview and design principles
- Architecture layers (CLI → Import → Extract → Merge → Validate → Generate)
- Intent-based design philosophy
- Component architecture
  - CLI layer
  - Intent extraction (LLM integration)
  - Intent management (merge, validate, classify)
  - Generation layer (Jinja2 templates)
  - Translation layer (deterministic conversion)
- Data flow and processing pipeline
- LLM provider abstraction
- Template system architecture
- Extensibility points
- Security architecture
- Performance considerations
- Design decisions and trade-offs

**Time to read**: 60-90 minutes

**When to use**:
- Contributing to the codebase
- Understanding system design
- Extending functionality
- Debugging complex issues
- Planning custom integrations
- Architectural reviews

**Format**: Technical design document with diagrams

---

### [API_REFERENCE.md](API_REFERENCE.md)
**Audience**: Developers, Python programmers

**Purpose**: Python API documentation for programmatic usage

**Key Sections**:
- Module structure and organization
- Public API reference
  - CLI module (`ops_translate.cli`)
  - Intent module (`ops_translate.intent`)
  - Generate module (`ops_translate.generate`)
  - LLM module (`ops_translate.llm`)
  - Translate module (`ops_translate.translate`)
  - Analyze module (`ops_translate.analyze`)
- Class and function signatures
- Parameters and return types
- Usage examples
- Error handling
- Extension points for custom development

**Time to read**: 45 minutes (full) or reference specific modules

**When to use**:
- Using ops-translate as a library
- Building custom integrations
- Extending with custom analyzers
- Programmatic workflow automation
- Understanding code organization
- Contributing code

**Format**: API reference with code examples

---

### [INTENT_SCHEMA.md](INTENT_SCHEMA.md)
**Audience**: Developers, advanced users, integrators

**Purpose**: Intent YAML schema reference and data model

**Key Sections**:
- Intent file structure
- Schema definition (JSON Schema)
- Field reference
  - `metadata` - Source file information
  - `parameters` - Input parameter definitions
  - `vm_spec` - Virtual machine specifications
  - `resources` - CPU, memory, storage, network
  - `environment` - Environment-specific settings
  - `tasks` - Workflow tasks (vRealize)
  - `decisions` - Decision points
  - `approvals` - Approval requirements
  - `tags` - Metadata tags
  - `validations` - Validation rules
  - `gaps` - Gap analysis results
  - `recommendations` - Expert guidance
- Data types and validation rules
- Examples for each section
- Schema evolution and versioning

**Time to read**: 30 minutes (full) or reference specific fields

**When to use**:
- Manually editing intent YAML
- Validating intent structure
- Understanding data model
- Building custom analyzers
- Integrating with external tools
- Debugging intent issues

**Format**: Schema reference with examples

---

### [POWERCLI_MAPPINGS.md](POWERCLI_MAPPINGS.md)
**Audience**: Migration engineers, developers

**Purpose**: PowerCLI cmdlet to Ansible/KubeVirt mapping reference

**Key Sections**:
- PowerCLI cmdlet mapping table
  - VM lifecycle: `New-VM`, `Set-VM`, `Start-VM`, `Stop-VM`, `Remove-VM`
  - Resource management: `Get-ResourcePool`, `Set-VMResourceConfiguration`
  - Storage: `New-HardDisk`, `Set-HardDisk`, `Get-Datastore`
  - Network: `New-NetworkAdapter`, `Set-NetworkAdapter`, `Get-VirtualPortGroup`
  - Tagging: `New-TagAssignment`, `Get-Tag`
  - vCenter: `Connect-VIServer`, `Disconnect-VIServer`
- Ansible module equivalents
  - `kubevirt.core.kubevirt_vm`
  - `kubernetes.core.k8s`
  - `community.general.*`
- KubeVirt manifest equivalents
- Parameter mapping details
- Semantic differences and gotchas
- Unsupported features and workarounds
- Examples for common patterns

**Time to read**: 30-45 minutes (full) or reference specific cmdlets

**When to use**:
- Understanding translation logic
- Debugging PowerCLI conversions
- Manually adjusting generated artifacts
- Contributing PowerCLI support
- Validating translation accuracy
- Planning migration feasibility

**Format**: Mapping reference table with examples

---

## Document Relationships

```
ARCHITECTURE.md (system design)
    ↓
    ├─→ API_REFERENCE.md (code interface)
    ├─→ INTENT_SCHEMA.md (data model)
    └─→ POWERCLI_MAPPINGS.md (translation logic)
```

- **ARCHITECTURE.md** provides the big picture
- **API_REFERENCE.md** shows how to interact with code
- **INTENT_SCHEMA.md** defines the data structure
- **POWERCLI_MAPPINGS.md** documents specific translations

---

## Learning Path for Developers

### Understanding the System (2-3 hours)

**Step 1: Overview** (30 min)
1. Read [ARCHITECTURE.md - System Overview](ARCHITECTURE.md)
2. Understand intent-based design philosophy
3. Review architecture layers

**Step 2: Data Model** (30 min)
1. Read [INTENT_SCHEMA.md](INTENT_SCHEMA.md)
2. Understand intent structure
3. Review examples

**Step 3: Translation Logic** (30 min)
1. Read [POWERCLI_MAPPINGS.md](POWERCLI_MAPPINGS.md)
2. Understand cmdlet mappings
3. Review semantic differences

**Step 4: Code Interface** (60 min)
1. Read [API_REFERENCE.md](API_REFERENCE.md)
2. Understand module organization
3. Review API examples

**Outcome**: Comprehensive understanding of system internals

---

### Contributing Code (1-2 hours)

**Preparation**:
1. Read [ARCHITECTURE.md - Extensibility Points](ARCHITECTURE.md)
2. Read [API_REFERENCE.md](API_REFERENCE.md) relevant modules
3. Review [INTENT_SCHEMA.md](INTENT_SCHEMA.md) for data requirements

**Implementation**:
1. Follow architecture patterns
2. Use existing API interfaces
3. Validate against intent schema
4. Add tests and documentation

**Outcome**: Production-quality contribution

---

## Use Cases by Document

### Use Case: Add Support for New PowerCLI Cmdlet

**Documents needed**:
1. [POWERCLI_MAPPINGS.md](POWERCLI_MAPPINGS.md) - Understand existing mappings
2. [ARCHITECTURE.md - Translation Layer](ARCHITECTURE.md) - Understand translation system
3. [API_REFERENCE.md - Translate Module](API_REFERENCE.md) - Use translation API
4. [INTENT_SCHEMA.md](INTENT_SCHEMA.md) - Extend schema if needed

**Time**: 2-4 hours

---

### Use Case: Build Custom Analyzer Plugin

**Documents needed**:
1. [ARCHITECTURE.md - Extensibility Points](ARCHITECTURE.md) - Plugin architecture
2. [API_REFERENCE.md - Intent Module](API_REFERENCE.md) - Analyzer API
3. [INTENT_SCHEMA.md](INTENT_SCHEMA.md) - Output format

**Time**: 4-8 hours

---

### Use Case: Understand Why Translation Produced Specific Output

**Documents needed**:
1. [ARCHITECTURE.md - Data Flow](ARCHITECTURE.md) - Processing pipeline
2. [POWERCLI_MAPPINGS.md](POWERCLI_MAPPINGS.md) - Specific cmdlet mapping
3. [INTENT_SCHEMA.md](INTENT_SCHEMA.md) - Intermediate data format

**Time**: 30 minutes

---

### Use Case: Extend LLM Provider Support

**Documents needed**:
1. [ARCHITECTURE.md - LLM Provider Abstraction](ARCHITECTURE.md) - Provider interface
2. [API_REFERENCE.md - LLM Module](API_REFERENCE.md) - Provider API
3. [INTENT_SCHEMA.md](INTENT_SCHEMA.md) - Expected output

**Time**: 3-6 hours

---

### Use Case: Debug Intent Schema Validation Error

**Documents needed**:
1. [INTENT_SCHEMA.md](INTENT_SCHEMA.md) - Schema definition
2. Error message from validation
3. [API_REFERENCE.md - Intent Module](API_REFERENCE.md) - Validation API

**Time**: 15-30 minutes

---

## Quick Reference by Task

### Task: Understand System Design
**Read**: [ARCHITECTURE.md](ARCHITECTURE.md)
**Time**: 60 minutes
**Outcome**: High-level understanding

### Task: Use ops-translate as Library
**Read**: [API_REFERENCE.md](API_REFERENCE.md)
**Time**: 30 minutes
**Outcome**: Programmatic usage

### Task: Manually Edit Intent YAML
**Read**: [INTENT_SCHEMA.md](INTENT_SCHEMA.md)
**Time**: 15 minutes
**Outcome**: Valid intent modifications

### Task: Understand PowerCLI Translation
**Read**: [POWERCLI_MAPPINGS.md](POWERCLI_MAPPINGS.md)
**Time**: 20 minutes
**Outcome**: Translation comprehension

### Task: Contribute New Feature
**Read**: All technical docs
**Time**: 2-3 hours
**Outcome**: Ready to implement

### Task: Debug Complex Issue
**Read**: [ARCHITECTURE.md](ARCHITECTURE.md) + relevant specific doc
**Time**: 30-60 minutes
**Outcome**: Root cause identification

---

## Comparison: User Guides vs. Technical Docs

| Aspect | User Guides | Technical Docs |
|--------|-------------|----------------|
| **Audience** | Users, operators | Developers, contributors |
| **Focus** | How to use | How it works |
| **Depth** | Practical usage | Internal design |
| **Examples** | Command-line usage | Code examples |
| **Location** | [../guides/](../guides/) | This directory |

**When in doubt**:
- Want to use the tool → [../guides/](../guides/)
- Want to extend the tool → This directory (technical/)

---

## Architecture Principles (from ARCHITECTURE.md)

### Layered Architecture
Import → Summarize → Extract → Merge → Validate → Generate

### Intent-Based Design
Platform-agnostic normalized representation (YAML)

### LLM-Minimal
Only extraction requires AI; generation is template-based

### Transparent
All assumptions and inferences logged

### Extensible
Custom templates, providers, translation profiles

### Conflict-Aware
Detects and reports merge issues

---

## Key Design Decisions

### Why Intent-Based?
- Decouples analysis from generation
- Enables inspection and modification
- Supports multiple output formats
- Allows deterministic generation

See [ARCHITECTURE.md - Intent-Based Design](ARCHITECTURE.md) for details.

### Why LLM for Extraction?
- Understands semantic meaning, not just syntax
- Handles non-standard code patterns
- Preserves business logic intent
- Reduces brittle parsing

See [ARCHITECTURE.md - LLM Integration](ARCHITECTURE.md) for details.

### Why Template-Based Generation?
- Deterministic and reproducible
- Customizable for organizations
- No AI cost for generation
- Transparent and auditable

See [ARCHITECTURE.md - Template System](ARCHITECTURE.md) for details.

---

## Contributing to Technical Documentation

### When to Update

**ARCHITECTURE.md**:
- New layers or components added
- Significant design changes
- New extensibility points
- Performance optimizations

**API_REFERENCE.md**:
- New public APIs added
- API signatures changed
- New modules created
- Breaking changes

**INTENT_SCHEMA.md**:
- Schema changes (new fields, types)
- Validation rules updated
- Examples added for clarity

**POWERCLI_MAPPINGS.md**:
- New cmdlet support added
- Mapping logic changes
- New edge cases discovered

### Documentation Standards

- Include code examples that work
- Document assumptions and limitations
- Explain "why" not just "what"
- Keep diagrams up to date
- Version and date updates

---

## Related Documentation

- **[../guides/](../guides/)** - User guides and tutorials (how to use)
- **[../reference/](../reference/)** - Quick reference and FAQ
- **[../planning/](../planning/)** - User stories and roadmap
- **[../stakeholder/](../stakeholder/)** - Executive summaries

---

## Quick Navigation

**I want to...**
- Understand system design → [ARCHITECTURE.md](ARCHITECTURE.md)
- Use ops-translate as library → [API_REFERENCE.md](API_REFERENCE.md)
- Edit intent YAML → [INTENT_SCHEMA.md](INTENT_SCHEMA.md)
- Understand PowerCLI translation → [POWERCLI_MAPPINGS.md](POWERCLI_MAPPINGS.md)
- Contribute code → Start with [ARCHITECTURE.md](ARCHITECTURE.md)
- Debug issue → [ARCHITECTURE.md](ARCHITECTURE.md) + specific doc
- Learn to use tool → [../guides/TUTORIAL.md](../guides/TUTORIAL.md)

---

**For developers and contributors**: Start with [ARCHITECTURE.md](ARCHITECTURE.md)

**Last Updated**: 2026-02-16
