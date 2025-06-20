# Agent: Implement HTTP Uploader

## Task Reference
From spec: `gdc_http_upload.md` - Task #4

## Role
Build HTTP PUT uploader with chunked transfer for GDC API.

## Context
- Core upload functionality for GDC HTTP Upload feature
- Must handle large files efficiently
- API endpoint and headers defined in spec

## Requirements from Spec
- HTTP PUT to `https://api.gdc.cancer.gov/v0/submission/files/{file_id}`
- Required headers: X-Auth-Token, Content-Type, Content-Length
- Chunked transfer for memory efficiency
- Support files up to 100GB
- Return GDC API response

## Implementation Guidelines
- Use requests library for HTTP
- Implement generator for chunk reading
- Default chunk size: 8192 bytes
- Stream request body to avoid memory issues
- Handle HTTP errors appropriately

## Inputs
- File path to upload
- File ID from manifest
- Authentication token string
- Optional: chunk size

## Expected Output
- Success: API response dict with status
- Failure: Raise requests.exceptions.RequestException
- Network errors handled by requests

## Success Criteria
- Constant memory usage during upload
- Correct headers sent to API
- Chunks yielded efficiently
- API response parsed correctly
- HTTP errors propagated properly