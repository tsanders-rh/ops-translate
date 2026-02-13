"""Profile schema dataclasses for Ansible translation configuration.

This module defines the profile structure used to drive deterministic translation
of vRealize workflows to Ansible. Profiles eliminate AI guessing for external
integrations by providing explicit configuration for NSX, ServiceNow, DNS, IPAM,
and other platform-specific components.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnvironmentConfig:
    """Configuration for a single target environment (dev, prod, etc.)."""

    openshift_api_url: str
    namespace: str | None = None
    node_selectors: dict[str, str] = field(default_factory=dict)


@dataclass
class ApprovalConfig:
    """Configuration for approval workflow handling.

    Supported models:
    - servicenow_change: Create ServiceNow change request
    - aap_workflow: Use Ansible Automation Platform workflow approval
    - gitops_pr: Create pull request for GitOps approval
    - manual_pause: Pause playbook for manual approval
    - blocked: No approval mechanism configured (generates BLOCKED stub)
    """

    model: str  # servicenow_change | aap_workflow | gitops_pr | manual_pause | blocked
    endpoint: str | None = None
    username_var: str | None = None
    password_var: str | None = None


@dataclass
class NetworkSecurityConfig:
    """Configuration for network security policy translation.

    Supported models:
    - calico: Use Calico NetworkPolicy
    - networkpolicy: Use standard Kubernetes NetworkPolicy
    - cilium: Use Cilium NetworkPolicy
    - istio: Use Istio AuthorizationPolicy
    - hybrid: Use multiple policy types
    - blocked: No network security configured (generates BLOCKED stub)
    """

    model: str  # calico | networkpolicy | cilium | istio | hybrid | blocked
    default_isolation: str = "namespace"  # namespace | pod | none


@dataclass
class ITSMConfig:
    """Configuration for ITSM (ServiceNow, Jira) integration.

    Supported providers:
    - servicenow: ServiceNow ITSM
    - jira: Atlassian Jira
    - manual: Manual ticketing (generates placeholder)
    """

    provider: str  # servicenow | jira | manual
    endpoint: str | None = None
    username_var: str | None = None
    password_var: str | None = None


@dataclass
class DNSConfig:
    """Configuration for DNS provider integration.

    Supported providers:
    - infoblox: Infoblox DDI
    - externaldns: Kubernetes ExternalDNS
    - coredns: CoreDNS with etcd backend
    - manual: Manual DNS management
    """

    provider: str  # infoblox | externaldns | coredns | manual
    endpoint: str | None = None
    credentials_var: str | None = None


@dataclass
class IPAMConfig:
    """Configuration for IPAM provider integration.

    Supported providers:
    - infoblox: Infoblox IPAM
    - whereabouts: Whereabouts CNI IPAM
    - static: Static IP allocation from profile
    """

    provider: str  # infoblox | whereabouts | static
    endpoint: str | None = None
    credentials_var: str | None = None


@dataclass
class StorageTierMapping:
    """Mapping from VMware storage tier to OpenShift storage class."""

    vmware_tier: str  # gold | silver | bronze
    openshift_storage_class: str


@dataclass
class ProfileSchema:
    """Complete profile schema for Ansible translation.

    Profiles drive deterministic translation by providing explicit mappings for
    external integrations and platform-specific configurations. Missing profile
    sections result in BLOCKED adapter stubs with guidance.
    """

    name: str
    description: str | None = None
    environments: dict[str, EnvironmentConfig] = field(default_factory=dict)
    approval: ApprovalConfig | None = None
    network_security: NetworkSecurityConfig | None = None
    itsm: ITSMConfig | None = None
    dns: DNSConfig | None = None
    ipam: IPAMConfig | None = None
    storage_tiers: list[StorageTierMapping] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)
