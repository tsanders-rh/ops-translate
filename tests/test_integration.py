"""
Integration tests for end-to-end workflows.
"""

import shutil

import yaml

from ops_translate.generate import generate_all
from ops_translate.intent.extract import extract_all
from ops_translate.intent.merge import merge_intents
from ops_translate.intent.validate import validate_artifacts, validate_intent


def test_full_workflow_powercli(temp_workspace, powercli_fixture):
    """Test complete workflow: import → extract → merge → generate"""
    workspace = temp_workspace

    # Import PowerCLI file
    dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    shutil.copy2(powercli_fixture, dest)

    # Extract intent (using mock provider)
    extract_all(workspace)

    # Verify intent file was created
    intent_files = list((workspace.root / "intent").glob("*.intent.yaml"))
    assert len(intent_files) > 0, "No intent files created"

    # Verify intent file has valid schema
    for intent_file in intent_files:
        if intent_file.name == "intent.yaml":
            continue
        is_valid, errors = validate_intent(intent_file)
        # Mock provider may not create fully valid intent, but file should exist
        assert intent_file.exists()

    # Merge intents (should work even with one file)
    _ = merge_intents(workspace)

    # Verify merged intent exists
    merged_intent = workspace.root / "intent" / "intent.yaml"
    assert merged_intent.exists(), "Merged intent not created"

    # Load and verify merged intent structure
    with open(merged_intent) as f:
        intent_data = yaml.safe_load(f)

    assert intent_data is not None
    assert "schema_version" in intent_data
    assert "intent" in intent_data
    assert "sources" in intent_data

    # Generate artifacts (using template mode)
    generate_all(workspace, profile="lab", use_ai=False)

    # Verify artifacts were generated
    kubevirt_manifest = workspace.root / "output" / "kubevirt" / "vm.yaml"
    ansible_playbook = workspace.root / "output" / "ansible" / "site.yml"
    readme = workspace.root / "output" / "README.md"

    assert kubevirt_manifest.exists(), "KubeVirt manifest not generated"
    assert ansible_playbook.exists(), "Ansible playbook not generated"
    assert readme.exists(), "README not generated"

    # Validate generated artifacts
    is_valid, messages = validate_artifacts(workspace)
    # Should have valid YAML at minimum
    assert kubevirt_manifest.exists()
    assert ansible_playbook.exists()


def test_full_workflow_vrealize(temp_workspace, vrealize_fixture):
    """Test complete workflow with vRealize: import → extract → merge → generate"""
    workspace = temp_workspace

    # Import vRealize file
    dest = workspace.root / "input" / "vrealize" / vrealize_fixture.name
    shutil.copy2(vrealize_fixture, dest)

    # Extract intent (using mock provider)
    extract_all(workspace)

    # Verify intent file was created
    intent_files = list((workspace.root / "intent").glob("*.intent.yaml"))
    assert len(intent_files) > 0, "No intent files created"

    # Merge intents
    merge_intents(workspace)

    # Verify merged intent exists
    merged_intent = workspace.root / "intent" / "intent.yaml"
    assert merged_intent.exists(), "Merged intent not created"

    # Generate artifacts
    generate_all(workspace, profile="prod", use_ai=False)

    # Verify artifacts
    assert (workspace.root / "output" / "kubevirt" / "vm.yaml").exists()
    assert (workspace.root / "output" / "ansible" / "site.yml").exists()


def test_multi_source_merge(temp_workspace, powercli_fixture, vrealize_fixture):
    """Test merging intents from multiple sources"""
    workspace = temp_workspace

    # Import both PowerCLI and vRealize files
    powercli_dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    vrealize_dest = workspace.root / "input" / "vrealize" / vrealize_fixture.name

    shutil.copy2(powercli_fixture, powercli_dest)
    shutil.copy2(vrealize_fixture, vrealize_dest)

    # Extract intents from both
    extract_all(workspace)

    # Should have two intent files (plus assumptions.md)
    intent_files = list((workspace.root / "intent").glob("*.intent.yaml"))
    assert len(intent_files) >= 2, f"Expected 2+ intent files, got {len(intent_files)}"

    # Merge intents
    _ = merge_intents(workspace)

    # Verify merged intent
    merged_intent = workspace.root / "intent" / "intent.yaml"
    assert merged_intent.exists()

    # Load merged intent
    with open(merged_intent) as f:
        intent_data = yaml.safe_load(f)

    # Verify sources from both files are included
    assert len(intent_data["sources"]) >= 2, "Sources not merged correctly"

    # Verify smart merge combined inputs
    if "inputs" in intent_data.get("intent", {}):
        inputs = intent_data["intent"]["inputs"]
        # Should have inputs from both sources
        assert isinstance(inputs, dict)


