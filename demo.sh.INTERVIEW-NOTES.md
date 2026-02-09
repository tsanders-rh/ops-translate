# Adding Interview Step to demo.sh

This document describes how to add the interview workflow to `demo.sh` for interactive gap resolution.

## Overview

The interview step helps resolve PARTIAL and EXPERT-GUIDED components by asking targeted questions and applying human expertise to improve translatability classifications.

## Workflow Position

The interview step should be inserted **between Scene 4 (Gap Analysis) and Scene 5 (Merge Intent)**:

```
Scene 1: Initialize & Import
Scene 2: Static Analysis Summary
Scene 3: Extract Operational Intent
Scene 4: Gap Analysis Review
Scene 4.5: Interview (NEW) ← Insert here
Scene 5: Merge Intent Files
Scene 6: Dry-Run Validation
Scene 7: Generate Artifacts
```

## Implementation

### New Scene 4.5: Interview

Add this section after Scene 4 (around line 242 in current demo.sh):

```bash
# ============================================================================
# Scene 4.5: Interactive Interview (Optional)
# ============================================================================
print_header "Scene 4.5: Interactive Interview"
print_narration "Generate targeted questions for PARTIAL/EXPERT-GUIDED components"
wait_short

# Check if there are any components requiring interview
if [ -f "intent/gaps.json" ] && grep -q "PARTIAL\|BLOCKED" intent/gaps.json; then
    print_narration "Generating interview questions for ambiguous components:"
    run_command "$OPS_CMD intent interview-generate"
    wait_short

    if [ -f "intent/interview.yaml" ]; then
        print_narration "Interview questions generated. Example questions:"
        run_command "cat intent/interview.yaml | head -30"
        wait_medium

        print_narration "In a real workflow, you would:"
        echo "  1. Review intent/interview.yaml"
        echo "  2. Answer questions based on your VMware environment knowledge"
        echo "  3. Save answers to intent/interview-answers.yaml"
        echo ""
        wait_short

        # For demo purposes, check if pre-created answers exist
        if [ -f "../examples/merge-scenario/interview-answers.yaml" ]; then
            print_narration "Using pre-created answers for demo:"
            run_command "cp ../examples/merge-scenario/interview-answers.yaml intent/"
            wait_short

            print_narration "Applying interview answers to update classifications:"
            run_command "$OPS_CMD intent interview-apply"
            wait_medium

            print_narration "Updated gap analysis (classifications improved):"
            run_command "cat intent/gaps.md | head -40"
            wait_short
        else
            print_narration "Skipping interview application (no answers provided for demo)"
            echo "  To use in production: ops-translate intent interview-apply"
        fi
    fi
else
    print_narration "No PARTIAL/EXPERT-GUIDED components detected - skipping interview"
fi

press_enter
```

## Command Details

### `ops-translate intent interview-generate`

**Purpose:** Generates targeted questions for components classified as PARTIAL or EXPERT-GUIDED (formerly BLOCKED)

**Output:** Creates `intent/interview.yaml` with questions like:
```yaml
questions:
  - id: network_selection_logic
    component: Network Selection
    context: "vRealize workflow uses Get-vRealizeNetwork with complex logic"
    question: "How does your VMware environment select networks for VMs?"
    options:
      - "Based on environment variable (dev/prod)"
      - "Based on cost center"
      - "Based on application tier"
      - "Custom logic"
    follow_up: "What attributes determine network selection?"
```

**Usage:**
```bash
ops-translate intent interview-generate
```

### `ops-translate intent interview-apply`

**Purpose:** Applies human-provided answers from `intent/interview-answers.yaml` to update component classifications

**Input:** Reads `intent/interview-answers.yaml`:
```yaml
answers:
  - id: network_selection_logic
    answer: "Based on environment variable (dev/prod)"
    details: "Dev uses dev-network, Prod uses prod-network-vlan100"
    confidence: high
```

**Effects:**
- Updates `intent/gaps.json` with improved classifications
- Updates `intent/gaps.md` report
- May promote components from PARTIAL → SUPPORTED or EXPERT-GUIDED → PARTIAL

**Usage:**
```bash
# After manually editing intent/interview-answers.yaml
ops-translate intent interview-apply
```

## Demo Files Needed

To support the interview demo, create:

### `examples/merge-scenario/interview-answers.yaml`

Pre-created answers for demo purposes:

```yaml
# Pre-created interview answers for demo
answers:
  - id: network_selection_logic
    answer: "Based on environment variable (dev/prod)"
    details: "Simple mapping: dev → dev-network, prod → prod-network"
    confidence: high

  - id: approval_routing
    answer: "Email-based approval"
    details: "Approval emails sent to ops-manager@example.com"
    confidence: high
```

## Testing

Test the interview flow:

```bash
# Run demo with interview step
./demo.sh

# Or test just the interview commands manually
cd demo-workspace
ops-translate intent interview-generate
# Edit intent/interview-answers.yaml manually
ops-translate intent interview-apply
cat intent/gaps.md  # Verify improved classifications
```

## Benefits

Adding the interview step demonstrates:

1. **Human-in-the-loop** approach to complex migrations
2. **Progressive refinement** of translatability classifications
3. **Knowledge capture** from VMware subject matter experts
4. **Improved automation** by converting PARTIAL → SUPPORTED classifications

## When to Use

The interview step is **optional** and most valuable when:

- Gaps report shows many PARTIAL or EXPERT-GUIDED components
- vRealize workflows have complex orchestration logic
- PowerCLI scripts have environment-specific branching
- You have VMware SMEs available to answer questions

## When to Skip

Skip the interview step if:

- Using mock LLM provider (doesn't generate complex components)
- All components are already SUPPORTED
- Running fully automated demo without interaction
- Time-constrained demo scenario

## Production Workflow

In production, the workflow is:

```bash
ops-translate intent extract              # Generates gaps
ops-translate intent interview-generate   # Creates questions
# → Human reviews intent/interview.yaml
# → Human creates intent/interview-answers.yaml with expertise
ops-translate intent interview-apply      # Updates classifications
ops-translate intent merge                # Merge with improved data
ops-translate generate                    # Generate artifacts
```

This captures institutional knowledge and improves migration success rates.
