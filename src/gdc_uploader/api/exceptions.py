"""Custom exceptions for GDC API operations.

This module defines all custom exceptions used by the GDC API client,
providing detailed error information and proper exception hierarchy.
"""

from typing import Optional, Dict, Any


class GDCAPIException(Exception):
    """Base exception for all GDC API errors.
    
    This is the parent class for all GDC-specific exceptions.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        response: Optional[Any] = None
    ):
        """Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code from the API
            details: Optional dictionary with additional error details
            response: Optional response object that caused the error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.response = response
    
    def __str__(self):
        """String representation of the exception."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def __repr__(self):
        """Detailed representation of the exception."""
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r})"


class GDCAuthenticationError(GDCAPIException):
    """Raised when authentication fails.
    
    This includes:
    - Invalid tokens
    - Expired tokens
    - Missing authentication
    - Insufficient permissions
    """
    pass


class GDCRateLimitError(GDCAPIException):
    """Raised when API rate limit is exceeded.
    
    Includes information about when to retry.
    """
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class GDCServerError(GDCAPIException):
    """Raised for server-side errors (5xx status codes).
    
    These are typically temporary errors that may succeed on retry.
    """
    pass


class GDCConnectionError(GDCAPIException):
    """Raised for connection-related errors.
    
    This includes:
    - Network timeouts
    - DNS failures
    - Connection refused
    - SSL/TLS errors
    """
    pass


class GDCValidationError(GDCAPIException):
    """Raised for validation errors (4xx status codes).
    
    This includes:
    - Invalid request parameters
    - Missing required fields
    - Invalid file formats
    - Business logic violations
    """
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Optional field name that failed validation
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.field = field


class GDCFileNotFoundError(GDCAPIException):
    """Raised when a requested file is not found in GDC."""
    pass


class GDCProjectNotFoundError(GDCAPIException):
    """Raised when a requested project is not found in GDC."""
    pass


class GDCUploadError(GDCAPIException):
    """Raised when file upload fails.
    
    This includes:
    - Checksum mismatches
    - File too large
    - Invalid file format
    - Upload interrupted
    """
    
    def __init__(
        self,
        message: str,
        file_id: Optional[str] = None,
        uploaded_bytes: Optional[int] = None,
        total_bytes: Optional[int] = None,
        **kwargs
    ):
        """Initialize upload error.
        
        Args:
            message: Error message
            file_id: UUID of the file being uploaded
            uploaded_bytes: Number of bytes successfully uploaded
            total_bytes: Total file size
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.file_id = file_id
        self.uploaded_bytes = uploaded_bytes
        self.total_bytes = total_bytes


class GDCChecksumError(GDCUploadError):
    """Raised when file checksum doesn't match expected value."""
    
    def __init__(
        self,
        message: str,
        expected_checksum: Optional[str] = None,
        actual_checksum: Optional[str] = None,
        **kwargs
    ):
        """Initialize checksum error.
        
        Args:
            message: Error message
            expected_checksum: Expected checksum value
            actual_checksum: Actual checksum value
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.expected_checksum = expected_checksum
        self.actual_checksum = actual_checksum


class GDCTimeoutError(GDCConnectionError):
    """Raised when an operation times out."""
    pass


class GDCRetryExhaustedError(GDCAPIException):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(
        self,
        message: str,
        attempts: Optional[int] = None,
        last_error: Optional[Exception] = None,
        **kwargs
    ):
        """Initialize retry exhausted error.
        
        Args:
            message: Error message
            attempts: Number of attempts made
            last_error: The last error encountered
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.attempts = attempts
        self.last_error = last_error