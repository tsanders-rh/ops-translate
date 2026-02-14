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
echo -e "  ${BOLD}1.${NC} Gap analysis - what needs manual work"
echo -e "  ${BOLD}2.${NC} Architecture guidance - how to handle NSX, approvals, etc."
echo -e "  ${BOLD}3.${NC} Generated code - Ansible + KubeVirt to get started"
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

print_narration "Import vRealize workflows with NSX networking components"
wait_short
run_command "$OPS_CMD import --source vrealize --file ../examples/virt-first-realworld/vrealize/provision-vm-with-nsx-firewall.workflow.xml"
wait_short

print_narration "Import vRealize workflow for web app with NSX load balancer"
wait_short
run_command "$OPS_CMD import --source vrealize --file ../examples/virt-first-realworld/vrealize/provision-web-app-with-nsx-lb.workflow.xml"
wait_short

print_narration "Import PowerCLI script for standard VM provisioning"
wait_short
run_command "$OPS_CMD import --source powercli --file ../examples/virt-first-realworld/powercli/New-StandardVM.ps1"
wait_short

print_narration "Import PowerCLI script for web tier provisioning"
wait_short
run_command "$OPS_CMD import --source powercli --file ../examples/virt-first-realworld/powercli/Provision-WebTier.ps1"
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


print_narration "This is pattern matching - no AI needed, runs offline."
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
echo -e "${YELLOW}For this terminal demo, here's what the report contains:${NC}"
echo ""
echo -e "  ${BOLD}Migration Effort Dashboard${NC} - Visual breakdown of migration complexity"
echo -e "  ${BOLD}Executive Summary${NC} - High-level metrics for decision makers"
echo -e "  ${BOLD}Component Analysis${NC} - Detailed breakdown with recommendations"
echo -e "  ${BOLD}Architecture Patterns${NC} - How to handle NSX, approvals, ServiceNow, etc."
echo ""
press_enter

# ============================================================================
# Scene 5: Extract Operational Intent
# ============================================================================
print_header "Scene 5: Extract Operational Intent"
print_narration "Extract normalized intent using AI (or mock provider for demo)"
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

print_narration "View one of the extracted intent files:"
wait_short
run_command "cat intent/provision-vm-with-nsx-firewall.intent.yaml | head -40"
wait_short

print_narration "Intent files normalize automation across different source formats."
echo -e "${CYAN}vRealize workflows → normalized YAML intent${NC}"
echo -e "${CYAN}PowerCLI scripts → same normalized YAML intent${NC}"
echo ""
wait_short

print_narration "Now merge individual intent files into unified intent:"
wait_short
run_command "$OPS_CMD intent merge"
wait_medium

print_narration "Merged intent file created at intent/intent.yaml"
echo -e "${CYAN}This unified intent is used for artifact generation${NC}"
echo ""
press_enter

# ============================================================================
# Scene 6: Generate with Linting
# ============================================================================
print_header "Scene 6: Generate Artifacts with Linting"
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
# Scene 7: Review Generated Code
# ============================================================================
print_header "Scene 7: Review Generated Code"
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
echo -e "${BOLD}${GREEN}✓ 2. Import${NC} vRealize workflows + PowerCLI scripts with NSX components"
echo -e "${BOLD}${GREEN}✓ 3. Analyze${NC} for gaps (SUPPORTED/PARTIAL/BLOCKED classification)"
echo -e "${BOLD}${GREEN}✓ 4. HTML reports${NC} for stakeholders and decision makers"
echo -e "${BOLD}${GREEN}✓ 5. Extract and merge${NC} operational intent using AI"
echo -e "${BOLD}${GREEN}✓ 6. Generate${NC} KubeVirt + Ansible artifacts with linting"
echo -e "${BOLD}${GREEN}✓ 7. Review${NC} generated code with architecture pattern links"
echo ""
echo -e "${CYAN}${BOLD}Key Takeaways:${NC}"
echo -e "  • ${BOLD}This is a PLANNING tool${NC} - not an automated migration button"
echo -e "  • ${BOLD}Gap analysis shows what needs manual work UPFRONT${NC}"
echo -e "  • ${BOLD}HTML reports${NC} are for execs, architects, and stakeholders"
echo -e "  • ${BOLD}Architecture Patterns${NC} = your migration playbook"
echo -e "  • ${BOLD}Linting${NC} = code quality built-in"
echo -e "  • ${BOLD}Multi-source support${NC} = handles vRealize and PowerCLI together"
echo ""
echo -e "${BOLD}${CYAN}What was analyzed:${NC}"
echo -e "  ${BOLD}vRealize Workflows:${NC}"
echo -e "    • provision-vm-with-nsx-firewall.workflow.xml - VM with NSX Security Groups"
echo -e "    • provision-web-app-with-nsx-lb.workflow.xml - Web app with NSX Load Balancer"
echo -e "  ${BOLD}PowerCLI Scripts:${NC}"
echo -e "    • New-StandardVM.ps1 - Standard VM provisioning (conflicts with vRealize)"
echo -e "    • Provision-WebTier.ps1 - Web tier with manual NSX steps"
echo -e "  ${BOLD}Results:${NC}"
echo -e "    → Gap analysis identified BLOCKED NSX components"
echo -e "    → Detected conflicts between vRealize and PowerCLI approaches"
echo -e "    → Architecture Patterns provide migration guidance"
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
