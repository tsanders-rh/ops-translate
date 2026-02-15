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

# ============================================================================
# Scene 0: Introduction
# ============================================================================
print_header "ops-translate: VMware Automation Translation & Migration"
echo -e "${BOLD}https://github.com/tsanders-rh/ops-translate${NC}"
echo ""
print_narration "ops-translate helps you migrate VMware automation to OpenShift."
echo ""
echo -e "${CYAN}You give it: vRealize workflows or PowerCLI scripts.${NC}"
echo -e "${CYAN}It gives you:${NC}"
echo ""
echo -e "  ${BOLD}1.${NC} ${GREEN}Automated translation${NC} - Basic VM provisioning works automatically"
echo -e "  ${BOLD}2.${NC} ${YELLOW}Gap analysis${NC} - What needs manual work (NSX, ServiceNow, etc.)"
echo -e "  ${BOLD}3.${NC} ${CYAN}Architecture guidance${NC} - How to handle blocked components"
echo -e "  ${BOLD}4.${NC} ${MAGENTA}Generated code${NC} - Ansible + KubeVirt to get started"
echo ""
wait_short
echo -e "${BOLD}${CYAN}What we'll demo:${NC}"
echo ""
echo -e "  • Initialize workspace and import vRealize workflows + PowerCLI scripts"
echo -e "  • Analyze for gaps (pattern matching, no AI required)"
echo -e "  • Generate HTML reports for stakeholders"
echo -e "  • Extract and merge operational intent with AI"
echo -e "  • Generate Ansible + KubeVirt code with linting"
echo ""

press_enter

# ============================================================================
# Scene 1: Initialize & Import
# ============================================================================
print_header "Scene 1: Initialize & Import"
print_narration "You don't migrate automation by rewriting everything blind."
echo -e "${MAGENTA}You start by understanding what you have.${NC}"
echo ""
wait_short

run_command "$OPS_CMD init demo-workspace"
run_command "cd demo-workspace"
press_enter
print_narration "Workspace created with organized directory structure:"
wait_short
if command -v tree &> /dev/null; then
    run_command "tree -L 2 -C"
else
    run_command "ls -la"
    echo ""
fi
press_enter

print_narration "Import simple PowerCLI script (basic VM provisioning)"
wait_short
run_command "$OPS_CMD import --source powercli --file ../examples/powercli/simple-vm.ps1"
wait_short

print_narration "Import environment-aware PowerCLI script (dev/prod branching)"
wait_short
run_command "$OPS_CMD import --source powercli --file ../examples/powercli/environment-aware.ps1"
wait_short

print_narration "Now import complex workflows with NSX networking..."
wait_short
run_command "$OPS_CMD import --source vrealize --file ../examples/virt-first-realworld/vrealize/provision-vm-with-nsx-firewall.workflow.xml"
wait_short

print_narration "Import vRealize workflow for web app with NSX load balancer"
wait_short
run_command "$OPS_CMD import --source vrealize --file ../examples/virt-first-realworld/vrealize/provision-web-app-with-nsx-lb.workflow.xml"
press_enter

# ============================================================================
# Scene 2: Analyze for Gaps
# ============================================================================
print_header "Scene 2: Analyze for Gaps"
print_narration "The analyze command is where the magic happens."
echo -e "${MAGENTA}It detects external dependencies: NSX networking, ServiceNow, custom plugins.${NC}"
echo ""
wait_short

print_narration "Then classifies each component:"
echo -e "  ${GREEN}SUPPORTED:${NC} Can translate automatically"
echo -e "  ${YELLOW}PARTIAL:${NC} Needs manual configuration"
echo -e "  ${RED}BLOCKED:${NC} No direct equivalent (check Architecture Patterns)"
echo ""
wait_short

print_narration "This is pattern matching - no AI needed, runs offline."
echo ""
print_narration "We should see:"
echo -e "  ${GREEN}SUPPORTED:${NC} Basic VM provisioning (CPU, memory, disk, tagging)"
echo -e "  ${RED}BLOCKED:${NC} NSX Security Groups, Load Balancers"
echo ""
press_enter

run_command "$OPS_CMD analyze"
wait_medium
press_enter

print_narration "Gap analysis created. Let's view the summary:"
wait_short
run_command "cat intent/gaps.md | head -40"
press_enter

print_narration "Full component details available in JSON format:"
wait_short
run_command "cat intent/gaps.json | head -30"
press_enter

# ============================================================================
# Scene 3: Generate HTML Report
# ============================================================================
print_header "Scene 3: Generate HTML Report"
print_narration "The HTML report is what you show to stakeholders."
echo ""
wait_short

