# User Guides

This directory contains comprehensive guides for using ops-translate, from first steps to advanced patterns.

## Documents

### [TUTORIAL.md](TUTORIAL.md)
**Audience**: First-time users, new team members

**Purpose**: Step-by-step walkthrough for your first migration

**What you'll learn**:
- Setting up your first workspace
- Importing PowerCLI scripts and vRealize workflows
- Running analysis and extracting intent
- Generating Ansible playbooks and KubeVirt manifests
- Deploying to OpenShift
- Handling common scenarios

**Prerequisites**: Basic understanding of VMware and OpenShift

**Time to complete**: 30-45 minutes (hands-on)

**When to use**:
- First time using ops-translate
- Onboarding new team members
- Understanding the complete workflow
- Learning by doing

**Format**: Progressive tutorial with real examples

---

### [USER_GUIDE.md](USER_GUIDE.md)
**Audience**: All users, especially platform engineers

**Purpose**: Complete command reference and usage documentation

**Key Sections**:
- Installation and setup
- All commands with detailed syntax and options
- Configuration file reference
- Environment profiles and customization
- Template mappings and customization
- Distributed locking configuration
- Output formats (YAML, JSON, Kustomize, ArgoCD)
- Advanced features and options
- Troubleshooting guide

**Time to read**: 60+ minutes (full) or reference specific sections

**When to use**:
- Looking up specific command syntax
- Understanding configuration options
- Customizing for your environment
- Reference during daily use
- Troubleshooting issues

**Format**: Comprehensive reference manual

---

### [PATTERNS.md](PATTERNS.md)
**Audience**: Migration architects, experienced users

**Purpose**: Migration patterns and best practices for complex scenarios

**Key Sections**:
- Common migration patterns
  - Simple VM provisioning
  - Multi-environment with branching
  - Enterprise governance workflows
  - NSX integration patterns
  - Custom integration patterns
- Advanced techniques
  - Custom template development
  - Translation profile customization
  - GitOps integration patterns
  - Multi-cluster strategies
- Anti-patterns (what to avoid)
- Performance optimization
- Security best practices
- Organizational patterns (how to structure team workflow)

**Time to read**: 45-60 minutes (full) or reference specific patterns

**When to use**:
- Planning complex migrations
- Solving non-trivial migration challenges
- Optimizing performance
- Implementing best practices
- Learning from real-world examples

**Format**: Pattern catalog with examples

---

### [FIELD_GUIDE.md](FIELD_GUIDE.md)
**Audience**: Platform engineers, operations teams

**Purpose**: Practical field guide for common scenarios and troubleshooting

**Key Sections**:
- Common scenarios with solutions
- Troubleshooting workflows
- Environment-specific guidance
- Known issues and workarounds
- Tips and tricks from the field
- Performance tuning
- Day-2 operations guidance

**Time to read**: 30 minutes (full) or reference specific scenarios

**When to use**:
- Encountering a specific problem
- Need quick practical solutions
- Learning from others' experiences
- Day-to-day operations support

**Format**: Scenario-based guide with practical solutions

---

## Document Progression

### Learning Path for New Users

**Day 1: Getting Started**
1. [TUTORIAL.md](TUTORIAL.md) - Complete hands-on tutorial (45 min)
2. [USER_GUIDE.md - Quick Start](USER_GUIDE.md) - Review basic commands (15 min)

**Week 1: Building Proficiency**
1. [USER_GUIDE.md](USER_GUIDE.md) - Read relevant sections for your use case (60 min)
2. [FIELD_GUIDE.md](FIELD_GUIDE.md) - Review common scenarios (30 min)
3. Practice with 3-5 real scripts

**Month 1: Mastery**
1. [PATTERNS.md](PATTERNS.md) - Study patterns for your migration complexity (60 min)
2. [FIELD_GUIDE.md](FIELD_GUIDE.md) - Deep dive on troubleshooting (30 min)
3. Customize templates for your organization

---

## Quick Reference by Use Case

### First Migration
**Read**: [TUTORIAL.md](TUTORIAL.md) → [USER_GUIDE.md - Commands](USER_GUIDE.md)
**Time**: 1 hour
**Outcome**: First successful artifact generation

### Complex Multi-Environment Migration
**Read**: [PATTERNS.md - Multi-Environment](PATTERNS.md) → [USER_GUIDE.md - Profiles](USER_GUIDE.md)
**Time**: 2 hours
**Outcome**: Environment-aware artifact generation

### NSX-Heavy Environment
**Read**: [PATTERNS.md - NSX Integration](PATTERNS.md) → [FIELD_GUIDE.md - NSX Scenarios](FIELD_GUIDE.md)
**Time**: 1 hour
**Outcome**: Strategy for handling NSX features

### Custom Template Development
**Read**: [PATTERNS.md - Custom Templates](PATTERNS.md) → [USER_GUIDE.md - Template Customization](USER_GUIDE.md)
**Time**: 2 hours
**Outcome**: Organization-specific templates

### Troubleshooting Issue
**Read**: [FIELD_GUIDE.md](FIELD_GUIDE.md) → [USER_GUIDE.md - Troubleshooting](USER_GUIDE.md) → [../reference/FAQ.md](../reference/FAQ.md)
**Time**: 15-30 minutes
**Outcome**: Issue resolution

---

## Comparison: When to Use Which Guide

