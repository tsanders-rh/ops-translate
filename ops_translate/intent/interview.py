"""
Decision Interview Module

Generates targeted questions for PARTIAL/EXPERT-GUIDED components to convert
ambiguity into explicit, versioned decisions that enable safer automation.

Key principles:
- Trust-first: No silent assumptions, questions are optional
- Targeted: 3-5 questions per component, not generic discovery
- Deterministic: Clear rules for how answers unlock automation
- Inline: Questions attached to specific gaps, not separate questionnaire
"""

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml

from ops_translate.intent.classify import ClassifiedComponent, TranslatabilityLevel


def generate_questions(
    components: list[ClassifiedComponent],
    workspace_path: Path | None = None,
) -> dict[str, Any]:
    """
    Generate targeted interview questions for PARTIAL/EXPERT-GUIDED components.

    Args:
        components: List of classified components from gap analysis
        workspace_path: Optional workspace path for context

    Returns:
        Question pack with schema version, generated timestamp, and questions

    Example:
        >>> components = [
        ...     ClassifiedComponent(
        ...         name="NSX Firewall",
        ...         level=TranslatabilityLevel.BLOCKED,
        ...         component_type="nsx_firewall",
        ...         ...
        ...     )
        ... ]
        >>> questions = generate_questions(components)
        >>> questions['questions'][0]['id']
        'nsx_firewall_equivalence'
    """
    questions = []

    # Generate questions only for PARTIAL/EXPERT-GUIDED/MANUAL components
    needs_interview = [
        c
        for c in components
        if c.level
        in (
            TranslatabilityLevel.PARTIAL,
            TranslatabilityLevel.BLOCKED,
            TranslatabilityLevel.MANUAL,
        )
    ]

    for component in needs_interview:
        component_questions = _generate_component_questions(component)
        questions.extend(component_questions)

    return {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "questions": questions,
    }


def _generate_component_questions(component: ClassifiedComponent) -> list[dict[str, Any]]:
    """
    Generate targeted questions for a specific component.

    Returns 3-5 sharp, decision-focused questions based on component type.

    Args:
        component: Classified component needing interview

    Returns:
        List of question dicts with id, prompt, options, impact statements
    """
    questions = []

    # Route to component-specific question generators
    if "nsx" in component.component_type.lower() and "firewall" in component.component_type.lower():
        questions.extend(_nsx_firewall_questions(component))
    elif (
        "nsx" in component.component_type.lower() and "segment" in component.component_type.lower()
    ):
        questions.extend(_nsx_segment_questions(component))
    elif "approval" in component.component_type.lower():
        questions.extend(_approval_questions(component))
    elif "rest" in component.component_type.lower() or "api" in component.component_type.lower():
        questions.extend(_api_call_questions(component))

    return questions


def _nsx_firewall_questions(component: ClassifiedComponent) -> list[dict[str, Any]]:
    """Generate questions for NSX firewall components."""
    return [
        {
            "id": f"nsx_firewall_equivalence_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "For firewall behavior, what level of equivalence is required?",
            "type": "single_choice",
            "options": [
                {
                    "value": "exact_nsx",
                    "label": "Exact NSX behavior required",
                    "impact": "Component stays EXPERT-GUIDED",
                },
                {
                    "value": "security_posture_equivalent",
                    "label": "Security posture equivalent acceptable",
                    "impact": "Enables PARTIAL automation with NetworkPolicy",
                },
                {
                    "value": "nonprod_best_effort",
                    "label": "Best-effort for non-production",
                    "impact": "Enables PARTIAL automation with warnings",
                },
            ],
            "default": "exact_nsx",
            "required": True,
        },
        {
            "id": f"nsx_firewall_scope_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "Where should network policies be enforced?",
            "type": "single_choice",
            "options": [
                {
                    "value": "namespace_only",
                    "label": "Namespace-scoped policies only",
                    "impact": "Safe for automation",
                },
                {
                    "value": "namespace_and_labels",
                    "label": "Namespace + label-based targeting",
                    "impact": "Recommended approach",
                },
                {
                    "value": "cluster_wide",
                    "label": "Cluster-wide policies",
                    "impact": "Requires architecture review (stays CUSTOM)",
                },
            ],
            "default": "namespace_and_labels",
            "required": True,
        },
        {
            "id": f"nsx_firewall_labels_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "Do workloads have stable labels for policy targeting?",
            "type": "single_choice",
            "options": [
                {
                    "value": "yes_existing",
                    "label": "Yes, existing label taxonomy",
                    "impact": "Enables NetworkPolicy generation",
                },
                {
                    "value": "yes_define_now",
                    "label": "Yes, can define labels now",
                    "impact": "Will generate recommended label schema",
                },
                {
                    "value": "no_unknown",
                    "label": "No or unknown",
                    "impact": "Cannot safely target policies (stays EXPERT-GUIDED)",
                },
            ],
            "default": "no_unknown",
            "required": True,
        },
    ]


