# Reference Documentation

This directory contains quick reference guides and FAQ for ops-translate.

## Documents

### [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
**Audience**: All users, especially platform engineers and hands-on practitioners

**Purpose**: One-page cheat sheet with essential commands, workflows, and troubleshooting

**Key Sections**:
- **Quick Start** (5 minutes): Fastest path to first artifact
- **Essential Commands**: All commands with syntax and examples
- **Configuration File**: Sample `ops-translate.yaml` with comments
- **Output Structure**: What gets generated and where
- **Classification System**: SUPPORTED/PARTIAL/BLOCKED/MANUAL explained
- **Common Workflows**: Step-by-step for typical scenarios
- **LLM Provider Setup**: Anthropic, OpenAI, Mock provider configuration
- **Template Mappings**: How to map VMware templates to KubeVirt images
- **Troubleshooting Quick Fixes**: Common errors and solutions
- **Cheat Sheet**: Command summary table

**Time to read**: 5-10 minutes (or reference specific sections)

**When to use**:
- Learning the tool for the first time
- Need quick command syntax reminder
- Troubleshooting common issues
- During demos and presentations
- As a desk reference (print-friendly)

**Print this**: Keep at your desk or display during migrations!

---

### [FAQ.md](FAQ.md)
**Audience**: All users, decision makers, technical teams

**Purpose**: Comprehensive Q&A covering 50+ common questions across all topics

**Key Sections**:
1. **General Questions** (6 Q&A)
   - What is ops-translate?
   - Who should use it?
   - Is it production-ready?
   - vs. MTV?
   - Does it need VMware access?
   - Supported languages/frameworks?

2. **Technical Questions** (13 Q&A)
   - How does AI extraction work?
   - Can I avoid using AI?
   - What VMware features are supported?
   - How accurate is translation?
   - Can I customize artifacts?
   - OpenShift/K8s version requirements?
   - Works with vanilla Kubernetes?

3. **Migration Planning** (9 Q&A)
   - How long does migration take?
   - Should I migrate all scripts at once?
   - What to migrate first?
   - How to handle scripts that can't be automated?
   - Can I run multiple times?

4. **Cost and ROI** (4 Q&A)
   - What does it cost?
   - What's the ROI?
   - Hidden costs?

5. **Security and Compliance** (5 Q&A)
   - Is code sent to external services?
   - Does it require credentials?
   - How to handle secrets?
   - Are artifacts secure?
   - Compliance requirements?

6. **Integration and Compatibility** (6 Q&A)
   - GitOps integration?
   - Works with AAP?
   - Existing Ansible collections?
   - Multi-cluster support?
   - CMDB/ServiceNow/ITSM integration?

7. **Troubleshooting** (10+ Q&A)
   - LLM API key errors
   - Generic extraction results
   - Ansible-lint failures
   - Merge conflicts
   - Network/storage issues
   - Schema validation failures
   - Debug output
   - Where to get help?

**Time to read**: 60+ minutes (full) or search for specific questions

**When to use**:
- Answering specific questions
- Addressing stakeholder concerns
- Troubleshooting issues
- Understanding capabilities
- Planning migrations
- Evaluating security/compliance

---

## Typical Usage Patterns

