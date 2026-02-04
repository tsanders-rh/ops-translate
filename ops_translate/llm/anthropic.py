"""
Anthropic Claude LLM provider implementation.
"""
import os
from typing import Optional
from ops_translate.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Anthropic client if API key is available."""
        api_key = os.environ.get(self.api_key_env)
        if api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. Install with: pip install anthropic"
                )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate text using Anthropic Claude.

        Args:
            prompt: The user prompt/input
            system_prompt: Optional system prompt for instruction
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)

        Returns:
            Generated text response

        Raises:
            ValueError: If API key not configured
            Exception: If API call fails
        """
        if not self.client:
            raise ValueError(
                f"Anthropic API key not found. Set {self.api_key_env} environment variable."
            )

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model or "claude-sonnet-4-5",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)

            # Extract text from response
            return response.content[0].text

        except Exception as e:
            raise Exception(f"Anthropic API call failed: {e}")

    def is_available(self) -> bool:
        """Check if Anthropic provider is available."""
        api_key = os.environ.get(self.api_key_env)
        return api_key is not None and self.client is not None
