"""Exception hierarchy for the GDC uploader project.

This module defines custom exceptions used throughout the GDC uploader.
All exceptions inherit from GDCUploaderError and provide specific error
codes and messages for different failure scenarios.
"""

from typing import Optional, Dict, Any


class GDCUploaderError(Exception):
    """Base exception for all GDC uploader errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Unique error code for this type of error
        details: Additional error details
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Unique error code (e.g., "E001")
            details: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"[{self.error_code}] {self.message}"


# File Discovery Errors (E100-E199)

class FileDiscoveryError(GDCUploaderError):
    """Base exception for file discovery errors."""
    pass


class FileNotFoundError(FileDiscoveryError):
    """Raised when a required file cannot be found."""
    
    def __init__(self, filename: str, uuid: str, search_paths: Optional[list] = None):
        super().__init__(
            f"File '{filename}' with UUID '{uuid}' not found",
            "E101",
            {"filename": filename, "uuid": uuid, "search_paths": search_paths}
        )


class InvalidDirectoryError(FileDiscoveryError):
    """Raised when the specified directory is invalid or inaccessible."""
    
    def __init__(self, directory: str, reason: str):
        super().__init__(
            f"Invalid directory '{directory}': {reason}",
            "E102",
            {"directory": directory, "reason": reason}
        )


# Metadata Errors (E200-E299)

class MetadataError(GDCUploaderError):
    """Base exception for metadata-related errors."""
    pass


class InvalidMetadataError(MetadataError):
    """Raised when metadata is malformed or invalid."""
    
    def __init__(self, reason: str, metadata_path: Optional[str] = None):
        super().__init__(
            f"Invalid metadata: {reason}",
            "E201",
            {"reason": reason, "metadata_path": metadata_path}
        )


class MissingMetadataFieldError(MetadataError):
    """Raised when a required metadata field is missing."""
    
    def __init__(self, field_name: str, file_uuid: Optional[str] = None):
        super().__init__(
            f"Required metadata field '{field_name}' is missing",
            "E202",
            {"field_name": field_name, "file_uuid": file_uuid}
        )


# Authentication Errors (E300-E399)

class AuthenticationError(GDCUploaderError):
    """Base exception for authentication errors."""
    pass


class TokenFileNotFoundError(AuthenticationError):
    """Raised when the GDC token file cannot be found."""
    
    def __init__(self, token_path: str):
        super().__init__(
            f"GDC token file not found: {token_path}",
            "E301",
            {"token_path": token_path}
        )


class InvalidTokenError(AuthenticationError):
    """Raised when the GDC token is invalid or expired."""
    
    def __init__(self, reason: str):
        super().__init__(
            f"Invalid GDC token: {reason}",
            "E302",
            {"reason": reason}
        )


# Upload Errors (E400-E499)

class UploadError(GDCUploaderError):
    """Base exception for upload errors."""
    pass


class UploadFailedError(UploadError):
    """Raised when a file upload fails."""
    
    def __init__(
        self,
        filename: str,
        uuid: str,
        reason: str,
        attempts: int = 1,
        http_status: Optional[int] = None
    ):
        super().__init__(
            f"Failed to upload '{filename}': {reason}",
            "E401",
            {
                "filename": filename,
                "uuid": uuid,
                "reason": reason,
                "attempts": attempts,
                "http_status": http_status
            }
        )


class UploadTimeoutError(UploadError):
    """Raised when an upload times out."""
    
    def __init__(self, filename: str, uuid: str, timeout_seconds: int):
        super().__init__(
            f"Upload timeout for '{filename}' after {timeout_seconds} seconds",
            "E402",
            {
                "filename": filename,
                "uuid": uuid,
                "timeout_seconds": timeout_seconds
            }
        )


class ConcurrentUploadError(UploadError):
    """Raised when parallel upload encounters an error."""
    
    def __init__(self, failed_count: int, total_count: int, first_error: str):
        super().__init__(
            f"{failed_count} of {total_count} uploads failed",
            "E403",
            {
                "failed_count": failed_count,
                "total_count": total_count,
                "first_error": first_error
            }
        )


# Validation Errors (E500-E599)

class ValidationError(GDCUploaderError):
    """Base exception for validation errors."""
    pass


class ChecksumMismatchError(ValidationError):
    """Raised when file checksum doesn't match expected value."""
    
    def __init__(self, filename: str, expected: str, actual: str):
        super().__init__(
            f"Checksum mismatch for '{filename}'",
            "E501",
            {
                "filename": filename,
                "expected_checksum": expected,
                "actual_checksum": actual
            }
        )


