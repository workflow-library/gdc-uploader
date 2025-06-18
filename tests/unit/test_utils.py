"""Unit tests for utils module."""

import pytest
import json
import yaml
import tempfile
import shutil
import platform
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add path for imports
import sys
sys.path.insert(0, '/workspaces/gdc-uploader-agents/agent-2-common-utilities/src')
sys.path.append('/workspaces/gdc-uploader-agents/agent-1-core-architecture/specs/interfaces')

from gdc_uploader.core.utils import (
    load_metadata,
    validate_metadata_structure,
    merge_metadata,
    load_token,
    validate_token_permissions,
    check_system_requirements,
    check_command_availability,
    ensure_dependencies,
    setup_logging,
    temporary_directory,
    generate_tsv_report,
    generate_json_report,
    format_size,
    format_duration,
    sanitize_filename,
    run_command,
    calculate_sha256,
    verify_checksum,
    batch_items,
    parallel_map,
    ExitCodes
)
from exceptions_interface import (
    InvalidMetadataError,
    TokenFileNotFoundError,
    InvalidTokenError,
    MissingDependencyError
)


class TestMetadataHandling:
    """Test metadata handling functions."""
    
    def test_load_json_metadata(self, tmp_path):
        """Test loading JSON metadata."""
        metadata_file = tmp_path / "metadata.json"
        test_data = {"files": [{"uuid": "123", "filename": "test.txt"}]}
        
        with open(metadata_file, "w") as f:
            json.dump(test_data, f)
            
        result = load_metadata(metadata_file)
        assert result == test_data
        
    def test_load_yaml_metadata(self, tmp_path):
        """Test loading YAML metadata."""
        metadata_file = tmp_path / "metadata.yaml"
        test_data = {"files": [{"uuid": "123", "filename": "test.txt"}]}
        
        with open(metadata_file, "w") as f:
            yaml.dump(test_data, f)
            
        result = load_metadata(metadata_file)
        assert result == test_data
        
    def test_load_nonexistent_metadata(self):
        """Test loading non-existent metadata file."""
        with pytest.raises(InvalidMetadataError, match="Metadata file not found"):
            load_metadata("/nonexistent/file.json")
            
    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON."""
        metadata_file = tmp_path / "invalid.json"
        metadata_file.write_text("{invalid json")
        
        with pytest.raises(InvalidMetadataError, match="Failed to parse"):
            load_metadata(metadata_file)
            
    def test_load_empty_metadata(self, tmp_path):
        """Test loading empty metadata file."""
        metadata_file = tmp_path / "empty.json"
        metadata_file.write_text("null")
        
        with pytest.raises(InvalidMetadataError, match="Metadata file is empty"):
            load_metadata(metadata_file)
            
    def test_validate_metadata_array_format(self):
        """Test validating metadata in array format."""
        metadata = [
            {"uuid": "123", "filename": "file1.txt"},
            {"uuid": "456", "filename": "file2.txt"}
        ]
        
        # Should not raise
        validate_metadata_structure(metadata)
        
    def test_validate_metadata_object_format(self):
        """Test validating metadata in object format."""
        metadata = {"uuid": "123", "filename": "test.txt"}
        
        # Should not raise
        validate_metadata_structure(metadata)
        
    def test_validate_metadata_files_format(self):
        """Test validating metadata with files array."""
        metadata = {
            "files": [
                {"uuid": "123", "filename": "test.txt"}
            ]
        }
        
        # Should not raise
        validate_metadata_structure(metadata)
        
    def test_validate_invalid_metadata_structure(self):
        """Test validating invalid metadata structure."""
        # Wrong type
        with pytest.raises(InvalidMetadataError, match="Invalid metadata type"):
            validate_metadata_structure("not a dict or list")
            
        # Empty array
        with pytest.raises(InvalidMetadataError, match="Metadata array is empty"):
            validate_metadata_structure([])
            
        # Missing required fields
        with pytest.raises(InvalidMetadataError, match="missing required field 'uuid'"):
            validate_metadata_structure([{"filename": "test.txt"}])
            
        with pytest.raises(InvalidMetadataError, match="missing required field 'filename'"):
            validate_metadata_structure([{"uuid": "123"}])
            
    def test_merge_metadata(self):
        """Test metadata merging."""
        base = {
            "version": "1.0",
            "files": [{"uuid": "123"}],
            "config": {"timeout": 30}
        }
        
        updates = {
            "version": "2.0",
            "config": {"retry": 3, "timeout": 60}
        }
        
        result = merge_metadata(base, updates)
        
        assert result["version"] == "2.0"
        assert result["files"] == [{"uuid": "123"}]
        assert result["config"]["timeout"] == 60
        assert result["config"]["retry"] == 3


class TestTokenHandling:
    """Test token handling functions."""
    
    def test_load_valid_token(self, tmp_path):
        """Test loading valid token."""
        token_file = tmp_path / "token.txt"
        test_token = "a" * 64  # 64 character hex token
        token_file.write_text(test_token)
        
        result = load_token(token_file)
        assert result == test_token
        
    def test_load_nonexistent_token(self):
        """Test loading non-existent token."""
        with pytest.raises(TokenFileNotFoundError):
            load_token("/nonexistent/token.txt")
            
    def test_load_empty_token(self, tmp_path):
        """Test loading empty token file."""
        token_file = tmp_path / "empty.txt"
        token_file.write_text("")
        
        with pytest.raises(InvalidTokenError, match="Token file is empty"):
            load_token(token_file)
            
    def test_load_short_token(self, tmp_path):
        """Test loading too short token."""
        token_file = tmp_path / "short.txt"
        token_file.write_text("short")
        
        with pytest.raises(InvalidTokenError, match="Token appears to be too short"):
            load_token(token_file)
            
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix permissions test")
    def test_validate_token_permissions(self, tmp_path):
        """Test token permission validation."""
        token_file = tmp_path / "token.txt"
        token_file.write_text("test token")
        
        # Set insecure permissions
        token_file.chmod(0o644)
        
        # Should log warning but not raise
        with patch('gdc_uploader.core.utils.logger') as mock_logger:
            validate_token_permissions(token_file)
            mock_logger.warning.assert_called()


class TestSystemUtilities:
    """Test system and environment utilities."""
    
    def test_check_system_requirements(self):
        """Test system requirements check."""
        info = check_system_requirements()
        
        assert "platform" in info
        assert "python_version" in info
        assert "cpu_count" in info
        assert "memory_total_gb" in info
        assert "memory_available_gb" in info
        assert "disk_usage" in info
        
    def test_check_command_availability(self):
        """Test command availability check."""
        # Python should always be available
        assert check_command_availability("python") is True
        
        # Non-existent command
        assert check_command_availability("nonexistent_command_xyz") is False
        
    def test_ensure_dependencies_success(self):
        """Test ensuring dependencies when all present."""
        # Python should be available
        ensure_dependencies(["python"])  # Should not raise
        
    def test_ensure_dependencies_missing(self):
        """Test ensuring dependencies when missing."""
        with pytest.raises(MissingDependencyError) as exc_info:
            ensure_dependencies(["nonexistent_command_xyz"])
            
        assert "nonexistent_command_xyz" in str(exc_info.value)


class TestLoggingUtilities:
    """Test logging utilities."""
    
    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        import logging
        
        setup_logging(log_level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG
        
    def test_setup_logging_with_file(self, tmp_path):
        """Test logging setup with file output."""
        import logging
        
        log_file = tmp_path / "test.log"
        setup_logging(log_level="INFO", log_file=log_file)
        
        # Log something
        logging.info("Test message")
        
        # Check file was created
        assert log_file.exists()
        assert "Test message" in log_file.read_text()
        
    def test_temporary_directory(self):
        """Test temporary directory context manager."""
        temp_path = None
        
        with temporary_directory(prefix="test_") as temp_dir:
            temp_path = temp_dir
            assert temp_dir.exists()
            assert temp_dir.is_dir()
            assert temp_dir.name.startswith("test_")
            
            # Create a file in it
            (temp_dir / "test.txt").write_text("test")
            
        # Directory should be cleaned up
        assert not temp_path.exists()


class TestReportGeneration:
    """Test report generation utilities."""
    
    def test_generate_tsv_report(self, tmp_path):
        """Test TSV report generation."""
        results = [
            {"uuid": "123", "filename": "file1.txt", "status": "success"},
            {"uuid": "456", "filename": "file2.txt", "status": "failed"}
        ]
        
        output_path = tmp_path / "report.tsv"
        generate_tsv_report(results, output_path)
        
        assert output_path.exists()
        lines = output_path.read_text().strip().split('\n')
        assert len(lines) == 3  # Header + 2 rows
        assert "uuid\tfilename\tstatus" in lines[0]
        
    def test_generate_tsv_report_custom_columns(self, tmp_path):
        """Test TSV report with custom columns."""
        results = [
            {"uuid": "123", "filename": "file1.txt", "status": "success", "extra": "data"},
        ]
        
        output_path = tmp_path / "report.tsv"
        generate_tsv_report(results, output_path, columns=["uuid", "status"])
        
        lines = output_path.read_text().strip().split('\n')
        assert "uuid\tstatus" in lines[0]
        assert "filename" not in lines[0]
        
    def test_generate_json_report(self, tmp_path):
        """Test JSON report generation."""
        results = [
            {"uuid": "123", "filename": "file1.txt", "status": "success"},
        ]
        metadata = {"version": "1.0"}
        
        output_path = tmp_path / "report.json"
        generate_json_report(results, output_path, metadata=metadata)
        
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)
            
        assert "timestamp" in data
        assert data["results"] == results
        assert data["metadata"] == metadata


class TestFormattingUtilities:
    """Test string and formatting utilities."""
    
    def test_format_size(self):
        """Test size formatting."""
        assert format_size(512) == "512.00 B"
        assert format_size(1024) == "1.00 KB"
        assert format_size(1024 * 1024) == "1.00 MB"
        assert format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"
        assert format_size(1024 * 1024 * 1024 * 1024 * 1024) == "1.00 PB"
        
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(30) == "30.0s"
        assert format_duration(90) == "1.5m"
        assert format_duration(3600) == "1.0h"
        assert format_duration(86400) == "1.0d"
        
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("normal.txt") == "normal.txt"
        assert sanitize_filename("file<>name.txt") == "file__name.txt"
        assert sanitize_filename("file:name|test?.txt") == "file_name_test_.txt"
        
        # Test length limiting
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".txt")


class TestCommandExecution:
    """Test command execution utilities."""
    
    def test_run_command_success(self):
        """Test successful command execution."""
        result = run_command(["echo", "test"])
        assert result.returncode == 0
        assert "test" in result.stdout
        
    def test_run_command_failure(self):
        """Test failed command execution."""
        with pytest.raises(subprocess.CalledProcessError):
            run_command(["false"])
            
    def test_run_command_timeout(self):
        """Test command timeout."""
        with pytest.raises(subprocess.TimeoutExpired):
            run_command(["sleep", "10"], timeout=1)


class TestChecksumUtilities:
    """Test checksum utilities."""
    
    def test_calculate_sha256(self, tmp_path):
        """Test SHA256 calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        sha256 = calculate_sha256(test_file)
        assert sha256 == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        
    def test_verify_checksum_md5(self, tmp_path):
        """Test MD5 checksum verification."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Correct checksum
        assert verify_checksum(test_file, "9a0364b9e99bb480dd25e1f0284c8555", "md5") is True
        
        # Wrong checksum
        assert verify_checksum(test_file, "wrong_checksum", "md5") is False
        
    def test_verify_checksum_sha256(self, tmp_path):
        """Test SHA256 checksum verification."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        expected = "1eebdf4fdc9fc7bf283031b93f9aef3338de9052fde2e2b0fe78da2a415bfe51"
        assert verify_checksum(test_file, expected, "sha256") is True
        
    def test_verify_checksum_invalid_algorithm(self, tmp_path):
        """Test invalid checksum algorithm."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            verify_checksum(test_file, "checksum", "invalid")


class TestBatchProcessing:
    """Test batch processing utilities."""
    
    def test_batch_items(self):
        """Test item batching."""
        items = list(range(10))
        
        batches = batch_items(items, 3)
        assert len(batches) == 4
        assert batches[0] == [0, 1, 2]
        assert batches[1] == [3, 4, 5]
        assert batches[2] == [6, 7, 8]
        assert batches[3] == [9]
        
    def test_parallel_map(self):
        """Test parallel mapping."""
        def square(x):
            return x * x
            
        items = list(range(10))
        results = parallel_map(square, items, max_workers=2)
        
        expected = [x * x for x in items]
        assert results == expected
        
    def test_parallel_map_with_errors(self):
        """Test parallel mapping with errors."""
        def may_fail(x):
            if x == 5:
                raise ValueError("Failed on 5")
            return x * 2
            
        items = list(range(10))
        results = parallel_map(may_fail, items)
        
        # Should have None for failed item
        assert results[5] is None
        assert results[0] == 0
        assert results[1] == 2


class TestExitCodes:
    """Test exit codes."""
    
    def test_exit_code_values(self):
        """Test exit code values."""
        assert ExitCodes.SUCCESS == 0
        assert ExitCodes.GENERAL_ERROR == 1
        assert ExitCodes.UPLOAD_FAILED == 2
        assert ExitCodes.FILE_NOT_FOUND == 4