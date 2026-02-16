# ops-translate Documentation

Welcome to the ops-translate documentation. This guide will help you find the right documentation for your needs.

## Documentation Structure

### For Stakeholders and Decision Makers

📊 **[stakeholder/](stakeholder/)** - Executive-level and decision-making documentation
- **[EXECUTIVE_SUMMARY.md](stakeholder/EXECUTIVE_SUMMARY.md)** - One-page overview for busy executives with ROI and business case
- **[COMPARISON.md](stakeholder/COMPARISON.md)** - Detailed comparison vs. alternatives (manual migration, professional services, etc.)

**Use when**: Presenting to leadership, building business case, evaluating alternatives

---

### For Project Planning

📋 **[planning/](planning/)** - Project planning and roadmap documentation
- **[USER_STORIES.md](planning/USER_STORIES.md)** - Comprehensive user stories, use cases, and requirements (current + future)
- **[ROADMAP.md](planning/ROADMAP.md)** - Product roadmap with quarterly milestones and feature timeline

**Use when**: Planning sprints, estimating timelines, prioritizing features

---

### For Quick Reference

🔍 **[reference/](reference/)** - Quick reference guides and FAQ
- **[QUICK_REFERENCE.md](reference/QUICK_REFERENCE.md)** - One-page cheat sheet with essential commands and workflows
- **[FAQ.md](reference/FAQ.md)** - Comprehensive Q&A covering 50+ common questions

**Use when**: Need quick answers, troubleshooting, learning commands

---

### For Users and Operators

📚 **[guides/](guides/)** - Comprehensive user guides and tutorials
- **[TUTORIAL.md](guides/TUTORIAL.md)** - Step-by-step walkthrough for first-time users (30-45 min hands-on)
- **[USER_GUIDE.md](guides/USER_GUIDE.md)** - Complete command reference and usage guide
- **[PATTERNS.md](guides/PATTERNS.md)** - Migration patterns for complex scenarios and best practices
- **[FIELD_GUIDE.md](guides/FIELD_GUIDE.md)** - Practical field guide for common scenarios and troubleshooting

**Use when**: Learning the tool, looking up commands, solving complex scenarios, daily operations

---

### For Developers and Contributors

🔧 **[technical/](technical/)** - Technical architecture and API documentation
- **[ARCHITECTURE.md](technical/ARCHITECTURE.md)** - System design, internals, and technical architecture
- **[API_REFERENCE.md](technical/API_REFERENCE.md)** - Python API reference for developers
- **[INTENT_SCHEMA.md](technical/INTENT_SCHEMA.md)** - Intent YAML schema reference and data model
- **[POWERCLI_MAPPINGS.md](technical/POWERCLI_MAPPINGS.md)** - PowerCLI to Ansible/KubeVirt mapping reference

**Use when**: Contributing code, extending functionality, understanding internals, debugging

---

## Quick Navigation by Role

### I'm an Executive / Decision Maker
**Start here**:
1. [Executive Summary](stakeholder/EXECUTIVE_SUMMARY.md) - 15 min read
2. [Comparison vs. Alternatives](stakeholder/COMPARISON.md) - Understand options
3. [User Stories](planning/USER_STORIES.md) - Review success metrics

**Goal**: Make informed decision about adopting ops-translate

---

### I'm a Migration Architect
**Start here**:
1. [User Stories](planning/USER_STORIES.md) - Understand capabilities and use cases
2. [Tutorial](guides/TUTORIAL.md) - Hands-on walkthrough
3. [Patterns](guides/PATTERNS.md) - Migration patterns for complex scenarios
4. [FAQ](reference/FAQ.md) - Address common concerns

**Goal**: Plan migration strategy and assess feasibility

---

### I'm a Platform Engineer
**Start here**:
1. [Quick Reference](reference/QUICK_REFERENCE.md) - Essential commands
2. [Tutorial](guides/TUTORIAL.md) - Step-by-step first migration
3. [User Guide](guides/USER_GUIDE.md) - Complete command reference
4. [PowerCLI Mappings](technical/POWERCLI_MAPPINGS.md) - Translation reference

**Goal**: Execute migrations efficiently

---

### I'm a Team Lead / Project Manager
**Start here**:
1. [User Stories](planning/USER_STORIES.md) - Features and requirements
2. [Roadmap](planning/ROADMAP.md) - Timeline and priorities
3. [Executive Summary](stakeholder/EXECUTIVE_SUMMARY.md) - ROI and metrics
4. [FAQ](reference/FAQ.md) - Address team questions

**Goal**: Plan project, allocate resources, track progress

---

