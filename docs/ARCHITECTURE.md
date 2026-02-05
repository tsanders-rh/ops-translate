# ops-translate Architecture

Technical architecture and design documentation for ops-translate.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Intent Schema](#intent-schema)
6. [LLM Integration](#llm-integration)
7. [Generation Pipeline](#generation-pipeline)
8. [Extension Points](#extension-points)

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ops-translate CLI                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐            │
│  │  Import   │───▶│  Extract  │───▶│   Merge   │            │
│  │  Module   │    │  Module   │    │  Module   │            │
│  └───────────┘    └───────────┘    └───────────┘            │
│        │                 │                  │               │
│        ▼                 ▼                  ▼               │
│  ┌───────────────────────────────────────────────────┐      │
│  │            Operational Intent Store               │      │
│  │         (YAML files in intent/ directory)         │      │
│  └───────────────────────────────────────────────────┘      │
│                          │                                  │
│                          ▼                                  │
│                  ┌───────────┐                              │
│                  │ Generate  │                              │
│                  │  Module   │                              │
│                  └───────────┘                              │
│                       │    │                                │
│              ┌────────┘    └────────┐                       │
│              ▼                      ▼                       │
│      ┌─────────────┐        ┌─────────────┐                 │
│      │   Ansible   │        │  KubeVirt   │                 │
│      │ Generator   │        │  Generator  │                 │
│      └─────────────┘        └─────────────┘                 │
│              │                       │                      │
└──────────────┼───────────────────────┼──────────────────────┘
               │                       │
               ▼                       ▼
        output/ansible/        output/kubevirt/
```

### Key Components

1. **CLI Layer** (`ops_translate/cli.py`)
   - Command-line interface using Typer
   - Workspace management
   - User interaction

2. **Import Module** (`ops_translate/workspace.py`)
   - File copying and validation
   - Metadata tracking
   - Hash computation for integrity

3. **Summarize Module** (`ops_translate/summarize/`)
   - Static analysis without AI
   - Pattern detection (PowerCLI and vRealize)
   - Markdown report generation

4. **Extract Module** (`ops_translate/intent/extract.py`)
   - LLM-powered intent extraction
   - Template-based extraction (no-AI mode)
   - Assumptions logging

5. **Merge Module** (`ops_translate/intent/merge.py`)
   - Smart merging of multiple intent sources
   - Conflict detection and reporting
   - Resolution strategies

6. **Validate Module** (`ops_translate/intent/validate.py`)
   - Intent schema validation
   - Artifact validation
   - Dry-run checks

7. **Generate Module** (`ops_translate/generate/`)
   - Ansible playbook generation
   - KubeVirt manifest generation
   - Profile-based customization

8. **LLM Module** (`ops_translate/llm/`)
   - Provider abstraction (Anthropic, OpenAI, Mock)
   - Prompt management
   - Response parsing

## Architecture Principles

### 1. Safety First

**No Destructive Operations**
- All operations are read-only on source systems
- No live VMware/vCenter access in v1
- No automatic execution of generated artifacts

**Explicit User Control**
- Every step requires explicit command
- Clear separation between analysis and generation
- Dry-run validation before deployment

**Transparent Decision Making**
- All AI assumptions logged to `intent/assumptions.md`
- All conflicts reported in `intent/conflicts.md`
- All intermediate artifacts written to disk

### 2. Modularity

**Component Independence**
- Each module has single responsibility
- Clean interfaces between components
- Swappable LLM providers

**Plugin Architecture**
- Easy to add new source types (future: Terraform, ARM templates)
- Easy to add new target platforms (future: AWS, Azure)
- Easy to add new LLM providers

### 3. Filesystem as Database

**Workspace-Centric Design**
- All state stored in filesystem
- No external database required
- Easy to version control

**Immutable Inputs**
- Imported files never modified
- Original sources preserved
- SHA-256 hashing for integrity

**Auditable Outputs**
- Every transformation saved to disk
- Complete audit trail
- Reproducible results

### 4. AI as Assistant, Not Authority

**Human in the Loop**
- AI suggestions, human decisions
- Manual editing always available
- Validation before generation

**Graceful Degradation**
- Works without AI (template mode)
- Falls back to mock provider if API unavailable
- Clear error messages

## Component Architecture

### CLI Layer

**Technology**: Typer (Python CLI framework)

**Responsibilities**:
- Parse command-line arguments
- Manage workspace context
- Orchestrate workflow steps
- Display results to user

**Key Files**:
- `ops_translate/cli.py` - All CLI commands

**Design Patterns**:
- Command pattern for each CLI command
- Dependency injection for workspace path
- Rich output formatting

### Import Module

**Purpose**: Safely copy source files into workspace.

**Flow**:
```python
def import_file(source_type: str, file_path: Path, workspace: Path):
    1. Validate source_type in ['powercli', 'vrealize']
    2. Check file exists and is readable
    3. Compute SHA-256 hash
    4. Copy to input/{source_type}/
    5. Log metadata
    6. Return status
```

**Metadata Logged**:
```json
{
  "file": "provision.ps1",
  "source_type": "powercli",
  "sha256": "abc123...",
  "imported_at": "2024-01-15T10:30:00Z",
  "original_path": "/path/to/provision.ps1"
}
```

### Summarize Module

**Purpose**: Detect automation patterns without AI.

**Architecture**:
```
summarize/
├── __init__.py
├── powercli.py      # PowerCLI pattern detection
└── vrealize.py      # vRealize pattern detection
```

**PowerCLI Pattern Detection** (`powercli.py`):

```python
def summarize(script_path: Path) -> str:
    content = script_path.read_text()

    # Extract parameters
    params = extract_parameters(content)

    # Detect patterns
    has_env_branching = detect_environment_branching(content)
    has_tagging = detect_tagging(content)
    has_network_storage = detect_network_storage(content)

    # Format markdown summary
    return format_summary(params, has_env_branching, ...)
```

**Pattern Detection Methods**:
- **Parameters**: Regex matching `param(...)` blocks
- **Environment Branching**: Look for `ValidateSet`, `if $env`, etc.
- **Tagging**: Look for `New-TagAssignment`, `.Tags`, `@{...}`
- **Network/Storage**: Look for network/storage cmdlets and variables

**vRealize Pattern Detection** (`vrealize.py`):

```python
def summarize(workflow_path: Path) -> str:
    tree = ET.parse(workflow_path)
    root = tree.getroot()

    # Parse XML structure
    inputs = extract_inputs(root)
    outputs = extract_outputs(root)

    # Detect patterns
    has_approval = detect_approval(root)
    has_env_branching = detect_environment_branching(root)

    return format_summary(inputs, outputs, ...)
```

**XML Pattern Detection**:
- **Inputs/Outputs**: Parse `<input>` and `<output>` elements
- **Approval**: Look for approval decision nodes
- **Branching**: Look for decision/conditional elements

### Extract Module

**Purpose**: Convert source automation to operational intent using AI or templates.

**Flow**:
```
┌──────────────┐
│ Source File  │
│ (PS1 or XML) │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Read Content    │
└──────┬───────────┘
       │
       ▼
    ┌──────┐
    │ AI?  │───No──▶┌────────────────┐
    └──┬───┘        │ Template-Based │
       │ Yes        │   Extraction   │
       ▼            └───────┬────────┘
┌──────────────────┐        │
│  Build Prompt    │        │
└──────┬───────────┘        │
       │                    │
       ▼                    │
┌──────────────────┐        │
│  Call LLM API    │        │
└──────┬───────────┘        │
       │                    │
       ▼                    ▼
┌────────────────────────────┐
│   Parse Intent YAML        │
└──────┬─────────────────────┘
       │
       ▼
┌────────────────────────────┐
│  Save to intent/*.yaml     │
│  Log assumptions to        │
│  intent/assumptions.md     │
└────────────────────────────┘
```

**Prompt Construction**:

The prompts are stored in `prompts/` directory:
- `intent_extract_powercli.md` - PowerCLI extraction
- `intent_extract_vrealize.md` - vRealize extraction
- `generate_artifacts.md` - Artifact generation

**Example Prompt Structure**:
```markdown
# Role
You are an expert in VMware automation and OpenShift migration.

# Task
Extract operational intent from this PowerCLI script.

# Input
{script_content}

# Output Format
Produce YAML following this schema:
{schema}

# Guidelines
- Preserve all input parameters
- Detect environment-specific logic
- Log any assumptions in assumptions section
```

**AI Response Parsing**:
```python
def parse_llm_response(response: str) -> dict:
    # Extract YAML from markdown code blocks
    yaml_content = extract_yaml_from_markdown(response)

    # Parse YAML
    intent = yaml.safe_load(yaml_content)

    # Validate against schema
    validate_intent_schema(intent)

    return intent
```

### Merge Module

**Purpose**: Combine multiple intent sources into unified intent.

**Smart Merging Logic**:

```python
def merge_intents(intents: List[dict]) -> tuple[dict, List[str]]:
    merged = {}
    conflicts = []

    # Merge inputs (combine all unique inputs)
    merged['inputs'] = merge_inputs(intents, conflicts)

    # Merge compute (use maximum values)
    merged['compute'] = merge_compute_max(intents, conflicts)

    # Merge networking (detect conflicts)
    merged['networking'] = merge_networking(intents, conflicts)

    # Merge governance (most restrictive wins)
    merged['governance'] = merge_governance_strict(intents, conflicts)

    return merged, conflicts
```

**Merge Strategies**:

| Field | Strategy | Rationale |
|-------|----------|-----------|
| inputs | Union | Combine all unique inputs |
| compute.cpu_count | Maximum | Provision for highest need |
| compute.memory_gb | Maximum | Provision for highest need |
| governance.approval_required | OR (any true → true) | Most restrictive |
| governance.quotas | Minimum | Most restrictive |
| networking.* | Conflict on difference | Needs manual resolution |
| storage.* | Conflict on difference | Needs manual resolution |

**Conflict Detection**:

```python
def detect_conflicts(intent1: dict, intent2: dict) -> List[str]:
    conflicts = []

    # Network mapping conflicts
    if intent1.get('networking', {}).get('network') != \
       intent2.get('networking', {}).get('network'):
        conflicts.append(
            "Network mapping differs: "
            f"{intent1['networking']['network']} vs "
            f"{intent2['networking']['network']}"
        )

    # Approval requirement conflicts
    if intent1.get('governance', {}).get('approval_required') != \
       intent2.get('governance', {}).get('approval_required'):
        conflicts.append(
            "Approval requirement mismatch: "
            f"{intent1['governance']['approval_required']} vs "
            f"{intent2['governance']['approval_required']}"
        )

    return conflicts
```

### Validate Module

**Purpose**: Validate intent and generated artifacts.

**Validation Pipeline**:

```python
def validate_intent(intent_path: Path) -> tuple[bool, List[str]]:
    errors = []

    # YAML syntax check
    try:
        with open(intent_path) as f:
            intent = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [f"YAML syntax error: {e}"]

    # Schema version check
    if intent.get('schema_version') != 1:
        errors.append("Invalid or missing schema_version")

    # Required fields
    required = ['type', 'workflow_name']
    for field in required:
        if field not in intent:
            errors.append(f"Missing required field: {field}")

    # Validate inputs
    if 'inputs' in intent:
        for input in intent['inputs']:
            if 'name' not in input:
                errors.append("Input missing 'name' field")

    return len(errors) == 0, errors
```

### Generate Module

**Purpose**: Create Ansible playbooks and KubeVirt manifests from intent.

**Architecture**:
```
generate/
├── __init__.py
├── generator.py      # Main generation orchestrator
├── ansible.py        # Ansible-specific generation
└── kubevirt.py       # KubeVirt-specific generation
```

**Generation Flow**:

```python
def generate_all(
    workspace: Path,
    profile_name: str,
    use_ai: bool = True
) -> None:
    # Load intent
    intent = load_intent(workspace / 'intent' / 'intent.yaml')

    # Load profile
    config = load_config(workspace / 'ops-translate.yaml')
    profile = config['profiles'][profile_name]

    # Generate KubeVirt manifest
    vm_yaml = generate_kubevirt(intent, profile, use_ai)
    write_file(workspace / 'output' / 'kubevirt' / 'vm.yaml', vm_yaml)

    # Generate Ansible playbook
    playbook = generate_ansible(intent, profile, use_ai)
    write_ansible_structure(workspace / 'output' / 'ansible', playbook)

    # Generate README
    readme = generate_readme(intent, profile)
    write_file(workspace / 'output' / 'README.md', readme)
```

**KubeVirt Generation** (`kubevirt.py`):

```python
def generate_kubevirt(
    intent: dict,
    profile: dict,
    use_ai: bool
) -> str:
    if use_ai:
        # Use LLM to generate
        prompt = build_kubevirt_prompt(intent, profile)
        llm = get_provider(config)
        yaml_content = llm.generate(prompt)
    else:
        # Use template
        yaml_content = render_kubevirt_template(intent, profile)

    return yaml_content
```

**Template Example** (simplified):
```python
def render_kubevirt_template(intent: dict, profile: dict) -> str:
    vm_name = intent['inputs'][0]['name']
    cpu = intent['compute']['cpu_count']
    memory = intent['compute']['memory_gb']
    namespace = profile['default_namespace']

    return f"""
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: {vm_name}
  namespace: {namespace}
spec:
  running: false
  template:
    spec:
      domain:
        cpu:
          cores: {cpu}
        resources:
          requests:
            memory: {memory}Gi
        devices:
          disks:
            - name: rootdisk
              disk:
                bus: virtio
      volumes:
        - name: rootdisk
          dataVolume:
            name: {vm_name}-rootdisk
"""
```

**Ansible Generation** (`ansible.py`):

```python
def generate_ansible(
    intent: dict,
    profile: dict,
    use_ai: bool
) -> dict:
    if use_ai:
        prompt = build_ansible_prompt(intent, profile)
        llm = get_provider(config)
        return llm.generate(prompt)
    else:
        return {
            'playbook': render_playbook_template(intent, profile),
            'tasks': render_tasks_template(intent, profile),
            'defaults': render_defaults_template(intent, profile)
        }

def write_ansible_structure(base_path: Path, content: dict):
    # Write main playbook
    write_file(base_path / 'site.yml', content['playbook'])

    # Write role structure
    role_path = base_path / 'roles' / 'provision_vm'
    write_file(role_path / 'tasks' / 'main.yml', content['tasks'])
    write_file(role_path / 'defaults' / 'main.yml', content['defaults'])
```

## Data Flow

### Complete Pipeline

```
1. IMPORT PHASE
   ┌──────────────┐
   │ PowerCLI.ps1 │──┐
   └──────────────┘  │
   ┌──────────────┐  │     ┌────────────────┐
   │ Workflow.xml │──┼────▶│ input/ folder  │
   └──────────────┘  │     └────────────────┘
   ┌──────────────┐  │
   │  Script2.ps1 │──┘
   └──────────────┘

2. SUMMARIZE PHASE (Optional)
   ┌────────────────┐
   │ input/ folder  │
   └────────┬───────┘
            │
            ▼
   ┌────────────────────┐
   │ Pattern Detection  │
   └────────┬───────────┘
            │
            ▼
   ┌────────────────────┐
   │ intent/summary.md  │
   └────────────────────┘

3. EXTRACT PHASE
   ┌────────────────┐
   │ input/ folder  │
   └────────┬───────┘
            │
            ▼
   ┌────────────────────┐
   │  LLM / Templates   │
   └────────┬───────────┘
            │
            ▼
   ┌────────────────────────────────┐
   │ intent/powercli.intent.yaml    │
   │ intent/vrealize.intent.yaml    │
   │ intent/assumptions.md          │
   └────────────────────────────────┘

4. MERGE PHASE
   ┌────────────────────────────────┐
   │ intent/powercli.intent.yaml    │
   │ intent/vrealize.intent.yaml    │
   └────────┬───────────────────────┘
            │
            ▼
   ┌────────────────────┐
   │  Smart Merging     │
   │  + Conflict Check  │
   └────────┬───────────┘
            │
            ▼
   ┌────────────────────────────────┐
   │ intent/intent.yaml             │
   │ intent/conflicts.md (if any)   │
   └────────────────────────────────┘

5. GENERATE PHASE
   ┌────────────────────┐
   │ intent/intent.yaml │
   └────────┬───────────┘
            │
            ▼
   ┌────────────────────────┐
   │ LLM / Templates        │
   │ + Profile Config       │
   └────────┬───────────────┘
            │
            ▼
   ┌────────────────────────────────┐
   │ output/kubevirt/vm.yaml        │
   │ output/ansible/site.yml        │
   │ output/ansible/roles/...       │
   │ output/README.md               │
   └────────────────────────────────┘
```

### State Transitions

```
┌──────────┐   import   ┌──────────┐
│ NO FILES │──────────▶ │ IMPORTED │
└──────────┘            └────┬─────┘
                             │ extract
                             ▼
                        ┌──────────┐
                        │ EXTRACTED│
                        └────┬─────┘
                             │ merge
                             ▼
                        ┌──────────┐
                        │  MERGED  │
                        └────┬─────┘
                             │ generate
                             ▼
                        ┌──────────┐
                        │GENERATED │
                        └──────────┘
```

Each state is represented by files on disk:
- **IMPORTED**: Files in `input/`
- **EXTRACTED**: Files in `intent/*.intent.yaml`
- **MERGED**: File `intent/intent.yaml`
- **GENERATED**: Files in `output/`

## Intent Schema

### Schema Version 1

```yaml
schema_version: 1  # Required
type: powercli | vrealize | custom  # Required
workflow_name: string  # Required

# Input parameters
inputs:
  - name: string  # Required
    type: string | int | bool | object  # Required
    required: bool  # Required
    default: any  # Optional
    description: string  # Optional
    allowed_values: list  # Optional for enums

# Compute resources
compute:
  cpu_count: int
  memory_gb: int
  cpu_cores_per_socket: int  # Optional
  cpu_hot_add: bool  # Optional
  memory_hot_add: bool  # Optional

# Networking configuration
networking:
  interfaces:
    - name: string
      network: string
      type: string  # vmxnet3, e1000, etc.

# Storage configuration
storage:
  volumes:
    - name: string
      size_gb: int
      storage_class: string
      thin_provisioned: bool  # Optional

# Environment branching
environment_branching:
  enabled: bool
  conditions:
    - if: string  # Condition expression
      then:  # Overrides when true
        compute: {...}
        networking: {...}
        storage: {...}

# Governance and compliance
governance:
  approval_required: bool
  approvers: list[string]  # Optional
  approval_timeout_hours: int  # Optional
  quotas:
    max_cpu: int
    max_memory_gb: int
    max_storage_gb: int
  tags:
    required: list[string]
    recommended: list[string]

# Metadata and tagging
metadata:
  tags:
    - key: string
      value: string
  labels:
    - key: string
      value: string
  annotations:
    - key: string
      value: string

# AI assumptions (from extraction)
assumptions:
  - description: string
    confidence: high | medium | low
```

### Schema Validation

Intent YAML is validated against JSON Schema:

```python
# Simplified validation logic
def validate_intent_schema(intent: dict) -> List[str]:
    errors = []

    # Required top-level fields
    if 'schema_version' not in intent:
        errors.append("Missing 'schema_version'")
    elif intent['schema_version'] != 1:
        errors.append(f"Unsupported schema_version: {intent['schema_version']}")

    if 'type' not in intent:
        errors.append("Missing 'type'")
    elif intent['type'] not in ['powercli', 'vrealize', 'custom']:
        errors.append(f"Invalid type: {intent['type']}")

    if 'workflow_name' not in intent:
        errors.append("Missing 'workflow_name'")

    # Validate inputs
    if 'inputs' in intent:
        for i, input_def in enumerate(intent['inputs']):
            if 'name' not in input_def:
                errors.append(f"Input {i}: missing 'name'")
            if 'type' not in input_def:
                errors.append(f"Input {i}: missing 'type'")
            if 'required' not in input_def:
                errors.append(f"Input {i}: missing 'required'")

    return errors
```

## LLM Integration

### Provider Abstraction

```python
# Base class
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

# Anthropic implementation
class AnthropicProvider(LLMProvider):
    def __init__(self, config: dict):
        self.model = config.get('model', 'claude-sonnet-4-5')
        self.api_key = os.getenv(config.get('api_key_env'))
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get('max_tokens', 4096),
            temperature=kwargs.get('temperature', 0.0),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def is_available(self) -> bool:
        return self.api_key is not None

# Factory function
def get_provider(config: dict) -> LLMProvider:
    provider_name = config['llm']['provider'].lower()

    if provider_name == 'anthropic':
        return AnthropicProvider(config['llm'])
    elif provider_name == 'openai':
        return OpenAIProvider(config['llm'])
    elif provider_name == 'mock':
        return MockProvider(config['llm'])
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
```

### Prompt Engineering

Prompts are structured as Markdown files in `prompts/`:

**Key Sections**:
1. **Role**: Set LLM context
2. **Task**: Define extraction/generation goal
3. **Input**: Source automation content
4. **Schema**: Expected output format
5. **Guidelines**: Specific instructions
6. **Examples**: Few-shot learning

**Example Prompt Template**:
```markdown
# Role
You are an expert in VMware PowerCLI and OpenShift migration.

# Task
Extract the operational intent from this PowerCLI script and produce structured YAML.

# Input
```powershell
{script_content}
```

# Output Schema
```yaml
schema_version: 1
type: powercli
workflow_name: <name>
inputs:
  - name: <param_name>
    type: <string|int|bool>
    required: <true|false>
compute:
  cpu_count: <number>
  memory_gb: <number>
```

# Guidelines
1. Extract ALL input parameters with correct types
2. Detect environment branching logic (dev/prod/staging)
3. Identify compute resource values
4. Note any approval or governance requirements
5. Log assumptions in the assumptions section

# Output
Provide the YAML inside a markdown code block.
```

### Response Parsing

```python
def extract_yaml_from_markdown(response: str) -> str:
    """Extract YAML from markdown code blocks."""
    # Look for ```yaml or ```
    pattern = r'```(?:yaml)?\n(.*?)\n```'
    match = re.search(pattern, response, re.DOTALL)

    if match:
        return match.group(1)
    else:
        # Assume entire response is YAML
        return response

def parse_intent_from_llm(response: str) -> dict:
    """Parse LLM response into intent dictionary."""
    yaml_content = extract_yaml_from_markdown(response)

    try:
        intent = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"LLM produced invalid YAML: {e}")

    # Validate schema
    errors = validate_intent_schema(intent)
    if errors:
        raise ValueError(f"Intent validation failed: {errors}")

    return intent
```

## Generation Pipeline

### Two-Phase Generation

**Phase 1: Intent → Intermediate Representation**
```python
def intent_to_ir(intent: dict, profile: dict) -> dict:
    """Convert intent to intermediate representation."""
    return {
        'vm_definition': {
            'name': extract_vm_name(intent),
            'cpu': intent['compute']['cpu_count'],
            'memory': intent['compute']['memory_gb'],
            'networks': extract_networks(intent, profile),
            'storage': extract_storage(intent, profile),
        },
        'automation': {
            'type': 'ansible',
            'tasks': extract_tasks(intent),
            'vars': extract_variables(intent, profile),
        },
        'governance': extract_governance(intent),
    }
```

**Phase 2: IR → Target Artifacts**
```python
def ir_to_kubevirt(ir: dict) -> str:
    """Render KubeVirt YAML from IR."""
    template = load_jinja2_template('kubevirt_vm.yaml.j2')
    return template.render(vm=ir['vm_definition'])

def ir_to_ansible(ir: dict) -> dict:
    """Render Ansible playbook from IR."""
    return {
        'site.yml': render_template('site.yml.j2', ir),
        'tasks/main.yml': render_template('tasks.yml.j2', ir),
        'defaults/main.yml': render_template('defaults.yml.j2', ir),
    }
```

### Profile Resolution

```python
def resolve_profile(intent: dict, profile: dict) -> dict:
    """Apply profile defaults to intent."""
    resolved = intent.copy()

    # Apply namespace
    if 'networking' not in resolved:
        resolved['networking'] = {}
    resolved['networking']['namespace'] = profile['default_namespace']

    # Apply network default if not specified
    if 'network' not in resolved.get('networking', {}):
        resolved['networking']['network'] = profile['default_network']

    # Apply storage class
    for volume in resolved.get('storage', {}).get('volumes', []):
        if 'storage_class' not in volume:
            volume['storage_class'] = profile['default_storage_class']

    return resolved
```

## Extension Points

### Adding New Source Types

To add support for new automation sources (e.g., Terraform, ARM templates):

1. **Add summarize module**: `ops_translate/summarize/terraform.py`
2. **Add extraction prompt**: `prompts/intent_extract_terraform.md`
3. **Update import command**: Accept new source type
4. **Add tests**: `tests/test_terraform.py`

### Adding New Target Platforms

To add support for new targets (e.g., AWS, Azure):

1. **Add generator module**: `ops_translate/generate/aws.py`
2. **Add generation prompt**: `prompts/generate_aws.md`
3. **Add templates**: `templates/aws/`
4. **Update generate command**: Accept new target type

### Adding New LLM Providers

To add a new LLM provider:

1. **Create provider class**: `ops_translate/llm/newprovider.py`
   ```python
   class NewProvider(LLMProvider):
       def generate(self, prompt: str, **kwargs) -> str:
           # Implementation
           pass

       def is_available(self) -> bool:
           # Check API key
           pass
   ```

2. **Update factory**: `ops_translate/llm/__init__.py`
   ```python
   def get_provider(config: dict) -> LLMProvider:
       provider = config['llm']['provider']
       if provider == 'newprovider':
           return NewProvider(config['llm'])
       # ...
   ```

3. **Add configuration**: Document in `ops-translate.yaml`

4. **Add tests**: `tests/test_llm.py`

### Custom Merge Strategies

To implement custom merge strategies:

```python
# ops_translate/intent/merge.py

def register_merge_strategy(field_path: str, strategy: Callable):
    """Register custom merge strategy for a field."""
    MERGE_STRATEGIES[field_path] = strategy

# Custom strategy example
def merge_custom_field(values: List[Any], conflicts: List[str]) -> Any:
    """Custom merge logic."""
    # Your logic here
    return merged_value

# Usage
register_merge_strategy('custom.field', merge_custom_field)
```

## Performance Considerations

### Caching

LLM responses are expensive. Consider caching:

```python
def extract_with_cache(
    source_file: Path,
    cache_dir: Path
) -> dict:
    # Compute cache key
    file_hash = sha256_file(source_file)
    cache_file = cache_dir / f"{file_hash}.intent.yaml"

    # Check cache
    if cache_file.exists():
        return yaml.safe_load(cache_file.read_text())

    # Extract (expensive)
    intent = extract_intent(source_file)

    # Save to cache
    cache_file.write_text(yaml.dump(intent))

    return intent
```

### Parallel Processing

For large workspaces with many files:

```python
from concurrent.futures import ThreadPoolExecutor

def extract_all_parallel(
    input_files: List[Path],
    max_workers: int = 4
) -> dict:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(extract_intent, f): f
            for f in input_files
        }

        results = {}
        for future in as_completed(futures):
            file = futures[future]
            results[file.name] = future.result()

        return results
```

## Security Considerations

### API Key Management

- Never store API keys in `ops-translate.yaml`
- Always use environment variables
- Support `.env` files for local development
- Mask API keys in logs

### File System Security

- Validate all file paths to prevent directory traversal
- Check file sizes before reading
- Sanitize file names during import
- Use SHA-256 for integrity verification

### LLM Safety

- Set reasonable token limits to prevent cost overruns
- Implement timeout for API calls
- Validate LLM responses before using
- Log all LLM interactions for auditability

## Testing Architecture

### Test Pyramid

```
                ┌────────────┐
                │ Integration│  (10 tests)
                │   Tests    │
                └────────────┘
              ┌────────────────┐
              │  Component     │  (30 tests)
              │    Tests       │
              └────────────────┘
          ┌──────────────────────┐
          │    Unit Tests        │  (60+ tests)
          │                      │
          └──────────────────────┘
```

### Test Structure

```
tests/
├── test_cli.py           # CLI command tests
├── test_integration.py   # End-to-end workflow tests
├── test_llm.py          # LLM provider tests
├── test_merge.py        # Merge logic tests
├── test_summarize.py    # Summarization tests
├── test_util.py         # Utility function tests
└── test_workspace.py    # Workspace management tests
```

### Mock LLM for Testing

```python
class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def generate(self, prompt: str, **kwargs) -> str:
        # Return predefined intent based on prompt content
        if 'powercli' in prompt.lower():
            return MOCK_POWERCLI_INTENT
        elif 'vrealize' in prompt.lower():
            return MOCK_VREALIZE_INTENT
        else:
            return MOCK_GENERIC_INTENT

    def is_available(self) -> bool:
        return True  # Always available
```

## Conclusion

The ops-translate architecture is designed for:
- **Safety**: No destructive operations, transparent decision making
- **Modularity**: Clean component boundaries, swappable providers
- **Simplicity**: Filesystem-based state, no external dependencies
- **Extensibility**: Easy to add new sources, targets, and providers

For detailed usage instructions, see the [User Guide](USER_GUIDE.md).

For step-by-step tutorials, see [TUTORIAL.md](TUTORIAL.md).

For API reference, see [API_REFERENCE.md](API_REFERENCE.md).
