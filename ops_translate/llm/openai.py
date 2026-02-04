"""
OpenAI LLM provider implementation.
"""
import os
from typing import Optional
from ops_translate.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client if API key is available."""
        api_key = os.environ.get(self.api_key_env)
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "openai package not installed. Install with: pip install openai"
                )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate text using OpenAI GPT.

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
                f"OpenAI API key not found. Set {self.api_key_env} environment variable."
            )

        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model or "gpt-4-turbo-preview",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Extract text from response
            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")

    def is_available(self) -> bool:
        """Check if OpenAI provider is available."""
        api_key = os.environ.get(self.api_key_env)
        return api_key is not None and self.client is not None
