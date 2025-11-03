"""
Unified exception handling for all LLM providers.
Provides consistent error types and status codes across different providers.
"""
from typing import Optional, Dict, Any


class ProviderError(Exception):
    """Base exception for all provider errors."""
    
    def __init__(
        self,
        provider: str,
        message: str,
        original_error: Optional[Exception] = None,
        status_code: int = 502,
        error_code: str = "provider_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize provider error.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic', 'gemini')
            message: Human-readable error message
            original_error: Original exception that was caught
            status_code: HTTP status code to return
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.provider = provider
        self.message = message
        self.original_error = original_error
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        result = {
            "type": self.__class__.__name__,
            "message": self.message,
            "code": self.error_code,
            "provider": self.provider,
        }
        if self.details:
            result["details"] = self.details
        return result


class ProviderAuthError(ProviderError):
    """Authentication error (invalid API key, etc.)."""
    
    def __init__(
        self,
        provider: str,
        message: str = "Authentication failed",
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            original_error=original_error,
            status_code=401,
            error_code="auth_error",
            details=details,
        )


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        provider: str,
        message: str = "Rate limit exceeded",
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            original_error=original_error,
            status_code=429,
            error_code="rate_limit_error",
            details=details,
        )


class ProviderTimeoutError(ProviderError):
    """Request timeout error."""
    
    def __init__(
        self,
        provider: str,
        message: str = "Request timeout",
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            original_error=original_error,
            status_code=504,
            error_code="timeout_error",
            details=details,
        )


class ProviderInvalidRequestError(ProviderError):
    """Invalid request error (bad parameters, etc.)."""
    
    def __init__(
        self,
        provider: str,
        message: str = "Invalid request",
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            original_error=original_error,
            status_code=400,
            error_code="invalid_request_error",
            details=details,
        )


class ProviderNotFoundError(ProviderError):
    """Resource not found error."""
    
    def __init__(
        self,
        provider: str,
        message: str = "Resource not found",
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            original_error=original_error,
            status_code=404,
            error_code="not_found_error",
            details=details,
        )


class ProviderServerError(ProviderError):
    """Server error (5xx errors from provider)."""
    
    def __init__(
        self,
        provider: str,
        message: str = "Provider server error",
        original_error: Optional[Exception] = None,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            original_error=original_error,
            status_code=status_code,
            error_code="server_error",
            details=details,
        )

