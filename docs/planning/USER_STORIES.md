# ops-translate User Stories and Use Cases

## Document Overview

This document provides comprehensive user stories and use cases for ops-translate, an AI-assisted migration tool that bridges VMware automation (PowerCLI scripts and vRealize Orchestrator workflows) to OpenShift Virtualization. Stories are organized by current capabilities and future considerations.

**Version**: v1 Prototype
**Last Updated**: 2026-02-16
**Status**: Evaluation and proof-of-concept tool

---

## Table of Contents

1. [User Personas](#user-personas)
2. [Current State User Stories](#current-state-user-stories)
3. [Future Considerations](#future-considerations)
4. [Success Metrics](#success-metrics)
5. [Non-Functional Requirements](#non-functional-requirements)

---

## User Personas

### Primary Personas

**P1: Migration Architect (Maya)**
- **Role**: Technical lead for VMware to OpenShift migration
- **Responsibilities**: Assessment, planning, risk evaluation
- **Goals**: Understand migration complexity, identify gaps, create migration roadmap
- **Technical Level**: Expert in both VMware and Kubernetes
- **Primary Concern**: Completeness and accuracy of migration analysis

**P2: Platform Engineer (Paulo)**
- **Role**: Hands-on engineer executing the migration
- **Responsibilities**: Converting scripts, testing playbooks, deploying to OpenShift
- **Goals**: Accelerate conversion work, maintain operational intent, reduce errors
- **Technical Level**: Strong Ansible/Kubernetes, learning VMware automation
- **Primary Concern**: Quality and reliability of generated artifacts

**P3: Operations Team Lead (Olivia)**
- **Role**: Manager of day-to-day VM operations
- **Responsibilities**: Provisioning VMs, enforcing policies, maintaining automation
- **Goals**: Minimize disruption during migration, preserve operational workflows
- **Technical Level**: VMware expert, limited Kubernetes exposure
- **Primary Concern**: Continuity of service delivery during transition

**P4: Application Owner (Adrian)**
- **Role**: Business stakeholder with VMs running applications
- **Responsibilities**: Application uptime, compliance, change approvals
- **Goals**: Understand impact to applications, approve migration plans
- **Technical Level**: Business-focused, limited infrastructure knowledge
- **Primary Concern**: Risk to application availability and compliance

### Secondary Personas

**S1: Security Engineer (Samira)**
- **Role**: Infrastructure security specialist
- **Responsibilities**: Network policies, compliance, vulnerability management
- **Goals**: Ensure security posture maintains or improves post-migration
- **Technical Level**: Deep security expertise, moderate infrastructure
- **Primary Concern**: Network segmentation and access control equivalence

**S2: Executive Sponsor (Eric)**
- **Role**: VP/Director funding the migration
- **Responsibilities**: Budget allocation, strategic decisions, stakeholder management
- **Goals**: Understand ROI, timeline, and business risk
- **Technical Level**: High-level technical understanding
- **Primary Concern**: Cost, timeline predictability, and business justification

---

## Current State User Stories

### Epic 1: Migration Assessment and Discovery

#### Story 1.1: Inventory Existing Automation
**As a** Migration Architect (Maya)
**I want to** import all PowerCLI scripts and vRealize workflows from my VMware environment
**So that** I have a complete inventory of automation that needs migration

**Acceptance Criteria:**
- Can import individual PowerCLI `.ps1` files
- Can import individual vRealize workflow `.xml` files
- Can import entire directories with mixed file types
- Can import vRealize `.package` and `.zip` bundles with auto-extraction
- System auto-detects file types and generates manifest
- Import is read-only and safe (no modifications to source files)

**Technical Details:**
- Command: `ops-translate import --source powercli --file <path>` or `--dir <path>`
- Supports both vRealize and PowerCLI sources
- Handles vRealize action index resolution
- Generates `manifest.json` with metadata

**Current Capability**: ✅ Fully Supported

---

#### Story 1.2: Understand Automation Complexity
**As a** Migration Architect (Maya)
**I want to** receive a static analysis summary of imported automation
**So that** I can understand the scope and complexity before investing in detailed analysis

**Acceptance Criteria:**
- Summary includes file count, line count, parameter count
- Identifies key VMware cmdlets and operations used
- Detects control flow complexity (conditionals, loops)
- Highlights vRealize workflow structure (tasks, decisions, approvals)
- Lists detected integrations (NSX, ServiceNow, IPAM, etc.)
- No LLM API calls required (fast, free operation)
- Output in human-readable markdown format

**Technical Details:**
- Command: `ops-translate summarize`
- Generates `intent/summary.md`
- Uses AST parsing for PowerCLI
- Uses XML parsing for vRealize workflows
- Identifies approval workflow items, event subscriptions, custom plugins

**Current Capability**: ✅ Fully Supported

---

#### Story 1.3: Extract Operational Intent with AI
**As a** Platform Engineer (Paulo)
**I want to** extract the normalized operational intent from VMware automation using AI
**So that** the semantic meaning and business logic is preserved in a platform-agnostic format

**Acceptance Criteria:**
- Supports Claude (Anthropic) and GPT (OpenAI) providers
- Extracts parameters with types, defaults, validation rules
- Identifies environment-specific branching logic (dev/prod)
- Captures resource requirements (CPU, memory, storage, network)
- Detects tagging and metadata operations
- Logs all AI assumptions in `intent/assumptions.md`
- Can operate with mock provider for testing without API costs
- Handles rate limiting and retries gracefully

**Technical Details:**
- Command: `ops-translate intent extract`
- Outputs `intent/*.intent.yaml` files (one per source)
- Uses configurable LLM provider (anthropic, openai, mock)
- Recommended model: `claude-sonnet-4-5`
- Typical cost: $0.01-0.30 per extraction depending on complexity

**Current Capability**: ✅ Fully Supported

---

#### Story 1.4: Generate Migration Readiness Report
**As an** Executive Sponsor (Eric)
**I want to** view an interactive HTML report showing migration readiness
**So that** I can understand feasibility, effort, and risks before approving the project

**Acceptance Criteria:**
- Professional HTML interface with visual dashboard
- Executive summary with key metrics (translatability percentage, effort estimate)
- 4-tab progressive disclosure: Overview, Source Files, Components, Expert Guidance
- Classification breakdown (SUPPORTED, PARTIAL, BLOCKED, MANUAL)
- Gap analysis with specific migration paths for unsupported features
- Expert recommendations organized by team (Platform, Network, Security, Application)
- Interactive filtering and search
- Export capability to PDF or CSV
- No external dependencies (single self-contained HTML file)

**Technical Details:**
- Command: `ops-translate report`
- Generates `report/index.html`
- Uses intent classification and gap analysis
- Includes specific OpenShift equivalents for VMware features
- Provides decision interview capability for PARTIAL/BLOCKED items

**Current Capability**: ✅ Fully Supported

**Example Metrics:**
- 31 components analyzed across 8 source files
- 65% fully automated (SUPPORTED)
- 20% requires configuration (PARTIAL)
- 10% requires decisions (BLOCKED)
- 5% requires custom development (MANUAL)

---

### Epic 2: Intent Management and Conflict Resolution

#### Story 2.1: Merge Multiple Automation Sources
**As a** Platform Engineer (Paulo)
**I want to** merge intent from multiple PowerCLI scripts and vRealize workflows
**So that** I have a single consolidated view of VM provisioning requirements

**Acceptance Criteria:**
- Combines multiple `*.intent.yaml` files into single `intent.yaml`
- Detects conflicts (e.g., different CPU counts for same parameter)
- Reports conflicts in `intent/conflicts.md` with line-by-line comparison
- Provides conflict resolution strategies
- Can force merge with `--force` flag for acceptable conflicts
- Preserves all source metadata for traceability

**Technical Details:**
- Command: `ops-translate intent merge`
- Conflict detection for parameters, tasks, requirements
- Uses deep dictionary merging with conflict tracking
- Outputs consolidated `intent/intent.yaml`

**Current Capability**: ✅ Fully Supported

---

#### Story 2.2: Validate Intent Against Schema
**As a** Platform Engineer (Paulo)
**I want to** validate my intent files against the schema before generation
**So that** I can catch errors early and ensure correct structure

**Acceptance Criteria:**
- Validates all intent YAML files against intent schema
- Reports schema violations with specific file, line, and error description
- Validates referenced resources exist (storage classes, networks, etc.)
- Fast operation (no API calls)
- Clear actionable error messages

**Technical Details:**
- Command: `ops-translate dry-run`
- JSON Schema validation
- Checks for required fields, correct types, valid enumerations
- Validates cross-references between intent elements

**Current Capability**: ✅ Fully Supported

---

#### Story 2.3: Interactive Decision Interview
**As a** Migration Architect (Maya)
**I want to** answer targeted questions about components classified as PARTIAL or BLOCKED
**So that** the tool can generate more complete artifacts with my domain knowledge

**Acceptance Criteria:**
- Interactive command-line interview for missing context
- Questions organized by component and classification
- Supports multiple choice, text input, and yes/no questions
- Example questions:
  - "What OpenShift network should VMware 'Production-VLAN-100' map to?"
  - "What storage class should be used for high-performance workloads?"
  - "Is manual approval required for production VM provisioning?"
- Saves answers to intent for regeneration
- Can re-run interview to update answers

**Technical Details:**
- Command: `ops-translate intent interview-generate` (create questions)
- Command: `ops-translate intent interview-apply` (apply answers to intent)
- Question templates based on gap analysis and classification
- Answers stored in intent YAML with metadata

**Current Capability**: ✅ Fully Supported

---

### Epic 3: Artifact Generation and Deployment

#### Story 3.1: Generate Ansible Playbooks and KubeVirt Manifests
**As a** Platform Engineer (Paulo)
**I want to** generate production-ready Ansible playbooks and KubeVirt manifests
**So that** I can provision VMs on OpenShift with the same operational intent as VMware

**Acceptance Criteria:**
- Generates valid KubeVirt `VirtualMachine` manifests in `output/kubevirt/`
- Generates Ansible playbooks with proper role structure in `output/ansible/`
- Includes all parameters with correct types and validation
- Translates environment branching to Ansible conditionals
- Maps VMware resources to OpenShift equivalents:
  - Resource pools → quotas and resource requests
  - Networks → NetworkAttachmentDefinitions
  - Datastores → StorageClasses
  - Templates → containerDisks, PVCs, or HTTP sources
- Includes comprehensive README with deployment instructions
- Supports multiple profiles (lab, staging, prod)

**Technical Details:**
- Command: `ops-translate generate --profile lab`
- Output format: YAML (default), JSON, Kustomize, ArgoCD
- Uses Jinja2 templates with intent data
- Can operate with `--no-ai` for deterministic template-only generation
- Includes `output/ansible/LOCKING_SETUP.md` for distributed locking configuration

**Current Capability**: ✅ Fully Supported

---

#### Story 3.2: Multi-Environment with Kustomize
**As a** Platform Engineer (Paulo)
**I want to** generate Kustomize overlays for dev, staging, and production
**So that** I can use GitOps to manage environment-specific configurations

**Acceptance Criteria:**
- Generates `base/` with common resources
- Generates `overlays/dev/`, `overlays/staging/`, `overlays/prod/`
- Environment-specific resource adjustments:
  - Dev: 2 CPU, 2Gi RAM, standard storage
  - Staging: 2 CPU, 4Gi RAM, standard storage
  - Prod: 4 CPU, 8Gi RAM, high-performance storage
- Valid kustomization.yaml in each directory
- Can apply with `kubectl apply -k output/overlays/prod`

**Technical Details:**
- Command: `ops-translate generate --format kustomize`
- Environment profiles defined in `ops-translate.yaml`
- Automatic resource patching via Kustomize
- Namespace customization per environment

**Current Capability**: ✅ Fully Supported

---

#### Story 3.3: ArgoCD GitOps Integration
**As a** Platform Engineer (Paulo)
**I want to** generate ArgoCD Application manifests
**So that** I can manage VM deployments with continuous delivery

**Acceptance Criteria:**
- Generates Kustomize structure (base + overlays)
- Generates ArgoCD `AppProject` in `output/argocd/project.yaml`
- Generates Application manifests per environment:
  - `dev-application.yaml`: automated sync with prune
  - `staging-application.yaml`: automated sync, no prune (safety)
  - `prod-application.yaml`: manual sync (full control)
- Applications point to correct Git repository and overlay paths
- Includes sync policies, health checks, and retry logic

**Technical Details:**
- Command: `ops-translate generate --format argocd`
- Requires Git repository URL in config
- ArgoCD 2.x compatible
- Supports automated and manual sync policies

**Current Capability**: ✅ Fully Supported

---

#### Story 3.4: Ansible Lint Integration
**As a** Platform Engineer (Paulo)
**I want to** automatically lint generated Ansible playbooks
**So that** I ensure best practices and catch common errors

**Acceptance Criteria:**
- Runs ansible-lint on all generated playbooks
- Reports warnings and errors with file locations
- Supports `--lint-strict` mode to treat warnings as errors
- Uses standard ansible-lint ruleset
- Only runs if ansible-lint is installed (graceful skip otherwise)

**Technical Details:**
- Command: `ops-translate generate --lint`
- Command: `ops-translate generate --lint-strict` (for CI/CD)
- Executes `ansible-lint` subprocess
- Returns non-zero exit code on lint failures in strict mode

**Current Capability**: ✅ Fully Supported

---

### Epic 4: Post-Migration and Day-2 Operations

#### Story 4.1: MTV Mode - Validate Existing VMs
**As an** Operations Team Lead (Olivia)
**I want to** generate validation playbooks for VMs already migrated via MTV
**So that** I can verify they match operational requirements and apply governance

**Acceptance Criteria:**
- Generates Ansible playbooks that verify VM existence instead of creating VMs
- Includes assertions for:
  - VM exists in specified namespace
  - CPU count matches requirements
  - Memory allocation matches requirements
  - Network configuration is correct
  - Storage volumes are attached
- Applies tags and labels as needed
- Reports configuration drift

**Technical Details:**
- Command: `ops-translate generate --assume-existing-vms`
- Global config: `assume_existing_vms: true` in `ops-translate.yaml`
- Uses `k8s_info` module instead of `kubevirt_vm`
- Generates validation assertions instead of creation tasks

**Current Capability**: ✅ Fully Supported

**Use Case**: Organization migrated 500 VMs using MTV, wants to apply governance and validation from legacy PowerCLI scripts

---

#### Story 4.2: Event-Driven Ansible Rulebooks
**As an** Operations Team Lead (Olivia)
**I want to** convert vRealize event subscriptions to Event-Driven Ansible (EDA) rulebooks
**So that** I can maintain reactive automation on OpenShift

**Acceptance Criteria:**
- Analyzes vRealize workflows with event subscriptions
- Generates EDA rulebook YAML in `output/eda/`
- Maps vRealize events to Kubernetes events:
  - VM created → watch for VirtualMachine creation
  - VM powered on → watch for VM running state
  - VM deleted → watch for VirtualMachine deletion
- Includes source configuration for Kubernetes event stream
- Includes action configuration to trigger Ansible playbooks
- Can generate EDA alongside normal output or exclusively

**Technical Details:**
- Command: `ops-translate generate --eda` (with Ansible/KubeVirt)
- Command: `ops-translate generate --eda-only` (EDA only)
- Outputs `output/eda/rulebook.yml`
- Requires ansible-rulebook runtime
- Event sources: `sabre1041.eda.k8s` collection

**Current Capability**: ✅ Fully Supported

**Example**: vRealize workflow triggers on VM creation to send notification → EDA rulebook watches VirtualMachine creation and triggers notification playbook

---

### Epic 5: Advanced Features and Customization

#### Story 5.1: Custom Template Mappings
**As a** Platform Engineer (Paulo)
**I want to** configure how VMware templates map to KubeVirt image sources
**So that** VMs use the correct OS images in my OpenShift environment

**Acceptance Criteria:**
- Define mappings in `ops-translate.yaml` profile
- Supports multiple image source types:
  - `registry:quay.io/containerdisks/centos:8` - Container registry
  - `pvc:namespace/pvc-name` - Existing PVC with disk image
  - `http:https://images.example.com/rhel8.qcow2` - HTTP/HTTPS URL
  - `blank` - Empty disk (for custom installs)
- Mappings applied during generation
- Warnings if unmapped templates are referenced

**Technical Details:**
- Configuration in `profiles.<name>.template_mappings`
- Example:
  ```yaml
  template_mappings:
    "RHEL8-Golden": "registry:quay.io/containerdisks/centos:8"
    "Windows-2022": "pvc:os-images/windows-server-2022"
  ```
- Used in KubeVirt `dataVolumeTemplates`

**Current Capability**: ✅ Fully Supported

---

#### Story 5.2: Distributed Locking for Concurrent Provisioning
**As a** Platform Engineer (Paulo)
**I want to** configure distributed locking for Ansible playbooks
**So that** concurrent VM provisioning doesn't cause race conditions

**Acceptance Criteria:**
- Supports three locking backends:
  - Redis (recommended for production)
  - Consul (alternative production option)
  - File-based (for lab/dev only)
- Generates locking setup documentation in `output/ansible/LOCKING_SETUP.md`
- Includes Ansible tasks for lock acquisition and release
- Configurable per profile
- Can disable locking with `--no-locking` for testing

**Technical Details:**
- Command: `ops-translate generate --locking-backend redis`
- Configuration: `profiles.<name>.locking.backend: redis|consul|file`
- Includes Redis/Consul connection parameters in generated playbooks
- Uses `community.general.redis_*` or `community.general.consul_*` modules

**Current Capability**: ✅ Fully Supported

---

#### Story 5.3: Custom Translation Profiles
**As a** Platform Engineer (Paulo)
**I want to** create custom translation profiles for deterministic adapter generation
**So that** I can ensure consistent mappings without AI variation

**Acceptance Criteria:**
- Define custom translation rules in separate YAML file
- Override default AI-based extraction with deterministic mappings
- Specify patterns for parameter extraction, resource mapping, etc.
- Load profile with `--translation-profile <path>`
- Useful for standardized environments or batch processing

**Technical Details:**
- Command: `ops-translate generate --translation-profile custom-profile.yaml`
- Profile defines extraction and generation rules
- Bypasses or supplements AI analysis
- Ensures reproducible results across runs

**Current Capability**: ✅ Fully Supported

---

### Epic 6: Gap Analysis and Expert Guidance

#### Story 6.1: Automated Gap Detection
**As a** Migration Architect (Maya)
**I want to** automatically identify VMware features that have no direct OpenShift equivalent
**So that** I can plan for manual work or alternative approaches

**Acceptance Criteria:**
- Analyzes vRealize workflows for complex integrations
- Detects NSX operations (segments, firewall rules, load balancers)
- Identifies external integrations (ServiceNow, IPAM, CMDB)
- Detects custom vRealize plugins and actions
- Reports detected gaps in `intent/gaps.json` and `intent/gaps.md`
- Classifies each component as SUPPORTED, PARTIAL, BLOCKED, or MANUAL
- No false positives on supported operations

**Technical Details:**
- Automatic during `intent extract` for vRealize workflows
- Uses pattern matching and API detection
- Outputs structured gap analysis with migration paths
- Integrated into migration readiness report

**Current Capability**: ✅ Fully Supported

**Example Gaps Detected:**
- NSX segment creation → Recommend Multus CNI or OVN-Kubernetes secondary networks
- vRealize REST integration → Recommend Ansible uri module
- Custom plugin → MANUAL classification with expert review needed

---

#### Story 6.2: Expert Recommendations by Team
**As a** Migration Architect (Maya)
**I want to** receive specific recommendations organized by responsible team
**So that** I can route work items to the right stakeholders

**Acceptance Criteria:**
- Recommendations grouped by team:
  - **Platform Team**: Core infrastructure, storage classes, quotas
  - **Network Team**: Network policies, Multus, CNI configuration
  - **Security Team**: RBAC, NetworkPolicies, segmentation
  - **Application Team**: Application-specific configurations
- Each recommendation includes:
  - Component affected
  - Issue description
  - Recommended solution with OpenShift specifics
  - Links to relevant documentation
  - Effort estimate (low, medium, high)
- Included in migration readiness report
- Exportable to JSON for project management tools

**Technical Details:**
- Generated during classification phase
- Outputs `intent/recommendations.json`
- Rendered in report's "Expert Guidance" tab
- Uses template library of common migration patterns

**Current Capability**: ✅ Fully Supported

---

### Epic 7: Quality and Validation

#### Story 7.1: Dry-Run Validation
**As a** Platform Engineer (Paulo)
**I want to** validate all generated artifacts before deployment
**So that** I can catch errors without touching the cluster

**Acceptance Criteria:**
- Validates KubeVirt manifests against Kubernetes schema
- Validates Ansible playbooks for syntax errors
- Checks referenced resources exist (StorageClasses, NetworkAttachmentDefinitions)
- Validates RBAC permissions for operations
- Reports all errors with file paths and line numbers
- Fast operation (no cluster communication required)

**Technical Details:**
- Command: `ops-translate dry-run`
- Uses `kubectl --dry-run=client` for manifest validation
- Uses `ansible-playbook --syntax-check` for playbook validation
- Validates intent schema compliance

**Current Capability**: ✅ Fully Supported

---

#### Story 7.2: Logged Assumptions and Transparency
**As a** Migration Architect (Maya)
**I want to** review all assumptions made by the AI during extraction
**So that** I can validate correctness and understand any inferences

**Acceptance Criteria:**
- All AI assumptions logged to `intent/assumptions.md`
- Includes:
  - Inferred parameter types
  - Assumed resource mappings
  - Interpreted business logic
  - Environment detection rules
- Each assumption includes source location (file, line)
- Clear distinction between explicit (from source) and inferred (by AI)
- Human-readable markdown format

**Technical Details:**
- Automatic during `intent extract`
- Generated by LLM provider with structured output
- Includes confidence levels where applicable

**Current Capability**: ✅ Fully Supported

---

## Future Considerations

### Epic 8: Enhanced AI Capabilities

#### Story 8.1: Multi-Step Workflow Orchestration
**As a** Platform Engineer (Paulo)
**I want to** translate complex multi-step vRealize workflows with branching logic
**So that** I can preserve orchestration patterns in Ansible

**Acceptance Criteria:**
- Supports nested decision trees
- Converts vRealize scriptable tasks to Ansible tasks with equivalent logic
- Handles loop constructs (forEach, while)
- Preserves error handling and rollback logic
- Generates structured Ansible roles with clear task dependencies

**Potential Challenges:**
- JavaScript to Ansible conversion complexity
- State management across tasks
- Error handling patterns differ between platforms

**Priority**: High - common in enterprise environments

---

#### Story 8.2: Custom Plugin Translation
**As a** Migration Architect (Maya)
**I want to** receive guidance for migrating custom vRealize plugins
**So that** I can plan development work for custom integrations

**Acceptance Criteria:**
- Analyzes custom plugin code (if available)
- Identifies plugin purpose and external dependencies
- Recommends Ansible equivalents:
  - Existing Ansible modules
  - Custom module development
  - REST API integration via uri module
  - External system alternatives
- Provides code skeleton for custom module development
- Estimates development effort

**Potential Approach:**
- Pattern matching for common plugin types
- LLM analysis of plugin JavaScript/Java code
- Template library for common integration patterns

**Priority**: Medium - impacts 20-30% of complex migrations

---

#### Story 8.3: Network Policy Generation from NSX Rules
**As a** Security Engineer (Samira)
**I want to** convert NSX firewall rules to Kubernetes NetworkPolicies
**So that** I can maintain network segmentation in OpenShift

**Acceptance Criteria:**
- Parses NSX firewall rule definitions
- Generates equivalent NetworkPolicy manifests
- Handles:
  - Source/destination selectors (labels instead of IPs)
  - Port and protocol rules
  - Allow/deny semantics
  - Rule priorities
- Recommends Calico NetworkPolicy for advanced features (layer 7, FQDN)
- Generates documentation explaining any limitations

**Potential Challenges:**
- NSX supports more complex rules than base NetworkPolicy
- IP-based rules need label-based translation
- May require Calico or OVN-Kubernetes for full equivalence

**Priority**: High - critical for security compliance

---

### Epic 9: Integration and Ecosystem

#### Story 9.1: GitOps Workflow Integration
**As a** Platform Engineer (Paulo)
**I want to** automatically commit generated artifacts to Git with structured PRs
**So that** I can integrate ops-translate into my GitOps workflow

**Acceptance Criteria:**
- Command: `ops-translate generate --git-commit`
- Creates feature branch with generated artifacts
- Generates comprehensive PR description including:
  - Source files analyzed
  - Classification summary
  - Known gaps and limitations
  - Deployment instructions
- Optionally pushes to remote and creates PR via GitHub/GitLab API
- Includes review checklist

**Potential Approach:**
- Git operations via GitPython library
- GitHub API via PyGithub
- GitLab API via python-gitlab
- Template-based PR descriptions

**Priority**: High - critical for enterprise adoption

---

#### Story 9.2: ServiceNow Integration for Change Management
**As an** Operations Team Lead (Olivia)
**I want to** automatically create ServiceNow change requests from migration plans
**So that** I can maintain compliance with change management processes

**Acceptance Criteria:**
- Analyzes migration readiness report
- Creates ServiceNow change request with:
  - Impacted VMs and applications
  - Risk assessment (based on classification)
  - Implementation plan (step-by-step)
  - Rollback plan
  - Required approvals
- Links change request to migration artifacts
- Updates change request as migration progresses

**Potential Approach:**
- ServiceNow REST API integration
- Configurable change request templates
- Approval workflow mapping

**Priority**: Medium - required for many enterprises

---

#### Story 9.3: Jira/Project Management Integration
**As a** Migration Architect (Maya)
**I want to** create Jira stories for MANUAL and BLOCKED components
**So that** I can track custom development work in our project management system

**Acceptance Criteria:**
- Automatically creates Jira stories for components requiring manual work
- Each story includes:
  - Component description and source file
  - Gap analysis and migration path
  - Effort estimate
  - Expert recommendations
  - Acceptance criteria
- Links related stories (e.g., network + security for NSX migration)
- Assigns to appropriate teams based on recommendation categorization

**Potential Approach:**
- Jira REST API via jira-python library
- Configurable story templates
- Team assignment rules

**Priority**: Medium - enhances project tracking

---

### Epic 10: Advanced Migration Scenarios

#### Story 10.1: Incremental Migration Support
**As a** Migration Architect (Maya)
**I want to** support phased migration with coexistence between VMware and OpenShift
**So that** I can reduce risk with gradual cutover

**Acceptance Criteria:**
- Generates playbooks that support both environments simultaneously
- Handles:
  - Conditional provisioning based on target platform
  - Cross-platform service discovery
  - Shared storage considerations
  - Network routing between platforms
- Provides rollback procedures
- Tracks migration state per VM

**Potential Approach:**
- Multi-cloud provisioning patterns
- Inventory-based targeting
- State management in external database

**Priority**: High - critical for large-scale migrations

---

#### Story 10.2: Bulk Migration Orchestration
**As a** Platform Engineer (Paulo)
**I want to** orchestrate migration of hundreds of VMs with dependency management
**So that** I can execute large-scale migrations efficiently

**Acceptance Criteria:**
- Analyzes VM dependencies (network, storage, application)
- Generates migration order respecting dependencies
- Supports parallel migration of independent VMs
- Implements throttling to avoid resource exhaustion
- Provides progress tracking and reporting
- Handles partial failures with resume capability

**Potential Approach:**
- Dependency graph construction
- Ansible Tower/AAP job templates
- External orchestration via Argo Workflows or Tekton

**Priority**: High - needed for production migrations

---

#### Story 10.3: Rollback and Recovery
**As an** Operations Team Lead (Olivia)
**I want to** automated rollback procedures for failed migrations
**So that** I can quickly recover from issues

**Acceptance Criteria:**
- Generates rollback playbooks alongside migration playbooks
- Captures pre-migration state
- Supports rollback at multiple stages:
  - Before VM start
  - After VM creation but before application deployment
  - Full rollback including data
- Validates rollback success
- Provides troubleshooting guide for manual recovery

**Potential Approach:**
- Snapshot-based recovery
- State capture in external storage
- Validation playbooks

**Priority**: High - critical for production confidence

---

### Epic 11: Performance and Scale

#### Story 11.1: Parallel Processing for Large Portfolios
**As a** Migration Architect (Maya)
**I want to** process hundreds of PowerCLI scripts in parallel
**So that** I can complete analysis of large automation portfolios quickly

**Acceptance Criteria:**
- Command: `ops-translate intent extract --parallel <N>`
- Processes multiple files concurrently
- Respects LLM API rate limits
- Shows progress bar with completion status
- Handles failures gracefully (retry failed items)
- Reduces total processing time by 5-10x for large portfolios

**Potential Approach:**
- Python multiprocessing or asyncio
- Queue-based work distribution
- Intelligent rate limiting

**Priority**: Medium - quality of life for large migrations

---

#### Story 11.2: Caching and Incremental Updates
**As a** Platform Engineer (Paulo)
**I want to** re-extract only changed files
**So that** I can iterate quickly on large automation portfolios

**Acceptance Criteria:**
- Detects file changes via hash comparison
- Skips re-processing of unchanged files
- Invalidates cache for dependent files
- Command: `ops-translate intent extract --incremental`
- Reduces re-extraction time by 90%+ for minor changes

**Potential Approach:**
- Hash-based change detection
- Dependency graph for invalidation
- Persistent cache storage

**Priority**: Low - nice to have for iteration

---

### Epic 12: Enhanced Reporting and Visibility

#### Story 12.1: Executive Dashboard with Timeline Projection
**As an** Executive Sponsor (Eric)
**I want to** view projected timeline and resource needs
**So that** I can plan budget and staffing

**Acceptance Criteria:**
- Estimates migration duration based on:
  - Component classification distribution
  - Historical velocity data
  - Team capacity
- Shows resource requirements (Platform, Network, Security team effort)
- Provides confidence intervals (best case, likely, worst case)
- Interactive timeline with milestones
- Export to project management tools (MS Project, Smartsheet)

**Potential Approach:**
- Effort estimation models based on classification
- Configurable velocity parameters
- Integration with project management APIs

**Priority**: Medium - valuable for planning

---

#### Story 12.2: Compliance and Audit Reporting
**As a** Security Engineer (Samira)
**I want to** generate compliance reports showing security posture changes
**So that** I can validate the migration meets regulatory requirements

**Acceptance Criteria:**
- Compares VMware and OpenShift security configurations
- Highlights improvements:
  - RBAC vs. traditional permissions
  - NetworkPolicy vs. NSX firewall
  - Pod security standards
- Identifies security gaps requiring remediation
- Maps to compliance frameworks (PCI-DSS, HIPAA, SOC2)
- Generates audit-ready documentation

**Potential Approach:**
- Security control mapping tables
- Compliance framework templates
- Gap analysis with remediation guidance

**Priority**: Medium - required for regulated industries

---

#### Story 12.3: Cost Analysis and Optimization
**As an** Executive Sponsor (Eric)
**I want to** understand cost implications of migration
**So that** I can validate ROI and budget allocation

**Acceptance Criteria:**
- Estimates OpenShift resource consumption based on:
  - VM sizing in PowerCLI scripts
  - Environment profiles (dev/staging/prod counts)
  - Storage and network requirements
- Compares to current VMware licensing and infrastructure costs
- Highlights cost optimization opportunities:
  - Rightsizing recommendations
  - Shared storage benefits
  - Reduced licensing costs
- Provides 3-year TCO projection

**Potential Approach:**
- Configurable cost models
- Resource consumption aggregation from intent
- TCO calculation templates

**Priority**: Low - valuable but not essential for technical migration

---

### Epic 13: Developer Experience

#### Story 13.1: VS Code Extension
**As a** Platform Engineer (Paulo)
**I want to** use ops-translate features directly in VS Code
**So that** I can work efficiently without switching contexts

**Acceptance Criteria:**
- Syntax highlighting for intent YAML files
- IntelliSense for intent schema
- Inline validation and error reporting
- Commands in command palette for extract, generate, etc.
- Preview generated artifacts in split view
- Integrated terminal for ops-translate commands

**Potential Approach:**
- VS Code Language Server Protocol (LSP)
- JSON Schema integration
- Extension API for command execution

**Priority**: Low - quality of life improvement

---

#### Story 13.2: Web UI for Non-Technical Stakeholders
**As an** Application Owner (Adrian)
**I want to** interact with ops-translate through a web interface
**So that** I can review migration plans without command-line expertise

**Acceptance Criteria:**
- Upload PowerCLI/vRealize files via drag-and-drop
- View migration readiness report in browser
- Provide decision interview answers via forms
- Download generated artifacts
- Track migration progress dashboard
- No local installation required

**Potential Approach:**
- FastAPI or Flask backend
- React or Vue.js frontend
- Web-based file upload and processing
- Integration with migration readiness report

**Priority**: Low - expands accessibility

---

### Epic 14: Testing and Validation

#### Story 14.1: Automated Integration Testing
**As a** Platform Engineer (Paulo)
**I want to** automatically test generated playbooks in a sandbox environment
**So that** I can validate they work before production deployment

**Acceptance Criteria:**
- Spins up temporary OpenShift namespace
- Executes generated playbooks
- Validates VM creation and configuration
- Cleans up resources after testing
- Reports test results with logs
- Command: `ops-translate test --profile lab`

**Potential Approach:**
- Integration with OpenShift sandbox clusters
- Ansible Molecule for playbook testing
- Automated namespace provisioning and cleanup

**Priority**: High - critical for production confidence

---

#### Story 14.2: Migration Dry-Run Simulation
**As a** Migration Architect (Maya)
**I want to** simulate the migration process without creating real resources
**So that** I can validate orchestration and timing

**Acceptance Criteria:**
- Simulates full migration workflow
- Reports expected resource creation order
- Identifies potential bottlenecks
- Estimates total migration time
- Validates dependencies and prerequisites
- No actual resources created

**Potential Approach:**
- Dry-run mode for Ansible with execution time estimation
- Dependency graph visualization
- Simulation engine for complex workflows

**Priority**: Medium - valuable for planning

---

### Epic 15: Extensibility and Customization

#### Story 15.1: Custom Analyzer Plugins
**As a** Platform Engineer (Paulo)
**I want to** create custom analyzers for proprietary automation frameworks
**So that** I can use ops-translate with non-standard VMware automation

**Acceptance Criteria:**
- Plugin API for custom source analyzers
- Documentation for plugin development
- Example plugins for common frameworks
- Plugin registration in config file
- Plugin validation and error handling

**Potential Approach:**
- Python plugin system with entry points
- Abstract base classes for analyzers
- Plugin discovery via setuptools

**Priority**: Low - benefits advanced users

---

#### Story 15.2: Custom Template Library
**As a** Platform Engineer (Paulo)
**I want to** maintain organization-specific Jinja2 templates
**So that** I can customize generated artifacts to our standards

**Acceptance Criteria:**
- Override default templates with custom versions
- Template inheritance from base templates
- Organization-specific:
  - Naming conventions
  - Tagging standards
  - Monitoring integration
  - Backup policies
- Template validation

**Potential Approach:**
- Template search path configuration
- Jinja2 template inheritance
- Schema validation for template output

**Priority**: Medium - needed for enterprise standardization

---

## Success Metrics

### Technical Metrics

**Migration Automation Rate**
- **Target**: 70%+ of components classified as SUPPORTED or PARTIAL
- **Measurement**: Classification breakdown in migration readiness report
- **Baseline**: Manual migration = 0% automation

**Time to First Artifact**
- **Target**: < 30 minutes from source files to deployable Ansible playbook
- **Measurement**: End-to-end workflow timing
- **Baseline**: Manual conversion = days to weeks

**Artifact Quality**
- **Target**: 90%+ of generated artifacts deploy successfully without modification
- **Measurement**: Success rate in test deployments
- **Baseline**: Manual artifacts require multiple iterations

### Business Metrics

**Migration Velocity**
- **Target**: 3-5x faster than manual migration
- **Measurement**: VMs migrated per week with ops-translate vs. manual
- **Baseline**: 5-10 VMs/week manual, target 15-50 VMs/week with tool

**Total Cost of Migration**
- **Target**: 40-60% reduction in migration project costs
- **Measurement**: Total project spend (labor + tools)
- **Baseline**: Manual migration costs

**Knowledge Retention**
- **Target**: 100% of operational intent captured in artifacts
- **Measurement**: % of source automation logic preserved in generated code
- **Baseline**: Manual migration often loses intent

### User Experience Metrics

**Time to Value**
- **Target**: < 2 hours from installation to first generated artifact
- **Measurement**: Onboarding time for new users
- **Baseline**: N/A (new tool)

**User Satisfaction**
- **Target**: 4+ out of 5 satisfaction score
- **Measurement**: Post-migration surveys
- **Questions**:
  - Ease of use
  - Quality of generated artifacts
  - Usefulness of gap analysis
  - Quality of documentation

**Adoption Rate**
- **Target**: 80%+ of migration projects use ops-translate
- **Measurement**: % of VMware migrations using tool vs. manual

---

## Non-Functional Requirements

### Security

**NFR-S1: Read-Only Operations**
- ops-translate SHALL NOT connect to live VMware or OpenShift environments
- All analysis based on exported files only
- No credentials required for operation

**NFR-S2: Secure Credential Handling**
- LLM API keys stored in environment variables only
- No credentials in generated artifacts
- Clear documentation on secret management for generated playbooks

**NFR-S3: Audit Trail**
- All LLM API calls logged with timestamps
- All assumptions documented in `assumptions.md`
- All user decisions captured in intent YAML

### Performance

**NFR-P1: Extraction Performance**
- Single PowerCLI file: < 30 seconds
- Single vRealize workflow: < 60 seconds
- 100 files (parallel processing): < 10 minutes

**NFR-P2: Generation Performance**
- Artifact generation: < 5 seconds (no LLM calls)
- Report generation: < 10 seconds
- Dry-run validation: < 5 seconds

**NFR-P3: Scalability**
- Support up to 1000 source files in single workspace
- Support VM intent with 100+ parameters
- Report rendering with 500+ components

### Reliability

**NFR-R1: Error Handling**
- Graceful handling of malformed PowerCLI/vRealize files
- Retry logic for transient LLM API failures
- Clear error messages with remediation guidance

**NFR-R2: Data Integrity**
- Schema validation for all intent YAML
- Conflict detection during merge
- Validation before artifact generation

**NFR-R3: Idempotency**
- Repeated extraction produces identical results (with same LLM model)
- Re-generation overwrites previous output cleanly
- Merge operations are repeatable

### Usability

**NFR-U1: Documentation**
- Comprehensive README with quick start
- Detailed user guide covering all commands
- Architecture documentation for developers
- Tutorial with real-world examples
- Inline help text for all commands

**NFR-U2: Error Messages**
- Actionable error messages (what went wrong + how to fix)
- Context-specific help (e.g., missing LLM API key)
- Links to relevant documentation

**NFR-U3: Progressive Disclosure**
- Simple workflows require minimal configuration
- Advanced features available but not required
- Sensible defaults for all optional parameters

### Compatibility

**NFR-C1: Platform Support**
- Linux (primary platform)
- macOS (supported)
- Windows (via WSL2)

**NFR-C2: Python Compatibility**
- Python 3.9+
- Virtual environment friendly
- Minimal system dependencies

**NFR-C3: OpenShift Compatibility**
- OpenShift 4.12+
- KubeVirt 1.0+
- Ansible 2.14+

### Maintainability

**NFR-M1: Code Quality**
- Type hints throughout codebase
- Comprehensive unit tests (target: 70%+ coverage)
- Integration tests for critical workflows
- Linting (pylint, flake8, mypy)

**NFR-M2: Extensibility**
- Plugin architecture for custom analyzers
- Template-based artifact generation
- Configurable LLM providers

**NFR-M3: Observability**
- Detailed logging at multiple levels (DEBUG, INFO, WARN, ERROR)
- Structured logs for machine parsing
- Performance metrics for optimization

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-16 | ops-translate team | Initial comprehensive user stories document |

---

## Appendix: Story Prioritization Matrix

| Epic | Priority | Complexity | User Impact | Timeline |
|------|----------|------------|-------------|----------|
| Migration Assessment | High | Medium | Critical | Current |
| Intent Management | High | Low | High | Current |
| Artifact Generation | High | High | Critical | Current |
| Post-Migration Ops | High | Medium | High | Current |
| Advanced Features | Medium | Medium | Medium | Current |
| Gap Analysis | High | Medium | Critical | Current |
| Quality & Validation | High | Low | High | Current |
| Enhanced AI | High | High | High | Q2 2026 |
| Integration | Medium | Medium | Medium | Q2-Q3 2026 |
| Advanced Migration | High | High | Critical | Q2-Q3 2026 |
| Performance & Scale | Medium | Medium | Medium | Q3 2026 |
| Enhanced Reporting | Medium | Low | Medium | Q3 2026 |
| Developer Experience | Low | Medium | Low | Q4 2026 |
| Testing & Validation | High | High | High | Q2 2026 |
| Extensibility | Low | High | Low | Q4 2026 |

---

**For Questions or Feedback**: Contact the ops-translate team or file an issue at the project repository.
