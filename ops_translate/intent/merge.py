"""
Intent merging logic.
Merges per-source intent files into a single intent.yaml.
"""
from pathlib import Path
from ops_translate.workspace import Workspace
import yaml


def merge_intents(workspace: Workspace) -> bool:
    """
    Merge per-source intent files into intent/intent.yaml.

    Returns:
        bool: True if conflicts were detected, False otherwise.
    """
    intent_dir = workspace.root / "intent"

    # Find all .intent.yaml files
    intent_files = list(intent_dir.glob("*.intent.yaml"))

    if not intent_files:
        raise FileNotFoundError("No intent files found to merge")

    # For now, just use the first intent file as base
    # TODO: Implement proper merging logic with conflict detection
    base_intent_file = intent_files[0]
    merged_intent = yaml.safe_load(base_intent_file.read_text())

    # Merge sources from all files
    all_sources = []
    for intent_file in intent_files:
        intent_data = yaml.safe_load(intent_file.read_text())
        all_sources.extend(intent_data.get('sources', []))

    merged_intent['sources'] = all_sources

    # Write merged intent
    output_file = workspace.root / "intent/intent.yaml"
    with open(output_file, 'w') as f:
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

    # Check for conflicts (simplified for now)
    conflicts = detect_conflicts(intent_files)

    if conflicts:
        conflicts_file = workspace.root / "intent/conflicts.md"
        conflicts_content = "# Intent Merge Conflicts\n\n" + "\n".join(conflicts)
        conflicts_file.write_text(conflicts_content)

    return bool(conflicts)


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
        intents.append({
            'file': intent_file.name,
            'data': intent_data
        })

    # Check workflow_name conflicts
    workflow_names = set()
    for intent in intents:
        wf_name = intent['data'].get('intent', {}).get('workflow_name')
        if wf_name:
            workflow_names.add((wf_name, intent['file']))

    if len(workflow_names) > 1:
        conflicts.append("## Workflow Name Conflict")
        conflicts.append("Different workflow names found:")
        for name, file in workflow_names:
            conflicts.append(f"- `{name}` (from {file})")
        conflicts.append("\n**Resolution:** Choose one workflow name or create separate workflows.\n")

    # Check workload_type conflicts
    workload_types = {}
    for intent in intents:
        wl_type = intent['data'].get('intent', {}).get('workload_type')
        if wl_type:
            if wl_type not in workload_types:
                workload_types[wl_type] = []
            workload_types[wl_type].append(intent['file'])

    if len(workload_types) > 1:
        conflicts.append("## Workload Type Conflict")
        conflicts.append("Different workload types found:")
        for wl_type, files in workload_types.items():
            file_list = ', '.join(files)
            conflicts.append(f"- `{wl_type}` (from {file_list})")
        conflicts.append("\n**Resolution:** Ensure all sources describe the same workload type or use 'mixed'.\n")

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
        inputs = intent['data'].get('intent', {}).get('inputs', {})
        for param_name, param_spec in inputs.items():
            if param_name not in all_inputs:
                all_inputs[param_name] = []
            all_inputs[param_name].append({
                'file': intent['file'],
                'spec': param_spec
            })

    # Check for conflicts in each parameter
    for param_name, specs in all_inputs.items():
        if len(specs) < 2:
            continue

        param_conflicts = []

        # Check for type conflicts
        types = set(spec['spec'].get('type') for spec in specs)
        if len(types) > 1:
            param_conflicts.append("**Type mismatch:**")
            for spec in specs:
                param_conflicts.append(f"- `{spec['spec'].get('type')}` (from {spec['file']})")

        # Check for required flag conflicts
        required_flags = set(spec['spec'].get('required') for spec in specs)
        if len(required_flags) > 1:
            param_conflicts.append("**Required flag mismatch:**")
            for spec in specs:
                param_conflicts.append(f"- `required={spec['spec'].get('required')}` (from {spec['file']})")

        # Check for default value conflicts
        defaults = {(str(spec['spec'].get('default')), spec['file']) for spec in specs if 'default' in spec['spec']}
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
        conflicts.append("\n**Resolution:** Reconcile parameter definitions or use different parameter names.\n")

    return conflicts