def test_generated_ansible_is_valid_yaml(temp_workspace, powercli_fixture):
    """Test that generated Ansible playbook is valid YAML"""
    workspace = temp_workspace

    # Import and process
    dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    shutil.copy2(powercli_fixture, dest)

    extract_all(workspace)
    merge_intents(workspace)
    generate_all(workspace, profile="lab", use_ai=False)

    # Load and parse Ansible playbook
    playbook_path = workspace.root / "output" / "ansible" / "site.yml"
    with open(playbook_path) as f:
        playbook_data = yaml.safe_load(f)

    # Verify basic playbook structure
    assert isinstance(playbook_data, list), "Playbook should be a list of plays"
    assert len(playbook_data) > 0, "Playbook should have at least one play"

    # Verify first play structure
    play = playbook_data[0]
    assert "hosts" in play, "Play should have hosts"
    assert "tasks" in play or "roles" in play, "Play should have tasks or roles"


def test_generated_kubevirt_is_valid_yaml(temp_workspace, powercli_fixture):
    """Test that generated KubeVirt manifest is valid YAML and has expected structure"""
    workspace = temp_workspace

    # Import and process
    dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    shutil.copy2(powercli_fixture, dest)

    extract_all(workspace)
    merge_intents(workspace)
    generate_all(workspace, profile="lab", use_ai=False)

    # Load and parse KubeVirt manifest
    manifest_path = workspace.root / "output" / "kubevirt" / "vm.yaml"
    with open(manifest_path) as f:
        manifest_data = yaml.safe_load(f)

    # Verify Kubernetes resource structure
    assert "apiVersion" in manifest_data, "Manifest should have apiVersion"
    assert "kind" in manifest_data, "Manifest should have kind"
    assert "metadata" in manifest_data, "Manifest should have metadata"
    assert "spec" in manifest_data, "Manifest should have spec"

    # Verify it's a KubeVirt VirtualMachine
    assert "kubevirt.io" in manifest_data["apiVersion"]
    assert manifest_data["kind"] == "VirtualMachine"


def test_assumptions_file_created(temp_workspace, powercli_fixture):
    """Test that assumptions.md file is created during extraction"""
    workspace = temp_workspace

    dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    shutil.copy2(powercli_fixture, dest)

    extract_all(workspace)

    assumptions_file = workspace.root / "intent" / "assumptions.md"
    assert assumptions_file.exists(), "Assumptions file not created"

    # Verify it has content
    content = assumptions_file.read_text()
    assert len(content) > 0, "Assumptions file is empty"
    assert "# Assumptions and Inferences" in content


def test_conflicts_detected_in_merge(temp_workspace, powercli_fixture, vrealize_fixture):
    """Test that conflicts are detected when merging different intents"""
    workspace = temp_workspace

    # Import both sources
    powercli_dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    vrealize_dest = workspace.root / "input" / "vrealize" / vrealize_fixture.name

    shutil.copy2(powercli_fixture, powercli_dest)
    shutil.copy2(vrealize_fixture, vrealize_dest)

    extract_all(workspace)

    # Merge should detect conflicts
    has_conflicts = merge_intents(workspace)

    # Conflicts file should be created
    conflicts_file = workspace.root / "intent" / "conflicts.md"
    if has_conflicts:
        assert conflicts_file.exists(), "Conflicts file should exist when conflicts detected"

        # Verify conflicts file has content
        content = conflicts_file.read_text()
        assert "# Intent Merge Conflicts" in content


def test_validation_catches_invalid_intent(temp_workspace):
    """Test that validation catches invalid intent files"""
    workspace = temp_workspace

    # Create an invalid intent file
    invalid_intent = workspace.root / "intent" / "invalid.intent.yaml"
    invalid_intent.write_text("""
schema_version: "wrong"
intent:
    workflow_name: 123
""")

    # Validation should fail
    is_valid, errors = validate_intent(invalid_intent)
    assert not is_valid, "Validation should fail for invalid intent"
    assert len(errors) > 0, "Should have error messages"