class FileSizeError(ValidationError):
    """Raised when file size doesn't match expected value."""
    
    def __init__(self, filename: str, expected: int, actual: int):
        super().__init__(
            f"File size mismatch for '{filename}'",
            "E502",
            {
                "filename": filename,
                "expected_size": expected,
                "actual_size": actual
            }
        )


# Configuration Errors (E600-E699)

class ConfigurationError(GDCUploaderError):
    """Base exception for configuration errors."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_item: str, reason: str):
        super().__init__(
            f"Invalid configuration for '{config_item}': {reason}",
            "E601",
            {"config_item": config_item, "reason": reason}
        )


class MissingDependencyError(ConfigurationError):
    """Raised when a required dependency is missing."""
    
    def __init__(self, dependency: str, install_hint: Optional[str] = None):
        super().__init__(
            f"Missing required dependency: {dependency}",
            "E602",
            {"dependency": dependency, "install_hint": install_hint}
        )


# Report Generation Errors (E700-E799)

class ReportError(GDCUploaderError):
    """Base exception for report generation errors."""
    pass


class ReportGenerationError(ReportError):
    """Raised when report generation fails."""
    
    def __init__(self, reason: str, report_type: str):
        super().__init__(
            f"Failed to generate {report_type} report: {reason}",
            "E701",
            {"reason": reason, "report_type": report_type}
        )


class ReportSaveError(ReportError):
    """Raised when saving report fails."""
    
    def __init__(self, output_path: str, reason: str):
        super().__init__(
            f"Failed to save report to '{output_path}': {reason}",
            "E702",
            {"output_path": output_path, "reason": reason}
        )


# Plugin System Errors (E800-E899)

class PluginError(GDCUploaderError):
    """Base exception for plugin system errors."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin cannot be found."""
    
    def __init__(self, plugin_name: str):
        super().__init__(
            f"Plugin '{plugin_name}' not found",
            "E801",
            {"plugin_name": plugin_name}
        )


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    
    def __init__(self, plugin_name: str, reason: str):
        super().__init__(
            f"Failed to load plugin '{plugin_name}': {reason}",
            "E802",
            {"plugin_name": plugin_name, "reason": reason}
        )


# Exit Codes for CLI

class ExitCodes:
    """Standard exit codes for the GDC uploader CLI."""
    
    SUCCESS = 0
    GENERAL_ERROR = 1
    UPLOAD_FAILED = 2
    INVALID_METADATA = 3
    FILE_NOT_FOUND = 4
    AUTHENTICATION_ERROR = 5
    CONFIGURATION_ERROR = 6
    VALIDATION_ERROR = 7
    
    @classmethod
    def from_exception(cls, error: GDCUploaderError) -> int:
        """Get exit code from exception type."""
        error_code_prefix = error.error_code[1]  # E1xx -> 1, E2xx -> 2, etc.
        
        mapping = {
            '1': cls.FILE_NOT_FOUND,
            '2': cls.INVALID_METADATA,
            '3': cls.AUTHENTICATION_ERROR,
            '4': cls.UPLOAD_FAILED,
            '5': cls.VALIDATION_ERROR,
            '6': cls.CONFIGURATION_ERROR,
            '7': cls.GENERAL_ERROR,
            '8': cls.CONFIGURATION_ERROR,
        }
        
        return mapping.get(error_code_prefix, cls.GENERAL_ERROR)