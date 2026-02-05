# ops-translate Demo Script

> **Duration**: ~5-7 minutes
> **Goal**: Showcase the complete migration workflow from PowerCLI to OpenShift Virtualization

## Demo Overview

This demo shows how ops-translate extracts operational intent from VMware automation and generates production-ready Kubernetes and Ansible artifacts in multiple formats.

**What we'll demonstrate:**
1. Import a PowerCLI script
2. Extract operational intent (with AI)
3. Validate with enhanced dry-run
4. Generate artifacts in multiple formats (YAML, GitOps, ArgoCD)
5. Customize templates for organizational standards

---

## Setup (Before Recording)

```bash
# Clean slate
rm -rf demo-workspace 2>/dev/null

# Set up LLM provider (use mock for demo to avoid costs)
export OPS_TRANSLATE_LLM_API_KEY="demo-key"
```

---

## Scene 1: Introduction (30 seconds)

**Narration:**
> "ops-translate is an AI-assisted CLI tool that migrates VMware automation to OpenShift Virtualization. Instead of manually rewriting PowerCLI scripts and vRealize workflows, ops-translate extracts operational intent and generates production-ready artifacts. Let's see it in action."

---

## Scene 2: Initialize & Import (45 seconds)

**Narration:**
> "First, we'll initialize a workspace and import an existing PowerCLI script that provisions VMs with environment-based configuration."

**Commands:**
```bash
# Initialize workspace
ops-translate init demo-workspace
cd demo-workspace

# Show what was created
tree -L 2

# Import a PowerCLI script with environment branching
ops-translate import --source powercli \
  --file ../examples/powercli/environment-aware.ps1
```

**Show:** Directory structure and successful import message with SHA256 hash.

---

## Scene 3: Summarize (No AI) (30 seconds)

**Narration:**
> "Before using AI, let's see what ops-translate can detect without any LLM calls using static analysis."

**Commands:**
```bash
# Analyze the script structure
ops-translate summarize

# Show what was detected
cat intent/summary.md
```

**Show:** Summary detecting parameters, environment branching (dev/prod), tags, network/storage profiles.

---

## Scene 4: Extract Intent (45 seconds)

**Narration:**
> "Now let's extract the normalized operational intent. This creates a platform-agnostic specification of what the automation does."

**Commands:**
```bash
# Extract operational intent using AI
ops-translate intent extract

# Show the extracted intent
cat intent/powercli.intent.yaml
```

**Show:** The intent YAML with:
- Workflow name
- Input definitions with types
- Environment branching logic
- Network/storage profile selection
- Metadata tags

---

## Scene 5: Enhanced Dry-Run Validation (60 seconds)

**Narration:**
> "One of our newest features is enhanced dry-run validation. This performs comprehensive pre-flight checks before generating artifacts."

**Commands:**
```bash
# Run enhanced validation
ops-translate dry-run
```

**Show:** The validation output:
- ✓ Schema validation passed
- ✓ Resource consistency checks
- Execution plan (7 steps)
- Review items
- Status: SAFE TO PROCEED

**Narration:**
> "Notice it validates schema, checks resource consistency, and even generates an execution plan showing exactly what will happen. Issues are categorized as BLOCKING, REVIEW, or SAFE."

---

## Scene 6: Generate Multiple Formats (90 seconds)

**Narration:**
> "ops-translate can generate artifacts in multiple formats for different deployment strategies. Let's start with standard YAML."

### YAML Format
**Commands:**
```bash
# Generate standard YAML
ops-translate generate --profile lab --format yaml

# Show what was created
tree output/
cat output/kubevirt/vm.yaml
```

**Show:** KubeVirt VirtualMachine manifest and Ansible playbook structure.

### Kustomize/GitOps Format
**Narration:**
> "For GitOps workflows, we can generate a complete Kustomize structure with environment-specific overlays."

**Commands:**
```bash
# Generate Kustomize structure
ops-translate generate --profile lab --format kustomize

# Show the GitOps structure
tree output/
cat output/base/kustomization.yaml
cat output/overlays/dev/kustomization.yaml
cat output/overlays/prod/kustomization.yaml
```

**Show:** Base + overlays structure. Highlight how prod overlay has 8Gi memory while dev has 2Gi.

