"""
Intent merging logic.
Merges per-source intent files into a single intent.yaml.
"""

from pathlib import Path
from ops_translate.workspace import Workspace
import yaml


def merge_intents(workspace: Workspace) -> bool:
    """
    Merge per-source intent files into intent/intent.yaml using intelligent merge strategies.

    Returns:
        bool: True if conflicts were detected, False otherwise.
    """
    intent_dir = workspace.root / "intent"

    # Find all .intent.yaml files
    intent_files = list(intent_dir.glob("*.intent.yaml"))

    if not intent_files:
        raise FileNotFoundError("No intent files found to merge")

    # Load all intent data
    intents = []
    all_sources = []
    for intent_file in intent_files:
        intent_data = yaml.safe_load(intent_file.read_text())
        intents.append({"file": intent_file.name, "data": intent_data})
        all_sources.extend(intent_data.get("sources", []))

    # Perform smart merge
    merged_intent = smart_merge(intents)
    merged_intent["sources"] = all_sources

    # Write merged intent
    output_file = workspace.root / "intent/intent.yaml"
    with open(output_file, "w") as f:
        yaml.dump(merged_intent, f, default_flow_style=False, sort_keys=False)

    # Validate merged intent against schema
    from ops_translate.intent.validate import validate_intent
    from rich.console import Console

    console = Console()

    is_valid, errors = validate_intent(output_file)
    if not is_valid:
        console.print(f"[yellow]Warning: Merged intent validation failed:[/yellow]")
        for error in errors:
            console.print(f"[yellow]  {error}[/yellow]")
        console.print(f"[yellow]Merged intent written but may have schema issues.[/yellow]")
    else:
        console.print(f"[dim]✓ Merged intent schema validation passed[/dim]")

    # Check for conflicts
    conflicts = detect_conflicts(intent_files)

    if conflicts:
        conflicts_file = workspace.root / "intent/conflicts.md"
        conflicts_content = "# Intent Merge Conflicts\n\n" + "\n".join(conflicts)
        conflicts_file.write_text(conflicts_content)

    return bool(conflicts)


def smart_merge(intents: list) -> dict:
    """
    Intelligently merge multiple intent data structures.

    Uses smart strategies:
    - Workflow name: Use first, note if different
    - Workload type: Use 'mixed' if different types
    - Inputs: Merge and reconcile compatible parameters
    - Governance: Use most restrictive policies, combine approvers
    - Compute: Average or use max values
    - Profiles: Combine all profiles
    - Metadata: Union of tags and labels

    Args:
        intents: List of dicts with 'file' and 'data' keys

    Returns:
        dict: Merged intent data
    """
    merged = {"schema_version": 1, "intent": {}}

    # Merge workflow_name - use first non-null
    workflow_names = [
        i["data"].get("intent", {}).get("workflow_name")
        for i in intents
        if i["data"].get("intent", {}).get("workflow_name")
    ]
    if workflow_names:
        merged["intent"]["workflow_name"] = workflow_names[0]

    # Merge workload_type - use 'mixed' if different
    workload_types = set(
        i["data"].get("intent", {}).get("workload_type")
        for i in intents
        if i["data"].get("intent", {}).get("workload_type")
    )
    if len(workload_types) == 1:
        merged["intent"]["workload_type"] = list(workload_types)[0]
    elif len(workload_types) > 1:
        merged["intent"]["workload_type"] = "mixed"

    # Merge inputs - combine and reconcile
    merged_inputs = _merge_inputs(intents)
    if merged_inputs:
        merged["intent"]["inputs"] = merged_inputs

    # Merge governance - use most restrictive
    merged_governance = _merge_governance(intents)
    if merged_governance:
        merged["intent"]["governance"] = merged_governance

    # Merge compute - use maximum values
    merged_compute = _merge_compute(intents)
    if merged_compute:
        merged["intent"]["compute"] = merged_compute

    # Merge profiles - combine all
    merged_profiles = _merge_profiles(intents)
    if merged_profiles:
        merged["intent"]["profiles"] = merged_profiles

    # Merge metadata - union of tags/labels
    merged_metadata = _merge_metadata(intents)
    if merged_metadata:
        merged["intent"]["metadata"] = merged_metadata

    # Merge network - combine interfaces
    merged_network = _merge_network(intents)
    if merged_network:
        merged["intent"]["network"] = merged_network

    # Merge storage - combine volumes
    merged_storage = _merge_storage(intents)
    if merged_storage:
        merged["intent"]["storage"] = merged_storage

    # Merge day2_operations - union of supported ops
    merged_day2 = _merge_day2_operations(intents)
    if merged_day2:
        merged["intent"]["day2_operations"] = merged_day2

    return merged


