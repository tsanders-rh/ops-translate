# ops-translate API Reference

Complete API reference for using ops-translate programmatically or extending its functionality.

## Table of Contents

1. [Overview](#overview)
2. [Workspace API](#workspace-api)
3. [Summarize API](#summarize-api)
4. [Intent Extraction API](#intent-extraction-api)
5. [Intent Merge API](#intent-merge-api)
6. [Validation API](#validation-api)
7. [Generation API](#generation-api)
8. [LLM Provider API](#llm-provider-api)
9. [Utility Functions](#utility-functions)
10. [Extending ops-translate](#extending-ops-translate)

## Overview

### Installation for Development

```bash
pip install -e ".[dev]"
```

### Basic Usage

```python
from pathlib import Path
from ops_translate.workspace import create_workspace, import_file
from ops_translate.intent.extract import extract_all
from ops_translate.intent.merge import merge_intents
from ops_translate.generate import generate_all

# Create workspace
workspace = Path("./my-workspace")
create_workspace(workspace)

# Import files
import_file(
    workspace=workspace,
    source_type="powercli",
    file_path=Path("/path/to/script.ps1")
)

# Extract intent
extract_all(workspace, use_ai=True)

# Merge intents
conflicts = merge_intents(workspace)

# Generate artifacts
generate_all(workspace, profile_name="lab", use_ai=True)
```

## Workspace API

Module: `ops_translate.workspace`

### create_workspace

Create a new ops-translate workspace.

**Signature**:
```python
def create_workspace(workspace_dir: Path) -> None
```

**Parameters**:
- `workspace_dir` (Path): Directory path for the workspace

**Returns**: None

**Raises**:
- `FileExistsError`: If workspace already exists
- `PermissionError`: If cannot create directory

**Example**:
```python
from pathlib import Path
from ops_translate.workspace import create_workspace

workspace = Path("./my-project")
create_workspace(workspace)
```

**Created Structure**:
```
my-project/
├── ops-translate.yaml
├── input/
│   ├── powercli/
│   └── vrealize/
├── intent/
├── mapping/
└── output/
    ├── ansible/
    └── kubevirt/
```

### get_workspace

Find the workspace directory from current location.

**Signature**:
```python
def get_workspace(start_path: Path = Path.cwd()) -> Optional[Path]
```

**Parameters**:
- `start_path` (Path, optional): Starting directory for search. Defaults to current directory.

**Returns**:
- `Path`: Workspace directory if found
- `None`: If no workspace found

**Example**:
```python
from ops_translate.workspace import get_workspace

workspace = get_workspace()
if workspace:
    print(f"Found workspace: {workspace}")
else:
    print("Not in a workspace")
```

**Search Logic**:
- Looks for `ops-translate.yaml` in current directory
- Walks up directory tree if not found
- Stops at filesystem root

### import_file

Import a source file into the workspace.

**Signature**:
```python
def import_file(
    workspace: Path,
    source_type: str,
    file_path: Path
) -> dict
```

**Parameters**:
- `workspace` (Path): Workspace directory
- `source_type` (str): Type of source (`"powercli"` or `"vrealize"`)
- `file_path` (Path): Path to file to import

**Returns**:
```python
{
    "file": str,            # Filename
    "source_type": str,     # Source type
    "sha256": str,          # SHA-256 hash
    "imported_at": str,     # ISO timestamp
    "original_path": str    # Original file path
}
```

**Raises**:
- `ValueError`: If source_type not in `["powercli", "vrealize"]`
- `FileNotFoundError`: If file_path doesn't exist
- `PermissionError`: If cannot read source or write destination

**Example**:
```python
from pathlib import Path
from ops_translate.workspace import import_file

metadata = import_file(
    workspace=Path("./my-workspace"),
    source_type="powercli",
    file_path=Path("/path/to/script.ps1")
)

print(f"Imported {metadata['file']} with hash {metadata['sha256']}")
```

### load_config

Load workspace configuration.

**Signature**:
```python
def load_config(workspace: Path) -> dict
```

**Parameters**:
- `workspace` (Path): Workspace directory

**Returns**: Configuration dictionary

**Raises**:
- `FileNotFoundError`: If ops-translate.yaml not found
- `yaml.YAMLError`: If config file invalid

**Example**:
```python
from ops_translate.workspace import load_config

config = load_config(Path("./my-workspace"))
llm_provider = config['llm']['provider']
profiles = config['profiles']
```

## Summarize API

Module: `ops_translate.summarize`

### PowerCLI Summarization

Module: `ops_translate.summarize.powercli`

#### summarize

Summarize a PowerCLI script.

**Signature**:
```python
def summarize(script_path: Path) -> str
```

**Parameters**:
- `script_path` (Path): Path to PowerCLI script (.ps1)

**Returns**: Markdown summary string

**Example**:
```python
from pathlib import Path
from ops_translate.summarize.powercli import summarize

summary = summarize(Path("./input/powercli/provision.ps1"))
print(summary)
```

**Output Example**:
```markdown
**File**: provision.ps1

**Parameters**:
- VMName (string, required)
- CPUCount (int, optional)

**Environment Branching**: Detected
**Tagging/Metadata**: Detected
**Network/Storage Selection**: Detected
```

#### extract_parameters

Extract parameters from PowerCLI script.

**Signature**:
```python
def extract_parameters(content: str) -> List[dict]
```

**Parameters**:
- `content` (str): PowerCLI script content

**Returns**: List of parameter dictionaries

**Example**:
```python
from ops_translate.summarize.powercli import extract_parameters

content = """
param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,

    [Parameter(Mandatory=$false)]
    [int]$CPUCount = 2
)
"""

params = extract_parameters(content)
# [
#     {"name": "VMName", "type": "string", "required": True},
#     {"name": "CPUCount", "type": "int", "required": False}
# ]
```

#### detect_environment_branching

Detect environment branching logic.

**Signature**:
```python
def detect_environment_branching(content: str) -> bool
```

**Parameters**:
- `content` (str): PowerCLI script content

**Returns**: True if environment branching detected

**Example**:
```python
from ops_translate.summarize.powercli import detect_environment_branching

content = """
[ValidateSet("dev", "prod")]
[string]$Environment

if ($Environment -eq "prod") {
    $CPUCount = 4
} else {
    $CPUCount = 2
}
"""

has_branching = detect_environment_branching(content)
# True
```

#### detect_tagging

Detect tagging/metadata operations.

**Signature**:
```python
def detect_tagging(content: str) -> bool
```

#### detect_network_storage

Detect network/storage selection logic.

**Signature**:
```python
def detect_network_storage(content: str) -> bool
```

### vRealize Summarization

Module: `ops_translate.summarize.vrealize`

#### summarize

Summarize a vRealize workflow.

**Signature**:
```python
def summarize(workflow_path: Path) -> str
```

**Parameters**:
- `workflow_path` (Path): Path to vRealize workflow XML

**Returns**: Markdown summary string

**Example**:
```python
from pathlib import Path
from ops_translate.summarize.vrealize import summarize

summary = summarize(Path("./input/vrealize/workflow.xml"))
print(summary)
```

#### detect_approval

Detect approval requirements in workflow.

**Signature**:
```python
def detect_approval(root: ET.Element) -> bool
```

**Parameters**:
- `root` (ET.Element): Parsed XML root element

**Returns**: True if approval detected

**Example**:
```python
import xml.etree.ElementTree as ET
from ops_translate.summarize.vrealize import detect_approval

tree = ET.parse("workflow.xml")
root = tree.getroot()

has_approval = detect_approval(root)
```

## Intent Extraction API

Module: `ops_translate.intent.extract`

### extract_all

Extract intent from all imported sources.

**Signature**:
```python
def extract_all(
    workspace: Path,
    use_ai: bool = True
) -> dict
```

**Parameters**:
- `workspace` (Path): Workspace directory
- `use_ai` (bool, optional): Use AI for extraction. Defaults to True.

**Returns**:
```python
{
    "powercli": dict,     # Extracted PowerCLI intent
    "vrealize": dict,     # Extracted vRealize intent
    "assumptions": str    # Assumptions log
}
```

**Example**:
```python
from pathlib import Path
from ops_translate.intent.extract import extract_all

results = extract_all(
    workspace=Path("./my-workspace"),
    use_ai=True
)

powercli_intent = results['powercli']
assumptions = results['assumptions']
```

**Side Effects**:
- Writes `intent/powercli.intent.yaml`
- Writes `intent/vrealize.intent.yaml`
- Writes `intent/assumptions.md`

### extract_from_powercli

Extract intent from a PowerCLI script.

**Signature**:
```python
def extract_from_powercli(
    script_path: Path,
    llm_provider: LLMProvider,
    use_ai: bool = True
) -> tuple[dict, str]
```

**Parameters**:
- `script_path` (Path): Path to PowerCLI script
- `llm_provider` (LLMProvider): LLM provider instance
- `use_ai` (bool, optional): Use AI. Defaults to True.

**Returns**:
```python
(
    intent_dict,      # Intent dictionary
    assumptions_str   # Assumptions markdown
)
```

**Example**:
```python
from pathlib import Path
from ops_translate.intent.extract import extract_from_powercli
from ops_translate.llm import get_provider

config = {"llm": {"provider": "mock"}}
provider = get_provider(config)

intent, assumptions = extract_from_powercli(
    script_path=Path("./script.ps1"),
    llm_provider=provider,
    use_ai=True
)
```

### extract_from_vrealize

Extract intent from a vRealize workflow.

**Signature**:
```python
def extract_from_vrealize(
    workflow_path: Path,
    llm_provider: LLMProvider,
    use_ai: bool = True
) -> tuple[dict, str]
```

**Parameters**: Same as `extract_from_powercli`

**Returns**: Same as `extract_from_powercli`

## Intent Merge API

Module: `ops_translate.intent.merge`

### merge_intents

Merge multiple intent sources into unified intent.

**Signature**:
```python
def merge_intents(workspace: Path) -> List[str]
```

**Parameters**:
- `workspace` (Path): Workspace directory

**Returns**: List of conflict strings (empty if no conflicts)

**Example**:
```python
from pathlib import Path
from ops_translate.intent.merge import merge_intents

conflicts = merge_intents(Path("./my-workspace"))

if conflicts:
    print("Conflicts detected:")
    for conflict in conflicts:
        print(f"  - {conflict}")
else:
    print("Merged successfully")
```

**Side Effects**:
- Writes `intent/intent.yaml`
- Writes `intent/conflicts.md` (if conflicts)

### smart_merge

Perform smart merge of intent dictionaries.

**Signature**:
```python
def smart_merge(intents: List[dict]) -> tuple[dict, List[str]]
```

**Parameters**:
- `intents` (List[dict]): List of intent dictionaries to merge

**Returns**:
```python
(
    merged_intent,  # Merged intent dictionary
    conflicts       # List of conflict descriptions
)
```

**Example**:
```python
from ops_translate.intent.merge import smart_merge

intent1 = {
    "schema_version": 1,
    "type": "powercli",
    "workflow_name": "provision_vm",
    "compute": {"cpu_count": 2, "memory_gb": 8}
}

intent2 = {
    "schema_version": 1,
    "type": "vrealize",
    "workflow_name": "vm_workflow",
    "compute": {"cpu_count": 4, "memory_gb": 16},
    "governance": {"approval_required": True}
}

merged, conflicts = smart_merge([intent1, intent2])

# merged = {
#     "schema_version": 1,
#     "workflow_name": "provision_vm",
#     "compute": {"cpu_count": 4, "memory_gb": 16},  # Max values
#     "governance": {"approval_required": True}
# }
```

### detect_conflicts

Detect conflicts between intent sources.

**Signature**:
```python
def detect_conflicts(intent1: dict, intent2: dict) -> List[str]
```

**Parameters**:
- `intent1` (dict): First intent
- `intent2` (dict): Second intent

**Returns**: List of conflict descriptions

**Example**:
```python
from ops_translate.intent.merge import detect_conflicts

intent1 = {"networking": {"network": "prod-net"}}
intent2 = {"networking": {"network": "production-network"}}

conflicts = detect_conflicts(intent1, intent2)
# ["Network mapping differs: prod-net vs production-network"]
```

## Validation API

Module: `ops_translate.intent.validate`

### validate_intent

Validate intent YAML against schema.

**Signature**:
```python
def validate_intent(intent_path: Path) -> tuple[bool, List[str]]
```

**Parameters**:
- `intent_path` (Path): Path to intent YAML file

**Returns**:
```python
(
    is_valid,  # True if valid
    errors     # List of error messages
)
```

**Example**:
```python
from pathlib import Path
from ops_translate.intent.validate import validate_intent

valid, errors = validate_intent(Path("./intent/intent.yaml"))

if valid:
    print("Intent is valid")
else:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

### validate_artifacts

Validate generated artifacts.

**Signature**:
```python
def validate_artifacts(workspace: Path) -> tuple[bool, List[str]]
```

**Parameters**:
- `workspace` (Path): Workspace directory

**Returns**:
```python
(
    is_valid,  # True if all valid
    messages   # List of validation messages
)
```

**Example**:
```python
from pathlib import Path
from ops_translate.intent.validate import validate_artifacts

valid, messages = validate_artifacts(Path("./my-workspace"))

for msg in messages:
    print(msg)
```

**Checks**:
- YAML syntax in generated files
- Ansible playbook structure
- KubeVirt manifest structure
- Required files presence

## Generation API

Module: `ops_translate.generate`

### generate_all

Generate all artifacts from intent.

**Signature**:
```python
def generate_all(
    workspace: Path,
    profile_name: str,
    use_ai: bool = True
) -> None
```

**Parameters**:
- `workspace` (Path): Workspace directory
- `profile_name` (str): Profile name from config
- `use_ai` (bool, optional): Use AI for generation. Defaults to True.

**Returns**: None

**Raises**:
- `FileNotFoundError`: If intent file not found
- `KeyError`: If profile not found in config
- `ValueError`: If intent validation fails

**Example**:
```python
from pathlib import Path
from ops_translate.generate import generate_all

generate_all(
    workspace=Path("./my-workspace"),
    profile_name="lab",
    use_ai=True
)
```

**Side Effects**:
- Writes `output/kubevirt/vm.yaml`
- Writes `output/ansible/site.yml`
- Writes `output/ansible/roles/provision_vm/tasks/main.yml`
- Writes `output/ansible/roles/provision_vm/defaults/main.yml`
- Writes `output/README.md`

### KubeVirt Generation

Module: `ops_translate.generate.kubevirt`

#### generate_kubevirt_manifest

Generate KubeVirt VirtualMachine manifest.

**Signature**:
```python
def generate_kubevirt_manifest(
    intent: dict,
    profile: dict,
    llm_provider: Optional[LLMProvider] = None
) -> str
```

**Parameters**:
- `intent` (dict): Intent dictionary
- `profile` (dict): Profile configuration
- `llm_provider` (LLMProvider, optional): LLM provider for AI generation

**Returns**: YAML manifest string

**Example**:
```python
from ops_translate.generate.kubevirt import generate_kubevirt_manifest
from ops_translate.llm import get_provider

intent = {
    "schema_version": 1,
    "workflow_name": "my-vm",
    "compute": {"cpu_count": 4, "memory_gb": 16}
}

profile = {
    "default_namespace": "virt-lab",
    "default_network": "lab-network",
    "default_storage_class": "nfs"
}

config = {"llm": {"provider": "mock"}}
provider = get_provider(config)

manifest = generate_kubevirt_manifest(intent, profile, provider)
print(manifest)
```

### Ansible Generation

Module: `ops_translate.generate.ansible`

#### generate_ansible_playbook

Generate Ansible playbook and role.

**Signature**:
```python
def generate_ansible_playbook(
    intent: dict,
    profile: dict,
    llm_provider: Optional[LLMProvider] = None
) -> dict
```

**Parameters**:
- `intent` (dict): Intent dictionary
- `profile` (dict): Profile configuration
- `llm_provider` (LLMProvider, optional): LLM provider for AI generation

**Returns**:
```python
{
    "site.yml": str,           # Main playbook
    "tasks/main.yml": str,     # Role tasks
    "defaults/main.yml": str   # Role defaults
}
```

**Example**:
```python
from ops_translate.generate.ansible import generate_ansible_playbook

ansible_files = generate_ansible_playbook(intent, profile, provider)

print(ansible_files['site.yml'])
print(ansible_files['tasks/main.yml'])
```

## LLM Provider API

Module: `ops_translate.llm`

### get_provider

Get LLM provider instance from configuration.

**Signature**:
```python
def get_provider(config: dict) -> LLMProvider
```

**Parameters**:
- `config` (dict): Configuration dictionary

**Returns**: LLMProvider instance

**Raises**:
- `ValueError`: If provider not supported

**Example**:
```python
from ops_translate.llm import get_provider

config = {
    "llm": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "api_key_env": "OPS_TRANSLATE_LLM_API_KEY"
    }
}

provider = get_provider(config)
```

### LLMProvider (Base Class)

Abstract base class for LLM providers.

**Methods**:

#### generate

```python
def generate(
    self,
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.0
) -> str
```

**Parameters**:
- `prompt` (str): User prompt
- `system_prompt` (str, optional): System prompt
- `max_tokens` (int, optional): Maximum tokens. Defaults to 4096.
- `temperature` (float, optional): Temperature. Defaults to 0.0.

**Returns**: Generated text

#### is_available

```python
def is_available(self) -> bool
```

**Returns**: True if provider is available (API key set, etc.)

### AnthropicProvider

Anthropic Claude provider.

**Example**:
```python
import os
from ops_translate.llm.anthropic import AnthropicProvider

os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-...'

config = {
    "provider": "anthropic",
    "model": "claude-sonnet-4-5",
    "api_key_env": "ANTHROPIC_API_KEY"
}

provider = AnthropicProvider(config)

if provider.is_available():
    response = provider.generate("Extract intent from this script...")
    print(response)
```

### OpenAIProvider

OpenAI provider.

**Example**:
```python
import os
from ops_translate.llm.openai import OpenAIProvider

os.environ['OPENAI_API_KEY'] = 'sk-...'

config = {
    "provider": "openai",
    "model": "gpt-4-turbo-preview",
    "api_key_env": "OPENAI_API_KEY"
}

provider = OpenAIProvider(config)

response = provider.generate("Extract intent...")
```

### MockProvider

Mock provider for testing.

**Example**:
```python
from ops_translate.llm.mock import MockProvider

config = {"provider": "mock", "model": "mock-model"}

provider = MockProvider(config)

# Always available, returns predefined responses
assert provider.is_available() == True

response = provider.generate("PowerCLI script here")
# Returns mock PowerCLI intent YAML
```

## Utility Functions

Module: `ops_translate.util`

### File Utilities

Module: `ops_translate.util.files`

#### ensure_dir

Ensure directory exists, creating if necessary.

**Signature**:
```python
def ensure_dir(path: Path) -> None
```

**Example**:
```python
from pathlib import Path
from ops_translate.util.files import ensure_dir

ensure_dir(Path("./output/ansible/roles/provision_vm/tasks"))
```

#### write_text

Write text to file, creating parent directories.

**Signature**:
```python
def write_text(path: Path, content: str) -> None
```

**Example**:
```python
from pathlib import Path
from ops_translate.util.files import write_text

write_text(
    Path("./output/kubevirt/vm.yaml"),
    "apiVersion: kubevirt.io/v1\n..."
)
```

### Hashing Utilities

Module: `ops_translate.util.hashing`

#### sha256_file

Compute SHA-256 hash of a file.

**Signature**:
```python
def sha256_file(path: Path) -> str
```

**Parameters**:
- `path` (Path): File path

**Returns**: Hex-encoded SHA-256 hash

**Example**:
```python
from pathlib import Path
from ops_translate.util.hashing import sha256_file

hash_value = sha256_file(Path("./script.ps1"))
print(f"SHA-256: {hash_value}")
```

#### sha256_string

Compute SHA-256 hash of a string.

**Signature**:
```python
def sha256_string(content: str) -> str
```

**Parameters**:
- `content` (str): String content

**Returns**: Hex-encoded SHA-256 hash

**Example**:
```python
from ops_translate.util.hashing import sha256_string

hash_value = sha256_string("hello world")
# "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
```

## Extending ops-translate

### Adding a Custom LLM Provider

Create a new provider class:

```python
# my_provider.py
from ops_translate.llm.base import LLMProvider

class MyProvider(LLMProvider):
    """Custom LLM provider."""

    def __init__(self, config: dict):
        self.model = config.get('model')
        self.api_key = os.getenv(config.get('api_key_env'))
        # Initialize your client

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0
    ) -> str:
        """Generate text using custom provider."""
        # Your implementation
        response = self.client.complete(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.text

    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.api_key is not None
```

Register the provider:

```python
# ops_translate/llm/__init__.py
from ops_translate.llm.my_provider import MyProvider

def get_provider(config: dict) -> LLMProvider:
    provider = config['llm']['provider'].lower()

    if provider == 'myprovider':
        return MyProvider(config['llm'])
    # ... existing providers
```

Use the provider:

```yaml
# ops-translate.yaml
llm:
  provider: myprovider
  model: my-model-name
  api_key_env: MY_PROVIDER_API_KEY
```

### Adding a Custom Merge Strategy

Register custom merge logic:

```python
from ops_translate.intent.merge import MERGE_STRATEGIES

def merge_custom_field(values: List[Any]) -> Any:
    """Custom merge logic for specific field."""
    # Your merge logic
    return merged_value

# Register strategy
MERGE_STRATEGIES['custom.field.path'] = merge_custom_field
```

### Adding a Custom Generator

Create a new generator module:

```python
# ops_translate/generate/custom.py

def generate_custom_artifact(
    intent: dict,
    profile: dict,
    llm_provider: Optional[LLMProvider] = None
) -> str:
    """Generate custom artifact from intent."""

    if llm_provider and llm_provider.is_available():
        # AI-powered generation
        prompt = build_custom_prompt(intent, profile)
        return llm_provider.generate(prompt)
    else:
        # Template-based generation
        return render_custom_template(intent, profile)

def build_custom_prompt(intent: dict, profile: dict) -> str:
    """Build prompt for custom artifact generation."""
    return f"""
Generate a custom artifact for:
Workflow: {intent['workflow_name']}
Profile: {profile}

Intent:
{yaml.dump(intent)}

Output should be...
"""
```

Use the custom generator:

```python
from pathlib import Path
from ops_translate.generate.custom import generate_custom_artifact
from ops_translate.llm import get_provider

config = load_config(workspace)
provider = get_provider(config)

intent = yaml.safe_load((workspace / "intent/intent.yaml").read_text())
profile = config['profiles']['lab']

custom_artifact = generate_custom_artifact(intent, profile, provider)

(workspace / "output/custom/artifact.yaml").write_text(custom_artifact)
```

### Creating Custom Validators

Add custom validation logic:

```python
from ops_translate.intent.validate import VALIDATORS

def validate_custom_field(intent: dict) -> List[str]:
    """Validate custom field in intent."""
    errors = []

    if 'custom_field' in intent:
        value = intent['custom_field']
        if not isinstance(value, str):
            errors.append("custom_field must be a string")

    return errors

# Register validator
VALIDATORS.append(validate_custom_field)
```

## Error Handling

### Common Exceptions

```python
from ops_translate.exceptions import (
    WorkspaceNotFoundError,
    IntentValidationError,
    LLMError,
    MergeConflictError
)

try:
    workspace = get_workspace()
except WorkspaceNotFoundError:
    print("Not in a workspace. Run ops-translate init first.")

try:
    extract_all(workspace, use_ai=True)
except LLMError as e:
    print(f"LLM error: {e}")
    # Fall back to template mode
    extract_all(workspace, use_ai=False)

try:
    conflicts = merge_intents(workspace)
    if conflicts:
        raise MergeConflictError(conflicts)
except MergeConflictError as e:
    print(f"Merge conflicts: {e.conflicts}")
    # Handle conflicts
```

## Type Hints

All public APIs include type hints:

```python
from typing import Optional, List, Dict, Tuple
from pathlib import Path

def example_function(
    required_param: str,
    optional_param: Optional[int] = None,
    list_param: List[str] = None
) -> Tuple[bool, List[str]]:
    """Example function with type hints."""
    if list_param is None:
        list_param = []

    return True, []
```

Use mypy for type checking:

```bash
mypy ops_translate/
```

## Testing Your Extensions

Test custom providers:

```python
# test_my_provider.py
from my_provider import MyProvider

def test_my_provider():
    config = {
        "provider": "myprovider",
        "model": "test-model",
        "api_key_env": "TEST_KEY"
    }

    provider = MyProvider(config)

    # Test availability
    assert provider.is_available()

    # Test generation
    result = provider.generate("test prompt")
    assert isinstance(result, str)
    assert len(result) > 0
```

Test custom generators:

```python
# test_custom_generator.py
from ops_translate.generate.custom import generate_custom_artifact
from ops_translate.llm.mock import MockProvider

def test_custom_generator():
    intent = {
        "schema_version": 1,
        "workflow_name": "test",
        "compute": {"cpu_count": 2}
    }

    profile = {"default_namespace": "test"}

    provider = MockProvider({})

    artifact = generate_custom_artifact(intent, profile, provider)

    assert artifact is not None
    assert "test" in artifact
```

## Next Steps

- Read the [User Guide](USER_GUIDE.md) for usage instructions
- Review the [Architecture](ARCHITECTURE.md) for system design
- Follow the [Tutorial](TUTORIAL.md) for hands-on examples
- Check the [source code](../ops_translate/) for implementation details