def _nsx_segment_questions(component: ClassifiedComponent) -> list[dict[str, Any]]:
    """Generate questions for NSX segment/networking components."""
    return [
        {
            "id": f"nsx_segment_isolation_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "What level of network isolation is required?",
            "type": "single_choice",
            "options": [
                {
                    "value": "namespace_isolation",
                    "label": "Namespace-level isolation sufficient",
                    "impact": "Can use NetworkPolicy",
                },
                {
                    "value": "vlan_required",
                    "label": "VLAN-level isolation required",
                    "impact": "Requires Multus CNI (PARTIAL automation)",
                },
                {
                    "value": "microsegmentation",
                    "label": "Microsegmentation required",
                    "impact": "Requires NetworkPolicy + service mesh (EXPERT-GUIDED)",
                },
            ],
            "default": "namespace_isolation",
            "required": True,
        }
    ]


def _approval_questions(component: ClassifiedComponent) -> list[dict[str, Any]]:
    """Generate questions for approval workflow components."""
    return [
        {
            "id": f"approval_target_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "How should approvals be handled post-migration?",
            "type": "single_choice",
            "options": [
                {
                    "value": "aap_workflow",
                    "label": "Ansible Automation Platform workflow",
                    "impact": "Generates AAP workflow stub (PARTIAL)",
                },
                {
                    "value": "ticketing_gate",
                    "label": "Ticketing system integration (ServiceNow/Jira)",
                    "impact": "Generates integration placeholder (CUSTOM)",
                },
                {
                    "value": "manual_process",
                    "label": "Manual approval process",
                    "impact": "Generates documented manual step (PARTIAL)",
                },
                {
                    "value": "remove_approval",
                    "label": "Remove approval requirement",
                    "impact": "Component becomes SUPPORTED (requires confirmation)",
                },
            ],
            "default": "aap_workflow",
            "required": True,
        },
        {
            "id": f"approval_scope_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "When is approval required?",
            "type": "single_choice",
            "options": [
                {
                    "value": "prod_only",
                    "label": "Production only",
                    "impact": "Environment-conditional approval",
                },
                {
                    "value": "prod_and_stage",
                    "label": "Production and staging",
                    "impact": "Multi-environment approval",
                },
                {
                    "value": "all_envs",
                    "label": "All environments",
                    "impact": "Universal approval gate",
                },
            ],
            "default": "prod_only",
            "required": True,
        },
    ]


def _api_call_questions(component: ClassifiedComponent) -> list[dict[str, Any]]:
    """Generate questions for REST/API call components."""
    return [
        {
            "id": f"api_purpose_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "What is the purpose of the external API calls?",
            "type": "single_choice",
            "options": [
                {
                    "value": "metadata_only",
                    "label": "Metadata/status queries only",
                    "impact": "PARTIAL: scaffold uri tasks, low risk",
                },
                {
                    "value": "network_change",
                    "label": "Network configuration changes",
                    "impact": "CUSTOM: higher risk, requires owner",
                },
                {
                    "value": "provisioning_change",
                    "label": "Provisioning/state changes",
                    "impact": "CUSTOM: requires idempotency plan",
                },
            ],
            "default": "metadata_only",
            "required": True,
        },
        {
            "id": f"api_auth_{component.location}",
            "component": component.name,
            "component_type": component.component_type,
            "location": component.location,
            "prompt": "How should authentication be handled?",
            "type": "single_choice",
            "options": [
                {
                    "value": "token_env_var",
                    "label": "Token from environment variable",
                    "impact": "Simple, suitable for dev/test",
                },
                {
                    "value": "vault_secret",
                    "label": "HashiCorp Vault or Kubernetes Secret",
                    "impact": "Production-grade secret management",
                },
                {
                    "value": "unknown",
                    "label": "Unknown or undecided",
                    "impact": "Component stays CUSTOM",
                },
            ],
            "default": "vault_secret",
            "required": True,
        },
    ]


