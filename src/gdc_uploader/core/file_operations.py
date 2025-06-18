"""File operations module for GDC uploader.

This module consolidates file discovery, validation, and filtering logic
that was previously duplicated across multiple upload scripts.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Set, Tuple, Callable
from dataclasses import dataclass, field
from fnmatch import fnmatch
import json

# Import from Agent 1's interfaces
import sys
sys.path.append('/workspaces/gdc-uploader-agents/agent-1-core-architecture/specs/interfaces')
from base_uploader_interface import FileEntry, FileDiscoveryStrategy
from exceptions_interface import (
    FileNotFoundError as GDCFileNotFoundError,
    InvalidDirectoryError,
    ValidationError,
    FileSizeError,
    ChecksumMismatchError
)

logger = logging.getLogger(__name__)


@dataclass
class FileSearchConfig:
    """Configuration for file discovery operations."""
    
    # Common subdirectories to search first
    subdirectories: List[str] = field(default_factory=lambda: [
        "fastq", "uBam", "sequence-files", "sequences", 
        "data", "files", "uploads", "output"
    ])
    
    # File patterns to include/exclude
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.tmp", "*.temp", "*.log", "*.md", ".DS_Store", ".*"
    ])
    
    # Search behavior flags
    recursive: bool = True
    follow_symlinks: bool = False
    case_sensitive: bool = True
    max_depth: Optional[int] = None
    
    # Validation options
    validate_checksums: bool = False
    validate_sizes: bool = True
    require_all_files: bool = True


class StandardFileDiscoveryStrategy(FileDiscoveryStrategy):
    """Standard file discovery implementation with configurable search patterns."""
    
    def __init__(self, config: Optional[FileSearchConfig] = None):
        """Initialize with configuration.
        
        Args:
            config: Search configuration (uses defaults if None)
        """
        self.config = config or FileSearchConfig()
        
    def discover(self, base_directory: Path, metadata: Dict[str, Any]) -> Iterator[FileEntry]:
        """Discover files matching the metadata.
        
        This method implements the standard search pattern used across all
        GDC upload scripts:
        1. Check common subdirectories first
        2. Fall back to recursive search if needed
        3. Apply include/exclude patterns
        
        Args:
            base_directory: Base directory to search
            metadata: GDC metadata for matching
            
        Yields:
            FileEntry objects for discovered files
        """
        if not base_directory.exists():
            raise InvalidDirectoryError(str(base_directory), "Directory does not exist")
            
        if not base_directory.is_dir():
            raise InvalidDirectoryError(str(base_directory), "Path is not a directory")
            
        # Extract file information from metadata
        file_specs = self._extract_file_specs(metadata)
        
        # Track which files we've found
        found_files: Set[str] = set()
        
        # First, try common subdirectories
        for file_uuid, file_info in file_specs.items():
            filename = file_info["filename"]
            
            # Skip if already found
            if file_uuid in found_files:
                continue
                
            # Check subdirectories first
            file_path = self._search_subdirectories(base_directory, filename)
            
            # If not found in subdirectories, search recursively
            if not file_path and self.config.recursive:
                file_path = self._search_recursive(base_directory, filename)
                
            if file_path:
                # Create FileEntry with all available metadata
                entry = FileEntry(
                    uuid=file_uuid,
                    filename=filename,
                    path=file_path,
                    size=file_info.get("size"),
                    md5sum=file_info.get("md5sum"),
                    metadata=file_info
                )
                
                # Validate if configured
                if self._validate_file(entry):
                    found_files.add(file_uuid)
                    yield entry
            elif self.config.require_all_files:
                raise GDCFileNotFoundError(
                    filename=filename,
                    uuid=file_uuid,
                    search_paths=[str(base_directory)] + [
                        str(base_directory / subdir) 
                        for subdir in self.config.subdirectories
                    ]
                )
                
    def _extract_file_specs(self, metadata: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract file specifications from GDC metadata.
        
        Args:
            metadata: GDC metadata dictionary
            
        Returns:
            Dictionary mapping UUID to file information
        """
        file_specs = {}
        
        # Handle different metadata formats
        if isinstance(metadata, list):
            # Array of file objects
            for item in metadata:
                if "uuid" in item and "filename" in item:
                    file_specs[item["uuid"]] = item
        elif isinstance(metadata, dict):
            # Single file or nested structure
            if "uuid" in metadata and "filename" in metadata:
                file_specs[metadata["uuid"]] = metadata
            elif "files" in metadata:
                # Nested files array
                return self._extract_file_specs(metadata["files"])
                
        return file_specs
        
    def _search_subdirectories(self, base_dir: Path, filename: str) -> Optional[Path]:
        """Search for file in common subdirectories.
        
        Args:
            base_dir: Base directory
            filename: File to search for
            
        Returns:
            Path to file if found, None otherwise
        """
        for subdir in self.config.subdirectories:
            # Try direct path
            if subdir:
                test_path = base_dir / subdir / filename
            else:
                test_path = base_dir / filename
                
            if test_path.exists() and test_path.is_file():
                if self._matches_patterns(test_path):
                    return test_path
                    
        # Also check base directory itself
        test_path = base_dir / filename
        if test_path.exists() and test_path.is_file():
            if self._matches_patterns(test_path):
                return test_path
                
        return None
        
    def _search_recursive(self, base_dir: Path, filename: str) -> Optional[Path]:
        """Recursively search for file.
        
        Args:
            base_dir: Base directory
            filename: File to search for
            
        Returns:
            Path to file if found, None otherwise
        """
        for root, dirs, files in os.walk(
            base_dir, 
            followlinks=self.config.follow_symlinks
        ):
            # Check depth limit
            if self.config.max_depth is not None:
                depth = len(Path(root).relative_to(base_dir).parts)
                if depth > self.config.max_depth:
                    dirs[:] = []  # Don't recurse deeper
                    continue
                    
            # Case sensitivity handling
            if self.config.case_sensitive:
                if filename in files:
                    file_path = Path(root) / filename
                    if self._matches_patterns(file_path):
                        return file_path
            else:
                # Case-insensitive search
                for file in files:
                    if file.lower() == filename.lower():
                        file_path = Path(root) / file
                        if self._matches_patterns(file_path):
                            return file_path
                            
        return None
        
    def _matches_patterns(self, file_path: Path) -> bool:
        """Check if file matches include/exclude patterns.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file should be included
        """
        filename = file_path.name
        
        # Check exclude patterns first
        for pattern in self.config.exclude_patterns:
            if fnmatch(filename, pattern):
                return False
                
        # Check include patterns (if any specified)
        if self.config.include_patterns:
            for pattern in self.config.include_patterns:
                if fnmatch(filename, pattern):
                    return True
            return False  # Didn't match any include pattern
            
        return True  # No include patterns, so include by default
        
    def _validate_file(self, entry: FileEntry) -> bool:
        """Validate file entry.
        
        Args:
            entry: File entry to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if not entry.path or not entry.path.exists():
            return False
            
        # Validate file size
        if self.config.validate_sizes and entry.size is not None:
            actual_size = entry.path.stat().st_size
            if actual_size != entry.size:
                raise FileSizeError(
                    filename=entry.filename,
                    expected=entry.size,
                    actual=actual_size
                )
                
        # Validate checksum
        if self.config.validate_checksums and entry.md5sum is not None:
            actual_md5 = calculate_md5(entry.path)
            if actual_md5 != entry.md5sum:
                raise ChecksumMismatchError(
                    filename=entry.filename,
                    expected=entry.md5sum,
                    actual=actual_md5
                )
                
        return True


class OptimizedFileDiscovery:
    """Optimized file discovery for large datasets."""
    
    def __init__(self, base_directory: Path):
        """Initialize with base directory.
        
        Args:
            base_directory: Base directory to index
        """
        self.base_directory = base_directory
        self._file_index: Optional[Dict[str, List[Path]]] = None
        
    def build_index(self, progress_callback: Optional[Callable[[int], None]] = None) -> None:
        """Build file index for faster lookups.
        
        Args:
            progress_callback: Optional callback for progress updates
        """
        self._file_index = {}
        file_count = 0
        
        for root, _, files in os.walk(self.base_directory):
            for file in files:
                file_path = Path(root) / file
                
                # Index by filename
                if file not in self._file_index:
                    self._file_index[file] = []
                self._file_index[file].append(file_path)
                
                file_count += 1
                if progress_callback and file_count % 1000 == 0:
                    progress_callback(file_count)
                    
        logger.info(f"Indexed {file_count} files in {len(self._file_index)} unique names")
        
    def find_file(self, filename: str) -> Optional[Path]:
        """Find file using index.
        
        Args:
            filename: File to find
            
        Returns:
            Path to file or None
        """
        if self._file_index is None:
            self.build_index()
            
        paths = self._file_index.get(filename, [])
        
        # Return first match (prefer shorter paths)
        if paths:
            return min(paths, key=lambda p: len(p.parts))
            
        return None
        
    def find_all_files(self, filename: str) -> List[Path]:
        """Find all instances of a file.
        
        Args:
            filename: File to find
            
        Returns:
            List of paths to matching files
        """
        if self._file_index is None:
            self.build_index()
            
        return self._file_index.get(filename, [])


def calculate_md5(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate MD5 checksum of a file.
    
    Args:
        file_path: Path to file
        chunk_size: Size of chunks to read
        
    Returns:
        MD5 hex digest
    """
    md5_hash = hashlib.md5()
    
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
            
    return md5_hash.hexdigest()


