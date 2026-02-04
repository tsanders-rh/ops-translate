"""
LLM provider abstraction layer.
"""

from ops_translate.llm.anthropic import AnthropicProvider
from ops_translate.llm.base import LLMProvider
from ops_translate.llm.mock import MockProvider
from ops_translate.llm.openai import OpenAIProvider


def get_provider(config: dict) -> LLMProvider:
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

    providers = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "mock": MockProvider,
    }

    if provider_name not in providers:
        raise ValueError(
            f"Unsupported provider: {provider_name}. Must be one of: {list(providers.keys())}"
        )

    return providers[provider_name](llm_config)


__all__ = ["LLMProvider", "AnthropicProvider", "OpenAIProvider", "MockProvider", "get_provider"]
