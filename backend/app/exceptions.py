"""
Custom Exception Classes for Application

Provides a hierarchy of custom exceptions with error codes,
context, and structured error information for better error handling.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for different types of exceptions"""
    
    # General errors (1000-1099)
    UNKNOWN_ERROR = "ERR_1000"
    INTERNAL_ERROR = "ERR_1001"
    NOT_IMPLEMENTED = "ERR_1002"
    
    # Authentication errors (1100-1199)
    AUTH_INVALID_TOKEN = "ERR_1100"
    AUTH_EXPIRED_TOKEN = "ERR_1101"
    AUTH_MISSING_TOKEN = "ERR_1102"
    AUTH_INVALID_CREDENTIALS = "ERR_1103"
    AUTH_INSUFFICIENT_PERMISSIONS = "ERR_1104"
    AUTH_USER_NOT_FOUND = "ERR_1105"
    AUTH_USER_INACTIVE = "ERR_1106"
    
    # Validation errors (1200-1299)
    VALIDATION_ERROR = "ERR_1200"
    VALIDATION_MISSING_FIELD = "ERR_1201"
    VALIDATION_INVALID_FORMAT = "ERR_1202"
    VALIDATION_OUT_OF_RANGE = "ERR_1203"
    VALIDATION_DUPLICATE = "ERR_1204"
    
    # Database errors (1300-1399)
    DB_CONNECTION_ERROR = "ERR_1300"
    DB_QUERY_ERROR = "ERR_1301"
    DB_NOT_FOUND = "ERR_1302"
    DB_CONSTRAINT_VIOLATION = "ERR_1303"
    DB_TRANSACTION_ERROR = "ERR_1304"
    
    # RAG errors (1400-1499)
    RAG_DOCUMENT_NOT_FOUND = "ERR_1400"
    RAG_INGESTION_ERROR = "ERR_1401"
    RAG_EMBEDDING_ERROR = "ERR_1402"
    RAG_RETRIEVAL_ERROR = "ERR_1403"
    RAG_CHUNKING_ERROR = "ERR_1404"
    RAG_INDEX_ERROR = "ERR_1405"
    RAG_QUERY_ERROR = "ERR_1406"
    
    # Agent errors (1500-1599)
    AGENT_EXECUTION_ERROR = "ERR_1500"
    AGENT_TIMEOUT = "ERR_1501"
    AGENT_INVALID_STATE = "ERR_1502"
    AGENT_TOOL_ERROR = "ERR_1503"
    AGENT_NOT_FOUND = "ERR_1504"
    
    # External service errors (1600-1699)
    EXTERNAL_API_ERROR = "ERR_1600"
    EXTERNAL_TIMEOUT = "ERR_1601"
    EXTERNAL_RATE_LIMIT = "ERR_1602"
    EXTERNAL_UNAVAILABLE = "ERR_1603"
    
    # Configuration errors (1700-1799)
    CONFIG_MISSING = "ERR_1700"
    CONFIG_INVALID = "ERR_1701"
    CONFIG_LOAD_ERROR = "ERR_1702"
    
    # Analytics errors (1800-1899)
    ANALYTICS_PROCESSING_ERROR = "ERR_1800"
    ANALYTICS_INVALID_DATA = "ERR_1801"
    ANALYTICS_CONNECTOR_ERROR = "ERR_1802"


class AppException(Exception):
    """
    Base exception class for all application exceptions
    
    Attributes:
        message: Human-readable error message
        error_code: Unique error code for the exception
        context: Additional context information
        original_error: Original exception if this wraps another exception
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_error = original_error
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        result = {
            "error": self.message,
            "error_code": self.error_code.value,
            "context": self.context
        }
        if self.original_error:
            result["original_error"] = str(self.original_error)
        return result
    
    def __str__(self) -> str:
        """String representation of the exception"""
        parts = [f"{self.error_code.value}: {self.message}"]
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.original_error:
            parts.append(f"Original: {str(self.original_error)}")
        return " | ".join(parts)


class AuthenticationException(AppException):
    """Exception raised for authentication-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.AUTH_INVALID_TOKEN,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message, error_code, context, original_error)


class ValidationException(AppException):
    """Exception raised for validation errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        ctx = context or {}
        if field:
            ctx["field"] = field
        super().__init__(message, error_code, ctx, original_error)


class DatabaseException(AppException):
    """Exception raised for database-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DB_QUERY_ERROR,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        ctx = context or {}
        if query:
            ctx["query"] = query
        super().__init__(message, error_code, ctx, original_error)


class RAGException(AppException):
    """Exception raised for RAG-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.RAG_QUERY_ERROR,
        document_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        ctx = context or {}
        if document_id:
            ctx["document_id"] = document_id
        super().__init__(message, error_code, ctx, original_error)


class AgentException(AppException):
    """Exception raised for agent-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.AGENT_EXECUTION_ERROR,
        agent_id: Optional[str] = None,
        state: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        ctx = context or {}
        if agent_id:
            ctx["agent_id"] = agent_id
        if state:
            ctx["state"] = state
        super().__init__(message, error_code, ctx, original_error)


class ExternalServiceException(AppException):
    """Exception raised for external service errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.EXTERNAL_API_ERROR,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        ctx = context or {}
        if service_name:
            ctx["service_name"] = service_name
        if status_code:
            ctx["status_code"] = status_code
        super().__init__(message, error_code, ctx, original_error)


class ConfigurationException(AppException):
    """Exception raised for configuration errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.CONFIG_INVALID,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        ctx = context or {}
        if config_key:
            ctx["config_key"] = config_key
        super().__init__(message, error_code, ctx, original_error)


class AnalyticsException(AppException):
    """Exception raised for analytics-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.ANALYTICS_PROCESSING_ERROR,
        data_source: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        ctx = context or {}
        if data_source:
            ctx["data_source"] = data_source
        super().__init__(message, error_code, ctx, original_error)
