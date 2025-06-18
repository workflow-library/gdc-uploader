"""Progress tracking module for GDC uploader.

This module provides unified progress tracking for uploads with support for:
- Console output with progress bars
- File-based reporting
- Thread-safe updates for parallel uploads
- Multiple output formats (human-readable, JSON, TSV)
"""

import time
import threading
import logging
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, TextIO, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import contextmanager
import sys
import shutil
from queue import Queue, Empty

# Import from local modules
from .base_uploader import FileEntry, UploadStatus, ProgressMonitor, UploadProgress
from .exceptions import ReportGenerationError, ReportSaveError

logger = logging.getLogger(__name__)


@dataclass
class ProgressStats:
    """Statistics for upload progress tracking."""
    
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    in_progress_files: int = 0
    
    total_bytes: int = 0
    transferred_bytes: int = 0
    
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Per-file statistics
    file_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
        
    @property
    def transfer_rate(self) -> float:
        """Calculate average transfer rate in bytes/second."""
        if self.elapsed_time > 0:
            return self.transferred_bytes / self.elapsed_time
        return 0.0
        
    @property
    def estimated_time_remaining(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if self.transfer_rate > 0 and self.total_bytes > self.transferred_bytes:
            remaining_bytes = self.total_bytes - self.transferred_bytes
            return remaining_bytes / self.transfer_rate
        return None
        
    @property
    def percentage_complete(self) -> float:
        """Calculate overall completion percentage."""
        if self.total_bytes > 0:
            return (self.transferred_bytes / self.total_bytes) * 100
        elif self.total_files > 0:
            return (self.completed_files / self.total_files) * 100
        return 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "skipped_files": self.skipped_files,
            "in_progress_files": self.in_progress_files,
            "total_bytes": self.total_bytes,
            "transferred_bytes": self.transferred_bytes,
            "elapsed_time": self.elapsed_time,
            "transfer_rate": self.transfer_rate,
            "percentage_complete": self.percentage_complete,
            "estimated_time_remaining": self.estimated_time_remaining,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None
        }


