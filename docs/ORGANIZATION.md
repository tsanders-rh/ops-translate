# Documentation Organization

## Directory Structure

```
docs/
├── README.md                          # Main navigation guide
│
├── stakeholder/                       # Executive & Decision Makers
│   ├── README.md                      # Guide to stakeholder docs
│   ├── EXECUTIVE_SUMMARY.md           # 15-min overview, ROI, business case
│   └── COMPARISON.md                  # vs. alternatives, cost analysis
│
├── planning/                          # Project Planning
│   ├── README.md                      # Guide to planning docs
│   ├── USER_STORIES.md                # 44 user stories, personas, metrics
│   └── ROADMAP.md                     # Quarterly roadmap through Q4 2026
│
├── reference/                         # Quick Reference
│   ├── README.md                      # Guide to reference docs
│   ├── QUICK_REFERENCE.md             # One-page cheat sheet
│   └── FAQ.md                         # 50+ Q&A across 7 categories
│
├── guides/                            # User Guides
│   ├── README.md                      # Guide to user documentation
│   ├── TUTORIAL.md                    # Step-by-step walkthrough (30-45 min)
│   ├── USER_GUIDE.md                  # Complete command reference
│   ├── PATTERNS.md                    # Migration patterns & best practices
│   └── FIELD_GUIDE.md                 # Practical scenarios & troubleshooting
│
└── technical/                         # Technical Documentation
    ├── README.md                      # Guide to technical docs
    ├── ARCHITECTURE.md                # System design & internals
    ├── API_REFERENCE.md               # Python API documentation
    ├── INTENT_SCHEMA.md               # Intent YAML schema & data model
    └── POWERCLI_MAPPINGS.md           # PowerCLI to Ansible/KubeVirt mappings
```

## Quick Navigation by Audience

### Executives / Decision Makers
→ **[stakeholder/](stakeholder/)**
- EXECUTIVE_SUMMARY.md - Business case and ROI
- COMPARISON.md - vs. alternatives

### Project Managers / Team Leads
→ **[planning/](planning/)**
- USER_STORIES.md - Features and requirements
- ROADMAP.md - Timeline and priorities

### Platform Engineers / Operators
→ **[guides/](guides/)**
- TUTORIAL.md - First-time walkthrough
- USER_GUIDE.md - Daily reference
- PATTERNS.md - Complex scenarios
- FIELD_GUIDE.md - Troubleshooting

### Developers / Contributors
→ **[technical/](technical/)**
- ARCHITECTURE.md - System design
- API_REFERENCE.md - Code interface
- INTENT_SCHEMA.md - Data model
- POWERCLI_MAPPINGS.md - Translation logic

### Quick Lookups
→ **[reference/](reference/)**
- QUICK_REFERENCE.md - Command cheat sheet
- FAQ.md - Common questions

## Document Purposes

### Stakeholder Documents
| Document | Purpose | Time to Read |
|----------|---------|--------------|
| EXECUTIVE_SUMMARY.md | Business case, ROI, decision criteria | 15 min |
| COMPARISON.md | Comparison vs. alternatives | 30 min |

### Planning Documents
| Document | Purpose | Time to Read |
|----------|---------|--------------|
| USER_STORIES.md | Detailed use cases and requirements | 60-90 min |
| ROADMAP.md | Product evolution timeline | 30 min |

### Reference Documents
| Document | Purpose | Time to Read |
|----------|---------|--------------|
| QUICK_REFERENCE.md | Command cheat sheet | 5-10 min |
| FAQ.md | Q&A for common questions | 60+ min |

### Guide Documents
| Document | Purpose | Time to Read |
|----------|---------|--------------|
| TUTORIAL.md | Hands-on first migration | 30-45 min |
| USER_GUIDE.md | Complete command reference | 60+ min |
| PATTERNS.md | Migration patterns | 45-60 min |
| FIELD_GUIDE.md | Practical troubleshooting | 30 min |

### Technical Documents
| Document | Purpose | Time to Read |
|----------|---------|--------------|
| ARCHITECTURE.md | System design & internals | 60-90 min |
| API_REFERENCE.md | Python API documentation | 45 min |
| INTENT_SCHEMA.md | Data model reference | 30 min |
| POWERCLI_MAPPINGS.md | Translation reference | 30-45 min |

## Where to Start

### "I'm evaluating ops-translate"
1. [stakeholder/EXECUTIVE_SUMMARY.md](stakeholder/EXECUTIVE_SUMMARY.md)
2. [stakeholder/COMPARISON.md](stakeholder/COMPARISON.md)
3. [guides/TUTORIAL.md](guides/TUTORIAL.md) - Try it yourself

### "I'm starting my first migration"
1. [reference/QUICK_REFERENCE.md](reference/QUICK_REFERENCE.md)
2. [guides/TUTORIAL.md](guides/TUTORIAL.md)
3. [guides/USER_GUIDE.md](guides/USER_GUIDE.md)

### "I'm planning a large migration project"
1. [planning/USER_STORIES.md](planning/USER_STORIES.md)
2. [guides/PATTERNS.md](guides/PATTERNS.md)
3. [planning/ROADMAP.md](planning/ROADMAP.md)

### "I'm contributing to ops-translate"
1. [technical/ARCHITECTURE.md](technical/ARCHITECTURE.md)
2. [technical/API_REFERENCE.md](technical/API_REFERENCE.md)
3. [planning/ROADMAP.md](planning/ROADMAP.md)

### "I have a specific question"
1. [reference/FAQ.md](reference/FAQ.md)
2. [reference/QUICK_REFERENCE.md](reference/QUICK_REFERENCE.md)
3. [guides/FIELD_GUIDE.md](guides/FIELD_GUIDE.md)

## README Files

Each subdirectory contains a README.md that provides:
- Document descriptions with audience and purpose
- Quick answers to common questions
- Usage patterns and workflows
- Related documentation links
- Time estimates for reading

**Always start with the README in each directory to understand what's available.**

## Navigation Tips

1. **Main entry point**: [docs/README.md](README.md) provides overview of all documentation
2. **Directory READMEs**: Each subdirectory has a README guiding you to the right document
3. **Cross-references**: Documents link to related content for easy navigation
4. **Search-friendly**: Use GitHub/GitLab search or grep to find specific topics

## Document Versions

All documents include version information and last updated date at the bottom:
```markdown
**Document Version**: 1.0
**Last Updated**: 2026-02-16
```

## Contributing to Documentation

See individual directory READMEs for contribution guidelines specific to each area.

General principles:
- User-focused (solve user problems, not describe features)
- Example-driven (show, don't just tell)
- Searchable (use clear headings and keywords)
- Maintainable (update version and date on changes)

**Last Updated**: 2026-02-16
