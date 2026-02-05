"""
OpenAI LLM provider implementation.
"""

import os

from ops_translate.exceptions import LLMAPIError, LLMProviderNotAvailableError
from ops_translate.llm.base import LLMProvider
from ops_translate.util.retry import RetryStrategy, is_retryable_error, retry_with_backoff


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
                raise ImportError("openai package not installed. Install with: pip install openai")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
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
            LLMProviderNotAvailableError: If API key not configured
            LLMAPIError: If API call fails
        """
        if not self.client:
            raise LLMProviderNotAvailableError("openai", self.api_key_env)

        # Use retry logic for API calls
        return self._generate_with_retry(prompt, system_prompt, max_tokens, temperature)

    @retry_with_backoff(**RetryStrategy.LLM_API)  # type: ignore[arg-type]
    def _generate_with_retry(
        self,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """
        Internal method with retry logic.

        Raises:
            LLMAPIError: If API call fails after retries
        """
        try:
            assert self.client is not None  # Checked in generate()
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
            content = response.choices[0].message.content
            return str(content) if content else ""

        except Exception as e:
            # Determine if error is retryable
            if is_retryable_error(e):
                # Re-raise to trigger retry
                raise
            else:
                # Non-retryable error
                raise LLMAPIError("OpenAI", str(e), retry_count=0)

    def is_available(self) -> bool:
        """Check if OpenAI provider is available."""
        api_key = os.environ.get(self.api_key_env)
        return api_key is not None and self.client is not None
