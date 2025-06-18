"""Unit tests for file_operations module."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add path for imports
import sys
sys.path.insert(0, '/workspaces/gdc-uploader-agents/agent-2-common-utilities/src')
sys.path.append('/workspaces/gdc-uploader-agents/agent-1-core-architecture/specs/interfaces')

from gdc_uploader.core.file_operations import (
    FileSearchConfig,
    StandardFileDiscoveryStrategy,
    OptimizedFileDiscovery,
    calculate_md5,
    calculate_file_stats,
    filter_files_by_metadata,
    organize_files_by_type
)
from base_uploader_interface import FileEntry
from exceptions_interface import (
    FileNotFoundError as GDCFileNotFoundError,
    InvalidDirectoryError,
    FileSizeError,
    ChecksumMismatchError
)


class TestFileSearchConfig:
    """Test FileSearchConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = FileSearchConfig()
        assert config.subdirectories == [
            "fastq", "uBam", "sequence-files", "sequences", 
            "data", "files", "uploads", "output"
        ]
        assert config.recursive is True
        assert config.follow_symlinks is False
        assert config.validate_checksums is False
        assert config.validate_sizes is True
        
    def test_custom_config(self):
        """Test custom configuration."""
        config = FileSearchConfig(
            subdirectories=["custom"],
            recursive=False,
            validate_checksums=True
        )
        assert config.subdirectories == ["custom"]
        assert config.recursive is False
        assert config.validate_checksums is True


