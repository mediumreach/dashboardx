"""
Error Handler Utilities

Provides centralized error handling, logging, and context building
for consistent error management across the application.
"""

import logging
import traceback
import sys
from typing import Optional, Dict, Any, Type
from datetime import datetime

from app.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: int = logging.ERROR,
    include_traceback: bool = True
) -> None:
    """
    Log an error with context and optional traceback
    
    Args:
        error: The exception to log
        context: Additional context information
        level: Logging level (default: ERROR)
        include_traceback: Whether to include full traceback
    """
    error_info = build_error_context(error, context)
    
    log_message = f"{error_info['error_type']}: {error_info['message']}"
    
    extra = {
        "error_code": error_info.get("error_code"),
        "error_type": error_info["error_type"],
        "context": error_info.get("context", {}),
        "timestamp": error_info["timestamp"]
    }
    
    if include_traceback:
        logger.log(level, log_message, exc_info=True, extra=extra)
    else:
        logger.log(level, log_message, extra=extra)


def build_error_context(
    error: Exception,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build comprehensive error context for logging and debugging
    
    Args:
        error: The exception to build context for
        additional_context: Additional context to include
        
    Returns:
        Dictionary with error information and context
    """
    context = {
        "error_type": type(error).__name__,
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add error code if it's an AppException
    if isinstance(error, AppException):
        context["error_code"] = error.error_code.value
        context["context"] = error.context
        if error.original_error:
            context["original_error"] = {
                "type": type(error.original_error).__name__,
                "message": str(error.original_error)
            }
    
    # Add additional context
    if additional_context:
        if "context" in context:
            context["context"].update(additional_context)
        else:
            context["context"] = additional_context
    
    return context


def format_traceback(error: Exception) -> str:
    """
    Format exception traceback as a string
    
    Args:
        error: The exception to format
        
    Returns:
        Formatted traceback string
    """
    return ''.join(traceback.format_exception(
        type(error),
        error,
        error.__traceback__
    ))


def get_error_response(
    error: Exception,
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Convert an exception to an API error response
    
    Args:
        error: The exception to convert
        include_details: Whether to include detailed error information
        
    Returns:
        Dictionary suitable for API error response
    """
    if isinstance(error, AppException):
        response = error.to_dict()
    else:
        response = {
            "error": str(error),
            "error_code": ErrorCode.INTERNAL_ERROR.value
        }
    
    if include_details:
        response["details"] = {
            "type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Include traceback in development mode
        if include_details:
            response["details"]["traceback"] = format_traceback(error)
    
    return response


def handle_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True,
    log_level: int = logging.ERROR
) -> Optional[Dict[str, Any]]:
    """
    Centralized exception handler
    
    Args:
        error: The exception to handle
        context: Additional context information
        reraise: Whether to re-raise the exception after handling
        log_level: Logging level for the error
        
    Returns:
        Error response dictionary if not re-raising
        
    Raises:
        The original exception if reraise is True
    """
    # Log the error
    log_error(error, context, log_level)
    
    # Get error response
    error_response = get_error_response(error)
    
    # Re-raise if requested
    if reraise:
        raise
    
    return error_response


def wrap_exception(
    original_error: Exception,
    exception_class: Type[AppException],
    message: str,
    error_code: Optional[ErrorCode] = None,
    context: Optional[Dict[str, Any]] = None
) -> AppException:
    """
    Wrap an exception in a custom AppException
    
    Args:
        original_error: The original exception
        exception_class: The AppException class to wrap with
        message: Human-readable error message
        error_code: Error code for the exception
        context: Additional context
        
    Returns:
        Wrapped exception
    """
    kwargs = {
        "message": message,
        "context": context,
        "original_error": original_error
    }
    
    if error_code:
        kwargs["error_code"] = error_code
    
    return exception_class(**kwargs)


class ErrorContext:
    """
    Context manager for error handling with automatic logging
    
    Example:
        with ErrorContext("Processing document", document_id=doc_id):
            process_document(doc_id)
    """
    
    def __init__(
        self,
        operation: str,
        log_level: int = logging.ERROR,
        reraise: bool = True,
        **context
    ):
        self.operation = operation
        self.log_level = log_level
        self.reraise = reraise
        self.context = context
        self.error: Optional[Exception] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error = exc_val
            
            # Add operation to context
            full_context = {
                "operation": self.operation,
                **self.context
            }
            
            # Log the error
            log_error(exc_val, full_context, self.log_level)
            
            # Return False to re-raise, True to suppress
            return not self.reraise
        
        return False


def safe_execute(
    func,
    *args,
    default=None,
    log_errors: bool = True,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Safely execute a function and return default value on error
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default: Default value to return on error
        log_errors: Whether to log errors
        context: Additional context for error logging
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            log_error(e, context, level=logging.WARNING)
        return default


async def async_safe_execute(
    func,
    *args,
    default=None,
    log_errors: bool = True,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Async version of safe_execute
    
    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        default: Default value to return on error
        log_errors: Whether to log errors
        context: Additional context for error logging
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or default value on error
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            log_error(e, context, level=logging.WARNING)
        return default
