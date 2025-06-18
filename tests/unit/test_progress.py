"""Unit tests for progress tracking module."""

import pytest
import time
import threading
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add path for imports
import sys
sys.path.insert(0, '/workspaces/gdc-uploader-agents/agent-2-common-utilities/src')
sys.path.append('/workspaces/gdc-uploader-agents/agent-1-core-architecture/specs/interfaces')

from gdc_uploader.core.progress import (
    ProgressStats,
    ConsoleProgressBar,
    ThreadSafeProgressTracker,
    ProgressReporter,
    FileProgressMonitor,
    create_upload_report,
    progress_tracking
)
from base_uploader_interface import FileEntry, UploadStatus, UploadProgress


class TestProgressStats:
    """Test ProgressStats dataclass."""
    
    def test_initial_stats(self):
        """Test initial statistics values."""
        stats = ProgressStats()
        
        assert stats.total_files == 0
        assert stats.completed_files == 0
        assert stats.failed_files == 0
        assert stats.total_bytes == 0
        assert stats.transferred_bytes == 0
        assert stats.elapsed_time > 0
        
    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation."""
        stats = ProgressStats()
        time.sleep(0.1)
        
        assert stats.elapsed_time >= 0.1
        
        # Test with end time
        stats.end_time = stats.start_time + 5.0
        assert stats.elapsed_time == 5.0
        
    def test_transfer_rate_calculation(self):
        """Test transfer rate calculation."""
        stats = ProgressStats()
        stats.transferred_bytes = 1024 * 1024  # 1 MB
        stats.start_time = time.time() - 1.0  # 1 second ago
        
        assert 900_000 < stats.transfer_rate < 1_100_000  # ~1 MB/s
        
    def test_percentage_complete(self):
        """Test completion percentage calculation."""
        stats = ProgressStats()
        
        # Test with bytes
        stats.total_bytes = 1000
        stats.transferred_bytes = 250
        assert stats.percentage_complete == 25.0
        
        # Test with files when no bytes
        stats.total_bytes = 0
        stats.total_files = 10
        stats.completed_files = 3
        assert stats.percentage_complete == 30.0
        
    def test_estimated_time_remaining(self):
        """Test estimated time remaining calculation."""
        stats = ProgressStats()
        stats.total_bytes = 1000
        stats.transferred_bytes = 200
        stats.start_time = time.time() - 2.0  # 2 seconds ago
        
        # Should estimate ~8 seconds remaining (800 bytes at 100 bytes/sec)
        eta = stats.estimated_time_remaining
        assert eta is not None
        assert 7.0 < eta < 9.0
        
    def test_to_dict(self):
        """Test dictionary conversion."""
        stats = ProgressStats()
        stats.total_files = 10
        stats.completed_files = 5
        
        data = stats.to_dict()
        assert data["total_files"] == 10
        assert data["completed_files"] == 5
        assert "elapsed_time" in data
        assert "start_time" in data


class TestConsoleProgressBar:
    """Test ConsoleProgressBar class."""
    
    def test_progress_bar_creation(self):
        """Test progress bar initialization."""
        bar = ConsoleProgressBar(
            total=100,
            width=20,
            prefix="Test",
            suffix="files"
        )
        
        assert bar.total == 100
        assert bar.width == 20
        assert bar.current == 0
        
    def test_progress_update(self):
        """Test progress updates."""
        bar = ConsoleProgressBar(total=10)
        
        bar.update(3)
        assert bar.current == 3
        
        bar.update(5)
        assert bar.current == 8
        
        # Test max limit
        bar.update(10)
        assert bar.current == 10
        
    def test_set_progress(self):
        """Test absolute progress setting."""
        bar = ConsoleProgressBar(total=100)
        
        bar.set_progress(50)
        assert bar.current == 50
        
        # Test max limit
        bar.set_progress(150)
        assert bar.current == 100
        
    @patch('sys.stdout')
    def test_render(self, mock_stdout):
        """Test progress bar rendering."""
        bar = ConsoleProgressBar(total=10, width=10)
        bar.set_progress(5)
        
        # Should write progress bar
        assert mock_stdout.write.called


class TestThreadSafeProgressTracker:
    """Test ThreadSafeProgressTracker class."""
    
    def test_tracker_initialization(self):
        """Test tracker initialization."""
        tracker = ThreadSafeProgressTracker()
        
        assert tracker._stats.total_files == 0
        assert len(tracker._callbacks) == 0
        
    def test_initialize_files(self):
        """Test file initialization."""
        tracker = ThreadSafeProgressTracker()
        
        files = [
            FileEntry(uuid="uuid1", filename="file1.txt", size=1000),
            FileEntry(uuid="uuid2", filename="file2.txt", size=2000)
        ]
        
        tracker.initialize_files(files)
        
        stats = tracker.get_stats()
        assert stats.total_files == 2
        assert stats.total_bytes == 3000
        assert len(stats.file_stats) == 2
        
    def test_file_progress_updates(self):
        """Test file progress update handling."""
        tracker = ThreadSafeProgressTracker()
        tracker.start()
        
        try:
            # Initialize a file
            files = [FileEntry(uuid="uuid1", filename="file1.txt", size=1000)]
            tracker.initialize_files(files)
            
            # Start upload
            tracker.mark_file_started("uuid1")
            time.sleep(0.1)  # Let update process
            
            # Update progress
            tracker.update_file_progress("uuid1", 500, 1000)
            time.sleep(0.1)  # Let update process
            
            stats = tracker.get_stats()
            assert stats.in_progress_files == 1
            assert stats.transferred_bytes >= 500
            
            # Complete upload
            tracker.mark_file_completed("uuid1", success=True)
            time.sleep(0.1)  # Let update process
            
            stats = tracker.get_stats()
            assert stats.completed_files == 1
            assert stats.in_progress_files == 0
            
        finally:
            tracker.stop()
            
    def test_failed_file_handling(self):
        """Test failed file handling."""
        tracker = ThreadSafeProgressTracker()
        tracker.start()
        
        try:
            files = [FileEntry(uuid="uuid1", filename="file1.txt")]
            tracker.initialize_files(files)
            
            tracker.mark_file_started("uuid1")
            tracker.mark_file_completed("uuid1", success=False, error="Test error")
            time.sleep(0.1)  # Let update process
            
            stats = tracker.get_stats()
            assert stats.failed_files == 1
            assert stats.file_stats["uuid1"]["error"] == "Test error"
            
        finally:
            tracker.stop()
            
    def test_callbacks(self):
        """Test progress callbacks."""
        tracker = ThreadSafeProgressTracker()
        tracker.start()
        
        callback_stats = []
        tracker.add_callback(lambda s: callback_stats.append(s))
        
        try:
            files = [FileEntry(uuid="uuid1", filename="file1.txt")]
            tracker.initialize_files(files)
            tracker.mark_file_started("uuid1")
            time.sleep(0.2)  # Let callbacks fire
            
            assert len(callback_stats) > 0
            
        finally:
            tracker.stop()


class TestProgressReporter:
    """Test ProgressReporter class."""
    
    def test_reporter_initialization(self):
        """Test reporter initialization."""
        reporter = ProgressReporter(
            output_format="json",
            update_interval=0.5
        )
        
        assert reporter.output_format == "json"
        assert reporter.update_interval == 0.5
        
    def test_rate_limiting(self):
        """Test update rate limiting."""
        reporter = ProgressReporter(update_interval=0.5)
        stats = ProgressStats()
        
        # First report should go through
        reporter.report(stats)
        last_update = reporter._last_update
        
        # Immediate second report should be skipped
        reporter.report(stats)
        assert reporter._last_update == last_update
        
        # After interval, should update
        time.sleep(0.6)
        reporter.report(stats)
        assert reporter._last_update > last_update
        
    def test_json_output(self, tmp_path):
        """Test JSON format output."""
        output_file = tmp_path / "progress.json"
        
        with ProgressReporter(output_format="json", output_file=output_file) as reporter:
            stats = ProgressStats(total_files=10, completed_files=5)
            reporter.report(stats)
            
        # Check file was written
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
            assert data["total_files"] == 10
            assert data["completed_files"] == 5
            
    def test_tsv_output(self, tmp_path):
        """Test TSV format output."""
        output_file = tmp_path / "progress.tsv"
        
        with ProgressReporter(output_format="tsv", output_file=output_file) as reporter:
            reporter.initialize(10, 1000)
            
            stats = ProgressStats(
                total_files=10,
                completed_files=5,
                total_bytes=1000,
                transferred_bytes=500
            )
            reporter.report(stats)
            
        # Check file was written with header
        assert output_file.exists()
        lines = output_file.read_text().strip().split('\n')
        assert len(lines) >= 2  # Header + data
        assert "timestamp" in lines[0]
        
    def test_format_bytes(self):
        """Test byte formatting."""
        assert ProgressReporter._format_bytes(512) == "512.00 B"
        assert ProgressReporter._format_bytes(1024) == "1.00 KB"
        assert ProgressReporter._format_bytes(1024 * 1024) == "1.00 MB"
        assert ProgressReporter._format_bytes(1024 * 1024 * 1024) == "1.00 GB"


class TestFileProgressMonitor:
    """Test FileProgressMonitor class."""
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        tracker = ThreadSafeProgressTracker()
        monitor = FileProgressMonitor(tracker)
        
        assert monitor.tracker == tracker
        assert monitor.file_entry is None
        
    def test_start_monitoring(self):
        """Test starting file monitoring."""
        tracker = ThreadSafeProgressTracker()
        tracker.start()
        monitor = FileProgressMonitor(tracker)
        
        try:
            file_entry = FileEntry(uuid="uuid1", filename="test.txt")
            tracker.initialize_files([file_entry])
            
            monitor.start_monitoring(file_entry)
            assert monitor.file_entry == file_entry
            
            # Should mark file as started
            time.sleep(0.1)
            stats = tracker.get_stats()
            assert stats.file_stats["uuid1"]["status"] == UploadStatus.IN_PROGRESS.value
            
        finally:
            monitor.stop_monitoring()
            tracker.stop()
            
    def test_get_progress(self):
        """Test getting current progress."""
        tracker = ThreadSafeProgressTracker()
        tracker.start()
        monitor = FileProgressMonitor(tracker)
        
        try:
            file_entry = FileEntry(uuid="uuid1", filename="test.txt", size=1000)
            tracker.initialize_files([file_entry])
            monitor.start_monitoring(file_entry)
            
            # Update progress
            tracker.update_file_progress("uuid1", 500, 1000)
            time.sleep(0.1)
            
            progress = monitor.get_progress()
            assert progress is not None
            assert progress.bytes_transferred == 500
            assert progress.total_bytes == 1000
            
        finally:
            monitor.stop_monitoring()
            tracker.stop()


class TestReportGeneration:
    """Test report generation functions."""
    
    def test_create_tsv_report(self, tmp_path):
        """Test TSV report creation."""
        stats = ProgressStats()
        stats.file_stats = {
            "uuid1": {
                "filename": "file1.txt",
                "status": UploadStatus.SUCCESS.value,
                "size": 1000,
                "transferred_bytes": 1000,
                "start_time": time.time() - 10,
                "end_time": time.time(),
                "error": None
            },
            "uuid2": {
                "filename": "file2.txt",
                "status": UploadStatus.FAILED.value,
                "size": 2000,
                "transferred_bytes": 500,
                "error": "Connection error"
            }
        }
        
        output_path = tmp_path / "report.tsv"
        create_upload_report(stats, output_path, format="tsv")
        
        assert output_path.exists()
        lines = output_path.read_text().strip().split('\n')
        assert len(lines) == 3  # Header + 2 files
        assert "uuid" in lines[0]
        assert "uuid1" in lines[1]
        assert "uuid2" in lines[2]
        
    def test_create_json_report(self, tmp_path):
        """Test JSON report creation."""
        stats = ProgressStats(total_files=2, completed_files=1, failed_files=1)
        stats.file_stats = {
            "uuid1": {"filename": "file1.txt", "status": "SUCCESS"}
        }
        
        output_path = tmp_path / "report.json"
        create_upload_report(stats, output_path, format="json")
        
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)
            assert "summary" in data
            assert "files" in data
            assert data["summary"]["total_files"] == 2


class TestProgressContextManager:
    """Test progress tracking context manager."""
    
    def test_context_manager(self):
        """Test progress tracking context manager."""
        files = [
            FileEntry(uuid="uuid1", filename="file1.txt", size=1000),
            FileEntry(uuid="uuid2", filename="file2.txt", size=2000)
        ]
        
        with progress_tracking(
            files,
            output_format="json",
            show_progress_bar=False
        ) as tracker:
            assert isinstance(tracker, ThreadSafeProgressTracker)
            
            # Tracker should be initialized
            stats = tracker.get_stats()
            assert stats.total_files == 2
            assert stats.total_bytes == 3000