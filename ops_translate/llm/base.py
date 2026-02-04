"""
Abstract base class for LLM providers.
"""
from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: dict):
        """
        Initialize LLM provider.

        Args:
            config: LLM configuration dict with 'model', 'api_key_env', etc.
        """
        self.config = config
        self.model = config.get('model')
        self.api_key_env = config.get('api_key_env', 'OPS_TRANSLATE_LLM_API_KEY')

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate text from the LLM.

        Args:
            prompt: The user prompt/input
            system_prompt: Optional system prompt for instruction
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            Generated text response

        Raises:
            Exception: If LLM API call fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is properly configured and available.

        Returns:
            True if provider can be used, False otherwise
        """
        pass

    def get_model_name(self) -> str:
        """Get the configured model name."""
        return self.model or "unknown"
