"""
Anthropic Claude LLM provider implementation.
"""

import os

from ops_translate.exceptions import LLMAPIError, LLMProviderNotAvailableError
from ops_translate.llm.base import LLMProvider
from ops_translate.util.redact import redact_sensitive
from ops_translate.util.retry import RetryStrategy, is_retryable_error, retry_with_backoff


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
        system_prompt: str | None = None,
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
            LLMProviderNotAvailableError: If API key not configured
            LLMAPIError: If API call fails
        """
        if not self.client:
            raise LLMProviderNotAvailableError("anthropic", self.api_key_env)

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
            if self.client is None:
                raise RuntimeError("Anthropic client not initialized. Call is_available() first.")
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
            text = response.content[0].text
            return str(text) if text else ""

        except Exception as e:
            # Redact any sensitive data from error message
            error_msg = redact_sensitive(str(e))
            # Determine if error is retryable
            if is_retryable_error(e):
                # Re-raise to trigger retry
                raise
            else:
                # Non-retryable error
                raise LLMAPIError("Anthropic", error_msg, retry_count=0)

    def is_available(self) -> bool:
        """Check if Anthropic provider is available."""
        api_key = os.environ.get(self.api_key_env)
        return api_key is not None and self.client is not None