def apply_answers(
    answers_file: Path,
    components: list[ClassifiedComponent],
) -> dict[str, Any]:
    """
    Apply user answers to derive decisions and update component classifications.

    Args:
        answers_file: Path to intent/answers.yaml
        components: Original classified components

    Returns:
        Decisions dict with schema version, derived timestamp, and decisions

    Example:
        >>> answers_file = Path("intent/answers.yaml")
        >>> decisions = apply_answers(answers_file, components)
        >>> decisions['decisions']['nsx_firewall']['classification']
        'PARTIAL'
    """
    # Load answers
    with open(answers_file) as f:
        answers_data = cast(dict[str, Any], yaml.safe_load(f))

    answers = answers_data.get("answers", {})

    # Derive decisions using deterministic rules
    decisions = {
        "schema_version": 1,
        "derived_at": datetime.utcnow().isoformat() + "Z",
        "decisions": {},
    }

    for component in components:
        component_decisions = _derive_component_decisions(component, answers)
        if component_decisions:
            decisions["decisions"][component.location] = component_decisions

    return decisions


def _derive_component_decisions(
    component: ClassifiedComponent,
    answers: dict[str, str],
) -> dict[str, Any] | None:
    """
    Derive decisions for a specific component based on answers.

    Uses deterministic rules to determine:
    - New classification level
    - Automation enablement flags
    - Warnings and manual steps required

    Args:
        component: Original classified component
        answers: User-provided answers dict

    Returns:
        Component decision dict or None if no applicable answers
    """
    # Route to component-specific decision logic
    if "nsx" in component.component_type.lower() and "firewall" in component.component_type.lower():
        return _nsx_firewall_decisions(component, answers)
    elif (
        "nsx" in component.component_type.lower() and "segment" in component.component_type.lower()
    ):
        return _nsx_segment_decisions(component, answers)
    elif "approval" in component.component_type.lower():
        return _approval_decisions(component, answers)
    elif "rest" in component.component_type.lower() or "api" in component.component_type.lower():
        return _api_call_decisions(component, answers)

    return None


def _nsx_firewall_decisions(
    component: ClassifiedComponent,
    answers: dict[str, str],
) -> dict[str, Any]:
    """Derive decisions for NSX firewall components using deterministic rules."""
    equivalence_key = f"nsx_firewall_equivalence_{component.location}"
    scope_key = f"nsx_firewall_scope_{component.location}"
    labels_key = f"nsx_firewall_labels_{component.location}"

    equivalence = answers.get(equivalence_key, "exact_nsx")
    scope = answers.get(scope_key, "namespace_and_labels")
    labels = answers.get(labels_key, "no_unknown")

    # Deterministic rules
    if equivalence == "exact_nsx":
        # Keep EXPERT-GUIDED
        return {
            "classification": "EXPERT-GUIDED",
            "reason": "User requires exact NSX behavior",
            "enable_networkpolicy_generation": False,
            "warnings": ["Exact NSX equivalence not possible with NetworkPolicy"],
        }

    if labels == "no_unknown":
        # Cannot target policies without labels
        return {
            "classification": "EXPERT-GUIDED",
            "reason": "Cannot safely target policies without label taxonomy",
            "enable_networkpolicy_generation": False,
            "warnings": ["NetworkPolicy requires pod labels for targeting"],
        }

    if scope == "cluster_wide":
        # Needs architecture review
        return {
            "classification": "CUSTOM",
            "reason": "Cluster-wide policies need architecture review",
            "enable_networkpolicy_generation": False,
            "manual_steps_required": [
                "Review cluster-wide policy requirements",
                "Consider namespace-scoped approach",
            ],
        }

    # If we get here: security posture acceptable + labels available + namespace-scoped
    return {
        "classification": "PARTIAL",
        "reason": f"User accepts {equivalence} + has label taxonomy",
        "enable_networkpolicy_generation": True,
        "warnings": [
            "NetworkPolicy does not support L7 filtering",
            "Stateful behavior differs from NSX DFW",
        ],
    }


