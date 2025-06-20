#!/usr/bin/env python3
"""
Utility functions for GDC uploader.
"""

from pathlib import Path
from typing import Optional, Iterator


def find_file(filename: str, search_dirs: Optional[list] = None) -> Optional[Path]:
    """
    Find file in current directory or common subdirectories.
    
    Args:
        filename: Name of file to find
        search_dirs: List of directories to search (default: common data dirs)
        
    Returns:
        Path to file if found, None otherwise
    """
    if search_dirs is None:
        search_dirs = ['fastq', 'bam', 'data', 'files', '.']
    
    # Check if file exists as given
    file_path = Path(filename)
    if file_path.exists():
        return file_path
    
    # Search in subdirectories
    for subdir in search_dirs:
        candidate = Path(subdir) / filename
        if candidate.exists():
            return candidate
    
    return None


def chunk_reader(file_obj, chunk_size: int, callback=None) -> Iterator[bytes]:
    """
    Read file in chunks with optional callback.
    
    Args:
        file_obj: File object to read
        chunk_size: Size of chunks in bytes
        callback: Optional callback function called with chunk size
        
    Yields:
        Chunks of file data
    """
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        if callback:
            callback(len(chunk))
        yield chunk


def format_size(size_bytes: int) -> str:
    """
    Format byte size as human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"