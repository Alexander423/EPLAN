"""
Retry decorator with exponential backoff for network operations.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, TypeVar

from ..constants import MAX_RETRIES, RETRY_BASE_DELAY, RETRY_MAX_DELAY, T
from .logging import get_logger


def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback called on each retry with (exception, attempt)

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger()
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}"
                        )

            raise last_exception  # type: ignore

        return wrapper
    return decorator
