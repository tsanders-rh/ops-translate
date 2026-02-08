# ops-translate — Multi-Source Merge Demo
# Professional VHS demo
# Run from repo root: vhs media/ops-translate-demo.tape

Output media/ops-translate-demo.mp4
Set Width 1280
Set Height 720
Set FontSize 18
Set Theme "Dracula"
Set TypingSpeed 50ms

# === Title card (using cat heredoc - clean output) ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Type "  ops-translate — Multi-Source Merge Demo"
Enter
Type "  VMware automation → OpenShift Virtualization"
Enter
Type "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 3s

# Clean workspace
Hide
Type "rm -rf demo-workspace 2>/dev/null || true && clear"
Enter
Show

# === Scene 1: Initialize & Import ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━ Scene 1: Initialize & Import ━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 1s

Type "ops-translate init demo-workspace"
Enter
Sleep 1.5s

Type "cd demo-workspace"
Enter
Sleep 500ms

Type "ops-translate import --source powercli --file ../examples/merge-scenario/dev-provision.ps1"
Enter
Sleep 1s

Type "ops-translate import --source powercli --file ../examples/merge-scenario/prod-provision.ps1"
Enter
Sleep 1s

Type "ops-translate import --source vrealize --file ../examples/merge-scenario/approval.workflow.xml"
Enter
Sleep 2s

Hide
Type "clear"
Enter
Show

# === Scene 2: Static Analysis (No AI) ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━ Scene 2: Static Analysis (No AI) ━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 1s

Type "ops-translate summarize"
Enter
Sleep 2s

Type "cat intent/summary.md | head -40"
Enter
Sleep 3s

Hide
Type "clear"
Enter
Show

# === Scene 3: Extract Intent (AI) ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━ Scene 3: Extract Intent (AI) ━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
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

Type "ls -1 intent/*.intent.yaml"
Enter
Sleep 1.5s

Type "cat intent/dev-provision.intent.yaml | head -30"
Enter
Sleep 3s

Hide
Type "clear"
Enter
Show

# === Scene 4: Gap Analysis ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━ Scene 4: Gap Analysis ━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 1s

Type "if [ -f intent/gaps.md ]; then cat intent/gaps.md | head -40; else echo 'No gaps detected'; fi"
Enter
Sleep 3s

Hide
Type "clear"
Enter
Show

# === Scene 5: Merge 3 Files → 1 Unified Workflow ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━ Scene 5: Merge 3 Files → 1 Unified Workflow ━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 1s

Type "ops-translate intent merge --force"
Enter
Sleep 1.5s

Type "cat intent/intent.yaml | head -40"
Enter
Sleep 3.5s

Hide
Type "clear"
Enter
Show

# === Scene 6: Dry-Run Validation ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━ Scene 6: Dry-Run Validation ━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 1s

Type "ops-translate dry-run || true"
Enter
Sleep 2.5s

Hide
Type "clear"
Enter
Show

# === Scene 7: Generate KubeVirt + Ansible ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━ Scene 7: Generate KubeVirt + Ansible ━━━"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 1s

Type "ops-translate generate --profile lab --format yaml"
Enter
Sleep 2.5s

Type "tree output/ || ls -R output/"
Enter
Sleep 2s

Type "cat output/kubevirt/vm.yaml | head -30"
Enter
Sleep 2.5s

Type "cat output/ansible/site.yml | head -20"
Enter
Sleep 3s

Hide
Type "clear"
Enter
Show

# === Wrap-up ===
Hide
Type "cat << 'EOF'"
Enter
Type ""
Enter
Type "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Type "  ✓ Demo Complete!"
Enter
Type "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Type ""
Enter
Type "Merged 3 sources into 1 unified workflow:"
Enter
Type "  • dev-provision.ps1 → Quick dev provisioning"
Enter
Type "  • prod-provision.ps1 → Governed prod provisioning"
Enter
Type "  • approval.workflow.xml → vRealize approval routing"
Enter
Type "  ↓"
Enter
Type "  Single workflow handling both environments"
Enter
Type ""
Enter
Type "GitHub: github.com/tsanders-rh/ops-translate"
Enter
Type "License: Apache-2.0"
Enter
Type ""
Enter
Type "EOF"
Enter
Show
Sleep 3s
