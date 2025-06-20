#!/usr/bin/env python3
"""
GDC validation functions for manifest and metadata.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def validate_manifest(manifest_path: Path) -> List[Dict[str, Any]]:
    """
    Validate and parse GDC manifest file.
    
    Args:
        manifest_path: Path to manifest JSON file
        
    Returns:
        List of file entries from manifest
        
    Raises:
        ValueError: If manifest is invalid
    """
    if not manifest_path.exists():
        raise ValueError(f"Manifest file not found: {manifest_path}")
    
    try:
        with open(manifest_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in manifest: {e}")
    
    # Handle both array and dict formats
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict) and 'files' in data:
        entries = data['files']
    else:
        raise ValueError("Manifest must be array or object with 'files' field")
    
    # Validate each entry has required fields
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {i} is not an object")
        if 'id' not in entry:
            raise ValueError(f"Entry {i} missing required field 'id'")
        if 'file_name' not in entry:
            raise ValueError(f"Entry {i} missing required field 'file_name'")
    
    return entries


def validate_token(token_path: Path) -> str:
    """
    Validate and read GDC token file.
    
    Args:
        token_path: Path to token file
        
    Returns:
        Token string
        
    Raises:
        ValueError: If token is invalid
    """
    if not token_path.exists():
        raise ValueError(f"Token file not found: {token_path}")
    
    with open(token_path) as f:
        token = f.read().strip()
    
    if not token:
        raise ValueError("Token file is empty")
    
    # Basic token format validation
    if len(token) < 20:
        raise ValueError("Token appears to be invalid (too short)")
    
    return token


def find_manifest_entry(entries: List[Dict[str, Any]], filename: str) -> Dict[str, Any]:
    """
    Find entry for specific file in manifest.
    
    Args:
        entries: List of manifest entries
        filename: Target filename
        
    Returns:
        Manifest entry for file
        
    Raises:
        ValueError: If file not found
    """
    for entry in entries:
        if entry.get('file_name') == filename:
            return entry
    
    raise ValueError(f"File '{filename}' not found in manifest")