def _nsx_segment_decisions(
    component: ClassifiedComponent,
    answers: dict[str, str],
) -> dict[str, Any]:
    """Derive decisions for NSX segment components."""
    isolation_key = f"nsx_segment_isolation_{component.location}"
    isolation = answers.get(isolation_key, "namespace_isolation")

    if isolation == "namespace_isolation":
        return {
            "classification": "PARTIAL",
            "reason": "Namespace-level isolation acceptable",
            "enable_networkpolicy_generation": True,
        }
    elif isolation == "vlan_required":
        return {
            "classification": "PARTIAL",
            "reason": "VLAN isolation requires Multus CNI",
            "enable_multus_nad_generation": True,
            "manual_steps_required": [
                "Configure Multus CNI on cluster",
                "Define NetworkAttachmentDefinition",
            ],
        }
    else:  # microsegmentation
        return {
            "classification": "EXPERT-GUIDED",
            "reason": "Microsegmentation requires NetworkPolicy + service mesh",
            "manual_steps_required": [
                "Evaluate service mesh options (Istio, Linkerd)",
                "Design microsegmentation strategy",
            ],
        }


def _approval_decisions(
    component: ClassifiedComponent,
    answers: dict[str, str],
) -> dict[str, Any]:
    """Derive decisions for approval components."""
    target_key = f"approval_target_{component.location}"
    scope_key = f"approval_scope_{component.location}"

    target = answers.get(target_key, "aap_workflow")
    scope = answers.get(scope_key, "prod_only")

    if target == "aap_workflow":
        return {
            "classification": "PARTIAL",
            "reason": "User chose AAP workflow target",
            "generate_aap_scaffold": True,
            "approval_scope": scope,
            "manual_steps_required": [
                "Configure AAP workflow template",
                "Set up approval notifications",
            ],
        }
    elif target == "ticketing_gate":
        return {
            "classification": "CUSTOM",
            "reason": "Ticketing integration requires custom development",
            "approval_scope": scope,
            "manual_steps_required": [
                "Develop ServiceNow/Jira integration",
                "Configure API credentials",
                "Test approval flow",
            ],
        }
    elif target == "manual_process":
        return {
            "classification": "PARTIAL",
            "reason": "Manual approval process documented",
            "generate_manual_gate_docs": True,
            "approval_scope": scope,
        }
    else:  # remove_approval
        return {
            "classification": "SUPPORTED",
            "reason": "Approval requirement removed by user decision",
            "risk_accepted": True,
            "warnings": ["Approval gate removed - ensure governance compliance"],
        }


def _api_call_decisions(
    component: ClassifiedComponent,
    answers: dict[str, str],
) -> dict[str, Any]:
    """Derive decisions for API call components."""
    purpose_key = f"api_purpose_{component.location}"
    auth_key = f"api_auth_{component.location}"

    purpose = answers.get(purpose_key, "metadata_only")
    auth = answers.get(auth_key, "vault_secret")

    if purpose == "metadata_only" and auth != "unknown":
        return {
            "classification": "PARTIAL",
            "reason": "Metadata-only purpose + auth available",
            "generate_uri_tasks": True,
            "auth_method": auth,
        }
    elif purpose in ("network_change", "provisioning_change"):
        return {
            "classification": "CUSTOM",
            "reason": f"API changes ({purpose}) require specialist review",
            "auth_method": auth,
            "manual_steps_required": [
                "Review idempotency requirements",
                "Identify owner team (NetOps/AppOps)",
                "Validate API error handling",
            ],
        }
    else:
        return {
            "classification": "CUSTOM",
            "reason": "Insufficient information for automation",
            "manual_steps_required": ["Define API call requirements"],
        }


