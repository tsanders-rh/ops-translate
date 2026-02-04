# ops-translate (Working Title)
AI-assisted operational translation CLI for VMware automation → Ansible + OpenShift Virtualization artifacts.

## 1) Objective (v1)
Build a CLI-first prototype that demonstrates:
- Importing **PowerCLI** scripts and **vRealize Orchestrator workflow exports** (representative XML)
- Extracting a **normalized Operational Intent Model** from each source
- Merging into a single `intent/intent.yaml` (with conflict reporting)
- Generating inspectable output artifacts:
  - Ansible role + playbook skeleton
  - KubeVirt VM manifest YAML
- Safety & trust: **no execution by default**, and all intermediate artifacts saved to disk.

Non-goals v1:
- No live VMware/vCenter access
- No NSX or advanced network policy conversion
- No full Ansible Controller/AAP workflow import (optional stub only)
- No production-grade correctness guarantees

## 2) Target User / POC Narrative
Target: ops/infra engineers and architects evaluating migration from VMware to OpenShift Virtualization.

Demo narrative:
1) Import a PowerCLI file + a vRO workflow XML
2) Run `summarize` (no AI): show detected features
3) Run `intent extract`: produces `intent/powercli.intent.yaml`, `intent/vrealize.intent.yaml`
4) Run `intent merge`: produces `intent/intent.yaml` + `intent/conflicts.md`
5) Run `generate`: outputs `output/ansible/...` and `output/kubevirt/vm.yaml`
6) Show: "two sources → one intent → one output set"

## 3) CLI Commands (Required)
CLI name: `ops-translate`

### 3.1 Workspace
- `ops-translate init <workspace_dir>`
  - Creates directories:
    - `input/powercli/`
    - `input/vrealize/`
    - `intent/`
    - `mapping/`
    - `output/ansible/`
    - `output/kubevirt/`
    - `runs/`
  - Writes `ops-translate.yaml` config (see below)

### 3.2 Import
- `ops-translate import --source <powercli|vrealize> --file <path>`
  - Copies file into correct `input/*` folder
  - Computes sha256 and writes metadata in `runs/<timestamp>/import.json`

### 3.3 Summarize (No AI)
- `ops-translate summarize`
  - Parses inputs and prints a summary:
    - Detected input parameters (names + types if possible)
    - Presence of approval semantics (if detectable)
    - Presence of env branching (dev/prod)
    - Presence of tagging/metadata operations
    - Presence of network/storage profile selection
  - Writes `intent/summary.md`

### 3.4 Intent Extraction (AI-backed)
- `ops-translate intent extract`
  - For each imported source file:
    - Reads file
    - Calls LLM with a prompt to produce normalized intent YAML
  - Outputs:
    - `intent/powercli.intent.yaml`
    - `intent/vrealize.intent.yaml`
    - `intent/assumptions.md` (combined)

### 3.5 Intent Edit
- `ops-translate intent edit [--file <intent file>]`
  - Opens `$EDITOR` (fallback: prints path with instruction)
  - Does not modify automatically

### 3.6 Intent Merge
- `ops-translate intent merge`
  - Loads per-source intents
  - Merges into `intent/intent.yaml`
  - If conflicts: write `intent/conflicts.md` and exit non-zero unless `--force`
  - Conflicts include:
    - Approval required in one source but not the other
    - Different network/storage mapping defaults
    - Different tag keys
    - Input schema mismatch

### 3.7 Mapping Preview (No AI required)
- `ops-translate map preview --target openshift`
  - Generates `mapping/preview.md` showing:
    - vRealize concepts → Ansible/OpenShift equivalents
    - PowerCLI constructs → Ansible equivalents

### 3.8 Generate Artifacts (AI-backed or templated)
- `ops-translate generate --profile <lab|prod> [--no-ai]`
  - Reads final `intent/intent.yaml`
  - Produces:
    - `output/kubevirt/vm.yaml` (KubeVirt VirtualMachine object)
    - `output/ansible/site.yml` (playbook)
    - `output/ansible/roles/provision_vm/tasks/main.yml`
    - `output/ansible/roles/provision_vm/defaults/main.yml`
    - `output/README.md` describing how to run artifacts
  - `--no-ai` uses deterministic Jinja templates only (minimal, but runnable)

### 3.9 Dry Run (Optional v1 but recommended)
- `ops-translate dry-run`
  - Validates:
    - intent schema is valid
    - generated YAML parses
  - Prints step plan and "SAFE/REVIEW/BLOCKING"
  - No API calls

