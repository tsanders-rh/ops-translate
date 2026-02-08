# ops-translate Demo Script

> **Duration**: ~4-5 minutes
> **Goal**: Showcase the complete multi-source merge workflow

## Demo Overview

This demo shows how ops-translate merges **multiple automation sources** into a **unified workflow** and generates production-ready artifacts.

**What we'll demonstrate:**
1. Import 3 sources (2 PowerCLI scripts + 1 vRealize workflow)
2. Extract operational intent from each source (with AI)
3. Review gap analysis
4. Merge into single unified workflow
5. Validate with dry-run
6. Generate KubeVirt and Ansible artifacts

**Key Feature**: Multi-source merge combines dev provisioning, prod provisioning, and approval workflow into one unified automation.

---

## Setup (Before Recording)

```bash
# First-time setup (if not already done)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Clean slate
rm -rf demo-workspace 2>/dev/null

# Set up LLM provider (use mock for demo to avoid costs)
export OPS_TRANSLATE_LLM_API_KEY="demo-key"
```

---

## Scene 1: Introduction (20 seconds)

**Narration:**
> "ops-translate is an AI-assisted CLI tool that migrates VMware automation to OpenShift Virtualization. Today we'll show how it merges multiple automation sources into a single unified workflow. Let's see it in action."

---

## Scene 2: Initialize & Import (45 seconds)

**Narration:**
> "First, we'll initialize a workspace and import three separate automation sources: dev provisioning, prod provisioning, and an approval workflow."

**Commands:**
```bash
# Initialize workspace
ops-translate init demo-workspace
cd demo-workspace

# Show what was created
tree -L 2

# Import dev provisioning script
ops-translate import --source powercli \
  --file ../examples/merge-scenario/dev-provision.ps1

# Import prod provisioning script
ops-translate import --source powercli \
  --file ../examples/merge-scenario/prod-provision.ps1

# Import approval workflow
ops-translate import --source vrealize \
  --file ../examples/merge-scenario/approval.workflow.xml
```

**Show:** Directory structure showing 3 imported files in `input/powercli/` and `input/vrealize/`

**Narration:**
> "We now have three sources: simple dev provisioning, governed prod provisioning, and vRealize approval routing."

---

## Scene 3: Summarize (No AI) (30 seconds)

**Narration:**
> "Before using AI, let's see what static analysis can detect across all three sources."

**Commands:**
```bash
# Analyze all sources without AI
ops-translate summarize

# Show what was detected
cat intent/summary.md
```

**Show:** Summary detecting parameters, environment branching, approval requirements across all sources.

---

## Scene 4: Extract Intent (45 seconds)

**Narration:**
> "Now let's extract normalized operational intent from each source. This creates three platform-agnostic intent files."

**Commands:**
```bash
# Extract operational intent using AI
ops-translate intent extract

# Show one of the intent files
cat intent/dev-provision.intent.yaml

# List all intent files
ls -1 intent/*.intent.yaml
```

**Show:**
- One intent YAML showing structure
- Three .intent.yaml files created (one per source)

**Narration:**
> "Notice we have three separate intent files. Now we'll merge them into one unified workflow."

---

## Scene 5: Review Gap Analysis (30 seconds)

**Narration:**
> "The extraction also performed gap analysis to identify components needing manual work."

**Commands:**
```bash
# View gap analysis (if exists)
cat intent/gaps.md | head -40
```

**Show:** Gap analysis report with translatability classifications.

---

## Scene 6: Merge Intent (60 seconds)

**Narration:**
> "This is the key feature: merging three intent files into one unified workflow that handles both dev and prod environments."

**Commands:**
```bash
# Merge all intent files
ops-translate intent merge --force

# Show the merged result
cat intent/intent.yaml
```

**Show:** Merged intent.yaml highlighting:
- Unified inputs (combined from all sources)
- Governance rules (approval required for prod)
- Environment profiles (dev and prod)
- Union of all operations

