"""
Tests for error handling, exceptions, and retry logic.
"""

import time
from unittest.mock import Mock

import pytest

from ops_translate.exceptions import (
    ArtifactValidationError,
    FileNotFoundError,
    IntentNotFoundError,
    IntentValidationError,
    InvalidSourceTypeError,
    LLMAPIError,
    LLMProviderNotAvailableError,
    MergeConflictError,
    OpsTranslateError,
    ProfileNotFoundError,
    WorkspaceAlreadyExistsError,
    WorkspaceNotFoundError,
    format_error_for_cli,
)
from ops_translate.util.retry import (
    RetryStrategy,
    is_retryable_error,
    retry_with_backoff,
    retry_with_logging,
)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_ops_translate_error_base(self):
        """Test base exception."""
        error = OpsTranslateError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.suggestion is None

    def test_ops_translate_error_with_suggestion(self):
        """Test exception with suggestion."""
        error = OpsTranslateError("Test error", "Try this fix")
        assert "Test error" in str(error)
        assert "Try this fix" in str(error)

    def test_workspace_not_found_error(self):
        """Test workspace not found exception."""
        error = WorkspaceNotFoundError()
        assert "workspace" in str(error).lower()
        assert "init" in str(error).lower()

    def test_workspace_not_found_error_with_path(self):
        """Test workspace not found with specific path."""
        error = WorkspaceNotFoundError("/some/path")
        assert "/some/path" in str(error)

    def test_workspace_already_exists_error(self):
        """Test workspace already exists exception."""
        error = WorkspaceAlreadyExistsError("/existing/path")
        assert "/existing/path" in str(error)
        assert "already exists" in str(error).lower()

    def test_file_not_found_error(self):
        """Test file not found exception."""
        error = FileNotFoundError("/path/to/file.ps1")
        assert "/path/to/file.ps1" in str(error)
        assert "not found" in str(error).lower()

    def test_invalid_source_type_error(self):
        """Test invalid source type exception."""
        error = InvalidSourceTypeError("invalid")
        assert "invalid" in str(error)
        assert "powercli" in str(error).lower()
        assert "vrealize" in str(error).lower()

    def test_intent_validation_error(self):
        """Test intent validation exception."""
        errors = ["Missing schema_version", "Invalid type"]
        error = IntentValidationError(errors)
        assert "2 error" in str(error)
        assert "schema_version" in str(error)
        assert "Invalid type" in str(error)

    def test_intent_validation_error_with_file(self):
        """Test intent validation exception with file path."""
        errors = ["Error 1"]
        error = IntentValidationError(errors, "intent/powercli.intent.yaml")
        assert "powercli.intent.yaml" in str(error)

    def test_intent_not_found_error(self):
        """Test intent not found exception."""
        error = IntentNotFoundError()
        assert "intent" in str(error).lower()
        assert "extract" in str(error).lower()

    def test_intent_not_found_error_specific(self):
        """Test intent not found with specific type."""
        error = IntentNotFoundError("powercli")
        assert "powercli" in str(error)

    def test_merge_conflict_error(self):
        """Test merge conflict exception."""
        conflicts = ["Network mismatch", "Approval difference"]
        error = MergeConflictError(conflicts)
        assert "2 conflict" in str(error)
        assert "Network mismatch" in str(error)
        assert "--force" in str(error)

    def test_llm_provider_not_available_error(self):
        """Test LLM provider not available exception."""
        error = LLMProviderNotAvailableError("anthropic", "ANTHROPIC_API_KEY")
        assert "anthropic" in str(error)
        assert "ANTHROPIC_API_KEY" in str(error)

    def test_llm_api_error(self):
        """Test LLM API error exception."""
        error = LLMAPIError("OpenAI", "Rate limit exceeded", retry_count=3)
        assert "OpenAI" in str(error)
        assert "Rate limit" in str(error)
        assert "3 retries" in str(error)

    def test_profile_not_found_error(self):
        """Test profile not found exception."""
        error = ProfileNotFoundError("missing-profile", ["lab", "prod"])
        assert "missing-profile" in str(error)
        assert "lab" in str(error)
        assert "prod" in str(error)

    def test_artifact_validation_error(self):
        """Test artifact validation exception."""
        errors = ["Invalid YAML", "Missing field"]
        error = ArtifactValidationError("output/vm.yaml", errors)
        assert "output/vm.yaml" in str(error)
        assert "Invalid YAML" in str(error)


