"""General utilities module for GDC uploader.

This module contains shared utility functions that don't fit into the
specific categories of file_operations, progress, or retry modules.
"""

import os
import json
import yaml
import logging
import subprocess
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, IO, Callable
from datetime import datetime, timezone
from contextlib import contextmanager
import platform
import psutil
import csv

# Use local exceptions
from .exceptions import (
    InvalidMetadataError,
    TokenFileNotFoundError,
    InvalidTokenError,
    ConfigurationError,
    MissingDependencyError
)

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to write logs to
    """
    log_format = '[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
        
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers
    )


def yaml_to_json(yaml_file: Union[str, Path]) -> Dict[str, Any]:
    """Convert YAML file to JSON format.
    
    Args:
        yaml_file: Path to YAML file
        
    Returns:
        Dictionary representation of YAML content
    """
    yaml_path = Path(yaml_file)
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        
    try:
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return data
    except yaml.YAMLError as e:
        raise InvalidMetadataError(f"Invalid YAML format: {e}")


# Metadata handling utilities

def load_metadata(metadata_path: Union[str, Path]) -> Dict[str, Any]:
    """Load metadata from JSON or YAML file.
    
    Args:
        metadata_path: Path to metadata file
        
    Returns:
        Metadata dictionary
        
    Raises:
        InvalidMetadataError: If metadata is invalid
    """
    metadata_path = Path(metadata_path)
    
    if not metadata_path.exists():
        raise InvalidMetadataError(
            f"Metadata file not found: {metadata_path}",
            str(metadata_path)
        )
        
    try:
        with open(metadata_path, 'r') as f:
            if metadata_path.suffix.lower() in ['.yaml', '.yml']:
                metadata = yaml.safe_load(f)
            else:
                metadata = json.load(f)
                
        # Validate basic structure
        if metadata is None:
            raise InvalidMetadataError(
                "Metadata file is empty",
                str(metadata_path)
            )
            
        return metadata
        
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise InvalidMetadataError(
            f"Failed to parse metadata file: {str(e)}",
            str(metadata_path)
        )
    except Exception as e:
        raise InvalidMetadataError(
            f"Error loading metadata: {str(e)}",
            str(metadata_path)
        )


def validate_metadata_structure(metadata: Dict[str, Any]) -> None:
    """Validate metadata has required GDC structure.
    
    Args:
        metadata: Metadata dictionary to validate
        
    Raises:
        InvalidMetadataError: If structure is invalid
    """
    # Handle both single file and array formats
    if isinstance(metadata, list):
        if not metadata:
            raise InvalidMetadataError("Metadata array is empty")
        files = metadata
    elif isinstance(metadata, dict):
        if "files" in metadata:
            files = metadata["files"]
        elif "uuid" in metadata and "filename" in metadata:
            files = [metadata]
        else:
            raise InvalidMetadataError(
                "Metadata must contain 'files' array or be a file object with 'uuid' and 'filename'"
            )
    else:
        raise InvalidMetadataError(
            f"Invalid metadata type: {type(metadata).__name__}"
        )
        
    # Validate each file entry
    for idx, file_entry in enumerate(files):
        if not isinstance(file_entry, dict):
            raise InvalidMetadataError(
                f"File entry {idx} is not a dictionary"
            )
            
        if "uuid" not in file_entry:
            raise InvalidMetadataError(
                f"File entry {idx} missing required field 'uuid'"
            )
            
        if "filename" not in file_entry:
            raise InvalidMetadataError(
                f"File entry {idx} missing required field 'filename'"
            )


def merge_metadata(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge metadata dictionaries recursively.
    
    Args:
        base: Base metadata
        updates: Updates to apply
        
    Returns:
        Merged metadata
    """
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_metadata(result[key], value)
        else:
            result[key] = value
            
    return result


# Token handling utilities

def load_token(token_path: Union[str, Path]) -> str:
    """Load GDC authentication token from file.
    
    Args:
        token_path: Path to token file
        
    Returns:
        Token string
        
    Raises:
        TokenFileNotFoundError: If token file not found
        InvalidTokenError: If token is invalid
    """
    token_path = Path(token_path)
    
    if not token_path.exists():
        raise TokenFileNotFoundError(str(token_path))
        
    try:
        with open(token_path, 'r') as f:
            token = f.read().strip()
            
        if not token:
            raise InvalidTokenError("Token file is empty")
            
        # Basic token validation (GDC tokens are typically long hex strings)
        if len(token) < 32:
            raise InvalidTokenError("Token appears to be too short")
            
        return token
        
    except IOError as e:
        raise InvalidTokenError(f"Error reading token file: {str(e)}")


def validate_token_permissions(token_path: Union[str, Path]) -> None:
    """Validate token file has secure permissions.
    
    Args:
        token_path: Path to token file
        
    Raises:
        ConfigurationError: If permissions are insecure
    """
    token_path = Path(token_path)
    
    if platform.system() != "Windows":
        # Check file permissions on Unix-like systems
        stat_info = token_path.stat()
        mode = stat_info.st_mode
        
        # Check if group or others have any permissions
        if mode & 0o077:
            logger.warning(
                f"Token file {token_path} has insecure permissions. "
                "Consider running: chmod 600 " + str(token_path)
            )


# System and environment utilities

