#!/usr/bin/env bash
#
# ops-translate Demo Script
# Automated demo that showcases all major features
#
# Prerequisites:
#   pip install -r requirements.txt
#   pip install -e .
#
# Usage:
#   ./demo.sh                 # Run with normal delays
#   ./demo.sh --fast          # Run with minimal delays
#   ./demo.sh --no-cleanup    # Don't clean up workspace after demo
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Timing
FAST_MODE=false
NO_CLEANUP=false
DELAY_SHORT=2
DELAY_MEDIUM=3
DELAY_LONG=5

# Parse arguments
for arg in "$@"; do
    case $arg in
        --fast)
            FAST_MODE=true
            DELAY_SHORT=0.5
            DELAY_MEDIUM=1
            DELAY_LONG=2
            ;;
        --no-cleanup)
            NO_CLEANUP=true
            ;;
    esac
done

# Detect ops-translate command
# Store the script directory to find venv later
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v ops-translate &> /dev/null; then
    OPS_CMD="ops-translate"
elif [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    # Use venv Python if available (development mode) with absolute path
    OPS_CMD="$SCRIPT_DIR/venv/bin/python -m ops_translate"
else
    # Fall back to system Python (may not work without installation)
    OPS_CMD="python3 -m ops_translate"
fi

# Helper functions
print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_narration() {
    echo -e "${MAGENTA}📣 $1${NC}"
    echo ""
}

print_command() {
    echo -e "${GREEN}$ $1${NC}"
}

run_command() {
    print_command "$1"
    eval "$1"
    echo ""
}

wait_short() {
    if [ "$FAST_MODE" = false ]; then
        sleep $DELAY_SHORT
    fi
}

wait_medium() {
    if [ "$FAST_MODE" = false ]; then
        sleep $DELAY_MEDIUM
    fi
}

wait_long() {
    if [ "$FAST_MODE" = false ]; then
        sleep $DELAY_LONG
    fi
}

press_enter() {
    if [ "$FAST_MODE" = false ]; then
        echo -e "${YELLOW}[Press Enter to continue...]${NC}"
        read -r
    else
        wait_short
    fi
    clear
}

# Cleanup function
cleanup() {
    if [ "$NO_CLEANUP" = false ]; then
        echo -e "${YELLOW}Cleaning up demo workspace...${NC}"
        cd ..
        rm -rf demo-workspace 2>/dev/null || true
    fi
}

# Set up trap for cleanup on exit
trap cleanup EXIT

# Main demo
clear

print_header "ops-translate Demo"
echo -e "${BOLD}AI-assisted migration from VMware automation to OpenShift Virtualization${NC}"
echo -e "${BOLD}https://github.com/tsanders-rh/ops-translate"
echo ""
print_narration "This demo shows the complete workflow:"
echo -e "  ${CYAN}Initialize → Import → Summarize → Extract → Review → Merge → Validate → Generate${NC}"
echo ""

press_enter

# ============================================================================
# Scene 1: Initialize & Import
# ============================================================================
print_header "Scene 1: Initialize & Import"
print_narration "Initialize workspace and import multiple automation sources"
wait_short

run_command "$OPS_CMD init demo-workspace"
run_command "cd demo-workspace"

print_narration "Workspace created with organized directory structure:"
wait_short
if command -v tree &> /dev/null; then
    run_command "tree -L 2 -C"
else
    run_command "ls -la"
    echo ""
fi
press_enter

print_narration "Import dev provisioning script"
wait_short
run_command "$OPS_CMD import --source powercli --file ../examples/merge-scenario/dev-provision.ps1"
wait_short

print_narration "Import prod provisioning script"
wait_short
run_command "$OPS_CMD import --source powercli --file ../examples/merge-scenario/prod-provision.ps1"
wait_short

print_narration "Import approval workflow"
wait_short
run_command "$OPS_CMD import --source vrealize --file ../examples/merge-scenario/approval.workflow.xml"
press_enter

# ============================================================================
# Scene 2: Summarize (No AI)
# ============================================================================
print_header "Scene 2: Static Analysis Summary"
print_narration "Analyze all sources WITHOUT AI to detect structure"
wait_short

run_command "$OPS_CMD summarize"
wait_medium

print_narration "See what was detected across all sources:"
wait_short
run_command "cat intent/summary.md | head -40"
press_enter

# ============================================================================
# Scene 3: Extract Intent
# ============================================================================
print_header "Scene 3: Extract Operational Intent"
print_narration "Extract normalized intent using AI (or mock provider)"
wait_short

# Configure mock provider to avoid API costs
cat > ops-translate.yaml << EOF
llm:
  provider: mock
  model: mock-model
  api_key_env: OPS_TRANSLATE_LLM_API_KEY

profiles:
  lab:
    default_namespace: virt-lab
    default_network: lab-network
    default_storage_class: nfs
  prod:
    default_namespace: virt-prod
    default_network: prod-network
    default_storage_class: ceph-rbd
EOF

run_command "$OPS_CMD intent extract"
press_enter

print_narration "View one of the extracted intent files:"
wait_short
run_command "cat intent/dev-provision.intent.yaml | head -30"
wait_short

print_narration "Three intent files created (one per source):"
run_command "ls -1 intent/*.intent.yaml"
press_enter

# ============================================================================
# Scene 4: Review Gap Analysis
# ============================================================================
print_header "Scene 4: Gap Analysis Review"
print_narration "View detected gaps and migration guidance"
wait_short

if [ -f "intent/gaps.md" ]; then
    print_narration "Gap analysis report (shows what needs manual work):"
    run_command "cat intent/gaps.md | head -40"
else
    print_narration "No gap analysis generated (mock provider or no complex components)"
fi
press_enter

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
    press_enter

    if [ -f "intent/questions.json" ]; then
        print_narration "Interview questions generated. Example questions:"
        run_command "cat intent/questions.json | head -30"
        wait_medium

        print_narration "In a real workflow, you would:"
        echo "  1. Review intent/questions.json"
        echo "  2. Answer questions based on your VMware environment knowledge"
        echo "  3. Save answers to intent/answers.yaml"
        echo ""
        wait_short

        # For demo purposes, check if pre-created answers exist
        if [ -f "../examples/merge-scenario/answers.yaml" ]; then
            print_narration "Using pre-created answers for demo:"
            run_command "cp ../examples/merge-scenario/answers.yaml intent/"
            wait_short

            print_narration "Applying interview answers to update classifications:"
            run_command "$OPS_CMD intent interview-apply"
            press_enter

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

# ============================================================================
# Scene 5: Merge Intent
# ============================================================================
print_header "Scene 5: Merge Intent Files"
print_narration "Merge 3 intent files into single unified workflow"
wait_short

run_command "$OPS_CMD intent merge --force"
wait_short

print_narration "View the merged intent (combines dev, prod, and approval):"
run_command "cat intent/intent.yaml | head -40"
wait_short

print_narration "Notice: unified inputs, governance rules, and environment profiles"
press_enter

# ============================================================================
# Scene 6: Dry-Run Validation
# ============================================================================
print_header "Scene 6: Dry-Run Validation"
print_narration "Validate intent structure before generating artifacts"
wait_short

run_command "$OPS_CMD dry-run || true"
echo ""
press_enter

# ============================================================================
# Scene 7: Generate Artifacts
# ============================================================================
print_header "Scene 7: Generate Artifacts"
print_narration "Generate KubeVirt manifests and Ansible playbooks"
wait_short

run_command "$OPS_CMD generate --profile lab --format yaml"
wait_medium

print_narration "Show generated structure:"
if command -v tree &> /dev/null; then
    run_command "tree output/"
else
    run_command "ls -R output/"
    echo ""
fi
press_enter

print_narration "KubeVirt VirtualMachine manifest:"
run_command "cat output/kubevirt/vm.yaml | head -30"
press_enter

print_narration "Ansible playbook structure:"
run_command "cat output/ansible/site.yml"
press_enter

  print_narration "Ansible tasks with gap analysis TODOs:"
  run_command "cat output/ansible/roles/provision_vm/tasks/main.yml | head -40"
  press_enter

# ============================================================================
# Wrap-up
# ============================================================================
print_header "Demo Complete!"
echo ""
echo -e "${BOLD}${CYAN}Complete Workflow Demonstrated:${NC}"
echo -e "${BOLD}${GREEN}✓ 1. Initialize${NC} workspace with organized structure"
echo -e "${BOLD}${GREEN}✓ 2. Import${NC} multiple sources (PowerCLI + vRealize)"
echo -e "${BOLD}${GREEN}✓ 3. Summarize${NC} with static analysis (no AI)"
echo -e "${BOLD}${GREEN}✓ 4. Extract${NC} operational intent using AI (creates 3 intent files)"
echo -e "${BOLD}${GREEN}✓ 5. Review${NC} gap analysis for migration guidance"
echo -e "${BOLD}${GREEN}✓ 6. Merge${NC} 3 intent files into unified workflow"
echo -e "${BOLD}${GREEN}✓ 7. Validate${NC} with enhanced dry-run checks"
echo -e "${BOLD}${GREEN}✓ 8. Generate${NC} KubeVirt + Ansible artifacts"
echo ""
echo -e "${CYAN}${BOLD}Key Takeaways:${NC}"
echo -e "  • ${BOLD}Multi-source merge${NC} - Combine dev, prod, approval into one workflow"
echo -e "  • ${BOLD}Safe by design${NC} - Read-only operations, no live access"
echo -e "  • ${BOLD}Transparent${NC} - Every step shows what's happening"
echo -e "  • ${BOLD}AI only for intent${NC} - Everything else is template-based"
echo -e "  • ${BOLD}Gap analysis${NC} - Know what needs manual work upfront"
echo ""
echo -e "${CYAN}${BOLD}What was merged:${NC}"
echo -e "  • dev-provision.ps1 - Quick provisioning for developers"
echo -e "  • prod-provision.ps1 - Governed provisioning with strict requirements"
echo -e "  • approval.workflow.xml - vRealize approval routing"
echo -e "  → Single unified workflow handling both environments"
echo ""
echo -e "${MAGENTA}GitHub:${NC} github.com/tsanders-rh/ops-translate"
echo -e "${MAGENTA}License:${NC} Apache-2.0"
echo ""

if [ "$NO_CLEANUP" = true ]; then
    echo -e "${YELLOW}Demo workspace left intact for exploration:${NC}"
    echo "  - demo-workspace/"
    echo ""
fi