### I'm a Developer / Contributor
**Start here**:
1. [Architecture](technical/ARCHITECTURE.md) - System design and internals
2. [API Reference](technical/API_REFERENCE.md) - Python API documentation
3. [Intent Schema](technical/INTENT_SCHEMA.md) - Data model reference
4. [Roadmap](planning/ROADMAP.md) - Future features and priorities

**Goal**: Contribute features or fix bugs

---

## Documentation by Task

### Task: Build Business Case
1. [Executive Summary](stakeholder/EXECUTIVE_SUMMARY.md) - ROI and benefits
2. [Comparison](stakeholder/COMPARISON.md) - Cost comparison examples
3. [User Stories - Success Metrics](planning/USER_STORIES.md#success-metrics)

### Task: Evaluate Feasibility
1. [Tutorial](guides/TUTORIAL.md) - Try it yourself (30 min)
2. [User Stories - Current State](planning/USER_STORIES.md#current-state-user-stories)
3. [FAQ - Migration Planning](reference/FAQ.md#migration-planning)

### Task: Plan Migration Project
1. [User Stories](planning/USER_STORIES.md) - Requirements and capabilities
2. [Patterns](guides/PATTERNS.md) - Migration patterns
3. [FAQ - Migration Planning](reference/FAQ.md#migration-planning)

### Task: First Migration
1. [Quick Reference](reference/QUICK_REFERENCE.md) - Essential commands
2. [Tutorial](guides/TUTORIAL.md) - Step-by-step walkthrough
3. [User Guide](guides/USER_GUIDE.md) - Detailed command reference

### Task: Troubleshooting
1. [FAQ - Troubleshooting](reference/FAQ.md#troubleshooting)
2. [Quick Reference - Troubleshooting](reference/QUICK_REFERENCE.md#troubleshooting-quick-fixes)
3. [Field Guide](guides/FIELD_GUIDE.md) - Common scenarios

### Task: Customize Templates
1. [Patterns](guides/PATTERNS.md) - Customization examples
2. [Architecture](technical/ARCHITECTURE.md) - Template system design
3. [User Guide - Advanced](guides/USER_GUIDE.md) - Custom templates section

### Task: Understand Roadmap
1. [Roadmap](planning/ROADMAP.md) - Feature timeline
2. [User Stories - Future](planning/USER_STORIES.md#future-considerations)
3. [Architecture](technical/ARCHITECTURE.md) - Extensibility points

---

## Documentation Standards

All documentation in this repository follows these standards:

- **Markdown format** - Easy to read in GitHub/GitLab, easy to convert to PDF
- **Active voice** - Clear, direct language
- **Code examples** - Runnable examples where applicable
- **Version tracking** - Document version and last updated date at bottom
- **Cross-references** - Links to related documentation
- **Progressive disclosure** - Summary first, details follow

---

## Contributing to Documentation

Found an error or want to improve documentation?

1. **Small fixes** - Submit PR directly
2. **New sections** - Open issue to discuss first
3. **New documents** - Follow structure and standards above

**Documentation principles**:
- User-focused (solve user problems, not describe features)
- Example-driven (show, don't just tell)
- Searchable (use clear headings and keywords)
- Maintainable (update version and date on changes)

---

## PDF Generation

To generate PDF versions for offline use or distribution:

```bash
# Using pandoc (recommended)
pandoc stakeholder/EXECUTIVE_SUMMARY.md -o EXECUTIVE_SUMMARY.pdf

# Using markdown-pdf (npm package)
markdown-pdf stakeholder/EXECUTIVE_SUMMARY.md
```

---

## Quick Links

### Most Popular Documents
1. [Executive Summary](stakeholder/EXECUTIVE_SUMMARY.md) - Overview and business case
2. [Quick Reference](reference/QUICK_REFERENCE.md) - Command cheat sheet
3. [Tutorial](guides/TUTORIAL.md) - First migration walkthrough
4. [FAQ](reference/FAQ.md) - Common questions
5. [User Guide](guides/USER_GUIDE.md) - Complete reference

### For Presentations
1. [Executive Summary](stakeholder/EXECUTIVE_SUMMARY.md) - 15-min executive presentation
2. [Comparison](stakeholder/COMPARISON.md) - Competitive analysis
3. [User Stories - Success Metrics](planning/USER_STORIES.md#success-metrics)

### For Learning
1. [Tutorial](guides/TUTORIAL.md) - Hands-on (30-45 min)
2. [Quick Reference](reference/QUICK_REFERENCE.md) - Essential commands
3. [Patterns](guides/PATTERNS.md) - Real-world scenarios

---

**Need help?** Start with the [FAQ](reference/FAQ.md) or open an issue in the project repository.

**Last Updated**: 2026-02-16
