"""GDC HTTP Upload - Simple file uploader to Genomic Data Commons."""

from .upload import (
    upload_file_with_progress, 
    main,
    SimpleProgress,
    detect_environment,
    get_progress_handler
)
from .validate import validate_manifest, validate_token, find_manifest_entry
from .utils import find_file, chunk_reader, format_size

__version__ = "1.0.0"
__all__ = [
    "upload_file_with_progress",
    "main",
    "SimpleProgress",
    "detect_environment", 
    "get_progress_handler",
    "validate_manifest", 
    "validate_token",
    "find_manifest_entry",
    "find_file",
    "chunk_reader",
    "format_size",
]