def _detect_governance_conflicts(intents: list) -> list:
    """Detect conflicts in governance policies."""
    conflicts = []
    has_header = False

    # Check approval requirements
    approval_specs = []
    for intent in intents:
        approval = intent['data'].get('intent', {}).get('governance', {}).get('approval', {})
        if approval:
            approval_specs.append({
                'file': intent['file'],
                'spec': approval
            })

    if len(approval_specs) > 1:
        # Check required_when conflicts
        required_when_specs = [spec for spec in approval_specs if 'required_when' in spec['spec']]
        if len(required_when_specs) > 1:
            conditions = set()
            for spec in required_when_specs:
                condition_str = str(spec['spec']['required_when'])
                conditions.add((condition_str, spec['file']))

            if len(conditions) > 1:
                if not has_header:
                    conflicts.append("## Governance Conflicts")
                    has_header = True
                conflicts.append("\n### Approval Requirement Mismatch")
                conflicts.append("Different approval conditions found:")
                for condition, file in conditions:
                    conflicts.append(f"- `{condition}` (from {file})")

        # Check approvers conflicts
        approver_specs = [spec for spec in approval_specs if 'approvers' in spec['spec']]
        if len(approver_specs) > 1:
            approver_lists = set()
            for spec in approver_specs:
                approver_list = tuple(sorted(spec['spec']['approvers']))
                approver_lists.add((str(approver_list), spec['file']))

            if len(approver_lists) > 1:
                if not has_header:
                    conflicts.append("## Governance Conflicts")
                    has_header = True
                conflicts.append("\n### Approver List Mismatch")
                conflicts.append("Different approver lists found:")
                for approvers, file in approver_lists:
                    conflicts.append(f"- `{approvers}` (from {file})")

    # Check quota conflicts
    quota_specs = []
    for intent in intents:
        quotas = intent['data'].get('intent', {}).get('governance', {}).get('quotas', {})
        if quotas:
            quota_specs.append({
                'file': intent['file'],
                'spec': quotas
            })

    if len(quota_specs) > 1:
        # Check each quota field
        for quota_field in ['max_cpu', 'max_memory_gb', 'max_storage_gb']:
            values = set()
            for spec in quota_specs:
                if quota_field in spec['spec']:
                    values.add((spec['spec'][quota_field], spec['file']))

            if len(values) > 1:
                if not has_header:
                    conflicts.append("## Governance Conflicts")
                    has_header = True
                conflicts.append(f"\n### Quota Mismatch: `{quota_field}`")
                conflicts.append("Different quota limits found:")
                for value, file in values:
                    conflicts.append(f"- `{value}` (from {file})")

    if conflicts:
        conflicts.append("\n**Resolution:** Use the most restrictive governance policy or create environment-specific profiles.\n")

    return conflicts


def _detect_compute_conflicts(intents: list) -> list:
    """Detect conflicts in compute resource specifications."""
    conflicts = []
    has_header = False

    compute_specs = []
    for intent in intents:
        compute = intent['data'].get('intent', {}).get('compute', {})
        if compute:
            compute_specs.append({
                'file': intent['file'],
                'spec': compute
            })

    if len(compute_specs) > 1:
        for field in ['cpu_cores', 'memory_gb', 'disk_gb']:
            values = set()
            for spec in compute_specs:
                if field in spec['spec']:
                    values.add((spec['spec'][field], spec['file']))

            if len(values) > 1:
                if not has_header:
                    conflicts.append("## Compute Resource Conflicts")
                    has_header = True
                conflicts.append(f"\n### `{field}` Mismatch")
                conflicts.append("Different resource specifications found:")
                for value, file in values:
                    conflicts.append(f"- `{value}` (from {file})")

    if conflicts:
        conflicts.append("\n**Resolution:** Choose one specification or make resources parameterized via inputs.\n")

    return conflicts


def _detect_profile_conflicts(intents: list) -> list:
    """Detect conflicts in environment profiles."""
    conflicts = []
    has_header = False

    # Collect all profiles
    all_profiles = {}
    for intent in intents:
        profiles = intent['data'].get('intent', {}).get('profiles', {})
        for profile_name, profile_value in profiles.items():
            if profile_name not in all_profiles:
                all_profiles[profile_name] = []
            all_profiles[profile_name].append({
                'file': intent['file'],
                'value': profile_value
            })

    # Check for conflicts
    for profile_name, values in all_profiles.items():
        if len(values) > 1:
            value_strs = set()
            for val in values:
                value_strs.add((str(val['value']), val['file']))

            if len(value_strs) > 1:
                if not has_header:
                    conflicts.append("## Profile Conflicts")
                    has_header = True
                conflicts.append(f"\n### Profile: `{profile_name}`")
                conflicts.append("Different values found:")
                for value_str, file in value_strs:
                    conflicts.append(f"- `{value_str}` (from {file})")

    if conflicts:
        conflicts.append("\n**Resolution:** Reconcile profile values or use conditional logic based on source.\n")

    return conflicts
