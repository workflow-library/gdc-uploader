#!/usr/bin/env python3
"""Unit tests for validation functions."""

import json
import pytest
from pathlib import Path
from gdc_uploader.validate import validate_manifest, validate_token, find_manifest_entry


def test_validate_manifest_array_format(tmp_path):
    """Test manifest validation with array format."""
    manifest = [
        {"id": "abc123", "file_name": "sample1.fastq.gz"},
        {"id": "def456", "file_name": "sample2.fastq.gz"}
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    
    entries = validate_manifest(manifest_path)
    assert len(entries) == 2
    assert entries[0]["id"] == "abc123"


def test_validate_manifest_object_format(tmp_path):
    """Test manifest validation with object format."""
    manifest = {
        "files": [
            {"id": "abc123", "file_name": "sample1.fastq.gz"},
            {"id": "def456", "file_name": "sample2.fastq.gz"}
        ]
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    
    entries = validate_manifest(manifest_path)
    assert len(entries) == 2
    assert entries[0]["id"] == "abc123"


def test_validate_manifest_missing_file():
    """Test manifest validation with missing file."""
    with pytest.raises(ValueError, match="Manifest file not found"):
        validate_manifest(Path("nonexistent.json"))


def test_validate_manifest_invalid_json(tmp_path):
    """Test manifest validation with invalid JSON."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{invalid json")
    
    with pytest.raises(ValueError, match="Invalid JSON"):
        validate_manifest(manifest_path)


def test_validate_token(tmp_path):
    """Test token validation."""
    token_path = tmp_path / "token.txt"
    token_path.write_text("abcdefghijklmnopqrstuvwxyz123456")
    
    token = validate_token(token_path)
    assert token == "abcdefghijklmnopqrstuvwxyz123456"


def test_validate_token_missing_file():
    """Test token validation with missing file."""
    with pytest.raises(ValueError, match="Token file not found"):
        validate_token(Path("nonexistent.txt"))


def test_validate_token_empty_file(tmp_path):
    """Test token validation with empty file."""
    token_path = tmp_path / "token.txt"
    token_path.write_text("")
    
    with pytest.raises(ValueError, match="Token file is empty"):
        validate_token(token_path)


def test_find_manifest_entry():
    """Test finding entry in manifest."""
    entries = [
        {"id": "abc123", "file_name": "sample1.fastq.gz"},
        {"id": "def456", "file_name": "sample2.fastq.gz"}
    ]
    
    entry = find_manifest_entry(entries, "sample2.fastq.gz")
    assert entry["id"] == "def456"
    
    with pytest.raises(ValueError, match="not found in manifest"):
        find_manifest_entry(entries, "sample3.fastq.gz")