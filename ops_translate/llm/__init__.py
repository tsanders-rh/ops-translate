"""
LLM provider abstraction layer.
"""

from typing import Any

from ops_translate.llm.anthropic import AnthropicProvider
from ops_translate.llm.base import LLMProvider
from ops_translate.llm.mock import MockProvider
from ops_translate.llm.openai import OpenAIProvider


def get_provider(config: dict[str, Any]) -> LLMProvider:
    """
    Factory function to get LLM provider based on config.

    Args:
        config: Configuration dict with 'llm' section

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    llm_config = config.get("llm", {})
    provider_name = llm_config.get("provider", "anthropic").lower()

    if provider_name == "anthropic":
        return AnthropicProvider(llm_config)
    elif provider_name == "openai":
        return OpenAIProvider(llm_config)
    elif provider_name == "mock":
        return MockProvider(llm_config)
    else:
        raise ValueError(
            f"Unsupported provider: {provider_name}. Must be one of: anthropic, openai, mock"
        )


__all__ = ["LLMProvider", "AnthropicProvider", "OpenAIProvider", "MockProvider", "get_provider"]