**Narration:**
> "Notice how each environment overlay automatically adjusts resources: dev gets 2Gi and 1 CPU, staging gets 4Gi and 2 CPUs, prod gets 8Gi and 4 CPUs. You can deploy with kubectl apply -k output/overlays/prod"

### ArgoCD Format
**Narration:**
> "For full GitOps automation with ArgoCD, we can generate Application manifests with environment-specific sync policies."

**Commands:**
```bash
# Generate ArgoCD Applications
ops-translate generate --profile lab --format argocd

# Show ArgoCD structure
tree output/argocd/
cat output/argocd/dev-application.yaml
cat output/argocd/prod-application.yaml
```

**Show:**
- dev-application.yaml with automated sync, prune, and self-heal
- prod-application.yaml with manual sync for safety

**Narration:**
> "Dev environment has automated sync with self-heal enabled, while production requires manual approval. This follows GitOps best practices."

---

## Scene 7: Template Customization (60 seconds)

**Narration:**
> "Organizations often need to customize generated artifacts to match their standards. Let's see how template customization works."

**Commands:**
```bash
# Start fresh with custom templates
cd ..
rm -rf custom-workspace

# Initialize with templates
ops-translate init custom-workspace --with-templates
cd custom-workspace

# Show the template structure
tree templates/

# Edit a template (show opening in editor)
cat templates/kubevirt/vm.yaml.j2
```

**Show:** The Jinja2 template with:
- Template variables: `{{ intent.workflow_name }}`
- Conditional logic: `{% if intent.metadata %}`
- Organizational customization points

**Narration:**
> "The --with-templates flag copies all default templates into your workspace. You can edit these Jinja2 templates to add organization-specific labels, annotations, resource limits, or custom Ansible tasks. When you run generate, your custom templates are used automatically."

---

## Scene 8: Wrap-up (30 seconds)

**Narration:**
> "In just a few minutes, we've taken a PowerCLI script and generated production-ready Kubernetes manifests, Ansible playbooks, Kustomize overlays, and ArgoCD Applications. ops-translate handles the translation work so you can focus on validating the migration strategy."

**Commands:**
```bash
# Show all generated formats side-by-side
ls -R output/
```

**Show:** Complete output directory structure.

**Narration:**
> "ops-translate is open source under Apache 2.0 license. Check out the GitHub repo for examples, documentation, and to try it yourself. Thanks for watching!"

**On-screen text:**
```
GitHub: github.com/tsanders-rh/ops-translate
Documentation: README.md
Examples: examples/
License: Apache-2.0
```

---

## Technical Setup Notes

### Recording Settings
- **Resolution**: 1920x1080 or 1280x720
- **Terminal**: Use a clean theme (e.g., Solarized Dark, Dracula)
- **Font size**: 14-16pt for readability
- **Terminal width**: 100-120 columns
- **Speed**: Use `asciinema` or similar to record and speed up where needed

### Pre-recording Checklist
- [ ] Clean terminal history (`history -c`)
- [ ] Set up aliases for commonly used commands
- [ ] Have example files ready
- [ ] Test all commands work end-to-end
- [ ] Mock LLM configured to avoid API costs
- [ ] Tree command installed (`brew install tree` / `apt-get install tree`)

### Editing Notes
- Add text overlays for key concepts
- Highlight important output (arrows/boxes)
- Speed up long command outputs (2x)
- Add music/intro/outro
- Include GitHub link at the end

### Alternative: Automated Demo Script
Use the provided `demo.sh` script to automate the demo:

```bash
./demo.sh --speed normal    # Run at normal speed
./demo.sh --speed fast      # Speed up delays
./demo.sh --record          # Record with asciinema
```

---

## Key Messages to Emphasize

1. **Safe by Design**: All operations are read-only, no live system access
2. **Transparent**: Every assumption logged, full visibility
3. **Flexible**: Multiple output formats for different workflows
4. **Customizable**: Template system for organizational standards
5. **Validated**: Enhanced dry-run catches issues before deployment
6. **Production-Ready**: Generates artifacts following best practices

---

## Common Demo Pitfalls to Avoid

- ❌ Don't show errors or retries
- ❌ Don't read long YAML files line-by-line
- ❌ Don't explain every single option
- ❌ Don't go too fast through important parts
- ✅ DO highlight the unique features (dry-run, multiple formats, templates)
- ✅ DO show real, working output
- ✅ DO emphasize the time savings
