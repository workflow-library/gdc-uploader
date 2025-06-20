#!/usr/bin/env python3
"""Test logging functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gdc_uploader.upload import Logger


class TestLogger:
    """Test Logger class functionality."""
    
    def test_logger_console_only(self, capsys):
        """Test logger with console output only."""
        logger = Logger()
        logger.echo("Test message")
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out
        
        logger.echo("Error message", err=True)
        captured = capsys.readouterr()
        assert "Error message" in captured.err
    
    def test_logger_with_file(self, tmp_path):
        """Test logger with file output."""
        log_file = tmp_path / "test.log"
        
        with Logger(log_file) as logger:
            logger.echo("Test message")
            logger.echo("Error message", err=True)
            logger.write_json({"status": "success"}, "Test JSON")
        
        # Read and verify log file
        content = log_file.read_text()
        assert "GDC Upload Log" in content
        assert "Test message" in content
        assert "ERROR: Error message" in content
        assert '"status": "success"' in content
        assert "Log ended at" in content
    
    def test_logger_append_mode(self, tmp_path):
        """Test logger in append mode."""
        log_file = tmp_path / "test.log"
        
        # First write
        with Logger(log_file) as logger:
            logger.echo("First message")
        
        # Append
        with Logger(log_file, append=True) as logger:
            logger.echo("Second message")
        
        content = log_file.read_text()
        assert "First message" in content
        assert "Second message" in content
        assert content.count("GDC Upload Log") == 2  # Two headers
    
    def test_logger_no_console(self, capsys):
        """Test logger with console output disabled."""
        logger = Logger()
        logger.echo("Test message", to_console=False)
        
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_logger_json_formatting(self, tmp_path):
        """Test JSON formatting in logger."""
        log_file = tmp_path / "test.log"
        
        test_data = {
            "status": "success",
            "file_id": "123",
            "bytes_uploaded": 1000
        }
        
        with Logger(log_file) as logger:
            logger.write_json(test_data, "Upload Result")
        
        content = log_file.read_text()
        assert "Upload Result:" in content
        assert json.dumps(test_data, indent=2) in content