# ops-translate: Frequently Asked Questions

## Table of Contents
- [General Questions](#general-questions)
- [Technical Questions](#technical-questions)
- [Migration Planning](#migration-planning)
- [Cost and ROI](#cost-and-roi)
- [Security and Compliance](#security-and-compliance)
- [Integration and Compatibility](#integration-and-compatibility)
- [Troubleshooting](#troubleshooting)

---

## General Questions

### What is ops-translate?

ops-translate is an AI-assisted migration tool that converts VMware PowerCLI scripts and vRealize Orchestrator workflows into production-ready Ansible playbooks and OpenShift Virtualization (KubeVirt) manifests. It preserves the operational intent and business logic from VMware automation while generating cloud-native equivalents.

### Who should use ops-translate?

ops-translate is designed for:
- **Migration architects** planning VMware to OpenShift Virtualization migrations
- **Platform engineers** executing automation conversion
- **Operations teams** maintaining VM provisioning and governance
- **Organizations** with 5+ PowerCLI scripts or vRealize workflows to migrate

### Is ops-translate production-ready?

**v1 is a prototype** for evaluation and proof-of-concept. Generated artifacts should be reviewed and validated before production use. The tool itself is stable for analysis and generation, but we recommend:
- Testing in lab/staging environments first
- Reviewing all generated artifacts
- Validating assumptions documented in `intent/assumptions.md`
- Starting with non-critical workloads

### How is this different from Migration Toolkit for Virtualization (MTV)?

**MTV** migrates VMs themselves (compute, storage, network).
**ops-translate** migrates the automation around VMs (provisioning scripts, workflows, governance).

They are complementary:
- Use **MTV** to move existing VMs from VMware to OpenShift
- Use **ops-translate** to migrate operational automation and provisioning workflows
- Use **ops-translate in MTV mode** (`--assume-existing-vms`) to generate validation playbooks for already-migrated VMs

### Does ops-translate require access to my VMware environment?

**No**. ops-translate is read-only and works entirely from exported files:
- Export PowerCLI scripts (`.ps1` files)
- Export vRealize workflows (`.xml` files or `.package` bundles)
- No credentials required
- No network access to VMware needed
- Safe to run on laptop or isolated environment

### What languages/frameworks does it support?

**Input formats**:
- VMware PowerCLI (PowerShell scripts)
- vRealize Orchestrator workflows (XML)
- vRealize Actions (JavaScript within packages)

**Output formats**:
- Ansible (YAML playbooks)
- KubeVirt (Kubernetes manifests)
- Kustomize (GitOps multi-environment)
- ArgoCD (Continuous Delivery)
- Event-Driven Ansible (EDA rulebooks)

---

## Technical Questions

### How does the AI extraction work?

ops-translate uses Large Language Models (LLMs) to understand the semantic meaning of imperative automation code:

1. **Static analysis** parses PowerCLI/vRealize structure (parameters, cmdlets, workflow tasks)
2. **LLM extraction** analyzes business logic, conditional flows, and operational intent
3. **Normalization** converts to platform-agnostic intent YAML
4. **Generation** uses Jinja2 templates to create Ansible/KubeVirt artifacts

**Supported LLM providers**:
- Anthropic Claude (recommended: `claude-sonnet-4-5`)
- OpenAI GPT (alternative: `gpt-4-turbo-preview`)
- Mock provider (for testing without API costs)

**Transparency**: All AI assumptions are logged to `intent/assumptions.md` for human review.

### What if I don't want to use AI?

You can use `--no-ai` mode with the generate command:
```bash
ops-translate generate --no-ai --profile lab
```

This uses template-based generation only, without AI assistance. It works well for:
- Simple, well-structured scripts
- Standardized provisioning patterns
- When you have custom translation profiles defined

For complex scripts with branching logic or unusual patterns, AI extraction typically produces better results.

### What VMware features are supported?

**Fully Supported (SUPPORTED classification)**:
- VM creation and configuration (New-VM, Set-VM)
- Resource allocation (CPU, memory, storage, network)
- Tags and metadata (New-TagAssignment, Set-Annotation)
- Power operations (Start-VM, Stop-VM, Restart-VM)
- Environment branching (if/else for dev/prod)
- Resource pools and folders
- Basic vRealize workflows (create, start, configure tasks)

**Partially Supported (PARTIAL classification)**:
- vRealize approval workflows → Ansible pause tasks
- Complex multi-NIC configurations → Requires NetworkAttachmentDefinition setup
- NSX basic operations → Requires manual network configuration
- Event subscriptions → Event-Driven Ansible rulebooks

**Requires Manual Work (BLOCKED/MANUAL classification)**:
- Advanced NSX (distributed firewalls, micro-segmentation)
- Custom vRealize plugins
- Complex JavaScript business logic in vRealize tasks
- External integrations (ServiceNow, IPAM, custom APIs)
- vSphere DRS/HA policies (no direct equivalent)

See the migration readiness report for detailed classification of your specific automation.

### How accurate is the translation?

Based on testing with real-world scripts:
- **Simple provisioning scripts**: 90-95% accuracy (minimal manual refinement)
- **Environment-aware scripts**: 80-90% accuracy (requires profile configuration)
- **Complex vRealize workflows**: 60-80% accuracy (manual work for custom logic)

**All generated artifacts should be reviewed** before production deployment. Use:
- `intent/assumptions.md` to validate AI inferences
- `ops-translate dry-run` to validate schemas
- `--lint` flag to check Ansible best practices
- Lab/staging testing before production

### Can I customize the generated artifacts?

Yes, multiple customization options:

**1. Configuration profiles** (`ops-translate.yaml`):
```yaml
profiles:
  prod:
    default_namespace: virt-prod
    default_network: prod-network
    default_storage_class: ceph-rbd
    template_mappings:
      "RHEL8-Golden": "registry:quay.io/containerdisks/centos:8"
```

**2. Custom Jinja2 templates**:
- Override default templates in your workspace
- Customize naming conventions, tagging standards, etc.
- Template inheritance from base templates

**3. Translation profiles**:
- Define deterministic mapping rules
- Ensure consistent output across runs
- Useful for batch processing

**4. Post-generation editing**:
- Generated artifacts are standard YAML
- Edit Ansible playbooks and KubeVirt manifests as needed
- Re-generation overwrites, so use custom templates for permanent changes

### What OpenShift/Kubernetes versions are required?

**Minimum requirements**:
- OpenShift 4.12+ (or Kubernetes 1.25+)
- KubeVirt 1.0+
- Ansible 2.14+
- Python 3.9+

**Recommended**:
- OpenShift 4.14+ for latest KubeVirt features
- Ansible 2.16+ for improved collections
- AAP (Ansible Automation Platform) for enterprise features

### Does it work with vanilla Kubernetes?

Yes, but with considerations:
- KubeVirt must be installed manually
- NetworkAttachmentDefinitions require Multus CNI
- Storage classes must be configured
- No OpenShift-specific features (Routes, etc.)

Generated artifacts are Kubernetes-native and will work on any conformant cluster with KubeVirt installed.

---

## Migration Planning

### How long does a migration take?

**Per-script processing** (with ops-translate):
- Simple script: 30-60 minutes (import → analyze → generate → review)
- Complex workflow: 1-2 hours (includes decision interview)
- Manual remediation: Varies (5% to 35% of scripts need manual work)

**Full migration timeline** (varies by organization):
- **Small** (100-500 VMs, 5-10 scripts): 1-2 weeks
- **Mid-size** (500-2000 VMs, 15-25 scripts): 1-2 months
- **Enterprise** (2000+ VMs, 50-100+ scripts): 2-4 months

Compare to manual migration (no tooling):
- Small: 2-3 months
- Mid-size: 6-12 months
- Enterprise: 12-24 months

### Should I migrate all scripts at once?

**No, phased approach is recommended**:

**Phase 1: Assessment** (1-2 weeks)
- Import all scripts
- Generate migration readiness report
- Classify and prioritize

**Phase 2: Simple scripts** (2-4 weeks)
- Migrate SUPPORTED scripts first
- Build confidence with quick wins
- Refine processes and templates

**Phase 3: Complex scripts** (4-8 weeks)
- PARTIAL scripts with manual configuration
- BLOCKED scripts with decision interviews
- MANUAL scripts with custom development

**Phase 4: Production rollout** (ongoing)
- Deploy to production incrementally
- Monitor and validate
- Iterate based on feedback

### What should I migrate first?

**Recommended prioritization**:

1. **Non-critical lab/dev scripts** (lowest risk)
   - Build team familiarity
   - Test the process
   - Identify issues early

2. **SUPPORTED classification scripts** (highest automation)
   - Quick wins
   - Minimal manual work
   - Builds momentum

3. **High-volume provisioning scripts** (highest value)
   - Most operational impact
   - ROI justification
   - Team enablement

4. **Complex governance workflows** (strategic)
   - Preserve critical business logic
   - May require most manual work
   - Save for when team is experienced

**Avoid starting with**:
- Production-critical scripts (too risky for learning)
- MANUAL classification scripts (too complex initially)
- Scripts with heavy NSX dependencies (require advanced setup)

### How do I handle scripts that can't be fully automated?

Use the **classification system** to plan manual work:

**PARTIAL** (needs configuration):
1. Review gap analysis in migration readiness report
2. Complete decision interview for missing context
3. Perform manual configuration (NetworkAttachmentDefinitions, StorageClasses)
4. Regenerate artifacts with updated intent
5. Validate and deploy

**BLOCKED** (needs decisions):
1. Review expert recommendations
2. Make architectural decisions (which CNI for NSX replacement, etc.)
3. Provide answers via decision interview
4. Regenerate with decisions applied

**MANUAL** (needs custom development):
1. Review generated artifact stubs
2. Develop custom Ansible modules or playbooks
3. Integrate with generated artifacts
4. Consider engaging professional services

**Key principle**: ops-translate reduces manual work by 70-90%, but some manual effort is expected. The tool makes that work visible and structured.

### Can I run ops-translate multiple times on the same scripts?

**Yes, it's designed for iteration**:

- **Re-import**: Updates manifest with latest files
- **Re-extract**: Can re-run with different LLM models or providers
- **Re-merge**: Updates consolidated intent
- **Re-generate**: Overwrites output directory with latest artifacts

**Use cases for iteration**:
- Updated source scripts from VMware
- Changed configuration profiles
- New answers to decision interview questions
- Improved custom templates

**Tip**: Use version control (Git) to track changes between iterations.

---

## Cost and ROI

### What does ops-translate cost?

**Software costs**:
- **ops-translate**: Open source, no license fees
- **LLM API costs**: $0.10-$0.30 per script (minimal)
  - Claude Sonnet 4.5: ~$0.15 per typical script
  - Can use mock provider for testing ($0)

**Infrastructure costs**:
- **OpenShift**: Existing infrastructure or new licensing (separate from tool)
- **Development environment**: Standard lab/staging clusters

**Professional services** (optional):
- Migration planning: 1-2 weeks
- Custom template development: 2-4 weeks
- Training and enablement: 1 week

**Total cost**: Typically 40-60% less than manual migration approach

### What's the ROI?

**Time savings example** (mid-size organization with 20 scripts):

**Manual migration**:
- 20 scripts × 3 weeks per script = 60 weeks
- At $100/hour × 40 hours/week = $240,000

**With ops-translate**:
- 20 scripts × 2 hours per script = 40 hours ($4,000)
- Manual work for 20% of scripts: 4 scripts × 1 week = 4 weeks ($16,000)
- LLM API costs: 20 × $0.20 = $4
- **Total: ~$20,000**

**ROI: $220,000 savings (92% reduction)**

**Additional benefits**:
- Faster time to market (8 weeks vs. 60 weeks)
- Higher quality (template-based vs. manual coding)
- Knowledge preservation (intent captured vs. lost)
- Reduced risk (validation and dry-run capabilities)

### Are there hidden costs?

**Potential additional costs to consider**:

1. **Learning curve**: 1-2 days for team to learn tool (minor)
2. **OpenShift training**: If team is new to Kubernetes (separate initiative)
3. **Template customization**: If organization has strict standards (2-4 weeks)
4. **Infrastructure**: If OpenShift cluster doesn't exist (separate project)
5. **Manual remediation**: For PARTIAL/BLOCKED/MANUAL scripts (varies, 5-35% of portfolio)

**Not hidden, but important**: The tool accelerates automation migration, but won't eliminate all manual work. Realistic expectation is 70-90% automation coverage.

---

## Security and Compliance

### Is my VMware automation code sent to external services?

**Yes, for AI extraction**:
- PowerCLI script content is sent to configured LLM provider (Anthropic or OpenAI)
- Used for semantic analysis and intent extraction only
- Subject to provider's data policies (see Anthropic/OpenAI terms)

**To avoid external transmission**:
- Use `--no-ai` mode (template-only generation)
- Use mock provider for testing
- Review your organization's acceptable use policies

**Important**:
- No live credentials are extracted or transmitted
- Only script content (which should not contain secrets) is analyzed
- Generated artifacts stay local unless you push to Git

### Does ops-translate require credentials?

**No credentials for VMware or OpenShift**:
- No vCenter/vRealize credentials
- No OpenShift/Kubernetes credentials
- Works entirely from exported files

**Only credential needed**:
- LLM API key (stored in environment variable)
- Example: `export OPS_TRANSLATE_LLM_API_KEY="your-key-here"`

**Generated artifacts**:
- Do NOT contain credentials
- Use Ansible best practices (external vars, vaults)
- Document secret management in generated README

### How do I handle secrets in generated playbooks?

**ops-translate generates playbooks that expect secrets via**:
1. **Ansible variables**: Define in `vars.yml` or inventory
2. **Ansible Vault**: Encrypt sensitive values
3. **External secret management**: HashiCorp Vault, CyberArk, etc.

**Example in generated playbook**:
```yaml
- name: Create VM
  kubevirt_vm:
    name: "{{ vm_name }}"
    namespace: "{{ namespace }}"
    # credentials NOT hardcoded, expected from vars
```

**Recommendations**:
- Use AAP (Ansible Automation Platform) credential management
- Integrate with OpenShift secrets for runtime values
- Never commit unencrypted secrets to Git

### Are generated artifacts secure?

**Security considerations**:

**✅ Good defaults**:
- Generated NetworkPolicies follow least-privilege
- RBAC recommendations in reports
- No hardcoded credentials
- Validation of resource limits

**⚠️ Review required**:
- Network policies may need tightening for your environment
- Storage security (encryption, access modes) must be configured
- Pod security standards should be validated
- Compliance requirements (PCI-DSS, HIPAA) need manual review

**Recommendation**:
- Conduct security review of generated artifacts before production
- Use OpenShift security scanning (StackRox, ACS)
- Implement GitOps approval workflows

### Does this meet compliance requirements?

**ops-translate provides**:
- Audit trail (all assumptions logged)
- Traceability (source to artifact mapping)
- Validation and dry-run capabilities
- Expert guidance for security considerations

**You must still**:
- Conduct compliance validation for your industry
- Review security controls in generated artifacts
- Implement change management (ServiceNow, approval workflows)
- Maintain documentation for audits

**For regulated industries**: Consider engaging compliance team early to review approach and validate controls.

---

## Integration and Compatibility

### Can I integrate with GitOps workflows?

**Yes, multiple options**:

**1. ArgoCD format** (built-in):
```bash
ops-translate generate --format argocd
```
Generates complete ArgoCD Application manifests with sync policies.

**2. Kustomize format**:
```bash
ops-translate generate --format kustomize
```
Generates base + overlay structure for multi-environment management.

**3. Manual Git integration**:
- Generated artifacts in `output/` directory
- Commit to Git repository manually
- Use with any GitOps tool (Flux, Argo, etc.)

**Future**: Planned GitOps workflow integration with automatic PR creation (see USER_STORIES.md Epic 9.1)

### Does it work with Ansible Automation Platform (AAP)?

**Yes**, generated playbooks are compatible with AAP:

**What works**:
- Standard Ansible playbook structure
- Role-based organization
- Variable management
- Job templates and workflows

**Integration steps**:
1. Import generated playbooks to AAP project
2. Create job templates for provisioning
3. Configure credentials (OpenShift, external systems)
4. Set up surveys for dynamic parameters
5. Create workflows for multi-step provisioning

**Generated artifacts include**:
- AAP-compatible playbook structure
- Variable separation for surveys
- Documentation for job template setup

### Can I use this with existing Ansible collections?

**Yes**, generated playbooks use standard collections:

**Required collections**:
- `community.general` - General-purpose modules
- `kubernetes.core` - Kubernetes/OpenShift operations
- `kubevirt.core` - KubeVirt VM management

**Optional collections** (based on features):
- `ansible.eda` - Event-Driven Ansible
- `redhat.openshift` - OpenShift-specific operations
- Custom collections - Can be integrated via templates

**Installation**:
```bash
ansible-galaxy collection install -r requirements.yml
```
Generated in `output/ansible/requirements.yml`

### Does it support multi-cluster deployments?

**Partial support**:

**Current capability**:
- Single cluster per profile
- Can define multiple profiles in config (dev, staging, prod)
- Each profile can target different cluster/namespace

**Limitations**:
- No built-in multi-cluster orchestration
- No federation or cluster sprawl support
- Manual process for cross-cluster deployments

**Workarounds**:
- Use ArgoCD ApplicationSets for multi-cluster
- Use Ansible Tower/AAP for multi-cluster job execution
- Run generate multiple times with different profiles

**Future**: Planned multi-cluster support in roadmap (USER_STORIES.md Epic 10.2)

### Can I integrate with CMDB/ServiceNow/ITSM?

**Current state**: No direct integration

**Possible approaches**:

**1. Manual export**:
- Export migration readiness report to CSV
- Import to ServiceNow/CMDB manually
- Track migration progress in ITSM tool

**2. API integration** (custom development):
- Use generated `intent/gaps.json` and `intent/recommendations.json`
- Build custom integration to ITSM APIs
- Automate change request creation

**3. Professional services**:
- Engage for custom ITSM integration
- Typical effort: 2-4 weeks

**Future**: Planned ServiceNow integration in roadmap (USER_STORIES.md Epic 9.2)

---

## Troubleshooting

### "LLM API key not found" error

**Cause**: Environment variable not set

**Solution**:
```bash
export OPS_TRANSLATE_LLM_API_KEY="your-anthropic-or-openai-key"
ops-translate intent extract
```

**Persistent solution**: Add to `~/.bashrc` or `~/.zshrc`

**Alternative**: Use mock provider for testing:
```yaml
# ops-translate.yaml
llm:
  provider: mock
```

### Intent extraction returns generic results

**Possible causes**:
1. **Using mock provider**: Only uses templates, no AI analysis
2. **Script too complex**: LLM struggles with very complex logic
3. **Rate limiting**: API calls failing silently

**Solutions**:
- Check `intent/assumptions.md` for logged issues
- Try different LLM model (e.g., `claude-opus-4-5` for complex scripts)
- Increase `rate_limit_delay` in config if hitting rate limits
- Break complex scripts into smaller pieces

### Generated playbooks fail ansible-lint

**Common issues**:
1. **Line too long**: Lint rule requires <160 characters
2. **Jinja spacing**: Lint prefers `{{ var }}` not `{{var}}`
3. **Command instead of module**: Should use modules not raw commands

**Solutions**:
- Review lint output: `ops-translate generate --lint`
- Edit generated playbooks to address warnings
- Create custom templates with lint-compliant formatting
- Use `--lint-strict` in CI/CD to catch early

**Note**: Minor lint warnings are often acceptable for generated code.

### "Conflict detected during merge" error

**Cause**: Multiple source files have incompatible requirements

**Example**:
- Script A: VM needs 4 CPUs
- Script B: Same VM needs 8 CPUs

**Solution**:
1. Review `intent/conflicts.md` for details
2. Choose resolution strategy:
   - **Manual edit**: Edit intent YAML to resolve
   - **Force merge**: `ops-translate intent merge --force` (uses last value)
   - **Keep separate**: Don't merge, generate separately

### Generated NetworkAttachmentDefinitions don't work

**Common issues**:
1. **Multus not installed**: Required for multiple networks
2. **CNI plugin mismatch**: Generated config doesn't match cluster CNI
3. **Namespace mismatch**: NetworkAttachmentDefinition in wrong namespace

**Solutions**:
- Verify Multus CNI installed: `oc get pods -n openshift-multus`
- Review cluster CNI: `oc get network.config.openshift.io cluster -o yaml`
- Customize network mappings in `ops-translate.yaml`:
```yaml
profiles:
  prod:
    network_mappings:
      "Production-VLAN-100": "prod-network-attachment"
```
- Consult OpenShift networking documentation

### VMs fail to start with "DataVolume not found"

**Cause**: Template mapping references non-existent PVC or invalid URL

**Solution**:
1. Review template mappings in config
2. Verify PVC exists: `oc get pvc -n <namespace>`
3. Test image URL accessibility
4. Update mappings:
```yaml
template_mappings:
  "RHEL8-Golden": "pvc:os-images/rhel8"  # Verify this PVC exists
```

### "Schema validation failed" during dry-run

**Cause**: Intent YAML doesn't match schema

**Common issues**:
- Missing required fields
- Wrong data types (string vs. integer)
- Invalid enumeration values

**Solution**:
1. Review error message for specific field
2. Check `docs/INTENT_SCHEMA.md` for requirements
3. Edit `intent/intent.yaml` to fix
4. Re-run: `ops-translate dry-run`

**If using AI extraction**: Check `intent/assumptions.md` to see if AI made incorrect inference.

### How do I get debug output?

**Enable verbose logging**:
```bash
ops-translate --log-level DEBUG intent extract
```

**Levels**:
- `ERROR`: Only errors
- `WARN`: Warnings and errors
- `INFO`: Normal operation (default)
- `DEBUG`: Detailed diagnostic output

**Check logs**:
- Console output shows all messages
- Some commands write to `intent/` directory (assumptions, gaps, etc.)
- LLM API calls are logged in DEBUG mode

### Where can I get help?

**Documentation**:
- README.md - Overview and quick start
- USER_STORIES.md - Use cases and roadmap
- FAQ.md - This document
- docs/USER_GUIDE.md - Complete command reference
- docs/TUTORIAL.md - Step-by-step walkthrough

**Community**:
- File issues at project repository
- Include debug output and anonymized script samples
- Check existing issues for known problems

**Professional Support**:
- Contact ops-translate team for enterprise support
- Professional services available for complex migrations
- Training and enablement packages available

---

## Questions Not Answered Here?

**Submit an issue** with:
- Your question
- Context (what you're trying to do)
- Any error messages or unexpected behavior

We'll update this FAQ based on common questions from the community.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-16
