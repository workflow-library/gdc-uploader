#!/usr/bin/env python3
"""Integration tests for progress tracking functionality."""

import time
import threading
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from gdc_uploader import upload_file_with_progress


class TestProgressIntegration:
    """Integration tests for progress tracking."""
    
    def test_real_time_progress_simulation(self, tmp_path):
        """Simulate real upload with progress tracking."""
        # Create a larger test file
        test_file = tmp_path / "large_test.bin"
        test_size = 1024 * 1024  # 1MB
        test_file.write_bytes(b"X" * test_size)
        
        progress_events = []
        start_time = None
        
        def track_progress(size):
            """Track progress with timestamps."""
            nonlocal start_time
            if start_time is None:
                start_time = time.time()
            
            progress_events.append({
                'size': size,
                'time': time.time() - start_time,
                'total_so_far': sum(e['size'] for e in progress_events) + size
            })
        
        # Mock the upload but simulate network delay
        def mock_put_with_delay(*args, **kwargs):
            """Simulate network upload with realistic delays."""
            data_generator = kwargs.get('data')
            
            # Consume the generator to simulate upload
            total_uploaded = 0
            for chunk in data_generator:
                total_uploaded += len(chunk)
                # Simulate network delay (100KB/s)
                time.sleep(len(chunk) / (100 * 1024))
            
            response = Mock()
            response.json.return_value = {
                "status": "success",
                "bytes_uploaded": total_uploaded
            }
            response.raise_for_status.return_value = None
            return response
        
        with patch('gdc_uploader.upload.tqdm') as mock_tqdm:
            # Create a mock progress bar that tracks updates
            mock_pbar = Mock()
            mock_pbar.update = track_progress
            mock_tqdm.return_value.__enter__.return_value = mock_pbar
            
            with patch('gdc_uploader.upload.requests.put', side_effect=mock_put_with_delay):
                result = upload_file_with_progress(
                    test_file,
                    "test-id",
                    "test-token",
                    chunk_size=8192  # 8KB chunks
                )
                
                # Verify progress tracking
                assert len(progress_events) > 0
                assert progress_events[-1]['total_so_far'] == test_size
                
                # Verify progress was incremental over time
                for i in range(1, len(progress_events)):
                    assert progress_events[i]['time'] > progress_events[i-1]['time']
                    assert progress_events[i]['total_so_far'] > progress_events[i-1]['total_so_far']
    
    def test_concurrent_progress_tracking(self, tmp_path):
        """Test progress tracking with multiple concurrent uploads."""
        # Create multiple test files
        files = []
        for i in range(3):
            test_file = tmp_path / f"test_{i}.bin"
            test_file.write_bytes(b"Y" * (100 * 1024))  # 100KB each
            files.append(test_file)
        
        progress_trackers = {
            str(f): [] for f in files
        }
        
        def upload_with_tracking(file_path, file_id):
            """Upload a file and track its progress."""
            progress_updates = []
            
            with patch('gdc_uploader.upload.tqdm') as mock_tqdm:
                mock_pbar = Mock()
                mock_pbar.update = lambda n: progress_updates.append(n)
                mock_tqdm.return_value.__enter__.return_value = mock_pbar
                
                with patch('gdc_uploader.upload.requests.put') as mock_put:
                    mock_response = Mock()
                    mock_response.json.return_value = {"status": "success"}
                    mock_response.raise_for_status.return_value = None
                    mock_put.return_value = mock_response
                    
                    upload_file_with_progress(
                        file_path,
                        file_id,
                        "test-token",
                        chunk_size=10240  # 10KB chunks
                    )
            
            progress_trackers[str(file_path)] = progress_updates
        
        # Run uploads concurrently
        threads = []
        for i, file_path in enumerate(files):
            thread = threading.Thread(
                target=upload_with_tracking,
                args=(file_path, f"test-id-{i}")
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all uploads
        for thread in threads:
            thread.join()
        
        # Verify each file had independent progress tracking
        for file_path, updates in progress_trackers.items():
            assert len(updates) == 10  # 100KB / 10KB = 10 chunks
            assert sum(updates) == 100 * 1024
    
    def test_progress_recovery_after_error(self, tmp_path):
        """Test progress tracking when upload fails and retries."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"Z" * 50000)  # 50KB
        
        progress_history = []
        attempt_count = 0
        
        def mock_put_with_failure(*args, **kwargs):
            """Fail first attempt, succeed on second."""
            nonlocal attempt_count
            attempt_count += 1
            
            data_generator = kwargs.get('data')
            bytes_received = 0
            
            # Consume data
            for chunk in data_generator:
                bytes_received += len(chunk)
                # Fail halfway through first attempt
                if attempt_count == 1 and bytes_received > 25000:
                    raise requests.RequestException("Connection reset")
            
            response = Mock()
            response.json.return_value = {"status": "success"}
            response.raise_for_status.return_value = None
            return response
        
        # First attempt - should fail
        with patch('gdc_uploader.upload.tqdm') as mock_tqdm:
            mock_pbar = Mock()
            mock_pbar.update = lambda n: progress_history.append(('attempt1', n))
            mock_tqdm.return_value.__enter__.return_value = mock_pbar
            
            with patch('gdc_uploader.upload.requests.put', side_effect=mock_put_with_failure):
                with pytest.raises(requests.RequestException):
                    upload_file_with_progress(test_file, "test-id", "token")
        
        # Verify partial progress was tracked
        attempt1_progress = [p[1] for p in progress_history if p[0] == 'attempt1']
        assert sum(attempt1_progress) > 20000  # At least some progress
        assert sum(attempt1_progress) < 50000  # But not complete
        
        # Reset for retry
        attempt_count = 0
        
        # Second attempt - should succeed
        with patch('gdc_uploader.upload.tqdm') as mock_tqdm:
            mock_pbar = Mock()
            mock_pbar.update = lambda n: progress_history.append(('attempt2', n))
            mock_tqdm.return_value.__enter__.return_value = mock_pbar
            
            with patch('gdc_uploader.upload.requests.put', side_effect=mock_put_with_failure):
                result = upload_file_with_progress(test_file, "test-id", "token")
                assert result["status"] == "success"
        
        # Verify second attempt completed
        attempt2_progress = [p[1] for p in progress_history if p[0] == 'attempt2']
        assert sum(attempt2_progress) == 50000