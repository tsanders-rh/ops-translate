"""
ops-translate: VMware automation migration planning tool.

Helps migrate VMware vRealize and PowerCLI automation to OpenShift Virtualization
by analyzing workflows, extracting operational intent, and generating Ansible playbooks
and KubeVirt manifests.

Main features:
- Gap analysis with SUPPORTED/PARTIAL/BLOCKED classifications
- HTML reports for stakeholders
- AI-powered intent extraction
- Ansible + KubeVirt code generation
- ansible-lint integration for code quality
- Incremental analysis with caching
"""