### First-Time User (Learning)
1. Read [QUICK_REFERENCE.md - Quick Start](QUICK_REFERENCE.md#quick-start-5-minutes)
2. Reference [QUICK_REFERENCE.md - Essential Commands](QUICK_REFERENCE.md#essential-commands)
3. Check [FAQ.md - General Questions](FAQ.md#general-questions) for context
4. Follow [../TUTORIAL.md](../TUTORIAL.md) for hands-on practice

**Time**: 30-60 minutes

---

### Active User (Daily Work)
1. Keep [QUICK_REFERENCE.md](QUICK_REFERENCE.md) open in browser tab
2. Reference [QUICK_REFERENCE.md - Command Summary](QUICK_REFERENCE.md#cheat-sheet-command-summary) for syntax
3. Use [FAQ.md - Troubleshooting](FAQ.md#troubleshooting) when issues arise
4. Refer to [QUICK_REFERENCE.md - Common Workflows](QUICK_REFERENCE.md#common-workflows) for patterns

**Time**: Quick reference as needed

---

### Troubleshooting
1. Check [QUICK_REFERENCE.md - Troubleshooting Quick Fixes](QUICK_REFERENCE.md#troubleshooting-quick-fixes)
2. If not resolved, check [FAQ.md - Troubleshooting](FAQ.md#troubleshooting)
3. If still stuck, consult [../FIELD_GUIDE.md](../FIELD_GUIDE.md)
4. Last resort: File issue with debug output

**Success rate**: 80%+ resolved with QUICK_REFERENCE + FAQ

---

### Answering Stakeholder Questions
1. Search [FAQ.md](FAQ.md) by category:
   - Executives → Cost and ROI, General
   - Security → Security and Compliance
   - Technical → Technical Questions
   - Project Managers → Migration Planning
2. Reference specific Q&A in responses
3. Point to [../stakeholder/](../stakeholder/) for deeper context

**Time saved**: 5-10 minutes per question vs. writing from scratch

---

### Demo Preparation
1. Review [QUICK_REFERENCE.md - Common Workflows](QUICK_REFERENCE.md#common-workflows)
2. Practice commands from [QUICK_REFERENCE.md - Essential Commands](QUICK_REFERENCE.md#essential-commands)
3. Have [QUICK_REFERENCE.md - Troubleshooting](QUICK_REFERENCE.md#troubleshooting-quick-fixes) ready for live demo issues
4. Prepare answers from [FAQ.md](FAQ.md) for anticipated questions

**Outcome**: Smooth, confident demo

---

## Quick Answers to Common Questions

### "How do I get started?"
See [QUICK_REFERENCE.md - Quick Start](QUICK_REFERENCE.md#quick-start-5-minutes)

**Answer**: 7 commands, 5 minutes to first artifact

---

### "What's the command to generate Kustomize?"
See [QUICK_REFERENCE.md - Essential Commands](QUICK_REFERENCE.md#generation)

**Answer**: `ops-translate generate --format kustomize`

---

### "Why is my LLM API key not working?"
See [QUICK_REFERENCE.md - Troubleshooting](QUICK_REFERENCE.md#troubleshooting-quick-fixes) and [FAQ.md - LLM API key errors](FAQ.md#llm-api-key-not-found-error)

**Answer**: `export OPS_TRANSLATE_LLM_API_KEY="your-key"`

---

### "How much does this cost?"
See [FAQ.md - Cost and ROI](FAQ.md#what-does-ops-translate-cost)

**Answer**: $0.10-$0.30 per script (LLM API), 40-60% total cost reduction vs. manual

---

### "Can I use this without AI?"
See [FAQ.md - Technical Questions](FAQ.md#what-if-i-dont-want-to-use-ai)

**Answer**: Yes, `--no-ai` mode uses templates only

---

### "Does this work with Ansible Automation Platform?"
See [FAQ.md - Integration](FAQ.md#does-it-work-with-ansible-automation-platform-aap)

**Answer**: Yes, generates AAP-compatible playbooks and role structure

---

### "How do I handle merge conflicts?"
See [QUICK_REFERENCE.md - Troubleshooting](QUICK_REFERENCE.md#conflict-detected-during-merge-error)

**Answer**: Review `intent/conflicts.md`, then `--force` or manual edit

---

### "What VMware features are supported?"
See [FAQ.md - Technical](FAQ.md#what-vmware-features-are-supported)

**Answer**: Full support for VM provisioning, tagging, basic vRealize workflows. Partial support for NSX, custom plugins require manual work.

---

## Search Tips

### By Command
Search [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for specific command names:
- `ops-translate init`
- `ops-translate import`
- `ops-translate generate`
- etc.

### By Error Message
Search [FAQ.md - Troubleshooting](FAQ.md#troubleshooting) or [QUICK_REFERENCE.md - Troubleshooting](QUICK_REFERENCE.md#troubleshooting-quick-fixes) for error text:
- "LLM API key not found"
- "Conflict detected"
- "Schema validation failed"
- etc.

### By Topic
Search [FAQ.md](FAQ.md) by section:
- Cost → "Cost and ROI"
- Security → "Security and Compliance"
- Features → "Technical Questions"
- Planning → "Migration Planning"

### By Use Case
Search [QUICK_REFERENCE.md - Common Workflows](QUICK_REFERENCE.md#common-workflows):
- Simple migration
- Production with governance
- MTV validation mode
- Event-driven automation

---

## Printable Versions

### For Desk Reference
**Print**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- Single-page command reference
- Troubleshooting quick fixes
- Common workflows

**Format**: Landscape orientation, small font (10pt)

### For Presentations
**Extract**:
- [QUICK_REFERENCE.md - Presentation Talking Points](QUICK_REFERENCE.md#presentation-talking-points)
- [FAQ.md](FAQ.md) specific Q&A for anticipated questions

**Use**: Speaker notes or backup slides

### For Training
**Print**:
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Give to all participants
- [FAQ.md](FAQ.md) selected sections - Address common concerns

**Format**: Handouts or digital reference

---

## Contribution Guidelines

### Updating QUICK_REFERENCE.md
- Keep it one-page (conceptually) - quick to scan
- Use tables for command syntax
- Include real examples that work
- Update version date

### Updating FAQ.md
- Add new questions based on user feedback
- Group related questions
- Provide actionable answers
- Link to detailed docs for deep dives
- Update "Questions Not Answered Here?" section

### When to Add New Question to FAQ
- Asked by 3+ different users
- Common point of confusion
- Required for decision-making
- Addresses misconception

---

## Related Documentation

- **[../stakeholder/](../stakeholder/)** - Executive summaries and comparisons
- **[../planning/](../planning/)** - User stories and roadmap
- **[../USER_GUIDE.md](../USER_GUIDE.md)** - Complete command reference
- **[../TUTORIAL.md](../TUTORIAL.md)** - Step-by-step walkthrough
- **[../FIELD_GUIDE.md](../FIELD_GUIDE.md)** - Field scenarios and troubleshooting

---

## Quick Links

**I need to...**
- Learn the tool → [QUICK_REFERENCE.md - Quick Start](QUICK_REFERENCE.md#quick-start-5-minutes)
- Remember a command → [QUICK_REFERENCE.md - Cheat Sheet](QUICK_REFERENCE.md#cheat-sheet-command-summary)
- Fix an error → [QUICK_REFERENCE.md - Troubleshooting](QUICK_REFERENCE.md#troubleshooting-quick-fixes) or [FAQ.md - Troubleshooting](FAQ.md#troubleshooting)
- Answer a question → [FAQ.md](FAQ.md) search by topic
- Do a demo → [QUICK_REFERENCE.md - Common Workflows](QUICK_REFERENCE.md#common-workflows)
- Understand costs → [FAQ.md - Cost and ROI](FAQ.md#cost-and-roi)
- Check compatibility → [FAQ.md - Integration](FAQ.md#integration-and-compatibility)

---

**Print-friendly**: Both documents designed for easy printing and desk reference.

**Last Updated**: 2026-02-16
