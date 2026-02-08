"""
Expert-guided recommendations for non-auto-translatable components.

This module provides structured recommendations and implementation guidance for
workflow components that cannot be safely auto-migrated (PARTIAL, BLOCKED, MANUAL).

The goal is not to auto-migrate unsupported logic, but to:
- Provide clear, expert-backed guidance
- Generate safe Ansible scaffolding
- Help customers understand what to build next and how
- Preserve ops-translate's trust-first, non-magical stance
"""

from enum import Enum
from typing import Any, NamedTuple


class OwnerRole(Enum):
    """Recommended team or role for implementing a recommendation."""

    NETOPS = "NetOps"
    SECOPS = "SecOps"
    PLATFORM = "Platform Team"
    APPOPS = "AppOps"
    CUSTOM = "Custom Development"

    def __str__(self) -> str:
        return self.value


class Recommendation(NamedTuple):
    """
    Structured expert guidance for implementing a non-auto-translatable component.

    This represents domain expertise encoded as actionable guidance, not a
    claim of feature parity or behavioral equivalence.

    Attributes:
        component_name: Name of the classified component
        component_type: Type of component (e.g., "nsx_firewall", "approval_workflow")
        reason_not_auto_translatable: Why this cannot be safely auto-migrated
        ansible_approach: Recommended Ansible implementation approach
        openshift_primitives: Suggested OpenShift/Kubernetes resources to use
        implementation_steps: Ordered list of implementation steps
        required_inputs: Variables/parameters needed for implementation
        testing_guidance: How to validate the implementation
        owner: Suggested team/role for implementation
        references: Links to docs, examples, or related issues
        ansible_role_stub: Optional Ansible role name to generate stub for
        ansible_todo_task: Optional TODO task to add to generated playbook

    Example:
        >>> rec = Recommendation(
        ...     component_name="NSX Distributed Firewall",
        ...     component_type="nsx_firewall",
        ...     reason_not_auto_translatable="NSX DFW has L7 filtering and stateful...",
        ...     ansible_approach="Use kubernetes.core.k8s to create NetworkPolicy...",
        ...     openshift_primitives=["NetworkPolicy", "Calico GlobalNetworkPolicy"],
        ...     implementation_steps=["Define allow-list policies", "Convert rules..."],
        ...     required_inputs={"firewall_rules": "List of NSX firewall rules..."},
        ...     testing_guidance="Test with pod-to-pod traffic...",
        ...     owner=OwnerRole.NETOPS,
        ...     references=["https://docs.openshift.com/container-platform/.../network_policy"],
        ...     ansible_role_stub="custom_nsx_firewall_migration",
        ...     ansible_todo_task="# TODO: Review and implement NSX firewall migration"
        ... )
    """

    component_name: str
    component_type: str
    reason_not_auto_translatable: str
    ansible_approach: str
    openshift_primitives: list[str]
    implementation_steps: list[str]
    required_inputs: dict[str, str]  # {var_name: description}
    testing_guidance: str
    owner: OwnerRole
    references: list[str] | None = None
    ansible_role_stub: str | None = None
    ansible_todo_task: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with enum values converted to strings
        """
        return {
            "component_name": self.component_name,
            "component_type": self.component_type,
            "reason_not_auto_translatable": self.reason_not_auto_translatable,
            "ansible_approach": self.ansible_approach,
            "openshift_primitives": self.openshift_primitives,
            "implementation_steps": self.implementation_steps,
            "required_inputs": self.required_inputs,
            "testing_guidance": self.testing_guidance,
            "owner": self.owner.value,
            "references": self.references or [],
            "ansible_role_stub": self.ansible_role_stub,
            "ansible_todo_task": self.ansible_todo_task,
        }

    def to_markdown(self) -> str:
        """
        Generate markdown documentation for this recommendation.

        Returns:
            Formatted markdown string suitable for recommendations.md
        """
        lines = [
            f"## {self.component_name}",
            "",
            f"**Component Type:** `{self.component_type}`  ",
            f"**Owner:** {self.owner.value}  ",
            "",
            "### Why Not Auto-Translatable",
            "",
            self.reason_not_auto_translatable,
            "",
            "### Recommended Ansible Approach",
            "",
            self.ansible_approach,
            "",
            "### OpenShift/Kubernetes Primitives",
            "",
        ]

        for primitive in self.openshift_primitives:
            lines.append(f"- `{primitive}`")

        lines.extend(["", "### Implementation Steps", ""])

        for i, step in enumerate(self.implementation_steps, 1):
            lines.append(f"{i}. {step}")

        lines.extend(["", "### Required Inputs", ""])

        if self.required_inputs:
            for var_name, description in self.required_inputs.items():
                lines.append(f"- `{var_name}`: {description}")
        else:
            lines.append("_No specific inputs required_")

        lines.extend(["", "### Testing & Validation", "", self.testing_guidance, ""])

        if self.references:
            lines.extend(["### References", ""])
            for ref in self.references:
                lines.append(f"- {ref}")
            lines.append("")

        if self.ansible_role_stub:
            lines.extend(
                [
                    "### Ansible Scaffolding",
                    "",
                    f"A role stub has been generated at: `roles/{self.ansible_role_stub}/`",
                    "",
                ]
            )

        lines.append("---")
        lines.append("")

        return "\n".join(lines)


class RecommendationEngine:
    """
    Base class for generating expert recommendations for classified components.

    Subclasses should implement pattern-specific recommendation logic for
    different types of components (NSX, approval workflows, etc.).
    """

    @staticmethod
    def generate_nsx_firewall_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for NSX distributed firewall rules.

        Args:
            component_name: Name of the firewall component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for NetworkPolicy migration
        """
        return Recommendation(
            component_name=component_name,
            component_type="nsx_firewall",
            reason_not_auto_translatable=(
                "NSX Distributed Firewall provides L7 filtering, stateful inspection, "
                "and micro-segmentation features that cannot be directly mapped to "
                "Kubernetes NetworkPolicy. Auto-translation would lose critical security "
                "enforcement and create a false sense of equivalence."
            ),
            ansible_approach=(
                "Use `kubernetes.core.k8s` module to create NetworkPolicy resources "
                "with an allow-list approach. For advanced requirements, consider "
                "Calico GlobalNetworkPolicy or OpenShift Egress Firewall."
            ),
            openshift_primitives=[
                "NetworkPolicy (Kubernetes native)",
                "EgressFirewall (OpenShift)",
                "GlobalNetworkPolicy (Calico)",
            ],
            implementation_steps=[
                "Analyze NSX firewall rules to extract source/destination patterns",
                "Define Kubernetes label taxonomy for pod selectors",
                "Create NetworkPolicy manifests with allow-list ingress/egress rules",
                "Document unsupported features (L7, stateful inspection) for NetOps review",
                "Test policies in dev environment with realistic traffic patterns",
                "Implement monitoring for policy violations and denied connections",
            ],
            required_inputs={
                "firewall_rules": "List of NSX firewall rules with source/dest/port/protocol",
                "namespace": "Target namespace for NetworkPolicy",
                "pod_labels": "Label selectors for affected pods",
            },
            testing_guidance=(
                "Test with pod-to-pod traffic in dev cluster. Verify both allowed and "
                "denied traffic. Use `kubectl exec` to test connectivity between pods. "
                "Monitor CNI logs for policy enforcement. Compare behavior against NSX "
                "firewall logs to identify gaps."
            ),
            owner=OwnerRole.NETOPS,
            references=[
                "https://docs.openshift.com/container-platform/latest/networking/network_policy/about-network-policy.html",
                "https://kubernetes.io/docs/concepts/services-networking/network-policies/",
                "https://docs.tigera.io/calico/latest/network-policy/",
            ],
            ansible_role_stub="custom_nsx_firewall_migration",
            ansible_todo_task=(
                "# TODO: Implement NSX firewall migration to NetworkPolicy\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_nsx_security_group_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for NSX security groups (dynamic membership).

        Args:
            component_name: Name of the security group component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for label-based policy migration
        """
        return Recommendation(
            component_name=component_name,
            component_type="nsx_security_group",
            reason_not_auto_translatable=(
                "NSX Security Groups support dynamic membership based on VM tags, "
                "network properties, and complex criteria. Kubernetes uses label selectors "
                "which are fundamentally different. Auto-translation cannot safely map "
                "dynamic NSX group membership to static label selectors without "
                "NetOps/SecOps review."
            ),
            ansible_approach=(
                "Define a Kubernetes label taxonomy that represents security zones and "
                "application tiers. Use Ansible to apply labels to workloads based on "
                "the NSX group membership criteria. Reference labels in NetworkPolicy "
                "selectors."
            ),
            openshift_primitives=[
                "Pod Labels",
                "Namespace Labels",
                "NetworkPolicy podSelector/namespaceSelector",
            ],
            implementation_steps=[
                "Document NSX security group membership rules and criteria",
                "Design Kubernetes label taxonomy (e.g., security.zone, app.tier)",
                "Map NSX group membership to label assignments",
                "Create Ansible tasks to label namespaces and workloads",
                "Update NetworkPolicy to reference label selectors",
                "Require NetOps/SecOps sign-off on label taxonomy and policy mapping",
            ],
            required_inputs={
                "security_groups": "List of NSX security groups with membership rules",
                "label_taxonomy": "Proposed Kubernetes label schema",
                "workload_inventory": "List of workloads and their security requirements",
            },
            testing_guidance=(
                "Validate label assignments match intended security group membership. "
                "Test NetworkPolicy enforcement with labeled pods. Review with SecOps "
                "to ensure security boundaries are maintained. Document any gaps in "
                "enforcement compared to NSX."
            ),
            owner=OwnerRole.SECOPS,
            references=[
                "https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/",
                "https://docs.openshift.com/container-platform/latest/networking/network_policy/about-network-policy.html",
            ],
            ansible_role_stub="custom_nsx_security_groups",
            ansible_todo_task=(
                "# TODO: Implement NSX security group to label migration\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# Requires NetOps/SecOps review of label taxonomy\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_approval_workflow_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
        complexity: str = "simple",
    ) -> Recommendation:
        """
        Generate recommendation for approval/governance workflows.

        Args:
            component_name: Name of the approval workflow
            location: Source location (file:line)
            evidence: Supporting evidence from source
            complexity: Complexity level ("simple", "medium", "complex")

        Returns:
            Structured recommendation for workflow migration
        """
        if complexity == "complex":
            ansible_approach = (
                "Implement approval workflow using Ansible Automation Platform (AAP) "
                "workflow templates with approval nodes. Integrate with external "
                "ticketing systems (ServiceNow, Jira) via REST API for enterprise "
                "approval processes."
            )
            implementation_steps = [
                "Map vRealize approval logic to AAP workflow template",
                "Identify approval decision points and escalation paths",
                "Configure AAP approval nodes with timeout and notification settings",
                "Integrate with external ticketing system via REST API",
                "Implement approval notification channels (email, Slack, etc.)",
                "Test approval workflow with realistic scenarios (approval, rejection, timeout)",
                "Document approval SLAs and escalation procedures",
            ]
            role_stub = "custom_complex_approval_workflow"
        else:
            ansible_approach = (
                "Implement simple approval using Ansible Automation Platform workflow "
                "templates with approval nodes, or use manual intervention tasks with "
                "`pause` module for basic approval gates."
            )
            implementation_steps = [
                "Identify approval requirements and decision criteria",
                "Create AAP workflow template with approval node",
                "Configure approval notification (email, webhook, etc.)",
                "Implement fallback logic for approval timeout",
                "Test approval and rejection scenarios",
            ]
            role_stub = "custom_approval_workflow"

        return Recommendation(
            component_name=component_name,
            component_type="approval_workflow",
            reason_not_auto_translatable=(
                "Approval workflows involve human decision-making, organizational "
                "processes, and external system integrations that cannot be automatically "
                "translated. Each organization has different approval requirements, "
                "SLAs, and escalation procedures that require process redesign."
            ),
            ansible_approach=ansible_approach,
            openshift_primitives=[
                "Ansible Automation Platform Workflow Templates",
                "AAP Approval Nodes",
                "External ticketing integration (ServiceNow/Jira)",
            ],
            implementation_steps=implementation_steps,
            required_inputs={
                "approval_criteria": "Decision criteria for approval (e.g., environment, cost)",
                "approvers": "List of approver roles or email addresses",
                "timeout_minutes": "Approval timeout before auto-rejection or escalation",
                "notification_channels": "How to notify approvers (email, Slack, etc.)",
            },
            testing_guidance=(
                "Test approval workflow with various scenarios: immediate approval, "
                "immediate rejection, timeout, and (if applicable) escalation. Verify "
                "notifications are sent correctly. Validate that rejected requests do not "
                "proceed with provisioning."
            ),
            owner=OwnerRole.PLATFORM,
            references=[
                "https://docs.ansible.com/automation-controller/latest/html/userguide/workflow_templates.html",
                "https://docs.ansible.com/automation-controller/latest/html/userguide/workflow_templates.html#approval-nodes",
            ],
            ansible_role_stub=role_stub,
            ansible_todo_task=(
                "# TODO: Implement approval workflow\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# This is a process redesign, not a syntax translation\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_rest_api_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for REST API / HTTP calls.

        Args:
            component_name: Name of the API call component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for Ansible uri module usage
        """
        return Recommendation(
            component_name=component_name,
            component_type="rest_api",
            reason_not_auto_translatable=(
                "REST API calls involve custom endpoints, authentication mechanisms, "
                "and payload formats that cannot be automatically translated without "
                "knowing the API contract. Each API has different retry, idempotency, "
                "and error handling requirements."
            ),
            ansible_approach=(
                "Use `ansible.builtin.uri` module to make HTTP requests. Implement "
                "proper authentication (token, basic, OAuth), retries, and idempotency "
                "checks. Handle errors gracefully and provide meaningful failure messages."
            ),
            openshift_primitives=[
                "N/A (External API integration)",
            ],
            implementation_steps=[
                "Document API endpoint URL, method, headers, and payload format",
                "Identify authentication requirements (API key, token, OAuth, etc.)",
                "Implement Ansible uri task with proper auth and headers",
                "Add retry logic with exponential backoff for transient failures",
                "Implement idempotency check (e.g., GET before POST to check if exists)",
                "Handle error responses with meaningful failure messages",
                "Test with API in dev/staging environment",
            ],
            required_inputs={
                "api_url": "Full URL of the API endpoint",
                "http_method": "HTTP method (GET, POST, PUT, DELETE, etc.)",
                "auth_type": "Authentication type (bearer, basic, api_key, oauth)",
                "payload": "Request body/payload (for POST/PUT)",
                "expected_status_codes": "List of success status codes (e.g., [200, 201])",
            },
            testing_guidance=(
                "Test API calls in dev environment. Verify authentication works. "
                "Test error scenarios (404, 401, 500) and ensure graceful handling. "
                "Validate idempotency by running playbook multiple times. "
                "Check retry logic by simulating transient failures."
            ),
            owner=OwnerRole.CUSTOM,
            references=[
                "https://docs.ansible.com/ansible/latest/collections/ansible/builtin/uri_module.html",
            ],
            ansible_role_stub="custom_api_integration",
            ansible_todo_task=(
                "# TODO: Implement REST API integration\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_vm_template_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for VM template/customization operations.

        Args:
            component_name: Name of the template component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for KubeVirt template migration
        """
        return Recommendation(
            component_name=component_name,
            component_type="vm_template",
            reason_not_auto_translatable=(
                "VM templates with custom guest customization, sysprep scripts, and "
                "post-deployment configuration require manual review. Template "
                "specifications, hardware versions, and customization logic must be "
                "carefully mapped to KubeVirt/cloud-init equivalents."
            ),
            ansible_approach=(
                "Create KubeVirt VirtualMachine templates with cloud-init for guest "
                "customization. Use Ansible to manage template lifecycle and inject "
                "runtime configuration. Convert sysprep/customization specs to cloud-init "
                "user-data and meta-data."
            ),
            openshift_primitives=[
                "VirtualMachine (KubeVirt)",
                "VirtualMachineInstanceTemplate",
                "ConfigMap (cloud-init data)",
                "Secret (sensitive data)",
            ],
            implementation_steps=[
                "Document VM template specifications (CPU, memory, disk, network)",
                "Extract guest customization requirements (hostname, IP, scripts, etc.)",
                "Convert customization specs to cloud-init format (user-data, meta-data)",
                "Create KubeVirt VirtualMachine template with appropriate resources",
                "Store cloud-init data in ConfigMap or Secret",
                "Test template instantiation and guest customization in dev cluster",
                "Validate post-boot configuration matches source template behavior",
            ],
            required_inputs={
                "template_name": "Name of the VM template",
                "vm_specs": "CPU, memory, disk size specifications",
                "customization_spec": "Guest customization requirements (cloud-init format)",
                "base_image": "Container disk image or DataVolume source",
            },
            testing_guidance=(
                "Test VM creation from template. Verify cloud-init customization runs "
                "correctly (check /var/log/cloud-init.log). Validate network configuration, "
                "hostname, and any post-boot scripts. Compare final VM state against "
                "source template expectations."
            ),
            owner=OwnerRole.PLATFORM,
            references=[
                "https://kubevirt.io/user-guide/virtual_machines/templates/",
                "https://cloudinit.readthedocs.io/en/latest/",
                "https://docs.openshift.com/container-platform/latest/virt/virtual_machines/creating_vms_custom/virt-creating-vms-from-templates.html",
            ],
            ansible_role_stub="custom_vm_template",
            ansible_todo_task=(
                "# TODO: Implement VM template migration to KubeVirt\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_storage_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for storage/volume operations.

        Args:
            component_name: Name of the storage component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for storage migration
        """
        return Recommendation(
            component_name=component_name,
            component_type="storage",
            reason_not_auto_translatable=(
                "Storage operations involve datastore selection, storage policies, and "
                "provisioning logic that require platform-specific decisions. Storage "
                "classes, access modes, and volume types must be mapped based on target "
                "infrastructure capabilities."
            ),
            ansible_approach=(
                "Use kubernetes.core.k8s module to create PersistentVolumeClaim resources "
                "with appropriate storage class and access mode. For VM disks, use KubeVirt "
                "DataVolume with CDI (Containerized Data Importer) for image conversion."
            ),
            openshift_primitives=[
                "PersistentVolumeClaim",
                "StorageClass",
                "DataVolume (KubeVirt CDI)",
                "VolumeSnapshot",
            ],
            implementation_steps=[
                "Identify storage requirements (size, performance tier, access mode)",
                "Map source datastore/storage policy to target storage class",
                "Create PersistentVolumeClaim or DataVolume manifest",
                "Configure appropriate access mode (ReadWriteOnce, ReadWriteMany)",
                "Implement volume attachment to VirtualMachine or Pod",
                "Plan data migration strategy if existing data needs transfer",
                "Test provisioning and I/O performance in target environment",
            ],
            required_inputs={
                "storage_size": "Required storage capacity (e.g., 100Gi)",
                "storage_class": "Target storage class name",
                "access_mode": "Volume access mode (ReadWriteOnce, ReadWriteMany, ReadOnlyMany)",
                "volume_mode": "Filesystem or Block",
            },
            testing_guidance=(
                "Test PVC creation and binding. Verify storage class provisions volume correctly. "
                "Test volume attachment to VM/pod. Run I/O benchmarks to validate performance. "
                "Test volume expansion if dynamic resizing is required."
            ),
            owner=OwnerRole.PLATFORM,
            references=[
                "https://docs.openshift.com/container-platform/latest/storage/understanding-persistent-storage.html",
                "https://kubevirt.io/user-guide/virtual_machines/disks_and_volumes/",
                "https://kubevirt.io/user-guide/operations/containerized_data_importer/",
            ],
            ansible_role_stub="custom_storage",
            ansible_todo_task=(
                "# TODO: Implement storage provisioning\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_custom_plugin_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for custom plugins/actions.

        Args:
            component_name: Name of the custom plugin
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for custom logic migration
        """
        return Recommendation(
            component_name=component_name,
            component_type="custom_plugin",
            reason_not_auto_translatable=(
                "Custom plugins and actions contain organization-specific business logic "
                "that cannot be automatically translated. Each plugin must be analyzed "
                "individually to understand its purpose, dependencies, and integration points."
            ),
            ansible_approach=(
                "Reimplement custom logic as Ansible modules, roles, or playbook tasks. "
                "For complex logic, consider wrapping in a custom Python module or REST "
                "API service that Ansible can invoke via uri or custom module."
            ),
            openshift_primitives=[
                "Job (Kubernetes)",
                "CronJob (scheduled tasks)",
                "Custom Ansible modules",
                "REST API integration",
            ],
            implementation_steps=[
                "Document plugin purpose, inputs, outputs, and dependencies",
                "Identify external systems or APIs the plugin interacts with",
                "Extract core business logic and determine if reimplementation is needed",
                "Design Ansible-native equivalent (task, role, module, or external service)",
                "Implement and test logic in isolation",
                "Integrate with workflow and validate end-to-end behavior",
                "Document any behavioral differences or limitations",
            ],
            required_inputs={
                "plugin_code": "Source code or pseudocode of plugin logic",
                "dependencies": "External systems, APIs, or libraries required",
                "inputs": "Plugin input parameters and types",
                "outputs": "Expected outputs and side effects",
            },
            testing_guidance=(
                "Test plugin logic with representative inputs. Validate outputs match "
                "expected behavior. Test error handling and edge cases. Verify integration "
                "with dependent systems. Compare behavior against original plugin."
            ),
            owner=OwnerRole.CUSTOM,
            references=[
                "https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html",
                "https://kubernetes.io/docs/concepts/workloads/controllers/job/",
            ],
            ansible_role_stub="custom_plugin",
            ansible_todo_task=(
                "# TODO: Implement custom plugin logic\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# This requires analysis of original plugin code\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_credentials_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for credential/authentication operations.

        Args:
            component_name: Name of the credential component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for credential migration
        """
        return Recommendation(
            component_name=component_name,
            component_type="credentials",
            reason_not_auto_translatable=(
                "Credential management involves sensitive data and organization-specific "
                "security policies. Credentials must be migrated using secure methods "
                "appropriate for the target platform (Secrets, external vaults, etc.)."
            ),
            ansible_approach=(
                "Store credentials in Kubernetes Secrets or integrate with external secret "
                "management (HashiCorp Vault, AWS Secrets Manager, etc.). Use Ansible Vault "
                "for encrypting sensitive playbook variables. Rotate credentials post-migration."
            ),
            openshift_primitives=[
                "Secret (Kubernetes)",
                "ServiceAccount",
                "External Secrets Operator",
                "HashiCorp Vault integration",
            ],
            implementation_steps=[
                "Identify all credential types (passwords, API keys, certificates, SSH keys)",
                "Determine credential usage patterns and dependencies",
                "Choose appropriate secret storage (Kubernetes Secret, external vault)",
                "Migrate credentials using secure transfer method (no plaintext storage)",
                "Update application/workflow to reference new secret storage",
                "Implement credential rotation policy",
                "Test authentication with new credential storage",
                "Revoke/rotate old credentials after successful migration",
            ],
            required_inputs={
                "credential_types": "Types of credentials (password, API key, certificate, etc.)",
                "secret_names": "Kubernetes Secret names for each credential",
                "access_scope": "Which services/pods need access to each credential",
            },
            testing_guidance=(
                "Test that applications can retrieve credentials from Secrets. Verify proper "
                "RBAC prevents unauthorized access. Test credential rotation procedure. "
                "Validate authentication works with migrated credentials. Confirm old credentials "
                "are revoked and no longer work."
            ),
            owner=OwnerRole.SECOPS,
            references=[
                "https://kubernetes.io/docs/concepts/configuration/secret/",
                "https://docs.openshift.com/container-platform/latest/nodes/pods/nodes-pods-secrets.html",
                "https://www.vaultproject.io/docs/platform/k8s",
                "https://external-secrets.io/",
            ],
            ansible_role_stub="custom_credentials",
            ansible_todo_task=(
                "# TODO: Migrate credentials securely\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# SECURITY: Never commit plaintext credentials\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_notification_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for email/notification operations.

        Args:
            component_name: Name of the notification component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for notification migration
        """
        return Recommendation(
            component_name=component_name,
            component_type="notification",
            reason_not_auto_translatable=(
                "Notification logic involves SMTP configuration, email templates, and "
                "organization-specific notification channels. Email sending requires "
                "integration with mail servers or notification services."
            ),
            ansible_approach=(
                "Use ansible.builtin.mail module for simple email notifications, or integrate "
                "with notification services (Slack, PagerDuty, Teams). For complex templates, "
                "use Jinja2 templates and REST API integrations."
            ),
            openshift_primitives=[
                "Job (for async notifications)",
                "Webhook integrations",
                "External notification services",
            ],
            implementation_steps=[
                "Identify notification triggers and recipients",
                "Document notification content and templates",
                "Configure SMTP relay or notification service credentials",
                "Implement Ansible mail task or webhook integration",
                "Create notification templates with dynamic content",
                "Test notification delivery and formatting",
                "Implement error handling for notification failures",
            ],
            required_inputs={
                "smtp_host": "SMTP server hostname (if using email)",
                "recipients": "Notification recipients (email addresses, channels)",
                "subject_template": "Subject line template",
                "body_template": "Message body template",
            },
            testing_guidance=(
                "Test email delivery to actual recipients. Verify formatting and dynamic "
                "content rendering. Test with failure scenarios to ensure error handling. "
                "Validate notification timing and triggers. Check spam filters don't block messages."
            ),
            owner=OwnerRole.APPOPS,
            references=[
                "https://docs.ansible.com/ansible/latest/collections/community/general/mail_module.html",
                "https://docs.ansible.com/ansible/latest/collections/ansible/builtin/uri_module.html",
            ],
            ansible_role_stub="custom_notifications",
            ansible_todo_task=(
                "# TODO: Implement notification integration\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )

    @staticmethod
    def generate_database_recommendation(
        component_name: str,
        location: str | None = None,
        evidence: str | None = None,
    ) -> Recommendation:
        """
        Generate recommendation for database operations.

        Args:
            component_name: Name of the database component
            location: Source location (file:line)
            evidence: Supporting evidence from source

        Returns:
            Structured recommendation for database integration
        """
        return Recommendation(
            component_name=component_name,
            component_type="database",
            reason_not_auto_translatable=(
                "Database operations require connection details, schema knowledge, and "
                "query logic specific to the database type. SQL queries, schema changes, "
                "and data manipulation must be reviewed for correctness and security."
            ),
            ansible_approach=(
                "Use Ansible database modules (postgresql, mysql, mongodb, etc.) for schema "
                "and data operations. Store connection details in Secrets. Use transactions "
                "and error handling for data integrity."
            ),
            openshift_primitives=[
                "Secret (database credentials)",
                "Service (database endpoint)",
                "StatefulSet (if hosting database in cluster)",
            ],
            implementation_steps=[
                "Document database type, connection details, and required operations",
                "Store database credentials in Kubernetes Secret",
                "Implement Ansible tasks using appropriate database module",
                "Add idempotency checks (verify before insert/update)",
                "Implement transaction handling and rollback logic",
                "Test with representative data in dev environment",
                "Validate data integrity and query performance",
            ],
            required_inputs={
                "db_type": "Database type (postgresql, mysql, mongodb, etc.)",
                "db_host": "Database hostname or service name",
                "db_name": "Database name",
                "db_credentials": "Secret containing username/password",
                "operations": "List of database operations (query, insert, update, delete)",
            },
            testing_guidance=(
                "Test database connectivity and authentication. Validate queries return expected "
                "results. Test idempotency by running tasks multiple times. Verify transaction "
                "rollback on errors. Test with edge cases and invalid data. Monitor for SQL injection vulnerabilities."
            ),
            owner=OwnerRole.APPOPS,
            references=[
                "https://docs.ansible.com/ansible/latest/collections/community/postgresql/",
                "https://docs.ansible.com/ansible/latest/collections/community/mysql/",
                "https://docs.ansible.com/ansible/latest/collections/community/mongodb/",
            ],
            ansible_role_stub="custom_database",
            ansible_todo_task=(
                "# TODO: Implement database integration\n"
                f"# Source: {location or 'unknown'}\n"
                f"# Evidence: {evidence or 'See gap analysis report'}\n"
                "# SECURITY: Use parameterized queries to prevent SQL injection\n"
                "# Review intent/recommendations.md for implementation guidance"
            ),
        )


def generate_recommendations_from_components(
    components: list,
) -> list[Recommendation]:
    """
    Generate structured recommendations from classified components.

    This function maps ClassifiedComponent instances to Recommendation instances,
    providing detailed implementation guidance for PARTIAL, BLOCKED, and MANUAL
    components.

    Args:
        components: List of ClassifiedComponent instances

    Returns:
        List of Recommendation objects for components requiring manual work
    """
    from ops_translate.intent.classify import TranslatabilityLevel

    recommendations = []

    for component in components:
        # Only generate recommendations for components that need manual work
        if component.level == TranslatabilityLevel.SUPPORTED:
            continue

        # Generate recommendation based on component type
        rec = None

        # NSX components
        if "nsx" in component.component_type:
            if (
                "firewall" in component.component_type
                or "distributed_firewall" in component.component_type
            ):
                rec = RecommendationEngine.generate_nsx_firewall_recommendation(
                    component_name=component.name,
                    location=component.location,
                    evidence=component.evidence,
                )
            elif "security_group" in component.component_type:
                rec = RecommendationEngine.generate_nsx_security_group_recommendation(
                    component_name=component.name,
                    location=component.location,
                    evidence=component.evidence,
                )

        # Approval workflows
        elif "approval" in component.component_type:
            # Determine complexity from component type
            complexity = "simple"
            if "complex" in component.component_type:
                complexity = "complex"
            elif "medium" in component.component_type:
                complexity = "medium"

            rec = RecommendationEngine.generate_approval_workflow_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
                complexity=complexity,
            )

        # REST API calls
        elif "rest" in component.component_type or "api" in component.component_type:
            rec = RecommendationEngine.generate_rest_api_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
            )

        # VM templates
        elif "template" in component.component_type or "customization" in component.component_type:
            rec = RecommendationEngine.generate_vm_template_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
            )

        # Storage operations
        elif (
            "storage" in component.component_type
            or "datastore" in component.component_type
            or "disk" in component.component_type
            or "volume" in component.component_type
        ):
            rec = RecommendationEngine.generate_storage_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
            )

        # Custom plugins/actions
        elif (
            "plugin" in component.component_type
            or "custom_action" in component.component_type
            or "script" in component.component_type
        ):
            rec = RecommendationEngine.generate_custom_plugin_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
            )

        # Credentials/authentication
        elif (
            "credential" in component.component_type
            or "auth" in component.component_type
            or "secret" in component.component_type
        ):
            rec = RecommendationEngine.generate_credentials_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
            )

        # Email/notifications
        elif (
            "email" in component.component_type
            or "notification" in component.component_type
            or "mail" in component.component_type
        ):
            rec = RecommendationEngine.generate_notification_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
            )

        # Database operations
        elif (
            "database" in component.component_type
            or "db" in component.component_type
            or "sql" in component.component_type
        ):
            rec = RecommendationEngine.generate_database_recommendation(
                component_name=component.name,
                location=component.location,
                evidence=component.evidence,
            )

        if rec:
            recommendations.append(rec)

    return recommendations


def generate_recommendations_markdown(recommendations: list[Recommendation]) -> str:
    """
    Generate complete recommendations.md file from a list of recommendations.

    Args:
        recommendations: List of Recommendation objects

    Returns:
        Complete markdown document with header and all recommendations
    """
    if not recommendations:
        return (
            "# Expert-Guided Migration Recommendations\n\n"
            "_No recommendations generated - all components are fully supported._\n"
        )

    lines = [
        "# Expert-Guided Migration Recommendations",
        "",
        "This document provides expert guidance for workflow components that cannot be "
        "safely auto-migrated.",
        "",
        "**Important**: These are recommendations, not drop-in replacements. Each "
        "recommendation requires review, testing, and validation before production use.",
        "",
        "## Summary",
        "",
        f"Total recommendations: {len(recommendations)}",
        "",
    ]

    # Group by owner role
    from collections import defaultdict

    by_owner = defaultdict(list)
    for rec in recommendations:
        by_owner[rec.owner].append(rec)

    lines.append("### By Team")
    lines.append("")
    for owner, recs in sorted(by_owner.items(), key=lambda x: x[0].value):
        lines.append(f"- **{owner.value}**: {len(recs)} recommendation(s)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Add each recommendation
    for rec in recommendations:
        lines.append(rec.to_markdown())

    return "\n".join(lines)


def generate_recommendations_json(recommendations: list[Recommendation]) -> str:
    """
    Generate JSON representation of recommendations.

    Args:
        recommendations: List of Recommendation objects

    Returns:
        JSON string
    """
    import json

    data = {
        "total_recommendations": len(recommendations),
        "recommendations": [rec.to_dict() for rec in recommendations],
    }

    return json.dumps(data, indent=2)
