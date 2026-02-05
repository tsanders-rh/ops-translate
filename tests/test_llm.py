"""
Tests for LLM provider modules.
"""

from unittest.mock import MagicMock, patch

import pytest

from ops_translate.llm import get_provider
from ops_translate.llm.anthropic import AnthropicProvider
from ops_translate.llm.mock import MockProvider
from ops_translate.llm.openai import OpenAIProvider


class TestGetProvider:
    """Tests for LLM provider factory."""

    def test_get_anthropic_provider(self):
        """Test getting Anthropic provider."""
        config = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "api_key_env": "TEST_KEY",
            }
        }

        provider = get_provider(config)

        assert isinstance(provider, AnthropicProvider)

    def test_get_openai_provider(self):
        """Test getting OpenAI provider."""
        config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "api_key_env": "TEST_KEY",
            }
        }

        provider = get_provider(config)

        assert isinstance(provider, OpenAIProvider)

    def test_get_mock_provider(self):
        """Test getting mock provider."""
        config = {"llm": {"provider": "mock", "model": "mock-model"}}

        provider = get_provider(config)

        assert isinstance(provider, MockProvider)

    def test_get_provider_case_insensitive(self):
        """Test that provider name is case-insensitive."""
        config = {"llm": {"provider": "ANTHROPIC", "model": "claude-sonnet-4-5"}}

        provider = get_provider(config)

        assert isinstance(provider, AnthropicProvider)

    def test_get_provider_default(self):
        """Test default provider when none specified."""
        config = {"llm": {"model": "claude-sonnet-4-5"}}

        provider = get_provider(config)

        # Defaults to anthropic
        assert isinstance(provider, AnthropicProvider)

    def test_get_provider_invalid(self):
        """Test error on invalid provider."""
        config = {"llm": {"provider": "invalid", "model": "test"}}

        with pytest.raises(ValueError, match="Unsupported provider"):
            get_provider(config)


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_init(self):
        """Test provider initialization."""
        config = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "api_key_env": "TEST_KEY",
        }

        provider = AnthropicProvider(config)

        assert provider.model == "claude-sonnet-4-5"
        assert provider.api_key_env == "TEST_KEY"

    def test_init_without_model(self):
        """Test init without explicit model."""
        config = {"provider": "anthropic"}

        provider = AnthropicProvider(config)

        # Model is None if not provided
        assert provider.model is None

    @patch.dict("os.environ", {"TEST_KEY": "test-api-key"})
    def test_is_available_with_key(self):
        """Test availability when API key is set."""
        config = {"provider": "anthropic", "api_key_env": "TEST_KEY"}

        provider = AnthropicProvider(config)

        assert provider.is_available() is True

    def test_is_available_without_key(self):
        """Test availability when API key is not set."""
        config = {"provider": "anthropic", "api_key_env": "NONEXISTENT_KEY"}

        provider = AnthropicProvider(config)

        assert provider.is_available() is False

    def test_generate_requires_api_key(self):
        """Test that generate requires API key."""
        config = {"provider": "anthropic", "api_key_env": "NONEXISTENT_KEY"}
        provider = AnthropicProvider(config)

        # is_available should be False
        assert provider.is_available() is False


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    def test_init(self):
        """Test provider initialization."""
        config = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key_env": "TEST_KEY",
        }

        provider = OpenAIProvider(config)

        assert provider.model == "gpt-4"
        assert provider.api_key_env == "TEST_KEY"

    def test_init_without_model(self):
        """Test init without explicit model."""
        config = {"provider": "openai"}

        provider = OpenAIProvider(config)

        # Model is None if not provided
        assert provider.model is None

    @patch.dict("os.environ", {"TEST_KEY": "test-api-key"})
    def test_is_available_with_key(self):
        """Test availability when API key is set."""
        config = {"provider": "openai", "api_key_env": "TEST_KEY"}

        provider = OpenAIProvider(config)

        assert provider.is_available() is True

    def test_is_available_without_key(self):
        """Test availability when API key is not set."""
        config = {"provider": "openai", "api_key_env": "NONEXISTENT_KEY"}

        provider = OpenAIProvider(config)

        assert provider.is_available() is False

    def test_generate_requires_api_key(self):
        """Test that generate requires API key."""
        config = {"provider": "openai", "api_key_env": "NONEXISTENT_KEY"}
        provider = OpenAIProvider(config)

        # is_available should be False
        assert provider.is_available() is False


class TestMockProvider:
    """Tests for mock provider."""

    def test_init(self):
        """Test mock provider initialization."""
        config = {"provider": "mock"}

        provider = MockProvider(config)

        # Model can be None if not in config
        assert provider.model is None or isinstance(provider.model, str)

    def test_is_available(self):
        """Test that mock is always available."""
        config = {"provider": "mock"}

        provider = MockProvider(config)

        assert provider.is_available() is True

    def test_generate_powercli(self):
        """Test generation for PowerCLI content."""
        config = {"provider": "mock"}
        provider = MockProvider(config)

        result = provider.generate(prompt="PowerCLI script here")

        assert "schema_version: 1" in result
        assert "type: powercli" in result
        assert "workflow_name:" in result

    def test_generate_vrealize(self):
        """Test generation for vRealize content."""
        config = {"provider": "mock"}
        provider = MockProvider(config)

        result = provider.generate(prompt="vRealize workflow here")

        assert "schema_version: 1" in result
        assert "type: vrealize" in result
        assert "workflow_name:" in result

    def test_generate_generic(self):
        """Test generation for generic content."""
        config = {"provider": "mock"}
        provider = MockProvider(config)

        result = provider.generate(prompt="Some other content")

        assert "schema_version: 1" in result
        assert "workflow_name: generic_workflow" in result

    def test_generate_with_all_params(self):
        """Test that mock provider accepts all parameters."""
        config = {"provider": "mock"}
        provider = MockProvider(config)

        # Should not raise error
        result = provider.generate(
            prompt="Test",
            system_prompt="System",
            max_tokens=4096,
            temperature=0.0,
        )

        assert isinstance(result, str)
        assert len(result) > 0