print_narration "It has:"
echo -e "  • Executive Summary with percentages ('75% automatable')"
echo -e "  • Migration Effort Dashboard (visual bars)"
echo -e "  • Architecture Patterns guide (5 patterns with code examples)"
echo -e "  • Component-level details with recommendations"
echo ""
wait_medium

print_narration "This is self-contained - you can email it, no external dependencies."
wait_short

run_command "$OPS_CMD report"
wait_medium

print_narration "Report generated! Let's see what was created:"
wait_short
if command -v tree &> /dev/null; then
    run_command "tree output/report/"
else
    run_command "ls -la output/report/"
    echo ""
fi
wait_short

print_narration "In a real demo, you would open output/report/index.html in a browser."
echo -e "${YELLOW}For this terminal demo, here's what the report shows:${NC}"
echo ""
echo -e "  ${BOLD}Executive Summary${NC} - High-level metrics for decision makers"
echo -e "  ${BOLD}Migration Effort Dashboard${NC} - Visual breakdown showing:"
echo -e "    ${GREEN}GREEN (SUPPORTED)${NC} - VM provisioning, compute, storage, tagging"
echo -e "    ${RED}RED (BLOCKED)${NC} - NSX Security Groups, Load Balancers"
echo -e "  ${BOLD}Component Analysis${NC} - Detailed breakdown with recommendations"
echo -e "  ${BOLD}Architecture Patterns${NC} - How to handle NSX, approvals, ServiceNow, etc."
echo ""
press_enter

# ============================================================================
# Scene 4: Extract Operational Intent
# ============================================================================
print_header "Scene 4: Extract Operational Intent"
print_narration "Extract normalized intent using AI"
wait_short

# Configure LLM provider and profiles
# If OPS_TRANSLATE_LLM_API_KEY is not set, use mock provider for demo
if [ -z "$OPS_TRANSLATE_LLM_API_KEY" ]; then
    echo -e "${YELLOW}Note: Using mock LLM provider (set OPS_TRANSLATE_LLM_API_KEY for real AI)${NC}"
    echo ""
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
else
    echo -e "${GREEN}Using configured LLM provider${NC}"
    echo ""
    cat > ops-translate.yaml << EOF
llm:
  provider: anthropic
  model: claude-sonnet-3-5-20241022
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
fi

run_command "$OPS_CMD intent extract"
wait_medium

