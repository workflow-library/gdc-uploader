#!/usr/bin/env python3
"""Integration tests simulating Seven Bridges Platform environment."""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from io import StringIO

from gdc_uploader.upload_robust import (
    detect_environment,
    get_progress_handler,
    upload_file_with_progress,
    main
)


class TestSBPEnvironment:
    """Test behavior in simulated SBP environment."""
    
    @pytest.fixture
    def sbp_env(self):
        """Fixture to simulate SBP environment."""
        env_vars = {
            'SBP_TASK_ID': 'test-task-123',
            'SBP_PROJECT_ID': 'test-project',
            'TERM': 'dumb',  # SBP often has limited terminal
        }
        with patch.dict(os.environ, env_vars):
            # Also patch isatty to return False
            with patch('sys.stdout.isatty', return_value=False):
                yield env_vars
    
    @pytest.fixture
    def cwl_env(self):
        """Fixture to simulate CWL environment."""
        env_vars = {
            'CWL_RUNTIME': 'true',
            'TMPDIR': '/tmp/cwl_tmp',
            'HOME': '/tmp/home',
        }
        with patch.dict(os.environ, env_vars):
            with patch('sys.stdout.isatty', return_value=False):
                yield env_vars
    
    def test_sbp_environment_detection(self, sbp_env):
        """Test that SBP environment is correctly detected."""
        env = detect_environment()
        
        assert env['is_sbp'] is True
        assert env['is_tty'] is False
        assert env['term'] == 'dumb'
    
    def test_cwl_environment_detection(self, cwl_env):
        """Test that CWL environment is correctly detected."""
        env = detect_environment()
        
        assert env['is_cwl'] is True
        assert env['is_tty'] is False
    
    def test_sbp_forces_simple_progress(self, sbp_env):
        """Test that SBP environment forces simple progress."""
        handler = get_progress_handler(1000, "Upload", mode='auto')
        
        from gdc_uploader.upload_robust import SimpleProgress
        assert isinstance(handler, SimpleProgress)
    
    def test_progress_output_in_sbp(self, sbp_env, tmp_path, capsys):
        """Test progress output format in SBP environment."""
        test_file = tmp_path / "test.bin"
        test_content = b"X" * 10000  # 10KB
        test_file.write_bytes(test_content)
        
        with patch('gdc_uploader.upload_robust.requests.put') as mock_put:
            def mock_put_func(*args, **kwargs):
                # Consume data to trigger progress
                data_gen = kwargs.get('data')
                if data_gen:
                    for chunk in data_gen:
                        pass
                
                mock_response = Mock()
                mock_response.json.return_value = {
                    "status": "success",
                    "file_id": "test-123"
                }
                mock_response.raise_for_status.return_value = None
                return mock_response
            
            mock_put.side_effect = mock_put_func
            
            result = upload_file_with_progress(
                test_file,
                "test-id",
                "test-token",
                chunk_size=1000,  # 1KB chunks for 10 updates
                progress_mode='auto'  # Should auto-detect SBP
            )
            
            captured = capsys.readouterr()
            output_lines = captured.out.strip().split('\n')
            
            # Verify output format
            assert any("Uploading: 0% (0/10,000 bytes)" in line for line in output_lines)
            assert any("Uploading: 10%" in line for line in output_lines)
            assert any("Uploading: 100% (10,000/10,000 bytes)" in line for line in output_lines)
            
            # Verify no ANSI codes or carriage returns
            assert '\r' not in captured.out
            assert '\033[' not in captured.out  # No ANSI escape codes
    
    def test_json_style_progress(self, sbp_env, tmp_path):
        """Test JSON-style progress output for machine parsing."""
        # This is a potential future enhancement
        # SBP could parse JSON progress messages
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")
        
        # Mock stdout to capture JSON output
        output = StringIO()
        
        with patch('sys.stdout', output):
            with patch('gdc_uploader.upload_robust.requests.put') as mock_put:
                mock_response = Mock()
                mock_response.json.return_value = {"status": "success"}
                mock_response.raise_for_status.return_value = None
                mock_put.return_value = mock_response
                
                # This would be a future feature
                # upload_file_with_progress(
                #     test_file, "id", "token", 
                #     progress_mode='json'
                # )
                
                # For now, just verify simple mode works
                upload_file_with_progress(
                    test_file, "id", "token",
                    progress_mode='simple'
                )
        
        output_str = output.getvalue()
        assert "Uploading:" in output_str


