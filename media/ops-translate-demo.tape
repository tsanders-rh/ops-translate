# ops-translate — Multi-Source Merge Demo (Terminal)
# Location: media/ops-translate-demo.tape
# Run from repo root: vhs media/ops-translate-demo.tape
#
# Assumptions:
# - You run this from the ops-translate repository root
# - `ops-translate` is on PATH (or run `pip install -e .` first)
# - Mock LLM provider configured (no API key needed)

Output media/ops-translate-demo.mp4
Set Width 1280
Set Height 720
Set FontSize 18
Set Theme "Dracula"
Set TypingSpeed 50ms

# --- Title card ---
Type "echo ''"
Enter
Type "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'"
Enter
Type "echo '  ops-translate — Multi-Source Merge Demo'"
Enter
Type "echo '  VMware automation → OpenShift Virtualization'"
Enter
Type "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'"
Enter
Type "echo ''"
Enter
Sleep 2s

# --- Clean start ---
Type "# Clean slate"
Enter
Type "rm -rf demo-workspace || true"
Enter
Sleep 500ms
Type "clear"
Enter

# --- Scene 1: Initialize & Import ---
Type "echo '━━━ Scene 1: Initialize & Import ━━━'"
Enter
Sleep 1s

Type "ops-translate init demo-workspace"
Enter
Sleep 1.5s

Type "cd demo-workspace"
Enter
Sleep 500ms

Type "echo ''"
Enter
Type "echo '📦 Importing 3 sources...'"
Enter
Sleep 1s

Type "ops-translate import --source powercli --file ../examples/merge-scenario/dev-provision.ps1"
Enter
Sleep 1.2s

Type "ops-translate import --source powercli --file ../examples/merge-scenario/prod-provision.ps1"
Enter
Sleep 1.2s

Type "ops-translate import --source vrealize --file ../examples/merge-scenario/approval.workflow.xml"
Enter
Sleep 1.5s

Type "echo ''"
Enter
Type "echo '✓ Imported: dev-provision, prod-provision, approval workflow'"
Enter
Sleep 2s
Type "clear"
Enter

# --- Scene 2: Summarize (No AI) ---
Type "echo '━━━ Scene 2: Static Analysis (No AI) ━━━'"
Enter
Sleep 1s

Type "ops-translate summarize"
Enter
Sleep 2s

Type "echo ''"
Enter
Type "echo '📊 Viewing summary...'"
Enter
Sleep 1s
Type "cat intent/summary.md | head -40"
Enter
Sleep 3s
Type "clear"
Enter

# --- Scene 3: Extract Intent (AI) ---
Type "echo '━━━ Scene 3: Extract Intent (AI) ━━━'"
Enter
Sleep 1s

Type "# Configure mock provider (no API key needed)"
Enter
Type "cat > ops-translate.yaml << 'EOF'"
Enter
Type "llm:"
Enter
Type "  provider: mock"
Enter
Type "  model: mock-model"
Enter
Type ""
Enter
Type "profiles:"
Enter
Type "  lab:"
Enter
Type "    default_namespace: virt-lab"
Enter
Type "    default_network: lab-network"
Enter
Type "    default_storage_class: nfs"
Enter
Type "EOF"
Enter
Sleep 1s

Type "ops-translate intent extract"
Enter
Sleep 2.5s

Type "echo ''"
Enter
Type "echo '📄 Created 3 intent files...'"
Enter
Sleep 1s
Type "ls -1 intent/*.intent.yaml"
Enter
Sleep 2s

Type "echo ''"
Enter
Type "echo '📖 Viewing one intent file...'"
Enter
Sleep 1s
Type "cat intent/dev-provision.intent.yaml | head -30"
Enter
Sleep 3s
Type "clear"
Enter

# --- Scene 4: Gap Analysis ---
Type "echo '━━━ Scene 4: Gap Analysis ━━━'"
Enter
Sleep 1s

Type "# Check for gap analysis"
Enter
Type "if [ -f intent/gaps.md ]; then cat intent/gaps.md | head -40; else echo 'No gaps detected'; fi"
Enter
Sleep 3s
Type "clear"
Enter

# --- Scene 5: Merge Intent ---
Type "echo '━━━ Scene 5: Merge 3 Files → 1 Unified Workflow ━━━'"
Enter
Sleep 1s

Type "ops-translate intent merge --force"
Enter
Sleep 1.5s

Type "echo ''"
Enter
Type "echo '🔀 Merged intent (combines dev + prod + approval)...'"
Enter
Sleep 1s
Type "cat intent/intent.yaml | head -40"
Enter
Sleep 3.5s

Type "echo ''"
Enter
Type "echo '✓ Notice: unified inputs, governance rules, environment profiles'"
Enter
Sleep 2s
Type "clear"
Enter

# --- Scene 6: Dry-Run Validation ---
Type "echo '━━━ Scene 6: Dry-Run Validation ━━━'"
Enter
Sleep 1s

Type "ops-translate dry-run || true"
Enter
Sleep 2.5s
Type "clear"
Enter

# --- Scene 7: Generate Artifacts ---
Type "echo '━━━ Scene 7: Generate KubeVirt + Ansible ━━━'"
Enter
Sleep 1s

Type "ops-translate generate --profile lab --format yaml"
Enter
Sleep 2.5s

Type "echo ''"
Enter
Type "echo '📁 Generated structure...'"
Enter
Sleep 1s
Type "tree output/ || ls -R output/"
Enter
Sleep 2.5s

Type "echo ''"
Enter
Type "echo '📄 KubeVirt manifest...'"
Enter
Sleep 1s
Type "cat output/kubevirt/vm.yaml | head -30"
Enter
Sleep 3s

Type "echo ''"
Enter
Type "echo '📄 Ansible playbook...'"
Enter
Sleep 1s
Type "cat output/ansible/site.yml | head -20"
Enter
Sleep 3s
Type "clear"
Enter

# --- Wrap-up ---
Type "echo ''"
Enter
Type "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'"
Enter
Type "echo '  ✓ Demo Complete!'"
Enter
Type "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'"
Enter
Type "echo ''"
Enter
Type "echo 'Merged 3 sources into 1 unified workflow:'"
Enter
Type "echo '  • dev-provision.ps1 → Quick dev provisioning'"
Enter
Type "echo '  • prod-provision.ps1 → Governed prod provisioning'"
Enter
Type "echo '  • approval.workflow.xml → vRealize approval routing'"
Enter
Type "echo '  ↓'"
Enter
Type "echo '  Single workflow handling both environments'"
Enter
Type "echo ''"
Enter
Type "echo 'GitHub: github.com/tsanders-rh/ops-translate'"
Enter
Type "echo 'License: Apache-2.0'"
Enter
Type "echo ''"
Enter
Sleep 3s
