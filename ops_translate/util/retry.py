"""
Retry logic with exponential backoff for resilient operations.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from ops_translate.exceptions import RetryableError

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int, int], None] | None = None,
):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each failure (default: 2.0)
        max_delay: Maximum delay between retries (default: 60.0)
        retryable_exceptions: Tuple of exception types to retry (default: all)
        on_retry: Optional callback called on each retry: (error, attempt, max_attempts)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=2.0)
        def call_api():
            response = requests.get("https://api.example.com")
            response.raise_for_status()
            return response.json()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        # Final attempt failed, raise the error
                        break

                    # Call retry callback if provided
                    if on_retry is not None:
                        on_retry(e, attempt, max_attempts)

                    # Wait before retrying
                    time.sleep(min(delay, max_delay))

                    # Increase delay for next attempt
                    delay *= backoff_factor

            # All retries exhausted
            assert last_exception is not None  # Always set in the except block
            raise RetryableError(last_exception, max_attempts, max_attempts)

        return wrapper

    return decorator


def retry_on_rate_limit(
    max_attempts: int = 5, initial_delay: float = 5.0, backoff_factor: float = 2.0
):
    """
    Specialized retry for rate limit errors (longer delays).

    Args:
        max_attempts: Maximum number of attempts (default: 5)
        initial_delay: Initial delay in seconds (default: 5.0)
        backoff_factor: Multiplier for delay (default: 2.0)

    Returns:
        Decorated function

    Example:
        @retry_on_rate_limit()
        def call_llm_api(prompt):
            return anthropic_client.messages.create(...)
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        max_delay=120.0,  # Up to 2 minutes for rate limits
        retryable_exceptions=(Exception,),  # Catch all, filter in callback
    )


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should be retried.

    Args:
        error: The exception to check

    Returns:
        True if error should be retried

    Retryable errors include:
    - Network errors
    - Timeout errors
    - Rate limit errors (429)
    - Server errors (500-599)
    """
    error_msg = str(error).lower()

    # Network/connection errors
    if any(
        keyword in error_msg
        for keyword in [
            "connection",
            "timeout",
            "timed out",
            "network",
            "unreachable",
        ]
    ):
        return True

    # Rate limiting
    if "rate limit" in error_msg or "429" in error_msg:
        return True

    # Server errors
    if any(
        keyword in error_msg
        for keyword in ["500", "502", "503", "504", "server error", "internal error"]
    ):
        return True

    # API-specific errors
    if "overloaded" in error_msg or "capacity" in error_msg:
        return True

    return False


def retry_with_logging(
    max_attempts: int = 3,
    log_callback: Callable[[str], None] | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Retry decorator with logging support.

    Args:
        max_attempts: Maximum number of attempts
        log_callback: Function to call with log messages
        retryable_exceptions: Exceptions to retry

    Returns:
        Decorated function

    Example:
        def log_retry(msg):
            print(f"[RETRY] {msg}")

        @retry_with_logging(max_attempts=3, log_callback=log_retry)
        def flaky_operation():
            # Operation that might fail
            pass
    """

    def on_retry_callback(error: Exception, attempt: int, max_attempts: int):
        if log_callback is not None:
            log_callback(f"Attempt {attempt}/{max_attempts} failed: {str(error)}. Retrying...")

    return retry_with_backoff(
        max_attempts=max_attempts,
        retryable_exceptions=retryable_exceptions,
        on_retry=on_retry_callback,
    )


class RetryStrategy:
    """
    Configurable retry strategy for different scenarios.
    """

    # Preset strategies
    AGGRESSIVE = {
        "max_attempts": 5,
        "initial_delay": 0.5,
        "backoff_factor": 1.5,
        "max_delay": 10.0,
    }

    MODERATE = {
        "max_attempts": 3,
        "initial_delay": 1.0,
        "backoff_factor": 2.0,
        "max_delay": 30.0,
    }

    CONSERVATIVE = {
        "max_attempts": 2,
        "initial_delay": 2.0,
        "backoff_factor": 3.0,
        "max_delay": 60.0,
    }

    LLM_API = {
        "max_attempts": 4,
        "initial_delay": 2.0,
        "backoff_factor": 2.0,
        "max_delay": 60.0,
    }

    RATE_LIMIT = {
        "max_attempts": 5,
        "initial_delay": 5.0,
        "backoff_factor": 2.0,
        "max_delay": 120.0,
    }

    @staticmethod
    def apply(strategy_name: str = "MODERATE") -> dict:
        """
        Get retry parameters for a named strategy.

        Args:
            strategy_name: Name of the strategy
                (AGGRESSIVE, MODERATE, CONSERVATIVE, LLM_API, RATE_LIMIT)

        Returns:
            Dictionary of retry parameters

        Example:
            params = RetryStrategy.apply("LLM_API")
            @retry_with_backoff(**params)
            def call_llm():
                ...
        """
        strategy = getattr(RetryStrategy, strategy_name, RetryStrategy.MODERATE)
        return strategy.copy()
