# GDC Uploader Architecture (v2.0)

## Overview

The GDC Uploader has been refactored to have a clean, modular architecture that eliminates code duplication and provides a consistent interface for all upload strategies.

## Directory Structure

```
src/gdc_uploader/
├── __init__.py              # Package initialization
├── cli.py                   # Simplified CLI using Click
├── core/                    # Core functionality (from Agents 1 & 2)
│   ├── base_uploader.py     # Abstract base class for all uploaders
│   ├── exceptions.py        # Unified exception hierarchy
│   ├── file_operations.py   # File discovery and validation
│   ├── plugins.py           # Plugin system for extensions
│   ├── progress.py          # Progress tracking utilities
│   ├── retry.py             # Retry handling with backoff
│   └── utils.py             # General utilities
├── api/                     # API client (from Agent 6)
│   ├── client.py            # GDC API client with rate limiting
│   ├── async_client.py      # Async version of API client
│   ├── auth.py              # Authentication handling
│   ├── exceptions.py        # API-specific exceptions
│   └── models.py            # Pydantic models for API data
├── cli/                     # CLI utilities (from Agent 4)
│   ├── options.py           # Reusable CLI option decorators
│   ├── output.py            # Rich output formatting
│   └── validators.py        # Input validation
└── uploaders/               # Concrete uploader implementations
    ├── standard.py          # Standard gdc-client based uploader
    ├── api.py               # Direct API upload
    ├── spot.py              # Spot instance aware uploader
    └── single.py            # Single file uploader
```

## Key Components

### 1. Base Architecture (Agent 1)
- **BaseUploader**: Abstract base class defining the interface all uploaders must implement
- **Exceptions**: Unified exception hierarchy for consistent error handling
- **Plugin System**: Extensibility through plugins

### 2. Common Utilities (Agent 2)
- **File Operations**: Centralized file discovery, validation, and handling
- **Progress Tracking**: Unified progress reporting across all uploaders
- **Retry Logic**: Configurable retry with exponential backoff
- **General Utils**: Logging, YAML/JSON conversion, etc.

### 3. API Client (Agent 6)
- **Rate Limiting**: Token bucket algorithm to respect API limits
- **Connection Pooling**: Efficient connection reuse
- **Retry Logic**: Automatic retry with backoff for transient failures
- **Type Safety**: Pydantic models for all API interactions

### 4. CLI (Agent 4)
- **Simplified Commands**: Clean command structure without duplication
- **Rich Output**: Beautiful terminal output with progress bars and tables
- **Reusable Options**: Common options defined once and reused

## Upload Strategies

### Standard Uploader
- Uses `gdc-client` executable
- Best for large files and stable connections
- Supports parallel uploads

### API Uploader
- Direct HTTP uploads using the API client
- Chunk-based uploads for reliability
- Built-in progress tracking

### Spot Uploader
- Designed for AWS Spot instances
- Checkpoint/resume capability
- Handles interruptions gracefully

### Single File Uploader
- Optimized for individual file uploads
- Simple interface for one-off uploads

## Usage Examples

```bash
# Standard upload
gdc-uploader upload -m metadata.json -t token.txt /path/to/files

# API upload with custom chunk size
gdc-uploader api-upload -m metadata.json -t token.txt --chunk-size 5242880 /path/to/files

# Convert YAML to JSON
gdc-uploader yaml2json config.yaml -o config.json
```

## Key Improvements

1. **No Code Duplication**: All uploaders share common utilities
2. **Consistent Interface**: Every uploader implements BaseUploader
3. **Better Error Handling**: Unified exception hierarchy
4. **Improved Performance**: Connection pooling and parallel processing
5. **Rich Output**: Beautiful CLI with progress bars and tables
6. **Type Safety**: Pydantic models for API data
7. **Extensibility**: Plugin system for custom uploaders

## Future Extensions

The architecture supports easy addition of:
- New upload strategies (implement BaseUploader)
- Custom file discovery logic (extend FileDiscovery)
- Additional API endpoints (extend GDCAPIClient)
- New CLI commands (add to cli.py)
- Custom plugins (implement Plugin interface)