| Situation | Use This Guide | Because |
|-----------|---------------|---------|
| Never used ops-translate | [TUTORIAL.md](TUTORIAL.md) | Step-by-step hands-on learning |
| Need command syntax | [USER_GUIDE.md](USER_GUIDE.md) | Complete command reference |
| Complex migration scenario | [PATTERNS.md](PATTERNS.md) | Proven patterns and best practices |
| Specific error or issue | [FIELD_GUIDE.md](FIELD_GUIDE.md) | Practical troubleshooting |
| Quick command reminder | [../reference/QUICK_REFERENCE.md](../reference/QUICK_REFERENCE.md) | One-page cheat sheet |
| Specific question | [../reference/FAQ.md](../reference/FAQ.md) | Q&A format |
| Understanding design | [../technical/ARCHITECTURE.md](../technical/ARCHITECTURE.md) | System internals |

---

## Common Workflows with Guide References

### Workflow 1: First-Time Setup and Migration
1. Read [TUTORIAL.md - Installation](TUTORIAL.md) for setup
2. Follow [TUTORIAL.md - First Migration](TUTORIAL.md) hands-on
3. Reference [USER_GUIDE.md - Commands](USER_GUIDE.md) for syntax details
4. Use [../reference/QUICK_REFERENCE.md](../reference/QUICK_REFERENCE.md) as ongoing reference

**Time**: 1-2 hours
**Outcome**: Comfortable with basic workflow

---

### Workflow 2: Production Migration Planning
1. Review [PATTERNS.md](PATTERNS.md) for your complexity level
2. Consult [USER_GUIDE.md - Configuration](USER_GUIDE.md) for profile setup
3. Check [FIELD_GUIDE.md](FIELD_GUIDE.md) for known issues in your scenario
4. Reference [../planning/USER_STORIES.md](../planning/USER_STORIES.md) for feature completeness

**Time**: 3-4 hours
**Outcome**: Detailed migration plan

---

### Workflow 3: Troubleshooting and Resolution
1. Check [FIELD_GUIDE.md](FIELD_GUIDE.md) for known issues
2. Consult [USER_GUIDE.md - Troubleshooting](USER_GUIDE.md) for detailed diagnostics
3. Search [../reference/FAQ.md](../reference/FAQ.md) for similar questions
4. Review [../reference/QUICK_REFERENCE.md - Troubleshooting](../reference/QUICK_REFERENCE.md) for quick fixes

**Time**: 15-30 minutes
**Outcome**: Issue resolved

---

### Workflow 4: Template Customization
1. Study [PATTERNS.md - Custom Templates](PATTERNS.md) for examples
2. Follow [USER_GUIDE.md - Template Customization](USER_GUIDE.md) for implementation
3. Reference [../technical/ARCHITECTURE.md - Template System](../technical/ARCHITECTURE.md) for internals
4. Test with real scripts

**Time**: 2-4 hours
**Outcome**: Custom templates for organization

---

## Training Materials

### New Team Member Onboarding (4 hours)
**Day 1 Morning** (2 hours):
- Read [../stakeholder/EXECUTIVE_SUMMARY.md](../stakeholder/EXECUTIVE_SUMMARY.md) for context (15 min)
- Complete [TUTORIAL.md](TUTORIAL.md) hands-on (45 min)
- Review [USER_GUIDE.md - Quick Start](USER_GUIDE.md) (15 min)
- Practice: First migration with provided sample (45 min)

**Day 1 Afternoon** (2 hours):
- Read [PATTERNS.md](PATTERNS.md) relevant sections (30 min)
- Review [FIELD_GUIDE.md](FIELD_GUIDE.md) common scenarios (30 min)
- Practice: Second migration with real script (60 min)

**Week 1**: Ongoing reference to [USER_GUIDE.md](USER_GUIDE.md) and [../reference/QUICK_REFERENCE.md](../reference/QUICK_REFERENCE.md)

---

### Advanced Workshop (4 hours)
**Session 1** (2 hours):
- Deep dive on [PATTERNS.md](PATTERNS.md) (60 min)
- Custom template development (60 min)

**Session 2** (2 hours):
- Complex scenario walkthrough (60 min)
- Troubleshooting workshop using [FIELD_GUIDE.md](FIELD_GUIDE.md) (60 min)

---

## Contribution Guidelines

### Updating Guides

**TUTORIAL.md**:
- Keep steps sequential and tested
- Use real, working examples
- Update for new commands/features
- Include screenshots or output examples

**USER_GUIDE.md**:
- Document all commands with full syntax
- Include examples for each option
- Keep troubleshooting section current
- Update for configuration changes

**PATTERNS.md**:
- Add patterns based on real migrations
- Include anti-patterns (what not to do)
- Provide complete working examples
- Document trade-offs and alternatives

**FIELD_GUIDE.md**:
- Add scenarios from field experience
- Include actual error messages
- Provide step-by-step resolution
- Note version-specific issues

---

## Related Documentation

- **[../reference/](../reference/)** - Quick reference and FAQ
- **[../technical/](../technical/)** - Architecture and API documentation
- **[../planning/](../planning/)** - User stories and roadmap
- **[../stakeholder/](../stakeholder/)** - Executive summaries and comparisons

---

## Quick Navigation

**I want to...**
- Learn the tool → [TUTORIAL.md](TUTORIAL.md)
- Look up a command → [USER_GUIDE.md](USER_GUIDE.md)
- Solve a complex scenario → [PATTERNS.md](PATTERNS.md)
- Fix a specific problem → [FIELD_GUIDE.md](FIELD_GUIDE.md)
- Quick command reminder → [../reference/QUICK_REFERENCE.md](../reference/QUICK_REFERENCE.md)
- Answer a question → [../reference/FAQ.md](../reference/FAQ.md)
- Understand internals → [../technical/ARCHITECTURE.md](../technical/ARCHITECTURE.md)

---

**Start here for first-time users**: [TUTORIAL.md](TUTORIAL.md)

**Last Updated**: 2026-02-16