class TestStandardFileDiscoveryStrategy:
    """Test StandardFileDiscoveryStrategy class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory structure."""
        temp = tempfile.mkdtemp()
        
        # Create test structure
        Path(temp, "fastq").mkdir()
        Path(temp, "bam").mkdir()
        Path(temp, "nested", "deep").mkdir(parents=True)
        
        # Create test files
        Path(temp, "test1.fastq").write_text("content1")
        Path(temp, "fastq", "test2.fastq").write_text("content2")
        Path(temp, "bam", "test3.bam").write_text("content3")
        Path(temp, "nested", "deep", "test4.fastq").write_text("content4")
        
        yield Path(temp)
        
        # Cleanup
        shutil.rmtree(temp)
        
    def test_discover_nonexistent_directory(self):
        """Test discovery with non-existent directory."""
        strategy = StandardFileDiscoveryStrategy()
        
        with pytest.raises(InvalidDirectoryError) as exc_info:
            list(strategy.discover(Path("/nonexistent"), {}))
        assert "Directory does not exist" in str(exc_info.value)
        
    def test_discover_file_instead_of_directory(self, temp_dir):
        """Test discovery with file path instead of directory."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("test")
        
        strategy = StandardFileDiscoveryStrategy()
        
        with pytest.raises(InvalidDirectoryError) as exc_info:
            list(strategy.discover(file_path, {}))
        assert "Path is not a directory" in str(exc_info.value)
        
    def test_discover_in_subdirectories(self, temp_dir):
        """Test file discovery in standard subdirectories."""
        metadata = {
            "files": [
                {"uuid": "uuid1", "filename": "test1.fastq"},
                {"uuid": "uuid2", "filename": "test2.fastq"}
            ]
        }
        
        strategy = StandardFileDiscoveryStrategy()
        results = list(strategy.discover(temp_dir, metadata))
        
        assert len(results) == 2
        assert results[0].uuid == "uuid1"
        assert results[0].filename == "test1.fastq"
        assert results[0].path == temp_dir / "test1.fastq"
        
        assert results[1].uuid == "uuid2"
        assert results[1].filename == "test2.fastq"
        assert results[1].path == temp_dir / "fastq" / "test2.fastq"
        
    def test_discover_recursive(self, temp_dir):
        """Test recursive file discovery."""
        metadata = [
            {"uuid": "uuid4", "filename": "test4.fastq"}
        ]
        
        strategy = StandardFileDiscoveryStrategy()
        results = list(strategy.discover(temp_dir, metadata))
        
        assert len(results) == 1
        assert results[0].uuid == "uuid4"
        assert results[0].path == temp_dir / "nested" / "deep" / "test4.fastq"
        
    def test_discover_with_size_validation(self, temp_dir):
        """Test file discovery with size validation."""
        metadata = {
            "uuid": "uuid1",
            "filename": "test1.fastq",
            "size": 8  # Correct size
        }
        
        config = FileSearchConfig(validate_sizes=True)
        strategy = StandardFileDiscoveryStrategy(config)
        results = list(strategy.discover(temp_dir, metadata))
        
        assert len(results) == 1
        assert results[0].size == 8
        
    def test_discover_with_size_mismatch(self, temp_dir):
        """Test file discovery with size mismatch."""
        metadata = {
            "uuid": "uuid1",
            "filename": "test1.fastq",
            "size": 999  # Wrong size
        }
        
        config = FileSearchConfig(validate_sizes=True)
        strategy = StandardFileDiscoveryStrategy(config)
        
        with pytest.raises(FileSizeError) as exc_info:
            list(strategy.discover(temp_dir, metadata))
        assert "test1.fastq" in str(exc_info.value)
        
    def test_discover_with_patterns(self, temp_dir):
        """Test file discovery with include/exclude patterns."""
        # Create additional files
        Path(temp_dir, "test.tmp").write_text("temp")
        Path(temp_dir, ".hidden").write_text("hidden")
        
        metadata = {
            "files": [
                {"uuid": "uuid1", "filename": "test1.fastq"},
                {"uuid": "uuid2", "filename": "test.tmp"},
                {"uuid": "uuid3", "filename": ".hidden"}
            ]
        }
        
        config = FileSearchConfig(
            exclude_patterns=["*.tmp", ".*"]
        )
        strategy = StandardFileDiscoveryStrategy(config)
        results = list(strategy.discover(temp_dir, metadata))
        
        # Should only find test1.fastq
        assert len(results) == 1
        assert results[0].filename == "test1.fastq"
        
    def test_discover_missing_required_file(self, temp_dir):
        """Test discovery with missing required file."""
        metadata = {
            "uuid": "uuid_missing",
            "filename": "nonexistent.fastq"
        }
        
        config = FileSearchConfig(require_all_files=True)
        strategy = StandardFileDiscoveryStrategy(config)
        
        with pytest.raises(GDCFileNotFoundError) as exc_info:
            list(strategy.discover(temp_dir, metadata))
        assert "nonexistent.fastq" in str(exc_info.value)
        assert "uuid_missing" in str(exc_info.value)


class TestOptimizedFileDiscovery:
    """Test OptimizedFileDiscovery class."""
    
    @pytest.fixture
    def temp_dir_with_many_files(self):
        """Create temporary directory with many files."""
        temp = tempfile.mkdtemp()
        temp_path = Path(temp)
        
        # Create nested structure with files
        for i in range(5):
            subdir = temp_path / f"dir{i}"
            subdir.mkdir()
            for j in range(10):
                (subdir / f"file{j}.txt").write_text(f"content{i}{j}")
                
        yield temp_path
        
        # Cleanup
        shutil.rmtree(temp)
        
    def test_build_index(self, temp_dir_with_many_files):
        """Test building file index."""
        discovery = OptimizedFileDiscovery(temp_dir_with_many_files)
        
        # Track progress
        progress_calls = []
        discovery.build_index(progress_callback=lambda x: progress_calls.append(x))
        
        # Should have indexed 50 files
        assert discovery._file_index is not None
        assert len(discovery._file_index) == 10  # 10 unique filenames
        
        # Each filename should have 5 paths
        for filename, paths in discovery._file_index.items():
            assert len(paths) == 5
            
    def test_find_file(self, temp_dir_with_many_files):
        """Test finding a file using index."""
        discovery = OptimizedFileDiscovery(temp_dir_with_many_files)
        
        # Find existing file
        result = discovery.find_file("file0.txt")
        assert result is not None
        assert result.name == "file0.txt"
        assert result.exists()
        
        # Find non-existent file
        result = discovery.find_file("nonexistent.txt")
        assert result is None
        
    def test_find_all_files(self, temp_dir_with_many_files):
        """Test finding all instances of a file."""
        discovery = OptimizedFileDiscovery(temp_dir_with_many_files)
        
        results = discovery.find_all_files("file0.txt")
        assert len(results) == 5
        
        # All should be named file0.txt
        for path in results:
            assert path.name == "file0.txt"


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_calculate_md5(self):
        """Test MD5 calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            
            md5 = calculate_md5(Path(f.name))
            assert md5 == "9a0364b9e99bb480dd25e1f0284c8555"
            
            Path(f.name).unlink()
            
    def test_calculate_file_stats(self):
        """Test file statistics calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            
            stats = calculate_file_stats(Path(f.name))
            
            assert stats["size"] == 12
            assert stats["readable"] is True
            assert "mtime" in stats
            assert "mode" in stats
            
            Path(f.name).unlink()
            
    def test_filter_files_by_metadata(self):
        """Test filtering files by metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            file1 = temp_path / "test1.txt"
            file2 = temp_path / "test2.txt"
            file3 = temp_path / "test3.txt"
            
            file1.write_text("a" * 10)
            file2.write_text("b" * 20)
            file3.write_text("c" * 30)
            
            files = [file1, file2, file3]
            metadata = [
                {"filename": "test1.txt", "size": 10},
                {"filename": "test2.txt", "size": 20}
            ]
            
            # Filter with strict mode
            results = filter_files_by_metadata(files, metadata, strict=True)
            assert len(results) == 2
            assert results[0][0] == file1
            assert results[1][0] == file2
            
            # Filter with wrong size
            metadata_wrong = [{"filename": "test1.txt", "size": 999}]
            results = filter_files_by_metadata(files, metadata_wrong, strict=True)
            assert len(results) == 0
            
    def test_organize_files_by_type(self):
        """Test organizing files by type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_dir = temp_path / "input"
            output_dir = temp_path / "output"
            input_dir.mkdir()
            
            # Create test files
            files = []
            for name in ["test.fastq", "test.bam", "test.vcf", "test.txt"]:
                file_path = input_dir / name
                file_path.write_text("content")
                files.append(file_path)
                
            # Organize files
            organized = organize_files_by_type(files, output_dir, copy=False)
            
            assert "fastq" in organized
            assert "bam" in organized
            assert "vcf" in organized
            assert "other" in organized
            
            # Check symlinks were created
            assert (output_dir / "fastq" / "test.fastq").is_symlink()
            assert (output_dir / "bam" / "test.bam").is_symlink()