class TestErrorFormatting:
    """Tests for CLI error formatting."""

    def test_format_custom_error(self):
        """Test formatting of custom exception."""
        error = WorkspaceNotFoundError()
        formatted = format_error_for_cli(error)
        assert "[red]Error:[/red]" in formatted
        assert "workspace" in formatted.lower()

    def test_format_custom_error_with_suggestion(self):
        """Test formatting exception with suggestion."""
        error = InvalidSourceTypeError("bad")
        formatted = format_error_for_cli(error)
        assert "[red]Error:[/red]" in formatted
        assert "[yellow]" in formatted  # Suggestion formatting
        assert "powercli" in formatted.lower()

    def test_format_generic_error(self):
        """Test formatting generic exception."""
        error = ValueError("Generic error message")
        formatted = format_error_for_cli(error)
        assert "[red]Error:[/red]" in formatted
        assert "Generic error message" in formatted

    def test_format_file_not_found(self):
        """Test formatting file not found."""
        error = FileNotFoundError("/missing/file.ps1")
        formatted = format_error_for_cli(error)
        assert "/missing/file.ps1" in formatted
        assert "ls -l" in formatted


class TestRetryLogic:
    """Tests for retry mechanisms."""

    def test_retry_with_backoff_success_first_try(self):
        """Test successful operation on first try."""
        mock_func = Mock(return_value="success")

        @retry_with_backoff(max_attempts=3)
        def operation():
            return mock_func()

        result = operation()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_with_backoff_success_after_failures(self):
        """Test success after some failures."""
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def operation():
            result = mock_func()
            if isinstance(result, Exception):
                raise result
            return result

        result = operation()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_with_backoff_all_failures(self):
        """Test all attempts failing."""
        mock_func = Mock(side_effect=Exception("persistent error"))

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def operation():
            return mock_func()

        with pytest.raises(Exception):
            operation()

        assert mock_func.call_count == 3

    def test_retry_with_backoff_delays(self):
        """Test exponential backoff delays."""
        call_times = []
        mock_func = Mock(side_effect=Exception("error"))

        @retry_with_backoff(max_attempts=3, initial_delay=0.05, backoff_factor=2.0)
        def operation():
            call_times.append(time.time())
            return mock_func()

        with pytest.raises(Exception):
            operation()

        # Check that delays increased
        assert len(call_times) == 3
        # Second call should be ~0.05s after first
        delay1 = call_times[1] - call_times[0]
        # Third call should be ~0.1s after second
        delay2 = call_times[2] - call_times[1]

        assert 0.04 < delay1 < 0.08  # Allow some variance
        assert 0.08 < delay2 < 0.15

    def test_retry_with_custom_exceptions(self):
        """Test retry only on specific exceptions."""
        transient_error = ConnectionError("network error")
        permanent_error = ValueError("validation error")

        mock_func = Mock(side_effect=[transient_error, "success"])

        @retry_with_backoff(
            max_attempts=3, initial_delay=0.01, retryable_exceptions=(ConnectionError,)
        )
        def operation():
            result = mock_func()
            if isinstance(result, Exception):
                raise result
            return result

        # Should retry on ConnectionError
        result = operation()
        assert result == "success"
        assert mock_func.call_count == 2

        # Should not retry on ValueError
        mock_func.reset_mock()
        mock_func.side_effect = permanent_error

        @retry_with_backoff(
            max_attempts=3, initial_delay=0.01, retryable_exceptions=(ConnectionError,)
        )
        def operation2():
            return mock_func()

        with pytest.raises(ValueError):
            operation2()

        assert mock_func.call_count == 1  # No retries

    def test_retry_with_callback(self):
        """Test retry callback is called."""
        callback_calls = []

        def on_retry(error, attempt, max_attempts):
            callback_calls.append((error, attempt, max_attempts))

        mock_func = Mock(side_effect=[Exception("error1"), Exception("error2"), "success"])

        @retry_with_backoff(max_attempts=3, initial_delay=0.01, on_retry=on_retry)
        def operation():
            result = mock_func()
            if isinstance(result, Exception):
                raise result
            return result

        result = operation()

        assert result == "success"
        assert len(callback_calls) == 2  # Two retries
        assert callback_calls[0][1] == 1  # First attempt number
        assert callback_calls[1][1] == 2  # Second attempt number