## 4) Configuration
File: `ops-translate.yaml`

Fields:
- `llm.provider`: one of `openai|anthropic|mock`
- `llm.model`: string
- `llm.api_key_env`: env var name (default `OPS_TRANSLATE_LLM_API_KEY`)
- `profiles.lab`:
  - `default_namespace`
  - `default_network`
  - `default_storage_class`
- `profiles.prod`: same fields

## 5) Operational Intent Schema (v1)
Store in `schema/intent.schema.json` and validate with `jsonschema`.

Minimal YAML structure:

```yaml
schema_version: 1
sources:
  - type: powercli
    file: input/powercli/provision-vm.ps1
  - type: vrealize
    file: input/vrealize/provision.workflow.xml

intent:
  workflow_name: provision_vm_with_governance
  workload_type: virtual_machine

  inputs:
    vm_name: { type: string, required: true }
    environment: { type: enum, values: [dev, prod], required: true }
    cpu: { type: integer, required: true, min: 1, max: 32 }
    memory_gb: { type: integer, required: true, min: 1, max: 256 }
    owner_email: { type: string, required: true }
    cost_center: { type: string, required: false }

  governance:
    approval:
      required_when:
        environment: prod

  profiles:
    network:
      when: { environment: prod }
      value: net-prod
    network_else: net-dev
    storage:
      when: { environment: prod }
      value: storage-gold
    storage_else: storage-standard

  metadata:
    tags:
      - key: env
        value_from: environment
      - key: owner
        value_from: owner_email
      - key: costCenter
        value_from: cost_center
        optional: true

  day2_operations:
    supported: [start, stop, reconfigure]
```

## 6) Parsing Rules (No AI)

### PowerCLI summarizer
- Parse `param(...)` block for params and types
- Detect environment branching:
  - look for `ValidateSet("dev","prod")` or string comparisons
- Detect tags:
  - look for `Tags=` or array like `@("env:"...)`
- Detect network/storage selection:
  - patterns like `$Network = if (...) { ... } else { ... }`

### vRealize summarizer
- Parse XML:
  - read `<displayName>`, `<inputs>`, `<outputs>`
  - find `<decision ... expression="...">`
  - find scriptable tasks and look for keywords: `approval`, `tag`, `network`, `storage`
- We do not need to support full vRO schema; just enough for representative exports.

## 7) LLM Prompts (Required)
Place prompts in `prompts/`.

- `prompts/intent_extract_powercli.md`
- `prompts/intent_extract_vrealize.md`
- `prompts/generate_artifacts.md`

Prompt requirements:
- Must output valid YAML only
- Must conform to intent schema
- Must include an assumptions list if anything inferred

## 8) Project Structure
```
ops-translate/
├── ops_translate/               # python package
│   ├── cli.py                   # Typer CLI entry
│   ├── workspace.py
│   ├── summarize/
│   │   ├── powercli.py
│   │   └── vrealize.py
│   ├── intent/
│   │   ├── extract.py
│   │   ├── merge.py
│   │   └── validate.py
│   ├── generate/
│   │   ├── ansible.py
│   │   └── kubevirt.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   └── mock.py
│   └── util/
│       ├── files.py
│       └── hashing.py
├── prompts/
├── templates/                   # jinja templates for --no-ai
├── schema/
├── examples/
│   ├── powercli/provision-vm.ps1
│   └── vrealize/provision.workflow.xml
├── tests/                       # minimal unit tests
├── pyproject.toml
├── README.md
└── SPEC.md
```

## 9) Acceptance Criteria (v1)
Running the following works end-to-end using included examples:

```bash
ops-translate init demo
cd demo
ops-translate import --source powercli --file ../examples/powercli/provision-vm.ps1
ops-translate import --source vrealize --file ../examples/vrealize/provision.workflow.xml
ops-translate summarize
ops-translate intent extract
ops-translate intent merge
ops-translate generate --profile lab --no-ai
```

Outputs created:
- `intent/intent.yaml`
- `output/kubevirt/vm.yaml`
- `output/ansible/site.yml`
- `output/ansible/roles/provision_vm/tasks/main.yml`

## 10) Guardrails
- Default behavior must be read-only.
- Never execute anything against VMware or OpenShift in v1.
- All outputs are local files.
- Clearly log every inference/assumption.

## 11) License
Use Apache-2.0 for the repo (unless you prefer MIT). Include LICENSE file.
