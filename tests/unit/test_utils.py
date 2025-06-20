#!/usr/bin/env python3
"""Unit tests for utility functions."""

import pytest
from pathlib import Path
from gdc_uploader.utils import find_file, chunk_reader, format_size


def test_find_file_in_current_dir(tmp_path):
    """Test finding file in current directory."""
    file_path = tmp_path / "sample.txt"
    file_path.touch()
    
    # Change to tmp directory
    import os
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        found = find_file("sample.txt")
        assert found == Path("sample.txt")
    finally:
        os.chdir(original_dir)


def test_find_file_in_subdir(tmp_path):
    """Test finding file in subdirectory."""
    subdir = tmp_path / "fastq"
    subdir.mkdir()
    file_path = subdir / "sample.fastq.gz"
    file_path.touch()
    
    import os
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        found = find_file("sample.fastq.gz")
        assert found == Path("fastq/sample.fastq.gz")
    finally:
        os.chdir(original_dir)


def test_find_file_not_found(tmp_path):
    """Test file not found."""
    import os
    original_dir = os.getcwd()
    try:
        os.chdir(tmp_path)
        found = find_file("nonexistent.txt")
        assert found is None
    finally:
        os.chdir(original_dir)


def test_chunk_reader():
    """Test chunk reader."""
    from io import BytesIO
    
    data = b"Hello, World! This is test data."
    file_obj = BytesIO(data)
    
    chunks = list(chunk_reader(file_obj, chunk_size=5))
    assert len(chunks) == 7
    assert chunks[0] == b"Hello"
    assert chunks[-1] == b"a."
    assert b"".join(chunks) == data


def test_chunk_reader_with_callback():
    """Test chunk reader with callback."""
    from io import BytesIO
    
    data = b"Test data"
    file_obj = BytesIO(data)
    
    sizes = []
    chunks = list(chunk_reader(file_obj, chunk_size=3, callback=sizes.append))
    
    assert sizes == [3, 3, 3]
    assert len(chunks) == 3


def test_format_size():
    """Test size formatting."""
    assert format_size(0) == "0.0 B"
    assert format_size(500) == "500.0 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1536) == "1.5 KB"
    assert format_size(1048576) == "1.0 MB"
    assert format_size(1073741824) == "1.0 GB"
    assert format_size(1099511627776) == "1.0 TB"