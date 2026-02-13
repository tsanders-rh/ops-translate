"""Profile loading, validation, and management.

This module handles loading and validating Ansible translation profiles.
Profiles drive deterministic translation by providing explicit configuration
for external integrations and platform-specific components.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from jsonschema import ValidationError, validate
from jsonschema.exceptions import SchemaError

from ops_translate.models.profile import (
    ApprovalConfig,
    DNSConfig,
    EnvironmentConfig,
    IPAMConfig,
    ITSMConfig,
    NetworkSecurityConfig,
    ProfileSchema,
    StorageTierMapping,
)

# Get project root to find schema
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Module-level schema cache for performance
_SCHEMA_CACHE: dict[str, dict] = {}


def _load_profile_schema() -> dict:
    """
    Load and cache profile JSON schema.

    Returns:
        Parsed JSON schema as dict

    Raises:
        FileNotFoundError: If schema file doesn't exist
    """
    schema_name = "profile"
    if schema_name not in _SCHEMA_CACHE:
        schema_file = PROJECT_ROOT / "schema/profile.schema.json"
        if not schema_file.exists():
            raise FileNotFoundError(
                f"Profile schema file not found: {schema_file}\n"
                f"This indicates an incomplete installation. Please reinstall ops-translate:\n"
                f"  pip install --force-reinstall ops-translate"
            )
        _SCHEMA_CACHE[schema_name] = json.loads(schema_file.read_text())
    return _SCHEMA_CACHE[schema_name]


def validate_profile_schema(profile_data: dict) -> tuple[bool, list[str]]:
    """
    Validate profile data against JSON schema.

    Args:
        profile_data: Profile data as dict (from YAML)

    Returns:
        tuple: (is_valid, error_messages)
    """
    try:
        schema = _load_profile_schema()
        validate(instance=profile_data, schema=schema)
        return (True, [])
    except ValidationError as e:
        # Format validation error
        path = ".".join(str(p) for p in e.path) if e.path else "root"
        main_error = f"Profile validation error at '{path}': {e.message}"

        errors = [main_error]

        # Add context based on validator type
        if e.validator == "required":
            missing = e.message.split("'")[1::2]
            errors.append(f"  Required properties missing: {', '.join(missing)}")
        elif e.validator == "enum":
            if hasattr(e.validator_value, "__iter__"):
                errors.append(f"  Allowed values: {', '.join(str(v) for v in e.validator_value)}")
                errors.append(f"  Got: {e.instance}")
        elif e.validator == "type":
            errors.append(f"  Expected type: {e.validator_value}")
            errors.append(f"  Got: {type(e.instance).__name__}")

        return (False, errors)
    except SchemaError as e:
        return (False, [f"Invalid profile schema: {e}"])
    except FileNotFoundError as e:
        return (False, [str(e)])


def _parse_environment_config(data: dict) -> EnvironmentConfig:
    """Parse environment config from dict."""
    return EnvironmentConfig(
        openshift_api_url=data["openshift_api_url"],
        namespace=data.get("namespace"),
        node_selectors=data.get("node_selectors", {}),
    )


def _parse_approval_config(data: dict) -> ApprovalConfig:
    """Parse approval config from dict."""
    return ApprovalConfig(
        model=data["model"],
        endpoint=data.get("endpoint"),
        username_var=data.get("username_var"),
        password_var=data.get("password_var"),
    )


def _parse_network_security_config(data: dict) -> NetworkSecurityConfig:
    """Parse network security config from dict."""
    return NetworkSecurityConfig(
        model=data["model"],
        default_isolation=data.get("default_isolation", "namespace"),
    )


def _parse_itsm_config(data: dict) -> ITSMConfig:
    """Parse ITSM config from dict."""
    return ITSMConfig(
        provider=data["provider"],
        endpoint=data.get("endpoint"),
        username_var=data.get("username_var"),
        password_var=data.get("password_var"),
    )


def _parse_dns_config(data: dict) -> DNSConfig:
    """Parse DNS config from dict."""
    return DNSConfig(
        provider=data["provider"],
        endpoint=data.get("endpoint"),
        credentials_var=data.get("credentials_var"),
    )


def _parse_ipam_config(data: dict) -> IPAMConfig:
    """Parse IPAM config from dict."""
    return IPAMConfig(
        provider=data["provider"],
        endpoint=data.get("endpoint"),
        credentials_var=data.get("credentials_var"),
    )


def _parse_storage_tier_mapping(data: dict) -> StorageTierMapping:
    """Parse storage tier mapping from dict."""
    return StorageTierMapping(
        vmware_tier=data["vmware_tier"],
        openshift_storage_class=data["openshift_storage_class"],
    )


def load_profile(profile_file: Path) -> ProfileSchema:
    """
    Load and parse profile from YAML file.

    Args:
        profile_file: Path to profile YAML file

    Returns:
        ProfileSchema instance

    Raises:
        FileNotFoundError: If profile file doesn't exist
        ValueError: If profile validation fails
        yaml.YAMLError: If YAML parsing fails
    """
    if not profile_file.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_file}")

    # Load YAML
    profile_data = yaml.safe_load(profile_file.read_text())

    # Validate against schema
    is_valid, errors = validate_profile_schema(profile_data)
    if not is_valid:
        error_msg = "\n".join(errors)
        raise ValueError(f"Profile validation failed:\n{error_msg}")

    # Parse into dataclass
    environments = {
        name: _parse_environment_config(env_data)
        for name, env_data in profile_data.get("environments", {}).items()
    }

    approval = None
    if "approval" in profile_data:
        approval = _parse_approval_config(profile_data["approval"])

    network_security = None
    if "network_security" in profile_data:
        network_security = _parse_network_security_config(profile_data["network_security"])

    itsm = None
    if "itsm" in profile_data:
        itsm = _parse_itsm_config(profile_data["itsm"])

    dns = None
    if "dns" in profile_data:
        dns = _parse_dns_config(profile_data["dns"])

    ipam = None
    if "ipam" in profile_data:
        ipam = _parse_ipam_config(profile_data["ipam"])

    storage_tiers = []
    if "storage_tiers" in profile_data:
        storage_tiers = [
            _parse_storage_tier_mapping(tier_data) for tier_data in profile_data["storage_tiers"]
        ]

    return ProfileSchema(
        name=profile_data["name"],
        description=profile_data.get("description"),
        environments=environments,
        approval=approval,
        network_security=network_security,
        itsm=itsm,
        dns=dns,
        ipam=ipam,
        storage_tiers=storage_tiers,
        custom=profile_data.get("custom", {}),
    )


def _remove_none_values(data: Any) -> Any:
    """
    Recursively remove None values from nested dicts/lists.

    Args:
        data: Data structure to clean

    Returns:
        Cleaned data structure with None values removed
    """
    if isinstance(data, dict):
        return {k: _remove_none_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [_remove_none_values(item) for item in data if item is not None]
    else:
        return data


def save_profile(profile: ProfileSchema, profile_file: Path) -> None:
    """
    Save profile to YAML file.

    Args:
        profile: ProfileSchema instance to save
        profile_file: Path to output YAML file
    """
    # Convert dataclass to dict
    profile_dict = asdict(profile)

    # Remove None values recursively to avoid schema validation errors on reload
    profile_dict = _remove_none_values(profile_dict)

    # Write YAML
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile_file.write_text(yaml.dump(profile_dict, default_flow_style=False, sort_keys=False))


def validate_profile_completeness(profile: ProfileSchema) -> dict[str, list[str]]:
    """
    Validate profile completeness and identify missing optional configs.

    This function checks which optional profile sections are missing. Missing
    sections will result in BLOCKED adapter stubs during generation.

    Args:
        profile: ProfileSchema instance to validate

    Returns:
        dict: Mapping of section names to list of warnings
              Empty dict if profile is complete
    """
    warnings: dict[str, list[str]] = {}

    if profile.approval is None:
        warnings["approval"] = [
            "No approval configuration provided",
            "Workflows requiring approval will generate BLOCKED stubs",
            "Add approval section to enable: "
            "servicenow_change, aap_workflow, gitops_pr, manual_pause",
        ]

    if profile.network_security is None:
        warnings["network_security"] = [
            "No network security configuration provided",
            "NSX firewall rules will generate BLOCKED stubs",
            "Add network_security section to enable: calico, networkpolicy, cilium, istio",
        ]

    if profile.itsm is None:
        warnings["itsm"] = [
            "No ITSM configuration provided",
            "ServiceNow/Jira ticket creation will generate BLOCKED stubs",
            "Add itsm section to enable: servicenow, jira, manual",
        ]

    if profile.dns is None:
        warnings["dns"] = [
            "No DNS configuration provided",
            "DNS record creation will generate BLOCKED stubs",
            "Add dns section to enable: infoblox, externaldns, coredns",
        ]

    if profile.ipam is None:
        warnings["ipam"] = [
            "No IPAM configuration provided",
            "IP address allocation will generate BLOCKED stubs",
            "Add ipam section to enable: infoblox, whereabouts, static",
        ]

    if not profile.storage_tiers:
        warnings["storage_tiers"] = [
            "No storage tier mappings provided",
            "Storage tier assignments may use default storage class",
            "Add storage_tiers to map VMware tiers to OpenShift storage classes",
        ]

    return warnings


def merge_profile_with_decisions(
    profile: ProfileSchema,
    decisions_file: Path,
) -> ProfileSchema:
    """
    Merge profile with user decisions from interview.

    User decisions from the interview process can override or supplement
    profile configurations. This allows profiles to provide defaults while
    still respecting user choices.

    Args:
        profile: Base profile
        decisions_file: Path to decisions.json from interview

    Returns:
        Merged ProfileSchema with decisions applied

    Note:
        This is a placeholder for future implementation when decision
        interview integration is ready. Currently returns profile unchanged.
    """
    # TODO: Implement decision merging when interview integration is ready
    # For now, return profile unchanged
    return profile
