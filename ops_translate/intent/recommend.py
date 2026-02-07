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