def _merge_inputs(intents: list) -> dict:
    """Merge input parameters across intents."""
    all_inputs = {}

    for intent in intents:
        inputs = intent["data"].get("intent", {}).get("inputs", {})
        for param_name, param_spec in inputs.items():
            if param_name not in all_inputs:
                all_inputs[param_name] = param_spec
            else:
                # Reconcile parameter specs
                existing = all_inputs[param_name]

                # Use stricter type if conflict (prefer specific over generic)
                if existing.get("type") != param_spec.get("type"):
                    # Keep first type but note the conflict exists
                    pass

                # Required wins over optional
                if param_spec.get("required", False):
                    existing["required"] = True

                # Use first default if different
                if "default" in param_spec and "default" not in existing:
                    existing["default"] = param_spec["default"]

                # Merge enum values if both are enums
                if existing.get("type") == "enum" and param_spec.get("type") == "enum":
                    existing_values = set(existing.get("values", []))
                    new_values = set(param_spec.get("values", []))
                    existing["values"] = sorted(existing_values | new_values)

                # Use more restrictive min/max
                if "min" in param_spec:
                    existing["min"] = max(existing.get("min", param_spec["min"]), param_spec["min"])
                if "max" in param_spec:
                    existing["max"] = min(existing.get("max", param_spec["max"]), param_spec["max"])

                # Combine descriptions
                if param_spec.get("description") and param_spec["description"] != existing.get(
                    "description"
                ):
                    existing["description"] = existing.get("description", param_spec["description"])

    return all_inputs


def _merge_governance(intents: list) -> dict:
    """Merge governance policies - use most restrictive."""
    governance = {}

    # Merge approval policies
    all_approvals = [
        i["data"].get("intent", {}).get("governance", {}).get("approval", {})
        for i in intents
        if i["data"].get("intent", {}).get("governance", {}).get("approval")
    ]

    if all_approvals:
        approval = {}

        # Combine all required_when conditions (approval required if ANY condition matches)
        required_when_conditions = {}
        for appr in all_approvals:
            if "required_when" in appr:
                required_when_conditions.update(appr["required_when"])

        if required_when_conditions:
            approval["required_when"] = required_when_conditions

        # Combine all approvers (union)
        all_approvers = set()
        for appr in all_approvals:
            if "approvers" in appr:
                all_approvers.update(appr["approvers"])

        if all_approvers:
            approval["approvers"] = sorted(all_approvers)

        governance["approval"] = approval

    # Merge quotas - use most restrictive (minimum values)
    all_quotas = [
        i["data"].get("intent", {}).get("governance", {}).get("quotas", {})
        for i in intents
        if i["data"].get("intent", {}).get("governance", {}).get("quotas")
    ]

    if all_quotas:
        quotas = {}

        for quota_field in ["max_cpu", "max_memory_gb", "max_storage_gb"]:
            values = [q[quota_field] for q in all_quotas if quota_field in q]
            if values:
                quotas[quota_field] = min(values)  # Most restrictive

        governance["quotas"] = quotas

    return governance


def _merge_compute(intents: list) -> dict:
    """Merge compute resources - use maximum values."""
    compute = {}

    all_compute = [
        i["data"].get("intent", {}).get("compute", {})
        for i in intents
        if i["data"].get("intent", {}).get("compute")
    ]

    if all_compute:
        for field in ["cpu_cores", "memory_gb", "disk_gb"]:
            values = [c[field] for c in all_compute if field in c]
            if values:
                compute[field] = max(values)  # Use maximum

    return compute