def calculate_file_stats(file_path: Path) -> Dict[str, Any]:
    """Calculate comprehensive file statistics.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file statistics
    """
    stat = file_path.stat()
    
    return {
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "ctime": stat.st_ctime,
        "mode": oct(stat.st_mode),
        "uid": stat.st_uid,
        "gid": stat.st_gid,
        "readable": os.access(file_path, os.R_OK),
        "writable": os.access(file_path, os.W_OK),
        "executable": os.access(file_path, os.X_OK)
    }


def filter_files_by_metadata(
    files: List[Path],
    metadata: Dict[str, Any],
    strict: bool = True
) -> List[Tuple[Path, Dict[str, Any]]]:
    """Filter files based on metadata criteria.
    
    Args:
        files: List of file paths
        metadata: Metadata with filtering criteria
        strict: If True, files must match all criteria
        
    Returns:
        List of tuples (path, matched_metadata)
    """
    results = []
    
    # Extract filtering criteria from metadata
    file_specs = {}
    if isinstance(metadata, list):
        for item in metadata:
            if "filename" in item:
                file_specs[item["filename"]] = item
    elif isinstance(metadata, dict) and "files" in metadata:
        return filter_files_by_metadata(files, metadata["files"], strict)
        
    for file_path in files:
        filename = file_path.name
        
        if filename in file_specs:
            spec = file_specs[filename]
            
            # Validate against specification
            if strict:
                try:
                    # Check size if specified
                    if "size" in spec:
                        actual_size = file_path.stat().st_size
                        if actual_size != spec["size"]:
                            continue
                            
                    # Check MD5 if specified
                    if "md5sum" in spec:
                        actual_md5 = calculate_md5(file_path)
                        if actual_md5 != spec["md5sum"]:
                            continue
                except (OSError, IOError):
                    continue
                    
            results.append((file_path, spec))
            
    return results


def organize_files_by_type(
    files: List[Path],
    output_dir: Path,
    copy: bool = False
) -> Dict[str, List[Path]]:
    """Organize files into subdirectories by type.
    
    Args:
        files: List of files to organize
        output_dir: Output directory
        copy: If True, copy files; if False, create symlinks
        
    Returns:
        Dictionary mapping file type to list of organized paths
    """
    import shutil
    
    organized = {}
    
    for file_path in files:
        # Determine file type
        suffix = file_path.suffix.lower()
        
        if suffix in [".fastq", ".fq", ".fastq.gz", ".fq.gz"]:
            file_type = "fastq"
        elif suffix in [".bam", ".sam"]:
            file_type = "bam"
        elif suffix in [".vcf", ".vcf.gz"]:
            file_type = "vcf"
        else:
            file_type = "other"
            
        # Create type directory
        type_dir = output_dir / file_type
        type_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy or link file
        dest_path = type_dir / file_path.name
        
        if copy:
            shutil.copy2(file_path, dest_path)
        else:
            if dest_path.exists():
                dest_path.unlink()
            dest_path.symlink_to(file_path.absolute())
            
        # Track organized files
        if file_type not in organized:
            organized[file_type] = []
        organized[file_type].append(dest_path)
        
    return organized