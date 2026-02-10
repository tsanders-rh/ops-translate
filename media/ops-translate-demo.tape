# ops-translate — Demo
# Professional VHS demo (clean shell, deterministic, no continuation prompts)
# Run from repo root: vhs media/ops-translate-demo.tape

Output media/ops-translate-demo.mp4
Set Width 1280
Set Height 720
Set FontSize 18
Set Theme "Dracula"
Set TypingSpeed 50ms
Set Shell bash

# === Clean shell setup ===
Hide
Type "reset"
Enter
Sleep 600ms
Type "export PS1='$ '"
Enter
Sleep 300ms
# Clean workspace
Type "rm -rf demo-workspace || true"
Enter
Sleep 500ms
Type "clear"
Enter
Sleep 300ms
Show

# === Title card ===
Type "#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Type "#"
Enter
Type "# ops-translate Demo"
Enter
Type "#"
Enter
Type "# Bridging the gap between VMware automation and
Enter
Type "# cloud-native infrastructure."
Enter
Type "#"
Enter
Type "# https://github.com/tsanders-rh/ops-translate"
Enter
Type "#"
Enter
Type "#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Sleep 2s
Hide
Type "clear"
Enter
Show
Sleep 500ms

# === Scene 1: Initialize & Import ===
Type "#━━━ Scene 1: Initialize & Import ━━━"
Enter 2
Sleep 900ms

Type "ops-translate init demo-workspace"
Enter 2
Sleep 1.5s

Type "cd demo-workspace"
Enter 2
Sleep 600ms

Type "ops-translate import --source powercli --file ../examples/merge-scenario/dev-provision.ps1"
Enter 2
Sleep 1.2s

Type "ops-translate import --source powercli --file ../examples/merge-scenario/prod-provision.ps1"
Enter 2
Sleep 1.2s

Type "ops-translate import --source vrealize --file ../examples/merge-scenario/approval.workflow.xml"
Enter 2
Sleep 1.6s

Type "# ✓ Imported: dev-provision, prod-provision, approval workflow"
Enter
Sleep 1.8s
Hide
Type "clear"
Enter
Show

# === Scene 2: Static Analysis (No AI) ===
Type "#━━━ Scene 2: Static Analysis (No AI) ━━━"
Enter 2
Sleep 900ms

Type "ops-translate summarize"
Enter 2
Sleep 2s

Type "# 📊 Viewing summary..."
Enter 2
Sleep 600ms

Type "cat intent/summary.md | head -40"
Enter
Sleep 3s
Hide
Type "clear"
Enter
Show

# === Scene 3: Extract Intent (AI) ===
Type "# ━━━ Scene 3: Extract Intent (AI) ━━━"
Enter 2
Sleep 900ms

Type "cat ops-translate.yaml"
Enter 2

Type "ops-translate intent extract"
Enter 2
Sleep 25s
Type "# 🧠 View one of the extracted intent files..."
Enter
Sleep 3s
Type "cat intent/dev-provision.intent.yaml | head -30"
Enter 
Sleep 10s
Type "#Three intent files created (one per source):"
Enter 2
Type "ls -1 intent/*.intent.yaml"
Enter
Sleep 10s
Hide
Type "clear"
Enter
Show

# === Scene 4: Gap Analysis ===
Type "# ━━━ Scene 4: Gap Analysis ━━━"
Enter
Sleep 900ms

Type "if [ -f intent/gaps.md ]; then cat intent/gaps.md | head -40; else echo 'No gaps detected'; fi"
Enter
Sleep 3s
Hide
Type "clear"
Enter
Show

# === Scene 5: Merge 3 Files → 1 Unified Workflow ===
Type "# ━━━ Scene 5: Merge 3 Files → 1 Unified Workflow ━━━"
Enter 2
Sleep 900ms

Type "ops-translate intent merge --force"
Enter 2
Sleep 2.2s

Type "# 🔀 View the merged intent (combines dev, prod, and approval)..."
Enter 2
Sleep 600ms

Type "cat intent/intent.yaml | head -40"
Enter
Sleep 5s
Hide
Type "clear"
Enter
Show

# === Scene 6: Dry-Run Validation ===
Type "# ━━━ Scene 6: Dry-Run Validation ━━━"
Enter 2
Sleep 900ms

Type "ops-translate dry-run || true"
Enter
Sleep 2.6s
Type "clear"
Enter

# === Scene 7: Generate KubeVirt + Ansible ===
Type "# ━━━ Scene 7: Generate KubeVirt + Ansible ━━━"
Enter 2
Sleep 900ms

Type "ops-translate generate --profile lab --format yaml"
Enter 2
Sleep 2.2s

Type "# 📄 KubeVirt VM spec..."
Enter 2
Sleep 600ms

Type "cat output/kubevirt/vm.yaml | head -30"
Enter 2
Sleep 3s

Type "# 📄 Ansible playbook..."
Enter 2
Sleep 600ms

Type "cat output/ansible/site.yml | head -20"
Enter
Sleep 3s
Hide
Type "clear"
Enter
Show

# === Wrap-up ===
Type "# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Type "#  Outcome:"
Enter
Type "#  • dev-provision.ps1 → Fast lab provisioning"
Enter
Type "#  • prod-provision.ps1 → Governed prod provisioning"
Enter
Type "#  • approval.workflow.xml → vRealize approval routing"
Enter 2
Type "#   Single workflow handling both environments"
Enter
Type "# GitHub: github.com/tsanders-rh/ops-translate"
Enter
Type "# License: Apache-2.0"
Enter
Type "# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Enter
Sleep 3s
