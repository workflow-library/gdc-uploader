# GDC API Client Library

A comprehensive Python client library for interacting with the Genomic Data Commons (GDC) API, providing robust file upload capabilities, metadata operations, and project management.

## Features

- **Robust HTTP Client**: Built on `requests` with automatic retry, rate limiting, and connection pooling
- **Async Support**: High-performance async client using `aiohttp` for concurrent operations
- **Authentication Management**: Flexible token management with multiple providers
- **Type Safety**: Pydantic models for all API requests and responses
- **Error Handling**: Comprehensive exception hierarchy for different error scenarios
- **Rate Limiting**: Token bucket algorithm to respect API limits
- **Progress Tracking**: Built-in progress callbacks for uploads
- **Resumable Uploads**: Support for resuming interrupted uploads

## Installation

```bash
pip install requests aiohttp pydantic aiofiles
```

## Quick Start

### Basic Usage

```python
from gdc_uploader.api import GDCAPIClient, TokenManager

# Create token manager
token_manager = TokenManager.from_file("/path/to/token.txt")

# Create API client
client = GDCAPIClient(
    token=token_manager.get_token(),
    rate_limit=10.0,  # 10 requests per second
    max_retries=3
)

# Upload a file
response = client.upload_file(
    project_id="TCGA-LUAD",
    file_id="550e8400-e29b-41d4-a716-446655440000",
    file_path="/path/to/data.bam",
    chunk_size=10 * 1024 * 1024  # 10MB chunks
)

print(f"Upload status: {response.status}")
print(f"Uploaded size: {response.uploaded_size:,} bytes")
```

### Async Usage

```python
import asyncio
from gdc_uploader.api import AsyncGDCAPIClient, TokenManager

async def upload_files():
    token_manager = TokenManager.from_file("/path/to/token.txt")
    
    async with AsyncGDCAPIClient(token_manager) as client:
        # Upload single file
        response = await client.upload_file(
            project_id="TCGA-LUAD",
            file_id="550e8400-e29b-41d4-a716-446655440000",
            file_path="/path/to/data.bam"
        )
        
        # Batch upload multiple files
        from gdc_uploader.api.models import BatchUploadRequest, FileUploadRequest
        
        batch_request = BatchUploadRequest(
            project_id="TCGA-LUAD",
            files=[
                FileUploadRequest(
                    file_id="file-uuid-1",
                    project_id="TCGA-LUAD",
                    file_path="/path/to/file1.bam",
                    file_size=1000000
                ),
                FileUploadRequest(
                    file_id="file-uuid-2",
                    project_id="TCGA-LUAD",
                    file_path="/path/to/file2.bam",
                    file_size=2000000
                )
            ],
            parallel_uploads=4
        )
        
        batch_response = await client.batch_upload(batch_request)
        print(f"Success rate: {batch_response.success_rate:.1f}%")

asyncio.run(upload_files())
```

## Authentication

### Token Providers

The library supports multiple ways to provide authentication tokens:

```python
from gdc_uploader.api import TokenManager

# From file
token_manager = TokenManager.from_file("/path/to/token.txt")

# From environment variable
token_manager = TokenManager.from_environment("GDC_TOKEN")

# From static string
token_manager = TokenManager.from_token("your-token-here")

# With caching and validation
token_manager = token_manager.with_caching(validation_client=client)
```

### Security Best Practices

- Store tokens in files with restricted permissions (600)
- Use environment variables in production
- Never commit tokens to version control
- Rotate tokens regularly

## Progress Tracking

```python
def progress_callback(uploaded: int, total: int):
    percentage = (uploaded / total) * 100
    print(f"Progress: {uploaded:,}/{total:,} bytes ({percentage:.1f}%)")

response = client.upload_file(
    project_id="TCGA-LUAD",
    file_id="file-uuid",
    file_path="/path/to/large-file.bam",
    progress_callback=progress_callback
)
```

## Resumable Uploads