class TestCWLIntegration:
    """Test CWL-specific integration."""
    
    def test_cwl_with_file_inputs(self, tmp_path):
        """Test handling of CWL file inputs."""
        # CWL often stages files in specific directories
        cwl_staging = tmp_path / "cwl_staging"
        cwl_staging.mkdir()
        
        # Simulate CWL file staging
        manifest = {
            "location": "file:///tmp/manifest.json",
            "class": "File",
            "contents": [{"id": "test-123", "file_name": "input.fastq"}]
        }
        
        manifest_file = cwl_staging / "manifest.json"
        manifest_file.write_text(json.dumps(manifest["contents"]))
        
        token_file = cwl_staging / "token.txt"
        token_file.write_text("test-token")
        
        input_file = cwl_staging / "input.fastq"
        input_file.write_text("@READ1\nACGT\n+\nIIII\n")
        
        with patch.dict(os.environ, {'CWL_RUNTIME': 'true'}):
            from click.testing import CliRunner
            from gdc_uploader.upload_robust import main
            
            runner = CliRunner()
            
            original_dir = os.getcwd()
            try:
                os.chdir(cwl_staging)
                
                with patch('gdc_uploader.upload_robust.requests.put') as mock_put:
                    mock_response = Mock()
                    mock_response.json.return_value = {"status": "success"}
                    mock_response.raise_for_status.return_value = None
                    mock_put.return_value = mock_response
                    
                    result = runner.invoke(main, [
                        '--manifest', 'manifest.json',
                        '--file', 'input.fastq',
                        '--token', 'token.txt'
                    ])
                    
                    assert result.exit_code == 0
                    assert "Starting upload..." in result.output
                    
                    # Verify simple progress was used
                    env = detect_environment()
                    assert env['is_cwl'] is True
            finally:
                os.chdir(original_dir)


class TestProgressModeSelection:
    """Test progress mode selection in various environments."""
    
    @pytest.mark.parametrize("env_vars,expected_simple", [
        ({}, False),  # Normal terminal
        ({'SBP_TASK_ID': '123'}, True),  # SBP
        ({'CWL_RUNTIME': 'true'}, True),  # CWL
        ({'TERM': 'dumb'}, True),  # Dumb terminal
        ({'CI': 'true'}, False),  # CI environment (might have good terminal)
    ])
    def test_auto_mode_selection(self, env_vars, expected_simple):
        """Test auto mode selects appropriate progress type."""
        with patch.dict(os.environ, env_vars, clear=False):
            # Assume TTY is False in test environment
            with patch('sys.stdout.isatty', return_value=False):
                handler = get_progress_handler(1000, "Test", mode='auto')
                
                from gdc_uploader.upload_robust import SimpleProgress
                if expected_simple or not sys.stdout.isatty():
                    assert isinstance(handler, SimpleProgress)


class TestErrorHandlingInSBP:
    """Test error handling in SBP environment."""
    
    def test_error_output_format(self, sbp_env, tmp_path):
        """Test that errors are clearly formatted in SBP."""
        from click.testing import CliRunner
        from gdc_uploader.upload_robust import main
        
        # Missing manifest file
        runner = CliRunner()
        result = runner.invoke(main, [
            '--manifest', 'missing.json',
            '--file', 'test.txt',
            '--token', 'token.txt'
        ])
        
        assert result.exit_code == 1
        assert "Error:" in result.output
        
        # Error should be on its own line for clarity
        error_lines = [l for l in result.output.split('\n') if 'Error:' in l]
        assert len(error_lines) >= 1