def save_questions(questions: dict[str, Any], output_file: Path) -> None:
    """Save generated questions to JSON file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        import json

        json.dump(questions, f, indent=2)


def save_decisions(decisions: dict[str, Any], output_file: Path) -> None:
    """Save derived decisions to YAML file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        yaml.dump(decisions, f, default_flow_style=False, sort_keys=False)


def load_decisions(decisions_file: Path) -> dict[str, Any] | None:
    """
    Load decisions from decisions.yaml file.

    Args:
        decisions_file: Path to intent/decisions.yaml

    Returns:
        Decisions dict or None if file doesn't exist

    Example:
        >>> decisions = load_decisions(Path("intent/decisions.yaml"))
        >>> if decisions:
        ...     print(decisions['decisions']['myworkflow']['classification'])
        'PARTIAL'
    """
    if not decisions_file.exists():
        return None

    with open(decisions_file) as f:
        return cast(dict[str, Any] | None, yaml.safe_load(f))


def apply_decisions_to_components(
    components: list[ClassifiedComponent],
    decisions: dict[str, Any],
) -> list[ClassifiedComponent]:
    """
    Apply decisions to reclassify components.

    Creates new ClassifiedComponent instances with updated classifications
    based on user decisions. Original components are not modified.

    Args:
        components: Original classified components
        decisions: Decisions dict from decisions.yaml

    Returns:
        New list of components with updated classifications

    Example:
        >>> decisions = load_decisions(Path("intent/decisions.yaml"))
        >>> updated = apply_decisions_to_components(components, decisions)
        >>> # Find the updated component
        >>> for comp in updated:
        ...     if comp.location == "myworkflow":
        ...         print(comp.level)
        TranslatabilityLevel.PARTIAL
    """
    if not decisions or "decisions" not in decisions:
        return components

    decision_map = decisions["decisions"]
    updated_components = []

    for component in components:
        # Check if there's a decision for this component
        if component.location in decision_map:
            decision = decision_map[component.location]
            new_classification = decision.get("classification")

            # Map string classification to TranslatabilityLevel enum
            level_map = {
                "SUPPORTED": TranslatabilityLevel.SUPPORTED,
                "PARTIAL": TranslatabilityLevel.PARTIAL,
                "EXPERT-GUIDED": TranslatabilityLevel.BLOCKED,
                "BLOCKED": TranslatabilityLevel.BLOCKED,  # Alias
                "CUSTOM": TranslatabilityLevel.MANUAL,
                "MANUAL": TranslatabilityLevel.MANUAL,  # Alias
            }

            if new_classification and new_classification in level_map:
                # Create new component with updated classification
                new_reason = decision.get("reason", component.reason)

                # Add decision-based notes to recommendations
                new_recommendations = (
                    list(component.recommendations) if component.recommendations else []
                )
                if decision.get("warnings"):
                    new_recommendations.insert(0, "⚠️ Decision-based warnings:")
                    for warning in decision["warnings"]:
                        new_recommendations.insert(1, f"  - {warning}")

                if decision.get("manual_steps_required"):
                    new_recommendations.append("Manual steps required:")
                    for step in decision["manual_steps_required"]:
                        new_recommendations.append(f"  - {step}")

                # Add decision metadata to evidence
                if component.evidence:
                    # Handle both string and list (for backward compatibility)
                    if isinstance(component.evidence, str):
                        new_evidence_list = component.evidence.split("\n")
                    else:
                        # Already a list (from older gaps.json)
                        new_evidence_list = list(component.evidence)
                else:
                    new_evidence_list = []
                new_evidence_list.append(
                    f"Decision applied: {new_classification} (from user answers)"
                )
                new_evidence = "\n".join(new_evidence_list)

                updated_component = ClassifiedComponent(
                    name=component.name,
                    component_type=component.component_type,
                    level=level_map[new_classification],
                    reason=new_reason,
                    openshift_equivalent=component.openshift_equivalent,
                    migration_path=component.migration_path,
                    location=component.location,
                    recommendations=new_recommendations,
                    evidence=new_evidence,
                )
                updated_components.append(updated_component)
            else:
                # No valid classification in decision, keep original
                updated_components.append(component)
        else:
            # No decision for this component, keep original
            updated_components.append(component)

    return updated_components
