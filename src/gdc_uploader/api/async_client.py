"""Asynchronous GDC API Client for high-performance concurrent operations.

This module provides an async version of the GDC API client using aiohttp
for better performance when handling multiple concurrent uploads.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Union, List, Tuple, AsyncIterator
from pathlib import Path
from datetime import datetime
import aiofiles
from contextlib import asynccontextmanager

import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError, ClientResponseError

from .exceptions import (
    GDCAPIException,
    GDCAuthenticationError,
    GDCRateLimitError,
    GDCServerError,
    GDCValidationError,
    GDCConnectionError,
    GDCTimeoutError
)
from .models import (
    FileUploadRequest,
    FileUploadResponse,
    FileStatus,
    UploadStatus,
    ProjectInfo,
    TokenValidationResponse,
    BatchUploadRequest,
    BatchUploadResponse
)
from .auth import TokenManager

logger = logging.getLogger(__name__)


class AsyncTokenBucket:
    """Async token bucket implementation for rate limiting."""
    
    def __init__(self, tokens: float, refill_rate: float):
        """Initialize the async token bucket.
        
        Args:
            tokens: Initial number of tokens (and max capacity)
            refill_rate: Tokens added per second
        """
        self.capacity = tokens
        self.tokens = tokens
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        async with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on time passed."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def wait_for_tokens(self, tokens: float = 1.0) -> float:
        """Wait until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time waited in seconds
        """
        start_time = time.time()
        while not await self.consume(tokens):
            await asyncio.sleep(0.1)  # Check every 100ms
        return time.time() - start_time


class AsyncGDCAPIClient:
    """Asynchronous client for interacting with the GDC API.
    
    This client provides high-performance async operations for:
    - Concurrent file uploads
    - Batch operations
    - Streaming uploads
    - Progress tracking
    """
    
    DEFAULT_BASE_URL = "https://api.gdc.cancer.gov"
    DEFAULT_SUBMISSION_URL = "https://api.gdc.cancer.gov/v0/submission"
    
    def __init__(
        self,
        token_manager: TokenManager,
        base_url: str = None,
        max_retries: int = 3,
        rate_limit: float = 10.0,  # requests per second
        timeout: ClientTimeout = None,
        connector_limit: int = 100,
        verify_ssl: bool = True,
        user_agent: str = "gdc-uploader-async/2.0"
    ):
        """Initialize the async GDC API client.
        
        Args:
            token_manager: Token manager for authentication
            base_url: Base URL for the GDC API
            max_retries: Maximum number of retry attempts
            rate_limit: Maximum requests per second
            timeout: aiohttp ClientTimeout configuration
            connector_limit: Maximum number of connections
            verify_ssl: Whether to verify SSL certificates
            user_agent: User agent string for requests
        """
        self.token_manager = token_manager
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.submission_url = f"{self.base_url}/v0/submission"
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.user_agent = user_agent
        
        # Initialize rate limiter
        self.rate_limiter = AsyncTokenBucket(rate_limit * 2, rate_limit)
        
        # Configure timeout
        self.timeout = timeout or ClientTimeout(
            total=300,
            connect=30,
            sock_connect=30,
            sock_read=300
        )
        
        # Configure connector
        self.connector = aiohttp.TCPConnector(
            limit=connector_limit,
            limit_per_host=30,
            ttl_dns_cache=300,
            enable_cleanup_closed=True
        )
        
        # Session will be created in async context
        self._session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start the client session."""
        if self._session is None:
            self._session = ClientSession(
                connector=self.connector,
                timeout=self.timeout,
                headers={
                    'User-Agent': self.user_agent,
                    'Accept': 'application/json'
                },
                connector_owner=False
            )
            # Validate token on startup
            await self._validate_token()
    
    async def close(self):
        """Close the client session and cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
        await self.connector.close()
    
    async def _validate_token(self):
        """Validate the authentication token."""
        try:
            response = await self.validate_token()
            if not response.is_valid:
                raise GDCAuthenticationError("Invalid authentication token")
            logger.info(f"Token validated successfully. User: {response.username}")
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise GDCAuthenticationError(f"Token validation failed: {str(e)}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with current token."""
        return {
            'X-Auth-Token': self.token_manager.get_token()
        }
    
    async def _make_request(
        self,
        method: str,
        url: str,
        retry_count: int = 0,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method
            url: Full URL to request
            retry_count: Current retry attempt
            **kwargs: Additional arguments for request
            
        Returns:
            Client response
            
        Raises:
            Various GDCAPIException subclasses
        """
        if not self._session:
            raise RuntimeError("Client not started. Use 'async with' or call start()")
        
        # Apply rate limiting
        wait_time = await self.rate_limiter.wait_for_tokens()
        if wait_time > 0:
            logger.debug(f"Rate limited, waited {wait_time:.2f}s")
        
        # Add authentication headers
        headers = kwargs.pop('headers', {})
        headers.update(self._get_headers())
        
        try:
            async with self._session.request(
                method, url, headers=headers, ssl=self.verify_ssl, **kwargs
            ) as response:
                # Check for specific error codes
                if response.status == 401:
                    raise GDCAuthenticationError("Authentication failed - invalid token")
                elif response.status == 429:
                    retry_after = response.headers.get('Retry-After', 60)
                    raise GDCRateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
                elif response.status >= 500:
                    if retry_count < self.max_retries:
                        wait_time = (2 ** retry_count) * 0.5  # Exponential backoff
                        logger.warning(
                            f"Server error {response.status}, retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        return await self._make_request(
                            method, url, retry_count + 1, **kwargs
                        )
                    raise GDCServerError(f"Server error: {response.status}")
                elif response.status >= 400:
                    error_msg = await self._parse_error_response(response)
                    raise GDCValidationError(f"Client error: {response.status} - {error_msg}")
                
                response.raise_for_status()
                return response
                
        except asyncio.TimeoutError:
            raise GDCTimeoutError(f"Request timed out: {method} {url}")
        except aiohttp.ClientConnectionError as e:
            raise GDCConnectionError(f"Connection failed: {str(e)}")
        except ClientError as e:
            raise GDCAPIException(f"Request failed: {str(e)}")
    
    async def _parse_error_response(self, response: aiohttp.ClientResponse) -> str:
        """Parse error message from API response."""
        try:
            error_data = await response.json()
            if isinstance(error_data, dict):
                return error_data.get('message', error_data.get('error', str(error_data)))
            return str(error_data)
        except Exception:
            return await response.text() or f"HTTP {response.status}"
    
    async def validate_token(self) -> TokenValidationResponse:
        """Validate the current authentication token.
        
        Returns:
            TokenValidationResponse with validation details
        """
        url = f"{self.base_url}/auth/user"
        response = await self._make_request("GET", url)
        data = await response.json()
        
        return TokenValidationResponse(
            is_valid=True,
            username=data.get("username", "unknown"),
            projects=data.get("projects", {})
        )
    
    async def upload_file_chunk(
        self,
        project_id: str,
        file_id: str,
        chunk: bytes,
        chunk_size: int,
        offset: int = 0,
        total_size: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> FileUploadResponse:
        """Upload a file chunk to GDC asynchronously.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            chunk: File chunk data
            chunk_size: Size of the chunk in bytes
            offset: Byte offset for this chunk
            total_size: Total file size
            progress_callback: Optional async callback for progress
            
        Returns:
            FileUploadResponse with upload details
        """
        url = f"{self.submission_url}/{project_id}/files/{file_id}"
        
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(chunk_size)
        }
        
        # Add Content-Range header if needed
        if offset > 0 or total_size:
            end_byte = offset + chunk_size - 1
            content_range = f"bytes {offset}-{end_byte}/"
            content_range += str(total_size) if total_size else "*"
            headers['Content-Range'] = content_range
        
        response = await self._make_request(
            "PUT",
            url,
            headers=headers,
            data=chunk
        )
        
        data = await response.json()
        
        # Call progress callback if provided
        if progress_callback:
            if asyncio.iscoroutinefunction(progress_callback):
                await progress_callback(offset + chunk_size, total_size)
            else:
                progress_callback(offset + chunk_size, total_size)
        
        return FileUploadResponse(
            file_id=file_id,
            status=data.get("status", "unknown"),
            uploaded_size=offset + chunk_size,
            timestamp=datetime.utcnow(),
            warnings=data.get("warnings", [])
        )
    
    async def upload_file(
        self,
        project_id: str,
        file_id: str,
        file_path: Union[str, Path],
        chunk_size: int = 1024 * 1024 * 10,  # 10MB chunks
        resume_from: int = 0,
        progress_callback: Optional[callable] = None
    ) -> FileUploadResponse:
        """Upload a complete file to GDC asynchronously.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            file_path: Path to the file to upload
            chunk_size: Size of each chunk in bytes
            resume_from: Byte offset to resume from
            progress_callback: Optional callback for progress
            
        Returns:
            FileUploadResponse with final upload status
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        logger.info(f"Uploading {file_path.name} ({file_size:,} bytes) to {project_id}/{file_id}")
        
        uploaded_size = resume_from
        last_response = None
        
        async with aiofiles.open(file_path, 'rb') as f:
            if resume_from > 0:
                await f.seek(resume_from)
                logger.info(f"Resuming upload from byte {resume_from:,}")
            
            while uploaded_size < file_size:
                # Read chunk
                chunk_data = await f.read(chunk_size)
                if not chunk_data:
                    break
                
                actual_chunk_size = len(chunk_data)
                
                # Upload chunk
                last_response = await self.upload_file_chunk(
                    project_id=project_id,
                    file_id=file_id,
                    chunk=chunk_data,
                    chunk_size=actual_chunk_size,
                    offset=uploaded_size,
                    total_size=file_size,
                    progress_callback=progress_callback
                )
                
                uploaded_size += actual_chunk_size
                
                # Log progress
                progress_pct = (uploaded_size / file_size) * 100
                logger.debug(f"Uploaded {uploaded_size:,}/{file_size:,} bytes ({progress_pct:.1f}%)")
        
        logger.info(f"File upload completed: {file_path.name}")
        return last_response
    
    async def batch_upload(
        self,
        batch_request: BatchUploadRequest,
        progress_callback: Optional[callable] = None
    ) -> BatchUploadResponse:
        """Upload multiple files concurrently.
        
        Args:
            batch_request: Batch upload request with file list
            progress_callback: Optional callback for overall progress
            
        Returns:
            BatchUploadResponse with results for all files
        """
        start_time = datetime.utcnow()
        results = []
        successful = 0
        failed = 0
        
        # Create upload tasks
        tasks = []
        for file_request in batch_request.files:
            task = self.upload_file(
                project_id=batch_request.project_id,
                file_id=file_request.file_id,
                file_path=file_request.file_path,
                chunk_size=file_request.chunk_size,
                resume_from=file_request.resume_from
            )
            tasks.append(task)
        
        # Run uploads with concurrency limit
        semaphore = asyncio.Semaphore(batch_request.parallel_uploads)
        
        async def upload_with_semaphore(file_request, task):
            async with semaphore:
                try:
                    result = await task
                    return result, None
                except Exception as e:
                    logger.error(f"Upload failed for {file_request.file_id}: {e}")
                    return None, e
        
        # Execute all uploads
        upload_tasks = [
            upload_with_semaphore(file_req, task)
            for file_req, task in zip(batch_request.files, tasks)
        ]
        
        completed_tasks = await asyncio.gather(*upload_tasks, return_exceptions=False)
        
        # Process results
        for idx, (result, error) in enumerate(completed_tasks):
            if error:
                failed += 1
                # Create error response
                results.append(FileUploadResponse(
                    file_id=batch_request.files[idx].file_id,
                    status=UploadStatus.FAILED,
                    uploaded_size=0,
                    timestamp=datetime.utcnow(),
                    errors=[str(error)]
                ))
            else:
                successful += 1
                results.append(result)
            
            # Progress callback
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(idx + 1, len(batch_request.files))
                else:
                    progress_callback(idx + 1, len(batch_request.files))
        
        return BatchUploadResponse(
            total_files=len(batch_request.files),
            successful=successful,
            failed=failed,
            results=results,
            start_time=start_time,
            end_time=datetime.utcnow()
        )
    
    async def get_file_status(self, project_id: str, file_id: str) -> FileStatus:
        """Get the status of a file in GDC.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            
        Returns:
            FileStatus object
        """
        url = f"{self.submission_url}/{project_id}/files/{file_id}"
        response = await self._make_request("GET", url)
        data = await response.json()
        
        return FileStatus(
            file_id=file_id,
            project_id=project_id,
            state=data.get("state", "unknown"),
            uploaded_size=data.get("size", 0),
            md5sum=data.get("md5sum"),
            created_datetime=data.get("created_datetime"),
            updated_datetime=data.get("updated_datetime")
        )
    
    async def stream_upload(
        self,
        project_id: str,
        file_id: str,
        stream: AsyncIterator[bytes],
        total_size: Optional[int] = None,
        chunk_size: int = 1024 * 1024 * 10
    ) -> FileUploadResponse:
        """Upload from an async stream/generator.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            stream: Async iterator yielding chunks
            total_size: Total size if known
            chunk_size: Size hint for buffering
            
        Returns:
            FileUploadResponse
        """
        offset = 0
        last_response = None
        buffer = bytearray()
        
        async for chunk in stream:
            buffer.extend(chunk)
            
            # Upload when buffer reaches chunk_size
            while len(buffer) >= chunk_size:
                upload_chunk = bytes(buffer[:chunk_size])
                buffer = buffer[chunk_size:]
                
                last_response = await self.upload_file_chunk(
                    project_id=project_id,
                    file_id=file_id,
                    chunk=upload_chunk,
                    chunk_size=len(upload_chunk),
                    offset=offset,
                    total_size=total_size
                )
                offset += len(upload_chunk)
        
        # Upload remaining buffer
        if buffer:
            last_response = await self.upload_file_chunk(
                project_id=project_id,
                file_id=file_id,
                chunk=bytes(buffer),
                chunk_size=len(buffer),
                offset=offset,
                total_size=total_size
            )
        
        return last_response