def _merge_profiles(intents: list) -> dict:
    """Merge environment profiles - combine all."""
    profiles = {}

    for intent in intents:
        intent_profiles = intent["data"].get("intent", {}).get("profiles", {})
        for profile_name, profile_value in intent_profiles.items():
            if profile_name not in profiles:
                profiles[profile_name] = profile_value
            # If already exists and different, keep first one

    return profiles


def _merge_metadata(intents: list) -> dict:
    """Merge metadata - union of tags and labels."""
    metadata = {}

    # Merge tags - combine unique tags
    all_tags = []
    seen_keys = set()

    for intent in intents:
        tags = intent["data"].get("intent", {}).get("metadata", {}).get("tags", [])
        for tag in tags:
            tag_key = tag.get("key")
            if tag_key and tag_key not in seen_keys:
                all_tags.append(tag)
                seen_keys.add(tag_key)

    if all_tags:
        metadata["tags"] = all_tags

    # Merge labels - combine all unique labels
    all_labels = {}
    for intent in intents:
        labels = intent["data"].get("intent", {}).get("metadata", {}).get("labels", {})
        all_labels.update(labels)

    if all_labels:
        metadata["labels"] = all_labels

    return metadata


def _merge_network(intents: list) -> dict:
    """Merge network configuration - combine interfaces."""
    network = {}

    all_interfaces = []
    seen_names = set()

    for intent in intents:
        interfaces = intent["data"].get("intent", {}).get("network", {}).get("interfaces", [])
        for interface in interfaces:
            iface_name = interface.get("name")
            if iface_name and iface_name not in seen_names:
                all_interfaces.append(interface)
                seen_names.add(iface_name)

    if all_interfaces:
        network["interfaces"] = all_interfaces

    return network


def _merge_storage(intents: list) -> dict:
    """Merge storage configuration - combine volumes."""
    storage = {}

    all_volumes = []
    seen_names = set()

    for intent in intents:
        volumes = intent["data"].get("intent", {}).get("storage", {}).get("volumes", [])
        for volume in volumes:
            vol_name = volume.get("name")
            if vol_name and vol_name not in seen_names:
                all_volumes.append(volume)
                seen_names.add(vol_name)

    if all_volumes:
        storage["volumes"] = all_volumes

    return storage


def _merge_day2_operations(intents: list) -> dict:
    """Merge day2 operations - union of supported operations."""
    day2_ops = {}

    all_ops = set()
    for intent in intents:
        ops = intent["data"].get("intent", {}).get("day2_operations", {}).get("supported", [])
        all_ops.update(ops)

    if all_ops:
        day2_ops["supported"] = sorted(all_ops)

    return day2_ops


def detect_conflicts(intent_files: list) -> list:
    """
    Detect conflicts between intent files.

    Returns:
        list: List of conflict descriptions.
    """
    conflicts = []

    if len(intent_files) < 2:
        return conflicts

    # Load all intent data
    intents = []
    for intent_file in intent_files:
        intent_data = yaml.safe_load(intent_file.read_text())
        intents.append({"file": intent_file.name, "data": intent_data})

    # Check workflow_name conflicts
    workflow_names = {}
    for intent in intents:
        wf_name = intent["data"].get("intent", {}).get("workflow_name")
        if wf_name:
            if wf_name not in workflow_names:
                workflow_names[wf_name] = []
            workflow_names[wf_name].append(intent["file"])

    if len(workflow_names) > 1:
        conflicts.append("## Workflow Name Conflict")
        conflicts.append("Different workflow names found:")
        for name, files in workflow_names.items():
            file_list = ", ".join(files)
            conflicts.append(f"- `{name}` (from {file_list})")
        conflicts.append(
            "\n**Resolution:** Choose one workflow name or create separate workflows.\n"
        )

    # Check workload_type conflicts
    workload_types = {}
    for intent in intents:
        wl_type = intent["data"].get("intent", {}).get("workload_type")
        if wl_type:
            if wl_type not in workload_types:
                workload_types[wl_type] = []
            workload_types[wl_type].append(intent["file"])

    if len(workload_types) > 1:
        conflicts.append("## Workload Type Conflict")
        conflicts.append("Different workload types found:")
        for wl_type, files in workload_types.items():
            file_list = ", ".join(files)
            conflicts.append(f"- `{wl_type}` (from {file_list})")
        conflicts.append(
            "\n**Resolution:** Ensure all sources describe the same workload type or use 'mixed'.\n"
        )

    # Check input parameter conflicts
    input_conflicts = _detect_input_conflicts(intents)
    if input_conflicts:
        conflicts.extend(input_conflicts)

    # Check governance conflicts
    governance_conflicts = _detect_governance_conflicts(intents)
    if governance_conflicts:
        conflicts.extend(governance_conflicts)

    # Check compute resource conflicts
    compute_conflicts = _detect_compute_conflicts(intents)
    if compute_conflicts:
        conflicts.extend(compute_conflicts)

    # Check profile conflicts
    profile_conflicts = _detect_profile_conflicts(intents)
    if profile_conflicts:
        conflicts.extend(profile_conflicts)

    return conflicts


