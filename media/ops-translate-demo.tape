# ops-translate — 5-Minute Demo (Terminal)
# Location: media/ops-translate-demo.tape
# Run from repo root: vhs media/ops-translate-demo.tape
#
# Assumptions:
# - You run this from the ops-translate repository root
# - `ops-translate` is on PATH (or run `pip install -e .` first)
# - Optional: `oc` logged into your CRC cluster if you want the dry-run step to succeed.

Output media/ops-translate-demo.mp4
Set Width 1280
Set Height 720
Set FontSize 18
Set Theme "Dracula"
Set TypingSpeed 75ms

# --- Title card (simple, terminal-only) ---
Type "echo ''"
Enter
Type "echo 'ops-translate — 5-Minute Demo'"
Enter
Type "echo 'VMware automation → OpenShift Virtualization (trust-first)'"
Enter
Type "echo ''"
Enter
Sleep 1200ms

# --- Clean start ---
Type "rm -rf demo output || true"
Enter
Sleep 500ms

# 1) Init + import
Type "ops-translate init demo"
Enter
Sleep 1200ms

Type "cd demo"
Enter
Sleep 500ms

Type "ops-translate import --source powercli --file ../examples/powercli/provision-vm.ps1"
Enter
Sleep 1400ms

Type "ops-translate import --source vrealize --file ../examples/vrealize/with-approval.workflow.xml"
Enter
Sleep 1600ms

# 2) Deterministic summary (no AI)
Type "ops-translate summarize"
Enter
Sleep 1400ms

Type "cat intent/summary.md"
Enter
Sleep 2400ms

# 3) Intent extraction (AI used once)
Type "ops-translate intent extract"
Enter
Sleep 1800ms

Type "cat intent/vrealize.intent.yaml"
Enter
Sleep 2400ms

Type "cat intent/assumptions.md"
Enter
Sleep 2400ms

# 4) Gap analysis & classification
Type "ops-translate analyze"
Enter
Sleep 1800ms

Type "cat intent/gaps.md"
Enter
Sleep 3200ms

# 5) Human decision point (CLI)
# NOTE: This assumes `ops-translate interview` is interactive.
# We answer a few representative questions using Type+Enter.
Type "ops-translate interview"
Enter
Sleep 1200ms

# --- Interview answers (edit these prompts/answers to match your actual interview flow) ---
# Approval handling
Type "manual"
Enter
Sleep 700ms

# REST/API purpose
Type "integration"
Enter
Sleep 700ms

# Network model / NSX equivalence tolerance
Type "map-to-ovn-kubernetes"
Enter
Sleep 700ms

# Ownership / approver group
Type "platform-team"
Enter
Sleep 700ms

Sleep 600ms

# 6) Generate OpenShift artifacts (deterministic templates)
Type "ops-translate generate --profile lab"
Enter
Sleep 2000ms

Type "ls -la output/kubevirt"
Enter
Sleep 1600ms

Type "ls -la output/ansible"
Enter
Sleep 1600ms

Type "grep -R 'REVIEW REQUIRED' -n output/ansible || true"
Enter
Sleep 1800ms

# 7) Show apply (dry-run first)
# If oc isn't logged in / CRC isn't running, this may fail. We keep it non-fatal with `|| true`.
Type "oc apply -f output/kubevirt/ --dry-run=server || true"
Enter
Sleep 2000ms

Type "oc apply -f output/kubevirt/ || true"
Enter
Sleep 1800ms

# --- Close card ---
Type "echo ''"
Enter
Type "echo 'Done.'"
Enter
Type "echo ''"
Enter
Type "echo 'One-sentence close:'"
Enter
Type "echo 'We do not rebuild VMware automation—we translate its intent into OpenShift-native operations, safely and transparently.'"
Enter
Type "echo ''"
Enter
Sleep 2200ms