def check_system_requirements() -> Dict[str, Any]:
    """Check system requirements and available resources.
    
    Returns:
        Dictionary with system information
    """
    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        "disk_usage": {}
    }
    
    # Check disk usage for current directory
    try:
        disk_usage = psutil.disk_usage(os.getcwd())
        info["disk_usage"]["current_dir"] = {
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "percent_used": disk_usage.percent
        }
    except Exception:
        pass
        
    return info


def check_command_availability(command: str) -> bool:
    """Check if a command is available in PATH.
    
    Args:
        command: Command to check
        
    Returns:
        True if command is available
    """
    try:
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def ensure_dependencies(required_commands: List[str]) -> None:
    """Ensure required commands are available.
    
    Args:
        required_commands: List of required commands
        
    Raises:
        MissingDependencyError: If a dependency is missing
    """
    missing = []
    
    for cmd in required_commands:
        if not check_command_availability(cmd):
            missing.append(cmd)
            
    if missing:
        install_hints = {
            "gdc-client": "Download from https://gdc.cancer.gov/access-data/gdc-data-transfer-tool",
            "parallel": "Install with: apt-get install parallel (Ubuntu) or brew install parallel (macOS)",
            "jq": "Install with: apt-get install jq (Ubuntu) or brew install jq (macOS)",
            "rg": "Install ripgrep from https://github.com/BurntSushi/ripgrep"
        }
        
        for cmd in missing:
            hint = install_hints.get(cmd, f"Please install {cmd}")
            raise MissingDependencyError(cmd, hint)


# Logging utilities

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None
) -> None:
    """Setup logging configuration.
    
    Args:
        log_level: Logging level
        log_file: Optional log file path
        log_format: Optional log format string
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format
    )
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)


@contextmanager
def temporary_directory(prefix: str = "gdc_upload_"):
    """Context manager for temporary directory.
    
    Args:
        prefix: Prefix for temporary directory name
        
    Yields:
        Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# Report generation utilities

def generate_tsv_report(
    results: List[Dict[str, Any]],
    output_path: Path,
    columns: Optional[List[str]] = None
) -> None:
    """Generate TSV report from results.
    
    Args:
        results: List of result dictionaries
        output_path: Path to save report
        columns: Optional list of columns (uses all if None)
    """
    if not results:
        logger.warning("No results to write to report")
        return
        
    # Determine columns
    if columns is None:
        columns = list(results[0].keys())
        
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter='\t')
        writer.writeheader()
        
        for result in results:
            writer.writerow({col: result.get(col, '') for col in columns})


def generate_json_report(
    results: List[Dict[str, Any]],
    output_path: Path,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Generate JSON report from results.
    
    Args:
        results: List of result dictionaries
        output_path: Path to save report
        metadata: Optional metadata to include
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results
    }
    
    if metadata:
        report["metadata"] = metadata
        
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)


# String and formatting utilities

def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds as human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace problematic characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
        
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        base, ext = os.path.splitext(filename)
        filename = base[:max_length - len(ext)] + ext
        
    return filename


# Command execution utilities

def run_command(
    command: List[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run command with proper error handling.
    
    Args:
        command: Command and arguments
        cwd: Working directory
        timeout: Timeout in seconds
        capture_output: Whether to capture output
        
    Returns:
        CompletedProcess instance
        
    Raises:
        subprocess.CalledProcessError: If command fails
    """
    logger.debug(f"Running command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            check=True
        )
        
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout}s: {' '.join(command)}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {' '.join(command)}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        raise


# Checksum utilities

def calculate_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate SHA256 checksum of a file.
    
    Args:
        file_path: Path to file
        chunk_size: Size of chunks to read
        
    Returns:
        SHA256 hex digest
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)
            
    return sha256_hash.hexdigest()


def verify_checksum(
    file_path: Path,
    expected_checksum: str,
    algorithm: str = "md5"
) -> bool:
    """Verify file checksum.
    
    Args:
        file_path: Path to file
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm (md5, sha256)
        
    Returns:
        True if checksum matches
    """
    if algorithm.lower() == "md5":
        from .file_operations import calculate_md5
        actual = calculate_md5(file_path)
    elif algorithm.lower() == "sha256":
        actual = calculate_sha256(file_path)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
        
    return actual.lower() == expected_checksum.lower()


# Exit code utilities

class ExitCodes:
    """Standard exit codes for CLI operations."""
    
    SUCCESS = 0
    GENERAL_ERROR = 1
    MISSING_PARAMETERS = 1
    UPLOAD_FAILED = 2
    INVALID_DATA = 3
    FILE_NOT_FOUND = 4
    AUTHENTICATION_ERROR = 5
    CONFIGURATION_ERROR = 6
    VALIDATION_ERROR = 7


# Batch processing utilities

def batch_items(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Split items into batches.
    
    Args:
        items: List of items
        batch_size: Size of each batch
        
    Returns:
        List of batches
    """
    return [
        items[i:i + batch_size]
        for i in range(0, len(items), batch_size)
    ]


def parallel_map(
    func: Callable,
    items: List[Any],
    max_workers: Optional[int] = None,
    desc: Optional[str] = None
) -> List[Any]:
    """Apply function to items in parallel.
    
    Args:
        func: Function to apply
        items: Items to process
        max_workers: Maximum parallel workers
        desc: Description for progress tracking
        
    Returns:
        List of results
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    if max_workers is None:
        max_workers = min(len(items), psutil.cpu_count() or 1)
        
    results = [None] * len(items)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(func, item): i
            for i, item in enumerate(items)
        }
        
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:
                logger.error(f"Error processing item {index}: {e}")
                results[index] = None
                
    return results