def _detect_input_conflicts(intents: list) -> list:
    """Detect conflicts in input parameters."""
    conflicts = []
    has_header = False

    # Collect all input parameters across intents
    all_inputs = {}
    for intent in intents:
        inputs = intent["data"].get("intent", {}).get("inputs", {})
        for param_name, param_spec in inputs.items():
            if param_name not in all_inputs:
                all_inputs[param_name] = []
            all_inputs[param_name].append({"file": intent["file"], "spec": param_spec})

    # Check for conflicts in each parameter
    for param_name, specs in all_inputs.items():
        if len(specs) < 2:
            continue

        param_conflicts = []

        # Check for type conflicts
        types = set(spec["spec"].get("type") for spec in specs)
        if len(types) > 1:
            param_conflicts.append("**Type mismatch:**")
            for spec in specs:
                param_conflicts.append(f"- `{spec['spec'].get('type')}` (from {spec['file']})")

        # Check for required flag conflicts
        required_flags = set(spec["spec"].get("required") for spec in specs)
        if len(required_flags) > 1:
            param_conflicts.append("**Required flag mismatch:**")
            for spec in specs:
                param_conflicts.append(
                    f"- `required={spec['spec'].get('required')}` (from {spec['file']})"
                )

        # Check for default value conflicts
        defaults = {
            (str(spec["spec"].get("default")), spec["file"])
            for spec in specs
            if "default" in spec["spec"]
        }
        if len(defaults) > 1:
            param_conflicts.append("**Default value mismatch:**")
            for default, file in defaults:
                param_conflicts.append(f"- `{default}` (from {file})")

        if param_conflicts:
            if not has_header:
                conflicts.append("## Input Parameter Conflicts")
                has_header = True
            conflicts.append(f"\n### Parameter: `{param_name}`")
            conflicts.extend(param_conflicts)

    if conflicts:
        conflicts.append(
            "\n**Resolution:** Reconcile parameter definitions or use different parameter names.\n"
        )

    return conflicts


