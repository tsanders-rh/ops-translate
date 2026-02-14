# demo.sh Improvement Plan

## What's Missing from Current Demo

1. **No `analyze` command** - Demo uses `summarize` but skips the critical `analyze` step for gap analysis
2. **No incremental analysis showcase** - New caching feature not demonstrated
3. **No HTML report generation** - Best feature for stakeholders not shown
4. **No ansible-lint integration** - Code quality validation not shown
5. **Architecture Patterns not mentioned** - Major documentation not highlighted
6. **Too focused on merge scenario** - Most users have single workflows, not merges

## Proposed Demo Flow Improvements

### Scene 0: What is ops-translate? (NEW)
**Problem it solves:**
- Quick intro: "Migrate VMware vRealize/PowerCLI automation to OpenShift"
- Show the before/after (vRO workflow → Ansible + KubeVirt)
- Set expectations: "Planning tool, not magic migration button"

### Scene 1: Initialize & Import (Keep but simplify)
**Changes:**
- Use single realistic workflow instead of merge scenario
- Import from examples/virt-first-realworld/ (has NSX components)
- Show 2-3 workflows max to keep demo focused

### Scene 2: Analyze for Gaps (NEW - Currently Missing!)
**Add this critical step:**
```bash
ops-translate analyze
```
**What to show:**
- Gap analysis with BLOCKED/PARTIAL/SUPPORTED classifications
- Console output showing detected NSX components
- intent/gaps.json and intent/gaps.md files
- Quick peek at recommendations

### Scene 3: Incremental Analysis (NEW - Show caching)
**Demonstrate the new caching feature:**
```bash
# First run
ops-translate analyze
# -> Analyzing 5 workflow(s)

# Second run (no changes)
ops-translate analyze
# -> Skipping 5 unchanged workflow(s)

# Modify one file
touch input/vrealize/provision-vm.workflow.xml

# Third run
ops-translate analyze
# -> Skipping 4 unchanged workflow(s)
# -> Analyzing 1 changed workflow(s)
```

### Scene 4: Generate HTML Report (NEW - Critical for demos!)
**Add report generation:**
```bash
ops-translate report
```
**What to show:**
- Open output/report/index.html in browser
- Show Migration Effort Dashboard (visual percentages)
- Show Architecture Patterns link
- Show Executive Summary
- This is THE feature that sells the tool to management

### Scene 5: Extract Intent (Keep but streamline)
**Changes:**
- Use real LLM if available, mock otherwise
- Show one intent.yaml file (not 3)
- Focus on what was extracted, not merge

### Scene 6: Generate with Linting (NEW)
**Demonstrate ansible-lint integration:**
```bash
ops-translate generate --profile lab --lint
```
**What to show:**
- Linting output (violations found)
- lint-report.md with details
- Show how --lint-strict would fail on violations

### Scene 7: Show Generated Code (Keep)
**What to show:**
- Ansible playbook with best practices
- KubeVirt VM manifest
- Pattern links in code comments (from BLOCKED components)

## Key Improvements Summary

### Add These Scenes:
1. **Scene 0**: What problem does this solve? (30 seconds)
2. **Scene 2**: `analyze` command (currently missing!)
3. **Scene 3**: Incremental analysis demo (NEW feature)
4. **Scene 4**: HTML report generation (CRITICAL for stakeholders)
5. **Scene 6**: Linting integration (NEW feature)

### Update These Scenes:
1. **Scene 1**: Use realistic single workflow (not merge scenario)
2. **Scene 5**: Simplify intent extraction (one file, not three)
3. **Scene 7**: Show pattern links in generated code

### Remove/Simplify:
1. Merge scenario (too complex for intro demo)
2. Interview questions (advanced feature, confusing for intro)
3. Multiple import sources (keep it simple)

## Recommended Timeline (5-7 minutes)

```
0:00-0:30  Scene 0: Introduction (what problem we solve)
0:30-1:00  Scene 1: Initialize + Import (single realistic workflow)
1:00-2:00  Scene 2: Analyze (show gap analysis)
2:00-2:30  Scene 3: Incremental analysis (show caching)
2:30-3:30  Scene 4: HTML Report (VISUAL, show in browser)
3:30-4:30  Scene 5: Extract Intent (show AI extraction)
4:30-5:30  Scene 6: Generate with Linting (show code quality)
5:30-6:00  Scene 7: Review Generated Code
6:00-7:00  Wrap-up: Next steps, documentation links
```

## Key Messaging to Add

**Opening hook:**
- "You don't migrate automation by rewriting everything blind"
- "You start by understanding what you have"

**What to emphasize:**
- "This is a PLANNING tool, not an automated migration button"
- "HTML reports are for stakeholders (execs, architects)"
- "Gap analysis shows what needs manual work UPFRONT"
- "Incremental analysis = fast iteration (70-90% faster)"
- "Architecture Patterns = your migration playbook"
- "Linting = code quality built-in"

**Closing line (CRITICAL):**
> **"You don't start with rewriting automation. You start with understanding it."**

This frames OpenShift as the *safer* choice, not the risky one.

**What NOT to emphasize:**
- Merge scenarios (too complex for intro)
- Interview questions (advanced feature)
- All the CLI flags (focus on happy path)

## Sample Narration Updates

### Scene 0 (NEW):
```
"ops-translate helps you migrate VMware automation to OpenShift.
You give it vRealize workflows or PowerCLI scripts.
It gives you:
  1. Gap analysis - what needs manual work
  2. Architecture guidance - how to handle NSX, approvals, etc.
  3. Generated code - Ansible + KubeVirt to get started

This is a PLANNING tool. It won't magically migrate everything,
but it will save you weeks of analysis and give you a clear path forward."
```

### Scene 2 (NEW - analyze):
```
"The analyze command is where the magic happens.
It detects external dependencies: NSX networking, ServiceNow, custom plugins.
Then classifies each component:
  - SUPPORTED: Can translate automatically
  - PARTIAL: Needs manual configuration
  - BLOCKED: No direct equivalent (check Architecture Patterns)

This is pattern matching - no AI needed, runs offline."
```

### Scene 4 (NEW - HTML report):
```
"The HTML report is what you show to stakeholders.
It has:
  - Executive Summary with percentages ('75% automatable')
  - Migration Effort Dashboard (visual bars)
  - Architecture Patterns guide (5 patterns with code examples)
  - Component-level details with recommendations

This is self-contained - you can email it, no external dependencies."
```

## Implementation Priority

**High Priority (Do First):**
1. Add Scene 2: analyze command
2. Add Scene 4: HTML report generation
3. Update Scene 1: Use single realistic workflow

**Medium Priority:**
4. Add Scene 3: Incremental analysis
5. Add Scene 6: Linting integration
6. Update narration throughout

**Low Priority:**
7. Add Scene 0: Introduction
8. Simplify merge scenario (or replace entirely)

## Example Workflow to Demo

**Instead of merge-scenario/, use virt-first-realworld/:**
- Has 5 realistic workflows
- Includes NSX components (shows BLOCKED classification)
- Has approvals (shows PARTIAL classification)
- Good mix of complexity

**Files to import:**
```bash
ops-translate import --source vrealize --file ../examples/virt-first-realworld/provision-vm-with-nsx-firewall.workflow.xml
ops-translate import --source vrealize --file ../examples/virt-first-realworld/provision-web-app-with-nsx-lb.workflow.xml
```

This gives enough complexity without being overwhelming.
