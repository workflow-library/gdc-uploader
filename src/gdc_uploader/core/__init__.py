"""Core components for GDC uploader."""

from .base_uploader import (
    BaseUploader,
    FileEntry,
    UploadResult,
    UploadProgress,
    UploadStatus,
    FileDiscoveryStrategy,
    ProgressMonitor
)
from .exceptions import (
    GDCUploaderError,
    FileNotFoundError,
    InvalidMetadataError,
    UploadFailedError,
    ValidationError
)

__all__ = [
    # Base classes
    'BaseUploader',
    'FileDiscoveryStrategy',
    'ProgressMonitor',
    
    # Data classes
    'FileEntry',
    'UploadResult',
    'UploadProgress',
    'UploadStatus',
    
    # Exceptions
    'GDCUploaderError',
    'FileNotFoundError',
    'InvalidMetadataError',
    'UploadFailedError',
    'ValidationError',
]