def _detect_governance_conflicts(intents: list) -> list:
    """Detect conflicts in governance policies."""
    conflicts = []
    has_header = False

    # Check approval requirements
    approval_specs = []
    for intent in intents:
        approval = intent["data"].get("intent", {}).get("governance", {}).get("approval", {})
        if approval:
            approval_specs.append({"file": intent["file"], "spec": approval})

    if len(approval_specs) > 1:
        # Check required_when conflicts
        required_when_specs = [spec for spec in approval_specs if "required_when" in spec["spec"]]
        if len(required_when_specs) > 1:
            conditions = {}
            for spec in required_when_specs:
                condition_str = str(spec["spec"]["required_when"])
                if condition_str not in conditions:
                    conditions[condition_str] = []
                conditions[condition_str].append(spec["file"])

            if len(conditions) > 1:
                if not has_header:
                    conflicts.append("## Governance Conflicts")
                    has_header = True
                conflicts.append("\n### Approval Requirement Mismatch")
                conflicts.append("Different approval conditions found:")
                for condition, files in conditions.items():
                    file_list = ", ".join(files)
                    conflicts.append(f"- `{condition}` (from {file_list})")

        # Check approvers conflicts
        approver_specs = [spec for spec in approval_specs if "approvers" in spec["spec"]]
        if len(approver_specs) > 1:
            approver_lists = {}
            for spec in approver_specs:
                approver_list = tuple(sorted(spec["spec"]["approvers"]))
                approver_key = str(approver_list)
                if approver_key not in approver_lists:
                    approver_lists[approver_key] = []
                approver_lists[approver_key].append(spec["file"])

            if len(approver_lists) > 1:
                if not has_header:
                    conflicts.append("## Governance Conflicts")
                    has_header = True
                conflicts.append("\n### Approver List Mismatch")
                conflicts.append("Different approver lists found:")
                for approvers, files in approver_lists.items():
                    file_list = ", ".join(files)
                    conflicts.append(f"- `{approvers}` (from {file_list})")

    # Check quota conflicts
    quota_specs = []
    for intent in intents:
        quotas = intent["data"].get("intent", {}).get("governance", {}).get("quotas", {})
        if quotas:
            quota_specs.append({"file": intent["file"], "spec": quotas})

    if len(quota_specs) > 1:
        # Check each quota field
        for quota_field in ["max_cpu", "max_memory_gb", "max_storage_gb"]:
            values = {}
            for spec in quota_specs:
                if quota_field in spec["spec"]:
                    val = spec["spec"][quota_field]
                    if val not in values:
                        values[val] = []
                    values[val].append(spec["file"])

            if len(values) > 1:
                if not has_header:
                    conflicts.append("## Governance Conflicts")
                    has_header = True
                conflicts.append(f"\n### Quota Mismatch: `{quota_field}`")
                conflicts.append("Different quota limits found:")
                for value, files in values.items():
                    file_list = ", ".join(files)
                    conflicts.append(f"- `{value}` (from {file_list})")

    if conflicts:
        conflicts.append(
            "\n**Resolution:** Use the most restrictive governance policy or create environment-specific profiles.\n"
        )

    return conflicts


def _detect_compute_conflicts(intents: list) -> list:
    """Detect conflicts in compute resource specifications."""
    conflicts = []
    has_header = False

    compute_specs = []
    for intent in intents:
        compute = intent["data"].get("intent", {}).get("compute", {})
        if compute:
            compute_specs.append({"file": intent["file"], "spec": compute})

    if len(compute_specs) > 1:
        for field in ["cpu_cores", "memory_gb", "disk_gb"]:
            values = {}
            for spec in compute_specs:
                if field in spec["spec"]:
                    val = spec["spec"][field]
                    if val not in values:
                        values[val] = []
                    values[val].append(spec["file"])

            if len(values) > 1:
                if not has_header:
                    conflicts.append("## Compute Resource Conflicts")
                    has_header = True
                conflicts.append(f"\n### `{field}` Mismatch")
                conflicts.append("Different resource specifications found:")
                for value, files in values.items():
                    file_list = ", ".join(files)
                    conflicts.append(f"- `{value}` (from {file_list})")

    if conflicts:
        conflicts.append(
            "\n**Resolution:** Choose one specification or make resources parameterized via inputs.\n"
        )

    return conflicts


def _detect_profile_conflicts(intents: list) -> list:
    """Detect conflicts in environment profiles."""
    conflicts = []
    has_header = False

    # Collect all profiles
    all_profiles = {}
    for intent in intents:
        profiles = intent["data"].get("intent", {}).get("profiles", {})
        for profile_name, profile_value in profiles.items():
            if profile_name not in all_profiles:
                all_profiles[profile_name] = []
            all_profiles[profile_name].append({"file": intent["file"], "value": profile_value})

    # Check for conflicts
    for profile_name, values in all_profiles.items():
        if len(values) > 1:
            value_strs = set()
            for val in values:
                value_strs.add((str(val["value"]), val["file"]))

            if len(value_strs) > 1:
                if not has_header:
                    conflicts.append("## Profile Conflicts")
                    has_header = True
                conflicts.append(f"\n### Profile: `{profile_name}`")
                conflicts.append("Different values found:")
                for value_str, file in value_strs:
                    conflicts.append(f"- `{value_str}` (from {file})")

    if conflicts:
        conflicts.append(
            "\n**Resolution:** Reconcile profile values or use conditional logic based on source.\n"
        )

    return conflicts