class TestRetryableErrorDetection:
    """Tests for retryable error detection."""

    def test_is_retryable_connection_error(self):
        """Test connection errors are retryable."""
        assert is_retryable_error(Exception("connection timeout"))
        assert is_retryable_error(Exception("network unreachable"))
        assert is_retryable_error(Exception("Connection refused"))

    def test_is_retryable_timeout_error(self):
        """Test timeout errors are retryable."""
        assert is_retryable_error(Exception("timeout occurred"))
        assert is_retryable_error(Exception("request timed out"))

    def test_is_retryable_rate_limit_error(self):
        """Test rate limit errors are retryable."""
        assert is_retryable_error(Exception("rate limit exceeded"))
        assert is_retryable_error(Exception("429 Too Many Requests"))

    def test_is_retryable_server_error(self):
        """Test server errors are retryable."""
        assert is_retryable_error(Exception("500 Internal Server Error"))
        assert is_retryable_error(Exception("502 Bad Gateway"))
        assert is_retryable_error(Exception("503 Service Unavailable"))
        assert is_retryable_error(Exception("504 Gateway Timeout"))

    def test_is_retryable_capacity_error(self):
        """Test capacity errors are retryable."""
        assert is_retryable_error(Exception("service overloaded"))
        assert is_retryable_error(Exception("insufficient capacity"))

    def test_is_not_retryable_validation_error(self):
        """Test validation errors are not retryable."""
        assert not is_retryable_error(Exception("invalid input"))
        assert not is_retryable_error(Exception("schema validation failed"))

    def test_is_not_retryable_auth_error(self):
        """Test authentication errors are not retryable."""
        assert not is_retryable_error(Exception("401 Unauthorized"))
        assert not is_retryable_error(Exception("403 Forbidden"))
        assert not is_retryable_error(Exception("invalid api key"))


class TestRetryStrategies:
    """Tests for retry strategy presets."""

    def test_aggressive_strategy(self):
        """Test aggressive retry strategy."""
        params = RetryStrategy.apply("AGGRESSIVE")
        assert params["max_attempts"] == 5
        assert params["initial_delay"] == 0.5

    def test_moderate_strategy(self):
        """Test moderate retry strategy."""
        params = RetryStrategy.apply("MODERATE")
        assert params["max_attempts"] == 3
        assert params["initial_delay"] == 1.0

    def test_conservative_strategy(self):
        """Test conservative retry strategy."""
        params = RetryStrategy.apply("CONSERVATIVE")
        assert params["max_attempts"] == 2
        assert params["initial_delay"] == 2.0

    def test_llm_api_strategy(self):
        """Test LLM API retry strategy."""
        params = RetryStrategy.apply("LLM_API")
        assert params["max_attempts"] == 4
        assert params["max_delay"] == 60.0

    def test_rate_limit_strategy(self):
        """Test rate limit retry strategy."""
        params = RetryStrategy.apply("RATE_LIMIT")
        assert params["max_attempts"] == 5
        assert params["max_delay"] == 120.0


class TestRetryWithLogging:
    """Tests for retry with logging."""

    def test_retry_with_logging_callback(self):
        """Test retry calls logging callback."""
        log_messages = []

        def log_callback(msg):
            log_messages.append(msg)

        mock_func = Mock(side_effect=[Exception("error1"), Exception("error2"), "success"])

        @retry_with_logging(
            max_attempts=3, log_callback=log_callback, retryable_exceptions=(Exception,)
        )
        def operation():
            result = mock_func()
            if isinstance(result, Exception):
                raise result
            return result

        result = operation()

        assert result == "success"
        assert len(log_messages) == 2
        assert "error1" in log_messages[0]
        assert "Attempt 1/3" in log_messages[0]
        assert "error2" in log_messages[1]
        assert "Attempt 2/3" in log_messages[1]
