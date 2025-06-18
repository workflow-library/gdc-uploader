"""Base uploader interface for GDC upload strategies.

This module defines the abstract base class that all GDC uploaders must implement.
It provides a consistent interface for file discovery, upload execution, progress
tracking, and report generation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Iterator


class UploadStatus(Enum):
    """Status of a file upload operation."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"
    SKIPPED = "SKIPPED"


@dataclass
class FileEntry:
    """Represents a file to be uploaded."""
    uuid: str
    filename: str
    path: Optional[Path] = None
    size: Optional[int] = None
    md5sum: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UploadResult:
    """Result of a single file upload attempt."""
    file_entry: FileEntry
    status: UploadStatus
    attempts: int = 0
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    bytes_transferred: Optional[int] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate upload duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class UploadProgress:
    """Progress information for an ongoing upload."""
    file_entry: FileEntry
    bytes_transferred: int
    total_bytes: int
    elapsed_time: float
    transfer_rate: float  # bytes per second
    estimated_time_remaining: Optional[float] = None
    
    @property
    def percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_bytes > 0:
            return (self.bytes_transferred / self.total_bytes) * 100
        return 0.0


class BaseUploader(ABC):
    """Abstract base class for all GDC upload strategies.
    
    This class defines the interface that all uploaders must implement. It provides
    hooks for file discovery, upload execution, progress tracking, and report generation.
    
    Attributes:
        metadata: Dictionary containing GDC metadata
        token_file: Path to the GDC authentication token
        base_directory: Base directory for file discovery
        thread_count: Number of parallel uploads (for parallel uploaders)
        retry_count: Number of retry attempts for failed uploads
    """
    
    def __init__(
        self,
        metadata: Dict[str, Any],
        token_file: Path,
        base_directory: Path,
        thread_count: int = 1,
        retry_count: int = 3
    ):
        """Initialize the uploader with configuration.
        
        Args:
            metadata: GDC metadata dictionary
            token_file: Path to GDC authentication token
            base_directory: Base directory for file discovery
            thread_count: Number of parallel uploads
            retry_count: Number of retry attempts
        """
        self.metadata = metadata
        self.token_file = token_file
        self.base_directory = base_directory
        self.thread_count = thread_count
        self.retry_count = retry_count
        self._progress_callback: Optional[Callable[[UploadProgress], None]] = None
        
    @abstractmethod
    def discover_files(self) -> List[FileEntry]:
        """Discover files to upload based on metadata.
        
        This method should search for files in the base directory and match them
        against the metadata. It should handle various directory structures and
        file naming conventions.
        
        Returns:
            List of FileEntry objects representing files to upload
        """
        pass
    
    @abstractmethod
    def validate_files(self, files: List[FileEntry]) -> List[FileEntry]:
        """Validate files before upload.
        
        This method should check file existence, size, checksums if available,
        and any other validation required before upload.
        
        Args:
            files: List of files to validate
            
        Returns:
            List of validated files (may exclude invalid files)
        """
        pass
    
    @abstractmethod
    def upload_file(self, file_entry: FileEntry) -> UploadResult:
        """Upload a single file.
        
        This method implements the actual upload logic for a single file.
        It should handle retries internally based on retry_count.
        
        Args:
            file_entry: File to upload
            
        Returns:
            UploadResult with status and details
        """
        pass
    
    @abstractmethod
    def upload_batch(self, files: List[FileEntry]) -> List[UploadResult]:
        """Upload multiple files.
        
        This method should handle parallel uploads if thread_count > 1.
        It should call upload_file for each file and manage concurrency.
        
        Args:
            files: List of files to upload
            
        Returns:
            List of UploadResult objects
        """
        pass
    
    def set_progress_callback(self, callback: Callable[[UploadProgress], None]) -> None:
        """Set a callback for progress updates.
        
        Args:
            callback: Function to call with progress updates
        """
        self._progress_callback = callback
    
    def _report_progress(self, progress: UploadProgress) -> None:
        """Report progress if callback is set.
        
        Args:
            progress: Progress information to report
        """
        if self._progress_callback:
            self._progress_callback(progress)
    
    @abstractmethod
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Generate upload report.
        
        This method should create a structured report of the upload session,
        including success/failure counts, timing information, and details
        for each file.
        
        Args:
            results: List of upload results
            
        Returns:
            Dictionary containing report data
        """
        pass
    
    @abstractmethod
    def save_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save report to file.
        
        This method should save the report in the appropriate format
        (TSV, JSON, etc.) based on the implementation.
        
        Args:
            report: Report data to save
            output_path: Path to save the report
        """
        pass
    
    def run(self) -> List[UploadResult]:
        """Execute the complete upload workflow.
        
        This is a template method that orchestrates the upload process:
        1. Discover files
        2. Validate files
        3. Upload files
        4. Generate and save report
        
        Returns:
            List of upload results
        """
        # Discover files
        files = self.discover_files()
        
        # Validate files
        validated_files = self.validate_files(files)
        
        # Upload files
        results = self.upload_batch(validated_files)
        
        # Generate and save report
        report = self.generate_report(results)
        self.save_report(report, Path("upload-report.tsv"))
        
        return results
    
    @abstractmethod
    def get_upload_command(self, file_entry: FileEntry) -> List[str]:
        """Get the command to execute for uploading a file.
        
        This method should return the command line arguments for the
        upload tool (e.g., gdc-client).
        
        Args:
            file_entry: File to upload
            
        Returns:
            List of command arguments
        """
        pass


class FileDiscoveryStrategy(ABC):
    """Strategy interface for file discovery algorithms."""
    
    @abstractmethod
    def discover(self, base_directory: Path, metadata: Dict[str, Any]) -> Iterator[FileEntry]:
        """Discover files matching the metadata.
        
        Args:
            base_directory: Base directory to search
            metadata: GDC metadata for matching
            
        Yields:
            FileEntry objects for discovered files
        """
        pass


class ProgressMonitor(ABC):
    """Interface for monitoring upload progress."""
    
    @abstractmethod
    def start_monitoring(self, file_entry: FileEntry) -> None:
        """Start monitoring progress for a file upload.
        
        Args:
            file_entry: File being uploaded
        """
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop monitoring progress."""
        pass
    
    @abstractmethod
    def get_progress(self) -> Optional[UploadProgress]:
        """Get current progress information.
        
        Returns:
            Current progress or None if not available
        """
        pass