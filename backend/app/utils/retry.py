"""
Retry Decorator and Utilities

Provides decorators and utilities for retrying operations with
exponential backoff, particularly useful for transient failures
in database operations and external API calls.
"""

import time
import logging
import functools
from typing import Callable, Type, Tuple, Optional, Any
import asyncio

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator to retry a function with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def fetch_data():
            # This will retry up to 3 times with exponential backoff
            return api.get_data()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            exc_info=True,
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "error": str(e)
                            }
                        )
                        raise
                    
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s...",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": current_delay,
                            "error": str(e)
                        }
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Async version of retry decorator
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Example:
        @async_retry(max_attempts=3, delay=1.0, backoff=2.0)
        async def fetch_data():
            # This will retry up to 3 times with exponential backoff
            return await api.get_data()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_attempts} attempts",
                            exc_info=True,
                            extra={
                                "function": func.__name__,
                                "attempts": max_attempts,
                                "error": str(e)
                            }
                        )
                        raise
                    
                    logger.warning(
                        f"Async function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s...",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": current_delay,
                            "error": str(e)
                        }
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_on_db_error(max_attempts: int = 3, delay: float = 0.5):
    """
    Specialized retry decorator for database operations
    
    Retries on common database errors like connection issues,
    deadlocks, and timeouts.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
    """
    # Import here to avoid circular dependencies
    from app.exceptions import DatabaseException
    
    return retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=2.0,
        exceptions=(DatabaseException, ConnectionError, TimeoutError)
    )


def retry_on_external_api_error(max_attempts: int = 3, delay: float = 1.0):
    """
    Specialized retry decorator for external API calls
    
    Retries on common API errors like timeouts, rate limits,
    and temporary unavailability.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
    """
    # Import here to avoid circular dependencies
    from app.exceptions import ExternalServiceException
    
    return retry(
        max_attempts=max_attempts,
        delay=delay,
        backoff=2.0,
        exceptions=(ExternalServiceException, ConnectionError, TimeoutError)
    )


class RetryContext:
    """
    Context manager for retry logic with more control
    
    Example:
        with RetryContext(max_attempts=3) as retry_ctx:
            for attempt in retry_ctx:
                try:
                    result = perform_operation()
                    break
                except Exception as e:
                    if not retry_ctx.should_retry(e):
                        raise
                    retry_ctx.wait()
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.initial_delay = delay
        self.current_delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.attempt = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def __iter__(self):
        self.attempt = 0
        return self
    
    def __next__(self):
        self.attempt += 1
        if self.attempt > self.max_attempts:
            raise StopIteration
        return self.attempt
    
    def should_retry(self, exception: Exception) -> bool:
        """Check if the exception should trigger a retry"""
        return isinstance(exception, self.exceptions) and self.attempt < self.max_attempts
    
    def wait(self):
        """Wait before the next retry"""
        if self.attempt < self.max_attempts:
            logger.info(
                f"Retrying in {self.current_delay}s (attempt {self.attempt}/{self.max_attempts})"
            )
            time.sleep(self.current_delay)
            self.current_delay *= self.backoff
    
    def reset(self):
        """Reset the retry context"""
        self.attempt = 0
        self.current_delay = self.initial_delay
