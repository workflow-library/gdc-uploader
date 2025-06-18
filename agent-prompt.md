# Agent 6: API Client Developer

You are Agent 6, responsible for creating a proper HTTP API client abstraction for all GDC API interactions.

## Your Mission

Extract and consolidate all HTTP/API interactions into a well-designed, reusable client library. Currently, API calls are scattered throughout the codebase with inconsistent error handling and no proper abstraction.

## Context

Current API usage issues:
- Direct `requests` calls scattered in multiple files
- No consistent error handling or retry logic
- No rate limiting implementation
- Session management is ad-hoc
- No connection pooling for performance

## Your Tasks

1. **Create `src/gdc_uploader/api/client.py`**
   - Design a clean API client class
   - Wrap all GDC API endpoints
   - Implement proper session management
   - Add rate limiting to respect API limits
   - Include comprehensive error handling
   - Support both synchronous and async operations

2. **Create `src/gdc_uploader/api/models.py`**
   - Define Pydantic models for API requests/responses
   - Add validation for API data
   - Create type-safe interfaces
   - Document all model fields

3. **Implement Authentication Management**
   - Secure token handling
   - Token validation and refresh
   - Support multiple authentication methods
   - Handle token expiration gracefully

4. **Add Connection Pooling**
   - Implement connection reuse for performance
   - Configure pool size and timeouts
   - Add connection health checks
   - Support concurrent requests

## Current API Usage to Consolidate

From `parallel_api_upload.py`:
```python
# Current: Direct API calls scattered in code
headers = {
    'X-Auth-Token': token,
    'Content-Type': 'application/octet-stream',
    'Content-Length': str(chunk_size)
}
response = session.put(url, headers=headers, data=chunk)
response.raise_for_status()
```

## Target API Client Design

```python
# src/gdc_uploader/api/client.py
from typing import Optional, Dict, Any, BinaryIO
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

class GDCAPIClient:
    """Client for interacting with the GDC API."""
    
    def __init__(
        self,
        token: str,
        base_url: str = "https://api.gdc.cancer.gov",
        max_retries: int = 3,
        rate_limit: float = 10.0,  # requests per second
        pool_connections: int = 10,
        pool_maxsize: int = 20
    ):
        self.token = token
        self.base_url = base_url
        self.rate_limit = rate_limit
        self._last_request_time = 0
        
        # Configure session with connection pooling
        self.session = Session()
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=Retry(
                total=max_retries,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504]
            )
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'X-Auth-Token': self.token,
            'User-Agent': 'gdc-uploader/2.0'
        })
    
    def upload_file_chunk(
        self,
        file_id: str,
        chunk: BinaryIO,
        chunk_size: int,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Upload a file chunk to GDC."""
        self._rate_limit()
        
        url = f"{self.base_url}/files/{file_id}"
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(chunk_size),
            'Content-Range': f'bytes {offset}-{offset + chunk_size - 1}/*'
        }
        
        response = self.session.put(url, headers=headers, data=chunk)
        response.raise_for_status()
        return response.json()
    
    def _rate_limit(self):
        """Implement rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        min_interval = 1.0 / self.rate_limit
        
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        
        self._last_request_time = time.time()
```

## API Models Design

```python
# src/gdc_uploader/api/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class FileUploadRequest(BaseModel):
    """Request model for file upload."""
    file_id: str = Field(..., description="GDC file UUID")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    md5sum: Optional[str] = Field(None, regex="^[a-f0-9]{32}$")
    
    @validator('file_id')
    def validate_uuid(cls, v):
        # UUID validation logic
        return v

class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    file_id: str
    status: str
    uploaded_size: int
    timestamp: datetime
    warnings: List[str] = []

class GDCError(BaseModel):
    """Error response from GDC API."""
    error_type: str
    message: str
    code: int
    details: Optional[Dict[str, Any]] = None
```

## Advanced Features

### Rate Limiting with Token Bucket
```python
class TokenBucket:
    """Token bucket for rate limiting."""
    def __init__(self, tokens: float, refill_rate: float):
        self.capacity = tokens
        self.tokens = tokens
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens."""
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def refill(self):
        """Refill tokens based on time passed."""
        now = time.time()
        tokens_to_add = (now - self.last_refill) * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
```

### Async Support
```python
import aiohttp
import asyncio

class AsyncGDCAPIClient:
    """Async version of GDC API client."""
    
    async def upload_file_chunk_async(self, ...):
        """Async file upload."""
        pass
```

## Error Handling

```python
class GDCAPIException(Exception):
    """Base exception for GDC API errors."""
    pass

class GDCAuthenticationError(GDCAPIException):
    """Authentication failed."""
    pass

class GDCRateLimitError(GDCAPIException):
    """Rate limit exceeded."""
    pass

class GDCServerError(GDCAPIException):
    """Server-side error."""
    pass
```

## Dependencies

- Can start immediately (no dependencies)
- Coordinate with Agent 3 on integration points
- Work with Agent 5 on mock implementations

## Success Criteria

- All API calls go through the client
- Consistent error handling across all operations
- Rate limiting prevents API throttling
- Connection pooling improves performance
- Comprehensive API documentation
- Both sync and async support

## Getting Started

1. Analyze current API usage patterns
2. Design the client interface
3. Implement core client functionality
4. Add rate limiting and connection pooling
5. Create comprehensive error handling
6. Document all endpoints and models
7. Update progress in `specs/agent-6-progress.md`

Remember: This client will be the single point of interaction with the GDC API - make it robust, performant, and easy to use!