class ConsoleProgressBar:
    """Simple console progress bar implementation."""
    
    def __init__(
        self,
        total: int,
        width: int = 50,
        prefix: str = "",
        suffix: str = "",
        fill: str = "█",
        empty: str = "░"
    ):
        """Initialize progress bar.
        
        Args:
            total: Total units to track
            width: Width of progress bar
            prefix: Text to show before bar
            suffix: Text to show after bar
            fill: Character for filled portion
            empty: Character for empty portion
        """
        self.total = total
        self.width = width
        self.prefix = prefix
        self.suffix = suffix
        self.fill = fill
        self.empty = empty
        self.current = 0
        self._lock = threading.Lock()
        
    def update(self, amount: int = 1) -> None:
        """Update progress by amount."""
        with self._lock:
            self.current = min(self.current + amount, self.total)
            self._render()
            
    def set_progress(self, current: int) -> None:
        """Set absolute progress."""
        with self._lock:
            self.current = min(current, self.total)
            self._render()
            
    def _render(self) -> None:
        """Render progress bar to console."""
        if self.total == 0:
            percent = 100.0
        else:
            percent = (self.current / self.total) * 100
            
        filled_length = int(self.width * self.current // self.total)
        bar = self.fill * filled_length + self.empty * (self.width - filled_length)
        
        # Build output string
        output = f"\r{self.prefix} |{bar}| {percent:.1f}% {self.suffix}"
        
        # Clear line and print
        sys.stdout.write("\r" + " " * (shutil.get_terminal_size().columns - 1))
        sys.stdout.write(output)
        sys.stdout.flush()
        
    def finish(self) -> None:
        """Complete the progress bar."""
        with self._lock:
            self.current = self.total
            self._render()
            print()  # New line after completion


class ThreadSafeProgressTracker:
    """Thread-safe progress tracker for parallel uploads."""
    
    def __init__(self):
        """Initialize tracker."""
        self._lock = threading.RLock()
        self._stats = ProgressStats()
        self._file_progress: Dict[str, UploadProgress] = {}
        self._callbacks: List[Callable[[ProgressStats], None]] = []
        self._update_queue = Queue()
        self._stop_event = threading.Event()
        self._update_thread = None
        
    def start(self) -> None:
        """Start the progress tracking system."""
        self._stop_event.clear()
        self._update_thread = threading.Thread(target=self._update_worker, daemon=True)
        self._update_thread.start()
        
    def stop(self) -> None:
        """Stop the progress tracking system."""
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=1.0)
            
    def add_callback(self, callback: Callable[[ProgressStats], None]) -> None:
        """Add a progress callback."""
        with self._lock:
            self._callbacks.append(callback)
            
    def initialize_files(self, files: List[FileEntry]) -> None:
        """Initialize tracking for a list of files.
        
        Args:
            files: List of files to track
        """
        with self._lock:
            self._stats.total_files = len(files)
            self._stats.total_bytes = sum(f.size or 0 for f in files)
            
            for file_entry in files:
                self._stats.file_stats[file_entry.uuid] = {
                    "filename": file_entry.filename,
                    "size": file_entry.size or 0,
                    "status": UploadStatus.PENDING.value,
                    "start_time": None,
                    "end_time": None,
                    "transferred_bytes": 0,
                    "attempts": 0,
                    "error": None
                }
                
    def update_file_progress(
        self,
        file_uuid: str,
        transferred_bytes: int,
        total_bytes: Optional[int] = None
    ) -> None:
        """Update progress for a specific file.
        
        Args:
            file_uuid: UUID of file being uploaded
            transferred_bytes: Bytes transferred so far
            total_bytes: Total bytes (if known)
        """
        update = {
            "type": "progress",
            "file_uuid": file_uuid,
            "transferred_bytes": transferred_bytes,
            "total_bytes": total_bytes
        }
        self._update_queue.put(update)
        
    def mark_file_started(self, file_uuid: str) -> None:
        """Mark a file as started."""
        update = {
            "type": "started",
            "file_uuid": file_uuid,
            "timestamp": time.time()
        }
        self._update_queue.put(update)
        
    def mark_file_completed(
        self,
        file_uuid: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Mark a file as completed.
        
        Args:
            file_uuid: UUID of completed file
            success: Whether upload was successful
            error: Error message if failed
        """
        update = {
            "type": "completed",
            "file_uuid": file_uuid,
            "success": success,
            "error": error,
            "timestamp": time.time()
        }
        self._update_queue.put(update)
        
    def get_stats(self) -> ProgressStats:
        """Get current progress statistics."""
        with self._lock:
            return self._stats
            
    def _update_worker(self) -> None:
        """Worker thread for processing updates."""
        while not self._stop_event.is_set():
            try:
                update = self._update_queue.get(timeout=0.1)
                self._process_update(update)
            except Empty:
                continue
                
    def _process_update(self, update: Dict[str, Any]) -> None:
        """Process a single update."""
        with self._lock:
            update_type = update["type"]
            file_uuid = update.get("file_uuid")
            
            if update_type == "progress" and file_uuid:
                # Update file progress
                if file_uuid in self._stats.file_stats:
                    file_stat = self._stats.file_stats[file_uuid]
                    old_transferred = file_stat.get("transferred_bytes", 0)
                    new_transferred = update["transferred_bytes"]
                    
                    # Update global transferred bytes
                    self._stats.transferred_bytes += (new_transferred - old_transferred)
                    
                    # Update file stats
                    file_stat["transferred_bytes"] = new_transferred
                    if update.get("total_bytes"):
                        file_stat["size"] = update["total_bytes"]
                        
            elif update_type == "started" and file_uuid:
                # Mark file as started
                if file_uuid in self._stats.file_stats:
                    self._stats.file_stats[file_uuid]["status"] = UploadStatus.IN_PROGRESS.value
                    self._stats.file_stats[file_uuid]["start_time"] = update["timestamp"]
                    self._stats.in_progress_files += 1
                    
            elif update_type == "completed" and file_uuid:
                # Mark file as completed
                if file_uuid in self._stats.file_stats:
                    file_stat = self._stats.file_stats[file_uuid]
                    file_stat["end_time"] = update["timestamp"]
                    
                    # Update counters
                    if file_stat["status"] == UploadStatus.IN_PROGRESS.value:
                        self._stats.in_progress_files -= 1
                        
                    if update["success"]:
                        file_stat["status"] = UploadStatus.SUCCESS.value
                        self._stats.completed_files += 1
                        # Ensure all bytes are counted as transferred
                        if file_stat["size"] > file_stat.get("transferred_bytes", 0):
                            diff = file_stat["size"] - file_stat.get("transferred_bytes", 0)
                            self._stats.transferred_bytes += diff
                            file_stat["transferred_bytes"] = file_stat["size"]
                    else:
                        file_stat["status"] = UploadStatus.FAILED.value
                        file_stat["error"] = update.get("error")
                        self._stats.failed_files += 1
                        
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(self._stats)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")


class ProgressReporter:
    """Handles progress reporting to various outputs."""
    
    def __init__(
        self,
        output_format: str = "human",
        output_file: Optional[Path] = None,
        update_interval: float = 1.0,
        show_progress_bar: bool = True
    ):
        """Initialize reporter.
        
        Args:
            output_format: Format for output (human, json, tsv)
            output_file: Optional file to write progress to
            update_interval: Minimum interval between updates
            show_progress_bar: Whether to show console progress bar
        """
        self.output_format = output_format
        self.output_file = output_file
        self.update_interval = update_interval
        self.show_progress_bar = show_progress_bar
        
        self._last_update = 0.0
        self._progress_bar: Optional[ConsoleProgressBar] = None
        self._file_handle: Optional[TextIO] = None
        
    def __enter__(self):
        """Context manager entry."""
        if self.output_file:
            self._file_handle = open(self.output_file, "w")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._file_handle:
            self._file_handle.close()
            
    def initialize(self, total_files: int, total_bytes: int) -> None:
        """Initialize reporting for a new session.
        
        Args:
            total_files: Total number of files
            total_bytes: Total bytes to transfer
        """
        if self.show_progress_bar and self.output_format == "human":
            self._progress_bar = ConsoleProgressBar(
                total=total_files,
                prefix="Progress",
                suffix=f"({total_files} files)"
            )
            
        # Write header for TSV format
        if self.output_format == "tsv" and self._file_handle:
            writer = csv.writer(self._file_handle, delimiter="\t")
            writer.writerow([
                "timestamp", "total_files", "completed_files", "failed_files",
                "total_bytes", "transferred_bytes", "percentage", "rate_mbps"
            ])
            
    def report(self, stats: ProgressStats) -> None:
        """Report progress statistics.
        
        Args:
            stats: Current progress statistics
        """
        # Rate limit updates
        now = time.time()
        if now - self._last_update < self.update_interval:
            return
        self._last_update = now
        
        # Update progress bar
        if self._progress_bar:
            self._progress_bar.set_progress(stats.completed_files + stats.failed_files)
            
        # Format and output based on format
        if self.output_format == "human":
            self._report_human(stats)
        elif self.output_format == "json":
            self._report_json(stats)
        elif self.output_format == "tsv":
            self._report_tsv(stats)
            
    def _report_human(self, stats: ProgressStats) -> None:
        """Report in human-readable format."""
        if not self._progress_bar:  # Console output without progress bar
            print(f"\nProgress Update ({datetime.now().strftime('%H:%M:%S')}):")
            print(f"  Files: {stats.completed_files}/{stats.total_files} completed")
            if stats.failed_files > 0:
                print(f"  Failed: {stats.failed_files}")
            print(f"  Data: {self._format_bytes(stats.transferred_bytes)}/{self._format_bytes(stats.total_bytes)}")
            print(f"  Rate: {self._format_bytes(stats.transfer_rate)}/s")
            
            if stats.estimated_time_remaining:
                eta = timedelta(seconds=int(stats.estimated_time_remaining))
                print(f"  ETA: {eta}")
                
    def _report_json(self, stats: ProgressStats) -> None:
        """Report in JSON format."""
        data = stats.to_dict()
        json_str = json.dumps(data, indent=2 if not self._file_handle else None)
        
        if self._file_handle:
            self._file_handle.write(json_str + "\n")
            self._file_handle.flush()
        else:
            print(json_str)
            
    def _report_tsv(self, stats: ProgressStats) -> None:
        """Report in TSV format."""
        if self._file_handle:
            writer = csv.writer(self._file_handle, delimiter="\t")
            writer.writerow([
                datetime.now().isoformat(),
                stats.total_files,
                stats.completed_files,
                stats.failed_files,
                stats.total_bytes,
                stats.transferred_bytes,
                f"{stats.percentage_complete:.2f}",
                f"{stats.transfer_rate / 1024 / 1024:.2f}"  # MB/s
            ])
            self._file_handle.flush()
            
    def finish(self, stats: ProgressStats) -> None:
        """Finish reporting and show final summary."""
        if self._progress_bar:
            self._progress_bar.finish()
            
        # Final summary
        if self.output_format == "human":
            print("\n" + "="*60)
            print("Upload Summary")
            print("="*60)
            print(f"Total Files: {stats.total_files}")
            print(f"Completed: {stats.completed_files}")
            print(f"Failed: {stats.failed_files}")
            print(f"Skipped: {stats.skipped_files}")
            print(f"Total Data: {self._format_bytes(stats.total_bytes)}")
            print(f"Transferred: {self._format_bytes(stats.transferred_bytes)}")
            print(f"Duration: {timedelta(seconds=int(stats.elapsed_time))}")
            print(f"Average Rate: {self._format_bytes(stats.transfer_rate)}/s")
            print("="*60)
            
    @staticmethod
    def _format_bytes(bytes_val: Union[int, float]) -> str:
        """Format bytes in human-readable form."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"


class FileProgressMonitor(ProgressMonitor):
    """Monitor progress of a single file upload."""
    
    def __init__(self, tracker: ThreadSafeProgressTracker):
        """Initialize monitor.
        
        Args:
            tracker: Parent progress tracker
        """
        self.tracker = tracker
        self.file_entry: Optional[FileEntry] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._log_file: Optional[Path] = None
        
    def start_monitoring(self, file_entry: FileEntry) -> None:
        """Start monitoring progress for a file upload.
        
        Args:
            file_entry: File being uploaded
        """
        self.file_entry = file_entry
        self._stop_event.clear()
        
        # Notify tracker
        self.tracker.mark_file_started(file_entry.uuid)
        
        # Start monitoring thread if we have a log file to monitor
        if hasattr(file_entry, 'metadata') and file_entry.metadata.get('log_file'):
            self._log_file = Path(file_entry.metadata['log_file'])
            self._monitor_thread = threading.Thread(
                target=self._monitor_log_file,
                daemon=True
            )
            self._monitor_thread.start()
            
    def stop_monitoring(self) -> None:
        """Stop monitoring progress."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            
    def get_progress(self) -> Optional[UploadProgress]:
        """Get current progress information.
        
        Returns:
            Current progress or None if not available
        """
        if not self.file_entry:
            return None
            
        stats = self.tracker.get_stats()
        file_stat = stats.file_stats.get(self.file_entry.uuid)
        
        if file_stat:
            return UploadProgress(
                file_entry=self.file_entry,
                bytes_transferred=file_stat.get("transferred_bytes", 0),
                total_bytes=file_stat.get("size", 0),
                elapsed_time=time.time() - (file_stat.get("start_time", time.time())),
                transfer_rate=stats.transfer_rate
            )
            
        return None
        
    def _monitor_log_file(self) -> None:
        """Monitor gdc-client log file for progress updates."""
        if not self._log_file or not self._log_file.exists():
            return
            
        # Pattern to match gdc-client progress output
        import re
        progress_pattern = re.compile(r"(\d+)%\s+\|.*\|\s+(\d+)/(\d+)")
        
        with open(self._log_file, "r") as f:
            # Seek to end of file
            f.seek(0, 2)
            
            while not self._stop_event.is_set():
                line = f.readline()
                if line:
                    match = progress_pattern.search(line)
                    if match:
                        percentage = int(match.group(1))
                        transferred = int(match.group(2))
                        total = int(match.group(3))
                        
                        self.tracker.update_file_progress(
                            self.file_entry.uuid,
                            transferred,
                            total
                        )
                else:
                    time.sleep(0.1)


def create_upload_report(
    stats: ProgressStats,
    output_path: Path,
    format: str = "tsv"
) -> None:
    """Create final upload report file.
    
    Args:
        stats: Final progress statistics
        output_path: Path to save report
        format: Report format (tsv, json)
    """
    try:
        if format == "tsv":
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f, delimiter="\t")
                
                # Write header
                writer.writerow([
                    "uuid", "filename", "status", "size", 
                    "transferred", "duration", "rate_mbps", "error"
                ])
                
                # Write file data
                for uuid, file_stat in stats.file_stats.items():
                    duration = 0
                    if file_stat.get("start_time") and file_stat.get("end_time"):
                        duration = file_stat["end_time"] - file_stat["start_time"]
                        
                    rate_mbps = 0
                    if duration > 0 and file_stat.get("size"):
                        rate_mbps = (file_stat["size"] / duration) / 1024 / 1024
                        
                    writer.writerow([
                        uuid,
                        file_stat.get("filename", ""),
                        file_stat.get("status", ""),
                        file_stat.get("size", 0),
                        file_stat.get("transferred_bytes", 0),
                        f"{duration:.2f}",
                        f"{rate_mbps:.2f}",
                        file_stat.get("error", "")
                    ])
                    
        elif format == "json":
            report_data = {
                "summary": stats.to_dict(),
                "files": stats.file_stats
            }
            
            with open(output_path, "w") as f:
                json.dump(report_data, f, indent=2)
                
    except Exception as e:
        raise ReportSaveError(str(output_path), str(e))


@contextmanager
def progress_tracking(
    files: List[FileEntry],
    output_format: str = "human",
    show_progress_bar: bool = True
):
    """Context manager for progress tracking.
    
    Args:
        files: List of files to track
        output_format: Output format
        show_progress_bar: Whether to show progress bar
        
    Yields:
        ThreadSafeProgressTracker instance
    """
    tracker = ThreadSafeProgressTracker()
    reporter = ProgressReporter(
        output_format=output_format,
        show_progress_bar=show_progress_bar
    )
    
    try:
        # Initialize
        tracker.start()
        tracker.initialize_files(files)
        tracker.add_callback(reporter.report)
        
        total_bytes = sum(f.size or 0 for f in files)
        reporter.initialize(len(files), total_bytes)
        
        yield tracker
        
    finally:
        # Cleanup
        tracker.stop()
        final_stats = tracker.get_stats()
        reporter.finish(final_stats)