#!/usr/bin/env bash
#
# ops-translate Demo Script
# Automated demo that showcases all major features
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
}

# Cleanup function
cleanup() {
    if [ "$NO_CLEANUP" = false ]; then
        echo -e "${YELLOW}Cleaning up demo workspace...${NC}"
        cd ..
        rm -rf demo-workspace custom-workspace 2>/dev/null || true
    fi
}

# Set up trap for cleanup on exit
trap cleanup EXIT

# Main demo
clear

print_header "ops-translate Demo"
echo -e "${BOLD}AI-assisted migration from VMware automation to OpenShift Virtualization${NC}"
echo ""
print_narration "This demo shows the complete workflow: Import → Extract → Validate → Generate"
wait_medium

# ============================================================================
# Scene 1: Initialize & Import
# ============================================================================
print_header "Scene 1: Initialize & Import"
print_narration "Initialize workspace and import a PowerCLI script"
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

print_narration "Import an environment-aware PowerCLI script"
wait_short
run_command "$OPS_CMD import --source powercli --file ../examples/powercli/environment-aware.ps1"
press_enter

# ============================================================================
# Scene 2: Summarize (No AI)
# ============================================================================
print_header "Scene 2: Static Analysis Summary"
print_narration "First, analyze the script WITHOUT AI to detect structure"
wait_short

run_command "$OPS_CMD summarize"
wait_medium

print_narration "See what was detected:"
wait_short
run_command "cat intent/summary.md | head -30"
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
wait_medium

print_narration "View the extracted intent YAML:"
wait_short
run_command "cat intent/environment-aware.intent.yaml | head -40"
press_enter

# ============================================================================
# Scene 4: Enhanced Dry-Run
# ============================================================================
print_header "Scene 4: Enhanced Dry-Run Validation"
print_narration "First, merge all intent files into a single intent.yaml"
wait_short

run_command "$OPS_CMD intent merge --force"
wait_short

print_narration "NEW FEATURE: Comprehensive pre-flight validation"
wait_short

run_command "$OPS_CMD dry-run || true"
echo ""
press_enter

# ============================================================================
# Scene 5: Generate YAML Format
# ============================================================================
print_header "Scene 5: Generate Standard YAML"
print_narration "Generate KubeVirt and Ansible artifacts"
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
wait_short

print_narration "KubeVirt VirtualMachine manifest:"
run_command "cat output/kubevirt/vm.yaml | head -30"
press_enter

# ============================================================================
# Scene 6: Generate Kustomize/GitOps Format
# ============================================================================
print_header "Scene 6: Generate GitOps with Kustomize"
print_narration "NEW FEATURE: Multi-environment GitOps structure"
wait_short

run_command "$OPS_CMD generate --profile lab --format kustomize"
wait_medium

print_narration "Kustomize structure with base + environment overlays:"
if command -v tree &> /dev/null; then
    run_command "tree output/"
else
    run_command "ls -R output/"
    echo ""
fi
wait_short

print_narration "Base kustomization:"
run_command "cat output/base/kustomization.yaml"
wait_short

print_narration "Dev overlay (2Gi memory, 1 CPU):"
run_command "cat output/overlays/dev/kustomization.yaml"
wait_short

print_narration "Prod overlay (8Gi memory, 4 CPUs):"
run_command "cat output/overlays/prod/kustomization.yaml | grep -A5 'patches:'"
press_enter

# ============================================================================
# Scene 7: Generate ArgoCD Format
# ============================================================================
print_header "Scene 7: Generate ArgoCD Applications"
print_narration "NEW FEATURE: Full GitOps with ArgoCD"
wait_short

run_command "$OPS_CMD generate --profile lab --format argocd"
wait_medium

print_narration "ArgoCD Application manifests:"
if command -v tree &> /dev/null; then
    run_command "tree output/argocd/"
else
    run_command "ls -R output/argocd/"
    echo ""
fi
wait_short

print_narration "Dev application (automated sync with self-heal):"
run_command "cat output/argocd/dev-application.yaml | grep -A10 'syncPolicy:'"
wait_short

print_narration "Prod application (manual sync for safety):"
run_command "cat output/argocd/prod-application.yaml | grep -A10 'syncPolicy:'"
press_enter

# ============================================================================
# Scene 8: Template Customization
# ============================================================================
print_header "Scene 8: Template Customization"
print_narration "NEW FEATURE: Initialize with editable templates"
wait_short

run_command "cd .."
run_command "$OPS_CMD init custom-workspace --with-templates"
run_command "cd custom-workspace"
wait_medium

print_narration "Template structure for customization:"
if command -v tree &> /dev/null; then
    run_command "tree templates/"
else
    run_command "ls -R templates/"
    echo ""
fi
wait_short

print_narration "KubeVirt template showing Jinja2 variables:"
run_command "cat templates/kubevirt/vm.yaml.j2 | head -20"
press_enter

# ============================================================================
# Wrap-up
# ============================================================================
print_header "Demo Complete!"
echo ""
echo -e "${BOLD}${GREEN}✓ Imported PowerCLI script${NC}"
echo -e "${BOLD}${GREEN}✓ Extracted operational intent${NC}"
echo -e "${BOLD}${GREEN}✓ Validated with enhanced dry-run${NC}"
echo -e "${BOLD}${GREEN}✓ Generated YAML, Kustomize, and ArgoCD formats${NC}"
echo -e "${BOLD}${GREEN}✓ Showed template customization${NC}"
echo ""
echo -e "${CYAN}${BOLD}Key Takeaways:${NC}"
echo -e "  • ${BOLD}Safe by design${NC} - Read-only operations"
echo -e "  • ${BOLD}Multiple formats${NC} - YAML, JSON, Kustomize, ArgoCD"
echo -e "  • ${BOLD}Validated output${NC} - Enhanced dry-run validation"
echo -e "  • ${BOLD}Customizable${NC} - Template system for org standards"
echo ""
echo -e "${MAGENTA}GitHub:${NC} github.com/tsanders-rh/ops-translate"
echo -e "${MAGENTA}License:${NC} Apache-2.0"
echo ""

if [ "$NO_CLEANUP" = true ]; then
    echo -e "${YELLOW}Demo workspaces left intact for exploration:${NC}"
    echo "  - demo-workspace/"
    echo "  - custom-workspace/"
    echo ""
fi
