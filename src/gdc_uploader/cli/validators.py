"""Custom validators and parameter types for GDC Uploader CLI."""

import json
from pathlib import Path
from typing import Any, Optional, Union

import click


class ThreadCount(click.ParamType):
    """Validate thread count is within reasonable bounds."""
    
    name = "thread_count"
    
    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> int:
        """Convert and validate thread count."""
        if isinstance(value, int):
            thread_count = value
        else:
            try:
                thread_count = int(value)
            except ValueError:
                self.fail(f"{value!r} is not a valid integer", param, ctx)
        
        if thread_count < 1:
            self.fail("Thread count must be at least 1", param, ctx)
        elif thread_count > 32:
            self.fail("Thread count must not exceed 32", param, ctx)
            
        return thread_count


class RetryCount(click.ParamType):
    """Validate retry count is within reasonable bounds."""
    
    name = "retry_count"
    
    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> int:
        """Convert and validate retry count."""
        if isinstance(value, int):
            retry_count = value
        else:
            try:
                retry_count = int(value)
            except ValueError:
                self.fail(f"{value!r} is not a valid integer", param, ctx)
        
        if retry_count < 0:
            self.fail("Retry count cannot be negative", param, ctx)
        elif retry_count > 10:
            self.fail("Retry count must not exceed 10", param, ctx)
            
        return retry_count


class GDCMetadataFile(click.Path):
    """Validate GDC metadata file format and content."""
    
    def __init__(self):
        super().__init__(exists=True, file_okay=True, dir_okay=False, path_type=Path)
    
    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> Path:
        """Convert and validate metadata file."""
        path = super().convert(value, param, ctx)
        
        # Validate file extension
        if path.suffix.lower() not in ['.json', '.yaml', '.yml']:
            self.fail(f"Metadata file must be JSON or YAML format, got {path.suffix}", param, ctx)
        
        # For JSON files, validate structure
        if path.suffix.lower() == '.json':
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    
                # Basic validation - check if it's a list or has expected structure
                if not isinstance(data, (list, dict)):
                    self.fail("Invalid JSON structure: expected object or array", param, ctx)
                    
                # If it's a list, check first item has required fields
                if isinstance(data, list) and data:
                    first_item = data[0]
                    if not isinstance(first_item, dict):
                        self.fail("Invalid JSON structure: array items must be objects", param, ctx)
                    
                    # Check for common GDC fields
                    required_fields = ['id', 'file_name']
                    missing_fields = [f for f in required_fields if f not in first_item]
                    if missing_fields:
                        self.fail(f"Missing required fields in metadata: {', '.join(missing_fields)}", param, ctx)
                        
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON file: {e}", param, ctx)
            except Exception as e:
                self.fail(f"Error reading metadata file: {e}", param, ctx)
                
        return path


class GDCTokenFile(click.Path):
    """Validate GDC token file."""
    
    def __init__(self):
        super().__init__(exists=True, file_okay=True, dir_okay=False, path_type=Path)
    
    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> Path:
        """Convert and validate token file."""
        path = super().convert(value, param, ctx)
        
        try:
            # Check file is readable and not empty
            content = path.read_text().strip()
            if not content:
                self.fail("Token file is empty", param, ctx)
                
            # Basic token format validation (should be a UUID-like string)
            if len(content) < 20:
                self.fail("Token appears to be invalid (too short)", param, ctx)
                
        except Exception as e:
            self.fail(f"Error reading token file: {e}", param, ctx)
            
        return path


class OutputDirectory(click.Path):
    """Validate output directory with auto-creation option."""
    
    def __init__(self, create: bool = True):
        super().__init__(file_okay=False, dir_okay=True, path_type=Path)
        self.create = create
    
    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> Path:
        """Convert and validate output directory."""
        path = Path(value)
        
        if not path.exists() and self.create:
            try:
                path.mkdir(parents=True, exist_ok=True)
                click.echo(f"Created output directory: {path}", err=True)
            except Exception as e:
                self.fail(f"Failed to create output directory: {e}", param, ctx)
        elif not path.exists():
            self.fail(f"Output directory does not exist: {path}", param, ctx)
        elif not path.is_dir():
            self.fail(f"Output path is not a directory: {path}", param, ctx)
            
        return path


def validate_field_name(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate field name for JSON operations."""
    if not value:
        raise click.BadParameter("Field name cannot be empty")
        
    # Check for common invalid characters
    invalid_chars = [' ', '.', '[', ']', '{', '}']
    for char in invalid_chars:
        if char in value:
            raise click.BadParameter(f"Field name cannot contain '{char}'")
            
    return value


def validate_file_prefix(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate file prefix for split operations."""
    if not value:
        raise click.BadParameter("File prefix cannot be empty")
        
    # Check for invalid filename characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in value:
            raise click.BadParameter(f"File prefix cannot contain '{char}'")
            
    return value


# Export custom types
THREAD_COUNT = ThreadCount()
RETRY_COUNT = RetryCount()
GDC_METADATA_FILE = GDCMetadataFile()
GDC_TOKEN_FILE = GDCTokenFile()