"""GDC API Client Package.

This package provides a comprehensive client library for interacting with
the Genomic Data Commons (GDC) API, including file uploads, metadata operations,
and project management.
"""

from .client import GDCAPIClient, TokenBucket
from .async_client import AsyncGDCAPIClient, AsyncTokenBucket
from .auth import (
    TokenManager,
    TokenProvider,
    FileTokenProvider,
    EnvironmentTokenProvider,
    StaticTokenProvider,
    CachedTokenProvider
)
from .exceptions import (
    GDCAPIException,
    GDCAuthenticationError,
    GDCRateLimitError,
    GDCServerError,
    GDCConnectionError,
    GDCValidationError,
    GDCFileNotFoundError,
    GDCProjectNotFoundError,
    GDCUploadError,
    GDCChecksumError,
    GDCTimeoutError,
    GDCRetryExhaustedError
)
from .models import (
    FileUploadRequest,
    FileUploadResponse,
    FileStatus,
    FileState,
    UploadStatus,
    ProjectInfo,
    ProjectState,
    TokenValidationResponse,
    GDCError,
    BatchUploadRequest,
    BatchUploadResponse,
    FileMetadata,
    UploadManifest
)

__version__ = "2.0.0"
__author__ = "GDC Uploader Team"

__all__ = [
    # Client
    "GDCAPIClient",
    "TokenBucket",
    "AsyncGDCAPIClient",
    "AsyncTokenBucket",
    
    # Authentication
    "TokenManager",
    "TokenProvider",
    "FileTokenProvider",
    "EnvironmentTokenProvider",
    "StaticTokenProvider",
    "CachedTokenProvider",
    
    # Exceptions
    "GDCAPIException",
    "GDCAuthenticationError",
    "GDCRateLimitError",
    "GDCServerError",
    "GDCConnectionError",
    "GDCValidationError",
    "GDCFileNotFoundError",
    "GDCProjectNotFoundError",
    "GDCUploadError",
    "GDCChecksumError",
    "GDCTimeoutError",
    "GDCRetryExhaustedError",
    
    # Models
    "FileUploadRequest",
    "FileUploadResponse",
    "FileStatus",
    "FileState",
    "UploadStatus",
    "ProjectInfo",
    "ProjectState",
    "TokenValidationResponse",
    "GDCError",
    "BatchUploadRequest",
    "BatchUploadResponse",
    "FileMetadata",
    "UploadManifest",
]