print_narration "View one of the extracted intent files:"
wait_short
# Show the first .intent.yaml file found (intent extract may have different naming)
INTENT_FILE=$(ls intent/*.intent.yaml 2>/dev/null | head -1)
if [ -n "$INTENT_FILE" ]; then
    run_command "cat $INTENT_FILE | head -40"
else
    echo -e "${YELLOW}No intent files found - intent extraction may have been skipped${NC}"
    echo ""
fi
wait_short

print_narration "Intent files normalize automation across different source formats."
echo -e "${CYAN}vRealize workflows → normalized YAML intent${NC}"
echo -e "${CYAN}PowerCLI scripts → same normalized YAML intent${NC}"
echo ""
wait_short

print_narration "Now merge individual intent files into unified intent:"
wait_short
run_command "$OPS_CMD intent merge --force"
wait_medium

print_narration "Merged intent file created at intent/intent.yaml"
echo -e "${CYAN}This unified intent is used for artifact generation${NC}"
echo ""
echo -e "${YELLOW}Note: --force used because PowerCLI + vRealize sources may have conflicting definitions${NC}"
echo -e "${YELLOW}In production, review intent/conflicts.md to resolve conflicts manually${NC}"
echo ""
press_enter

# ============================================================================
# Scene 5: Generate with Linting
# ============================================================================
print_header "Scene 5: Generate Artifacts with Linting"
print_narration "Generate KubeVirt manifests and Ansible playbooks with code quality checks"
wait_short

run_command "$OPS_CMD generate --profile lab --format yaml --lint"
wait_medium

print_narration "Linting checks for Ansible best practices:"
echo -e "  • Task naming conventions"
echo -e "  • Deprecated module usage"
echo -e "  • Security vulnerabilities"
echo -e "  • YAML formatting issues"
echo ""
wait_short

if [ -f "output/lint-report.md" ]; then
    print_narration "Lint report generated. Let's view it:"
    run_command "cat output/lint-report.md | head -40"
    press_enter
else
    print_narration "No linting violations found (or ansible-lint not installed)."
    echo -e "${CYAN}Install ansible-lint for code quality checks: pip install ansible-lint${NC}"
    echo ""
    press_enter
fi

print_narration "Show generated structure:"
if command -v tree &> /dev/null; then
    run_command "tree output/ansible/"
else
    run_command "ls -R output/ansible/"
    echo ""
fi
press_enter

# ============================================================================
# Scene 6: Review Generated Code
# ============================================================================
print_header "Scene 6: Review Generated Code"
print_narration "Generated code includes links to Architecture Patterns for BLOCKED components"
wait_short

print_narration "KubeVirt VirtualMachine manifest:"
run_command "cat output/kubevirt/vm.yaml | head -30"
press_enter

print_narration "Ansible playbook structure:"
run_command "cat output/ansible/site.yml"
press_enter

print_narration "Ansible tasks with architecture pattern links:"
run_command "cat output/ansible/roles/provision_vm/tasks/main.yml | head -50"
wait_short

print_narration "Notice: BLOCKED components include links to PATTERNS.md"
echo -e "${CYAN}Example: NSX Security Groups → Pattern 5.1${NC}"
echo -e "${CYAN}Example: NSX Tier Gateways → Pattern 5.2${NC}"
echo ""
press_enter

# ============================================================================
# Wrap-up
# ============================================================================
print_header "Demo Complete!"
echo ""
echo -e "${BOLD}${CYAN}Complete Workflow Demonstrated:${NC}"
echo -e "${BOLD}${GREEN}✓ 1. Initialize${NC} workspace with organized structure"
echo -e "${BOLD}${GREEN}✓ 2. Import${NC} PowerCLI scripts + vRealize workflows"
echo -e "${BOLD}${GREEN}✓ 3. Analyze${NC} for gaps (SUPPORTED/PARTIAL/BLOCKED classification)"
echo -e "${BOLD}${GREEN}✓ 4. HTML reports${NC} for stakeholders and decision makers"
echo -e "${BOLD}${GREEN}✓ 5. Extract and merge${NC} operational intent using AI"
echo -e "${BOLD}${GREEN}✓ 6. Generate${NC} KubeVirt + Ansible artifacts with linting"
echo -e "${BOLD}${GREEN}✓ 7. Review${NC} generated code with architecture pattern links"
echo ""
echo -e "${CYAN}${BOLD}Key Takeaways:${NC}"
echo -e "  • ${GREEN}${BOLD}70-80% of VM provisioning auto-translates${NC} (compute, storage, networking)"
echo -e "  • ${YELLOW}${BOLD}Gap analysis shows what needs manual work UPFRONT${NC}"
echo -e "  • ${BOLD}Architecture Patterns${NC} provide guidance for NSX, approvals, custom integrations"
echo -e "  • ${BOLD}HTML reports${NC} for execs, architects, and stakeholders"
echo -e "  • ${BOLD}Linting${NC} ensures code quality for generated artifacts"
echo -e "  • ${BOLD}Pattern-based analysis${NC} runs offline without AI/LLM"
echo ""
echo -e "${BOLD}${CYAN}What was analyzed:${NC}"
echo -e "  ${BOLD}PowerCLI Scripts:${NC}"
echo -e "    • simple-vm.ps1 - Basic VM provisioning ${GREEN}(SUPPORTED)${NC}"
echo -e "    • environment-aware.ps1 - Dev/prod branching and tagging ${GREEN}(SUPPORTED)${NC}"
echo -e "  ${BOLD}vRealize Workflows:${NC}"
echo -e "    • provision-vm-with-nsx-firewall.workflow.xml ${RED}(NSX components BLOCKED)${NC}"
echo -e "    • provision-web-app-with-nsx-lb.workflow.xml ${RED}(NSX load balancer BLOCKED)${NC}"
echo -e "  ${BOLD}Results:${NC}"
echo -e "    → ${GREEN}Basic VM provisioning, compute, storage = auto-translates${NC}"
echo -e "    → ${RED}NSX Security Groups and Load Balancers = need Architecture Patterns${NC}"
echo -e "    → Gap analysis works for BOTH PowerCLI and vRealize sources"
echo ""
echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${MAGENTA}  You don't start with rewriting automation.${NC}"
echo -e "${BOLD}${MAGENTA}  You start with understanding it.${NC}"
echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${MAGENTA}GitHub:${NC} github.com/tsanders-rh/ops-translate"
echo -e "${MAGENTA}License:${NC} Apache-2.0"
echo ""

if [ "$NO_CLEANUP" = true ]; then
    echo -e "${YELLOW}Demo workspace left intact for exploration:${NC}"
    echo "  - demo-workspace/"
    echo ""
fi