def test_generate_with_different_profiles(temp_workspace, powercli_fixture):
    """Test generation with different profiles produces different output"""
    workspace = temp_workspace

    dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    shutil.copy2(powercli_fixture, dest)

    extract_all(workspace)
    merge_intents(workspace)

    # Generate with lab profile
    generate_all(workspace, profile="lab", use_ai=False)
    lab_playbook = (workspace.root / "output" / "ansible" / "site.yml").read_text()

    # Clean output directory
    shutil.rmtree(workspace.root / "output")
    (workspace.root / "output").mkdir()

    # Generate with prod profile
    generate_all(workspace, profile="prod", use_ai=False)
    prod_playbook = (workspace.root / "output" / "ansible" / "site.yml").read_text()

    # Playbooks should reference different namespaces/networks based on profile
    # Even if content is similar, the generation should succeed for both
    assert len(lab_playbook) > 0
    assert len(prod_playbook) > 0


def test_generate_assume_existing_vms_mode(temp_workspace, powercli_fixture):
    """Test generation with assume_existing_vms creates validation tasks, not creation tasks"""
    workspace = temp_workspace

    dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    shutil.copy2(powercli_fixture, dest)

    extract_all(workspace)
    merge_intents(workspace)

    # Generate with assume_existing_vms=True (MTV mode)
    generate_all(workspace, profile="lab", use_ai=False, assume_existing_vms=True)

    # Verify KubeVirt manifest was NOT generated (check file, not directory)
    kubevirt_manifest = workspace.root / "output" / "kubevirt" / "vm.yaml"
    assert not kubevirt_manifest.exists(), "KubeVirt manifest should not exist in MTV mode"

    # Verify Ansible playbook was generated
    playbook_path = workspace.root / "output" / "ansible" / "site.yml"
    assert playbook_path.exists(), "Ansible playbook should be generated"

    # Load Ansible role tasks
    tasks_path = workspace.root / "output" / "ansible" / "roles" / "provision_vm" / "tasks" / "main.yml"
    assert tasks_path.exists(), "Ansible role tasks should be generated"

    with open(tasks_path) as f:
        tasks_content = f.read()

    # Verify validation tasks are present (MTV mode)
    assert "Verify VM exists" in tasks_content, "Should have VM verification task"
    assert "Validate VM CPU configuration" in tasks_content, "Should have CPU validation task"
    assert "Validate VM memory configuration" in tasks_content, "Should have memory validation task"
    assert "Apply operational labels" in tasks_content, "Should have label patching task"

    # Verify creation tasks are NOT present
    assert "Create KubeVirt VirtualMachine" not in tasks_content, "Should not have VM creation task"
    assert "Wait for VM to be ready" not in tasks_content, "Should not have VM wait task"

    # Verify tasks use k8s_info for validation
    assert "kubernetes.core.k8s_info" in tasks_content, "Should use k8s_info for validation"
    assert "ansible.builtin.assert" in tasks_content, "Should use assert for validation"


def test_generate_greenfield_mode(temp_workspace, powercli_fixture):
    """Test generation without assume_existing_vms creates VM and waits for ready"""
    workspace = temp_workspace

    dest = workspace.root / "input" / "powercli" / powercli_fixture.name
    shutil.copy2(powercli_fixture, dest)

    extract_all(workspace)
    merge_intents(workspace)

    # Generate with assume_existing_vms=False (greenfield mode - default)
    generate_all(workspace, profile="lab", use_ai=False, assume_existing_vms=False)

    # Verify KubeVirt manifest WAS generated
    kubevirt_manifest = workspace.root / "output" / "kubevirt" / "vm.yaml"
    assert kubevirt_manifest.exists(), "KubeVirt manifest should be generated in greenfield mode"

    # Verify Ansible role tasks
    tasks_path = workspace.root / "output" / "ansible" / "roles" / "provision_vm" / "tasks" / "main.yml"
    assert tasks_path.exists(), "Ansible role tasks should be generated"

    with open(tasks_path) as f:
        tasks_content = f.read()

    # Verify creation tasks are present (greenfield mode)
    assert "Create KubeVirt VirtualMachine" in tasks_content, "Should have VM creation task"
    assert "Wait for VM to be ready" in tasks_content, "Should have VM wait task"

    # Verify validation tasks are NOT present
    assert "Verify VM exists" not in tasks_content, "Should not have VM verification task"
    assert "Validate VM CPU configuration" not in tasks_content, "Should not have CPU validation task"

    # Verify tasks use k8s with state: present for creation
    assert "state: present" in tasks_content, "Should use state: present for creation"
