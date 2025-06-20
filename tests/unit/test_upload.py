#!/usr/bin/env python3
"""Unit tests for upload functionality with environment-aware progress."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import os

from click.testing import CliRunner

from gdc_uploader.upload import (
    upload_file_with_progress, 
    SimpleProgress,
    detect_environment,
    get_progress_handler,
    main
)
from gdc_uploader.utils import chunk_reader


class TestSimpleProgress:
    """Test simple progress functionality."""
    
    def test_simple_progress_updates(self, capsys):
        """Test that SimpleProgress prints at correct intervals."""
        progress = SimpleProgress(10000, "Testing")  # Larger file for finer control
        
        with progress as p:
            # Initial message
            captured = capsys.readouterr()
            assert "Testing: 0.00% (0.00/0.00 GB)" in captured.out
            
            # First update triggers because last_percent starts at -1
            p.update(10)  # 0.1%
            captured = capsys.readouterr()
            assert "Testing: 0.10%" in captured.out
            
            # Small update - no output (less than 0.25% from last)
            p.update(10)  # 0.2% total
            captured = capsys.readouterr()
            assert captured.out == ""
            
            # Update to trigger 0.25% threshold
            p.update(20)  # Now at 0.4%
            captured = capsys.readouterr()
            assert "Testing: 0.40%" in captured.out
            assert " GB) - " in captured.out
            assert " MB/s" in captured.out
            
            # Jump to 50%
            p.update(4960)
            captured = capsys.readouterr()
            assert "Testing: 50.00%" in captured.out
        
        # Exit should print 100%
        captured = capsys.readouterr()
        assert "Testing: 100.00% (0.00/0.00 GB)" in captured.out


class TestEnvironmentDetection:
    """Test environment detection."""
    
    def test_detect_environment(self):
        """Test environment detection returns expected keys."""
        env = detect_environment()
        assert 'is_tty' in env
        assert 'is_sbp' in env
        assert 'is_cwl' in env
        assert 'term' in env
    
    def test_sbp_environment(self):
        """Test SBP environment detection."""
        with patch.dict(os.environ, {'SBP_TASK_ID': '12345'}):
            env = detect_environment()
            assert env['is_sbp'] is True
    
    def test_cwl_environment(self):
        """Test CWL environment detection."""
        with patch.dict(os.environ, {'CWL_RUNTIME': 'true'}):
            env = detect_environment()
            assert env['is_cwl'] is True


class TestProgressHandler:
    """Test progress handler selection."""
    
    def test_none_mode(self):
        """Test none mode returns None."""
        handler = get_progress_handler(1000, "Test", mode='none')
        assert handler is None
    
    def test_simple_mode(self):
        """Test simple mode returns SimpleProgress."""
        handler = get_progress_handler(1000, "Test", mode='simple')
        assert isinstance(handler, SimpleProgress)
    
    def test_auto_mode_in_sbp(self):
        """Test auto mode selects simple in SBP."""
        with patch.dict(os.environ, {'SBP_TASK_ID': '12345'}):
            handler = get_progress_handler(1000, "Test", mode='auto')
            assert isinstance(handler, SimpleProgress)


class TestUploadWithProgress:
    """Test upload functionality with progress modes."""
    
    def test_upload_simple_progress(self, tmp_path, capsys):
        """Test upload with simple progress mode."""
        test_file = tmp_path / "test.txt"
        test_content = b"Test data" * 1000  # ~9KB
        test_file.write_bytes(test_content)
        
        with patch('gdc_uploader.upload.requests.put') as mock_put:
            def consume_data(*args, **kwargs):
                # Consume the data generator
                data_gen = kwargs.get('data')
                if data_gen:
                    list(data_gen)
                
                mock_response = Mock()
                mock_response.json.return_value = {"status": "success"}
                mock_response.raise_for_status.return_value = None
                return mock_response
            
            mock_put.side_effect = consume_data
            
            result = upload_file_with_progress(
                test_file,
                "test-id",
                "test-token",
                chunk_size=1000,
                progress_mode='simple'
            )
            
            captured = capsys.readouterr()
            assert "Uploading: 0.00%" in captured.out
            assert "Uploading: 100.00%" in captured.out
            assert " GB) - " in captured.out
            assert " MB/s" in captured.out
            assert result["status"] == "success"
    
    def test_upload_no_progress(self, tmp_path, capsys):
        """Test upload with no progress mode."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        with patch('gdc_uploader.upload.requests.put') as mock_put:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "success"}
            mock_response.raise_for_status.return_value = None
            mock_put.return_value = mock_response
            
            result = upload_file_with_progress(
                test_file,
                "test-id",
                "test-token",
                progress_mode='none'
            )
            
            captured = capsys.readouterr()
            # Should have no progress output
            assert "Uploading:" not in captured.out
            assert result["status"] == "success"


class TestCLI:
    """Test CLI functionality."""
    
    def test_cli_with_progress_mode(self, tmp_path):
        """Test CLI with progress mode option."""
        from click.testing import CliRunner
        
        manifest = [{"id": "test-123", "file_name": "test.txt"}]
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))
        
        token_file = tmp_path / "token.txt"
        token_file.write_text("test-token-abc123def456ghi789")
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        runner = CliRunner()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            with patch('gdc_uploader.upload.upload_file_with_progress') as mock_upload:
                mock_upload.return_value = {"status": "success"}
                
                result = runner.invoke(main, [
                    '--manifest', 'manifest.json',
                    '--file', 'test.txt',
                    '--token', 'token.txt',
                    '--progress-mode', 'simple'
                ])
                
                assert result.exit_code == 0
                assert "Starting upload..." in result.output
                assert "✓ Upload successful!" in result.output
        finally:
            os.chdir(original_dir)
    
    def test_cli_with_output_file(self, tmp_path):
        """Test CLI with output file logging."""
        manifest = [{
            "id": "test-123",
            "file_name": "test.txt",
            "file_size": 100
        }]
        
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))
        
        token_file = tmp_path / "token.txt"
        token_file.write_text("test-token-abc123def456ghi789")
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        log_file = tmp_path / "upload.log"
        
        runner = CliRunner()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            with patch('gdc_uploader.upload.upload_file_with_progress') as mock_upload:
                mock_upload.return_value = {"status": "success", "file_id": "test-123"}
                
                result = runner.invoke(main, [
                    '--manifest', 'manifest.json',
                    '--file', 'test.txt',
                    '--token', 'token.txt',
                    '--output', str(log_file)
                ])
                
                assert result.exit_code == 0
                assert log_file.exists()
                
                log_content = log_file.read_text()
                assert "GDC Upload Log" in log_content
                assert "test.txt" in log_content
                assert '"status": "success"' in log_content
        finally:
            os.chdir(original_dir)


class TestUtilityFunctions:
    """Test utility functions still work."""
    
    def test_chunk_reader_with_callback(self):
        """Test chunk reader with callback."""
        data = b"A" * 5000  # 5KB
        file_obj = BytesIO(data)
        
        callback_sizes = []
        chunks = list(chunk_reader(
            file_obj,
            chunk_size=1000,
            callback=lambda size: callback_sizes.append(size)
        ))
        
        assert len(callback_sizes) == 5
        assert sum(callback_sizes) == len(data)
        assert b"".join(chunks) == data