**Narration:**
> "Notice the merged workflow includes approval requirements from vRealize, resource constraints from both dev and prod, and unified metadata. One workflow, multiple environments."

---

## Scene 7: Dry-Run Validation (30 seconds)

**Narration:**
> "Before generating, let's validate the merged intent with dry-run checks."

**Commands:**
```bash
# Validate merged intent
ops-translate dry-run
```

**Show:** Validation output showing schema checks and execution plan.

---

## Scene 8: Generate Artifacts (45 seconds)

**Narration:**
> "Now we'll generate production-ready KubeVirt and Ansible artifacts from our merged workflow."

**Commands:**
```bash
# Generate YAML artifacts
ops-translate generate --profile lab --format yaml

# Show generated structure
tree output/

# View KubeVirt manifest
cat output/kubevirt/vm.yaml | head -30

# View Ansible playbook
cat output/ansible/site.yml | head -20
```

**Show:**
- Complete output directory structure
- KubeVirt VirtualMachine manifest
- Ansible playbook with environment-aware logic

---

## Scene 9: Wrap-up (30 seconds)

**Narration:**
> "In just a few minutes, we've merged three separate automation sources into one unified workflow and generated production-ready artifacts for OpenShift Virtualization."

**On-screen text:**
```
✓ Merged 3 sources:
  • dev-provision.ps1 → Quick dev provisioning
  • prod-provision.ps1 → Governed prod provisioning
  • approval.workflow.xml → vRealize approval routing
  ↓
  Single unified workflow handling both environments

GitHub: github.com/tsanders-rh/ops-translate
License: Apache-2.0
```

**Narration:**
> "ops-translate is open source. Check out the GitHub repo for more examples and documentation. Thanks for watching!"

---

## Technical Setup Notes

### Recording Settings
- **Resolution**: 1920x1080 or 1280x720
- **Terminal**: Clean theme (Solarized Dark, Dracula)
- **Font size**: 14-16pt for readability
- **Terminal width**: 100-120 columns
- **Speed**: Use `asciinema` or similar to record

### Pre-recording Checklist
- [ ] Clean terminal history (`history -c`)
- [ ] Test all commands work end-to-end
- [ ] Mock LLM configured to avoid API costs
- [ ] Tree command installed (`brew install tree`)
- [ ] Example files present in `examples/merge-scenario/`

### Alternative: Automated Demo Script

Use the provided `demo.sh` script to automate the demo:

```bash
./demo.sh              # Run with normal delays
./demo.sh --fast       # Run with minimal delays
./demo.sh --no-cleanup # Keep workspace after demo
```

The script automatically runs all commands and provides narration.

---

## Key Messages to Emphasize

1. **Multi-Source Merge**: Combine separate dev, prod, and approval automation into one unified workflow
2. **Safe by Design**: Read-only operations, no live system access
3. **Transparent**: Every step shows what's happening
4. **AI for Intent Only**: Extraction uses AI, everything else is deterministic
5. **Gap Analysis**: Know what needs manual work upfront
6. **Production-Ready**: Generates complete KubeVirt + Ansible artifacts

---

## What Makes This Demo Compelling

✅ **Real-world scenario**: Organizations actually have separate dev/prod automation
✅ **Shows the merge value**: Demonstrates why merging makes sense
✅ **Complete workflow**: Import → Extract → Merge → Validate → Generate
✅ **Tangible output**: Real KubeVirt and Ansible artifacts

---

## Common Demo Pitfalls to Avoid

- ❌ Don't skip explaining WHY we're merging (show the value)
- ❌ Don't read entire YAML files (show key sections only)
- ❌ Don't go too fast through the merge step (it's the key feature)
- ✅ DO highlight unified inputs and governance in merged intent
- ✅ DO show that 3 files → 1 unified workflow
- ✅ DO emphasize production-ready output