```python
# Check current upload status
status = client.get_file_status("TCGA-LUAD", "file-uuid")
print(f"Already uploaded: {status.uploaded_size:,} bytes")

# Resume from where it left off
response = client.upload_file(
    project_id="TCGA-LUAD",
    file_id="file-uuid",
    file_path="/path/to/file.bam",
    resume_from=status.uploaded_size
)
```

## Error Handling

```python
from gdc_uploader.api import (
    GDCAPIClient,
    GDCAuthenticationError,
    GDCRateLimitError,
    GDCUploadError
)

try:
    client.upload_file(...)
except GDCAuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Refresh token and retry
except GDCRateLimitError as e:
    print(f"Rate limited: {e}")
    print(f"Retry after: {e.retry_after} seconds")
except GDCUploadError as e:
    print(f"Upload failed: {e}")
    print(f"File ID: {e.file_id}")
    print(f"Uploaded: {e.uploaded_bytes}/{e.total_bytes}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Advanced Features

### Custom Rate Limiting

```python
# Create custom token bucket
from gdc_uploader.api import TokenBucket

bucket = TokenBucket(
    tokens=100,      # Initial tokens
    refill_rate=20   # Tokens per second
)

# Use with client
client = GDCAPIClient(
    token=token,
    rate_limit=20.0  # 20 requests per second
)
```

### Connection Pooling

```python
client = GDCAPIClient(
    token=token,
    pool_connections=20,  # Number of connection pools
    pool_maxsize=50,      # Max connections per pool
    timeout=(30.0, 300.0) # (connect, read) timeouts
)
```

### Streaming Uploads (Async)

```python
async def generate_chunks():
    """Generate file chunks on the fly."""
    with open("large-file.bam", "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            yield chunk

async with AsyncGDCAPIClient(token_manager) as client:
    response = await client.stream_upload(
        project_id="TCGA-LUAD",
        file_id="file-uuid",
        stream=generate_chunks(),
        total_size=file_size
    )
```

## API Models

All API interactions use type-safe Pydantic models:

```python
from gdc_uploader.api.models import (
    FileUploadRequest,
    FileUploadResponse,
    FileStatus,
    ProjectInfo,
    TokenValidationResponse
)

# Models provide validation
request = FileUploadRequest(
    file_id="invalid-uuid",  # Will raise validation error
    project_id="TCGA-LUAD",
    file_path="/path/to/file.bam",
    file_size=1000000
)

# Models have helpful properties
status = FileStatus(...)
print(f"Upload progress: {status.upload_progress:.1f}%")
print(f"Is uploaded: {status.is_uploaded}")
```

## Best Practices

1. **Use context managers** to ensure proper cleanup:
   ```python
   with GDCAPIClient(token) as client:
       client.upload_file(...)
   ```

2. **Handle retries** at the application level for critical operations:
   ```python
   for attempt in range(3):
       try:
           response = client.upload_file(...)
           break
       except GDCServerError:
           if attempt == 2:
               raise
           time.sleep(2 ** attempt)
   ```

3. **Monitor rate limits** to avoid throttling:
   ```python
   try:
       client.upload_file(...)
   except GDCRateLimitError as e:
       time.sleep(e.retry_after)
       client.upload_file(...)
   ```

4. **Use async client** for concurrent operations:
   ```python
   # Upload 10 files concurrently
   async with AsyncGDCAPIClient(token_manager) as client:
       tasks = [
           client.upload_file(project_id, file_id, path)
           for file_id, path in files
       ]
       results = await asyncio.gather(*tasks)
   ```

## Troubleshooting

### Common Issues

1. **Token validation fails**
   - Ensure token file exists and is readable
   - Check token hasn't expired
   - Verify token has necessary permissions

2. **Connection errors**
   - Check network connectivity
   - Verify firewall rules
   - Ensure SSL certificates are valid

3. **Upload failures**
   - Check file exists and is readable
   - Verify file size matches metadata
   - Ensure sufficient disk space

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('gdc_uploader.api')
```

## Contributing

See the main project README for contribution guidelines.

## License

This project is licensed under the MIT License.