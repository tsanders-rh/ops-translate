"""
Intent extraction from source files using LLM.
"""
from pathlib import Path
from ops_translate.workspace import Workspace


def extract_all(workspace: Workspace):
    """
    Extract intent from all imported source files.

    Outputs:
    - intent/powercli.intent.yaml (if PowerCLI files present)
    - intent/vrealize.intent.yaml (if vRealize files present)
    - intent/assumptions.md
    """
    # TODO: Implement LLM-based intent extraction
    # For now, create placeholder files

    assumptions = []

    # Process PowerCLI files
    powercli_dir = workspace.root / "input/powercli"
    if powercli_dir.exists():
        ps_files = list(powercli_dir.glob("*.ps1"))
        if ps_files:
            intent_content = create_placeholder_intent("powercli", ps_files[0].name)
            output_file = workspace.root / "intent/powercli.intent.yaml"
            output_file.write_text(intent_content)
            assumptions.append(f"- PowerCLI: Created placeholder intent from {ps_files[0].name}")

    # Process vRealize files
    vrealize_dir = workspace.root / "input/vrealize"
    if vrealize_dir.exists():
        xml_files = list(vrealize_dir.glob("*.xml"))
        if xml_files:
            intent_content = create_placeholder_intent("vrealize", xml_files[0].name)
            output_file = workspace.root / "intent/vrealize.intent.yaml"
            output_file.write_text(intent_content)
            assumptions.append(f"- vRealize: Created placeholder intent from {xml_files[0].name}")

    # Write assumptions
    assumptions_file = workspace.root / "intent/assumptions.md"
    assumptions_content = "# Assumptions\n\n" + "\n".join(assumptions)
    assumptions_file.write_text(assumptions_content)


def create_placeholder_intent(source_type: str, filename: str) -> str:
    """Create a placeholder intent YAML."""
    return f"""schema_version: 1
sources:
  - type: {source_type}
    file: input/{source_type}/{filename}

intent:
  workflow_name: provision_vm
  workload_type: virtual_machine

  inputs:
    vm_name:
      type: string
      required: true
    environment:
      type: enum
      values: [dev, prod]
      required: true
    cpu:
      type: integer
      required: true
      min: 1
      max: 32
    memory_gb:
      type: integer
      required: true
      min: 1
      max: 256

  governance:
    approval:
      required_when:
        environment: prod

  profiles:
    network:
      when: {{ environment: prod }}
      value: net-prod
    network_else: net-dev
    storage:
      when: {{ environment: prod }}
      value: storage-gold
    storage_else: storage-standard

  metadata:
    tags:
      - key: env
        value_from: environment
      - key: managed_by
        value: ops-translate
"""
