"""
Test unified error handling across providers.
"""
import pytest
from mindiv.providers.exceptions import (
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderInvalidRequestError,
    ProviderNotFoundError,
    ProviderServerError,
)


def test_provider_error_basic():
    """Test basic ProviderError creation."""
    error = ProviderError(
        provider="test",
        message="Test error",
        status_code=502,
        error_code="test_error",
    )
    
    assert error.provider == "test"
    assert error.message == "Test error"
    assert error.status_code == 502
    assert error.error_code == "test_error"
    assert str(error) == "Test error"


def test_provider_error_to_dict():
    """Test ProviderError to_dict conversion."""
    error = ProviderError(
        provider="openai",
        message="API error",
        status_code=502,
        error_code="api_error",
        details={"retry_after": 60},
    )
    
    result = error.to_dict()
    assert result["type"] == "ProviderError"
    assert result["message"] == "API error"
    assert result["code"] == "api_error"
    assert result["provider"] == "openai"
    assert result["details"]["retry_after"] == 60


def test_provider_auth_error():
    """Test ProviderAuthError."""
    error = ProviderAuthError(
        provider="openai",
        message="Invalid API key",
    )
    
    assert error.status_code == 401
    assert error.error_code == "auth_error"
    assert error.message == "Invalid API key"


def test_provider_rate_limit_error():
    """Test ProviderRateLimitError."""
    error = ProviderRateLimitError(
        provider="anthropic",
        message="Rate limit exceeded",
    )
    
    assert error.status_code == 429
    assert error.error_code == "rate_limit_error"


def test_provider_timeout_error():
    """Test ProviderTimeoutError."""
    error = ProviderTimeoutError(
        provider="gemini",
        message="Request timeout",
    )
    
    assert error.status_code == 504
    assert error.error_code == "timeout_error"


def test_provider_invalid_request_error():
    """Test ProviderInvalidRequestError."""
    error = ProviderInvalidRequestError(
        provider="openai",
        message="Invalid parameters",
    )
    
    assert error.status_code == 400
    assert error.error_code == "invalid_request_error"


def test_provider_not_found_error():
    """Test ProviderNotFoundError."""
    error = ProviderNotFoundError(
        provider="openai",
        message="Model not found",
    )
    
    assert error.status_code == 404
    assert error.error_code == "not_found_error"


def test_provider_server_error():
    """Test ProviderServerError."""
    error = ProviderServerError(
        provider="anthropic",
        message="Internal server error",
        status_code=500,
    )
    
    assert error.status_code == 500
    assert error.error_code == "server_error"


def test_error_with_original_exception():
    """Test error with original exception."""
    original = ValueError("Original error")
    error = ProviderError(
        provider="test",
        message="Wrapped error",
        original_error=original,
    )
    
    assert error.original_error is original
    assert isinstance(error.original_error, ValueError)


def test_error_inheritance():
    """Test error class inheritance."""
    auth_error = ProviderAuthError("test", "Auth failed")
    
    assert isinstance(auth_error, ProviderError)
    assert isinstance(auth_error, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

