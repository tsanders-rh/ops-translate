"""
Mock LLM provider for testing (no API calls).
"""

from ops_translate.llm.base import LLMProvider


class MockProvider(LLMProvider):
    """
    Mock LLM provider that returns canned responses.
    Useful for testing without making actual API calls.
    """

    def __init__(self, config: dict):
        super().__init__(config)

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        Return a mock response based on prompt content.

        Args:
            prompt: The user prompt/input
            system_prompt: Optional system prompt (ignored in mock)
            max_tokens: Maximum tokens (ignored in mock)
            temperature: Sampling temperature (ignored in mock)

        Returns:
            Mock YAML response
        """
        # Detect what kind of extraction is being requested
        if "PowerCLI" in prompt or ".ps1" in prompt:
            return self._mock_powercli_intent()
        elif "vRealize" in prompt or ".xml" in prompt or "workflow" in prompt.lower():
            return self._mock_vrealize_intent()
        else:
            return self._mock_generic_intent()

    def _mock_powercli_intent(self) -> str:
        """Return mock intent YAML for PowerCLI."""
        return """schema_version: 1
sources:
  - type: powercli
    file: input/powercli/provision-vm.ps1

intent:
  workflow_name: provision_vm_with_governance
  workload_type: virtual_machine

  inputs:
    vm_name:
      type: string
      required: true
    environment:
      type: enum
      values: [dev, prod]
      required: true
    cpu:
      type: integer
      required: true
      min: 1
      max: 32
    memory_gb:
      type: integer
      required: true
      min: 1
      max: 256
    owner_email:
      type: string
      required: true
    cost_center:
      type: string
      required: false

  governance:
    approval:
      required_when:
        environment: prod

  profiles:
    network:
      when: { environment: prod }
      value: prod-network
    network_else: dev-network
    storage:
      when: { environment: prod }
      value: storage-gold
    storage_else: storage-standard

  metadata:
    tags:
      - key: env
        value_from: environment
      - key: owner
        value_from: owner_email
      - key: managed-by
        value: ops-translate
      - key: cost-center
        value_from: cost_center
        optional: true

  day2_operations:
    supported: [start, stop, reconfigure]
"""

    def _mock_vrealize_intent(self) -> str:
        """Return mock intent YAML for vRealize."""
        return """schema_version: 1
sources:
  - type: vrealize
    file: input/vrealize/provision.workflow.xml

intent:
  workflow_name: provision_vm_with_governance
  workload_type: virtual_machine

  inputs:
    vm_name:
      type: string
      required: true
    environment:
      type: string
      required: true
    cpu_count:
      type: number
      required: true
      min: 1
      max: 32
    memory_gb:
      type: number
      required: true
      min: 1
      max: 256
    owner_email:
      type: string
      required: true
    cost_center:
      type: string
      required: false

  governance:
    approval:
      required_when:
        environment: prod

  profiles:
    network:
      when: { environment: prod }
      value: prod-network
    network_else: dev-network
    storage:
      when: { environment: prod }
      value: storage-gold
    storage_else: storage-standard

  metadata:
    tags:
      - key: env
        value_from: environment
      - key: owner
        value_from: owner_email
      - key: managed-by
        value: ops-translate
      - key: provisioned-date
        value: "{{ date }}"
"""

    def _mock_generic_intent(self) -> str:
        """Return generic mock intent YAML."""
        return """schema_version: 1
sources: []

intent:
  workflow_name: generic_workflow
  workload_type: virtual_machine
  inputs: {}
"""

    def is_available(self) -> bool:
        """Mock provider is always available."""
        return True
