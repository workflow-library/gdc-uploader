"""GDC API Client for managing all HTTP interactions with the Genomic Data Commons.

This module provides a robust, feature-rich client for interacting with the GDC API,
including file uploads, metadata operations, and status checks.
"""

import time
import logging
from typing import Optional, Dict, Any, BinaryIO, Union, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from requests import Session, Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException, HTTPError, Timeout, ConnectionError

from .exceptions import (
    GDCAPIException,
    GDCAuthenticationError,
    GDCRateLimitError,
    GDCServerError,
    GDCValidationError,
    GDCConnectionError
)
from .models import (
    FileUploadRequest,
    FileUploadResponse,
    FileStatus,
    UploadStatus,
    ProjectInfo,
    TokenValidationResponse
)

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket implementation for rate limiting.
    
    This algorithm allows burst traffic while maintaining an average rate limit.
    """
    
    def __init__(self, tokens: float, refill_rate: float):
        """Initialize the token bucket.
        
        Args:
            tokens: Initial number of tokens (and max capacity)
            refill_rate: Tokens added per second
        """
        self.capacity = tokens
        self.tokens = tokens
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = False  # Simple lock for thread safety
    
    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def refill(self):
        """Refill tokens based on time passed."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def wait_for_tokens(self, tokens: float = 1.0) -> float:
        """Wait until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time waited in seconds
        """
        start_time = time.time()
        while not self.consume(tokens):
            time.sleep(0.1)  # Check every 100ms
        return time.time() - start_time


class GDCAPIClient:
    """Client for interacting with the GDC API.
    
    This client provides:
    - Automatic retry logic with exponential backoff
    - Rate limiting to respect API limits
    - Connection pooling for performance
    - Comprehensive error handling
    - Progress tracking for uploads
    - Token validation and refresh
    """
    
    DEFAULT_BASE_URL = "https://api.gdc.cancer.gov"
    DEFAULT_SUBMISSION_URL = "https://api.gdc.cancer.gov/v0/submission"
    
    def __init__(
        self,
        token: str,
        base_url: str = None,
        max_retries: int = 3,
        rate_limit: float = 10.0,  # requests per second
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        timeout: Tuple[float, float] = (30.0, 300.0),  # (connect, read) timeouts
        verify_ssl: bool = True,
        user_agent: str = "gdc-uploader/2.0"
    ):
        """Initialize the GDC API client.
        
        Args:
            token: GDC authentication token
            base_url: Base URL for the GDC API
            max_retries: Maximum number of retry attempts
            rate_limit: Maximum requests per second
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in pool
            timeout: Tuple of (connect timeout, read timeout) in seconds
            verify_ssl: Whether to verify SSL certificates
            user_agent: User agent string for requests
        """
        self.token = token
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.submission_url = f"{self.base_url}/v0/submission"
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        # Initialize rate limiter
        self.rate_limiter = TokenBucket(rate_limit * 2, rate_limit)  # Allow burst
        
        # Configure session with connection pooling
        self.session = Session()
        
        # Create retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "DELETE", "OPTIONS", "TRACE"],
            raise_on_status=False  # We'll handle status codes ourselves
        )
        
        # Create adapter with pooling and retry
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        # Mount adapter for both HTTP and HTTPS
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'X-Auth-Token': self.token,
            'User-Agent': user_agent,
            'Accept': 'application/json'
        })
        
        # Validate token on initialization
        self._validate_token()
    
    def _validate_token(self):
        """Validate the authentication token."""
        try:
            response = self.validate_token()
            if not response.is_valid:
                raise GDCAuthenticationError("Invalid authentication token")
            logger.info(f"Token validated successfully. User: {response.username}")
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise GDCAuthenticationError(f"Token validation failed: {str(e)}")
    
    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Response:
        """Make an HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            url: Full URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            GDCAPIException: For various API errors
        """
        # Apply rate limiting
        wait_time = self.rate_limiter.wait_for_tokens()
        if wait_time > 0:
            logger.debug(f"Rate limited, waited {wait_time:.2f}s")
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        # Set SSL verification
        kwargs['verify'] = self.verify_ssl
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Check for specific error codes
            if response.status_code == 401:
                raise GDCAuthenticationError("Authentication failed - invalid token")
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 60)
                raise GDCRateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
            elif response.status_code >= 500:
                raise GDCServerError(f"Server error: {response.status_code} - {response.text}")
            elif response.status_code >= 400:
                error_msg = self._parse_error_response(response)
                raise GDCValidationError(f"Client error: {response.status_code} - {error_msg}")
            
            response.raise_for_status()
            return response
            
        except ConnectionError as e:
            raise GDCConnectionError(f"Connection failed: {str(e)}")
        except Timeout as e:
            raise GDCConnectionError(f"Request timed out: {str(e)}")
        except HTTPError as e:
            if hasattr(e, 'response') and e.response is not None:
                error_msg = self._parse_error_response(e.response)
                raise GDCAPIException(f"HTTP error: {e.response.status_code} - {error_msg}")
            raise GDCAPIException(f"HTTP error: {str(e)}")
        except RequestException as e:
            raise GDCAPIException(f"Request failed: {str(e)}")
    
    def _parse_error_response(self, response: Response) -> str:
        """Parse error message from API response."""
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                return error_data.get('message', error_data.get('error', response.text))
            return str(error_data)
        except Exception:
            return response.text or f"HTTP {response.status_code}"
    
    def validate_token(self) -> TokenValidationResponse:
        """Validate the current authentication token.
        
        Returns:
            TokenValidationResponse with validation details
        """
        url = urljoin(self.base_url, "/auth/user")
        response = self._make_request("GET", url)
        data = response.json()
        
        return TokenValidationResponse(
            is_valid=True,
            username=data.get("username", "unknown"),
            projects=data.get("projects", {})
        )
    
    def upload_file_chunk(
        self,
        project_id: str,
        file_id: str,
        chunk: Union[bytes, BinaryIO],
        chunk_size: int,
        offset: int = 0,
        total_size: Optional[int] = None,
        progress_callback: Optional[callable] = None
    ) -> FileUploadResponse:
        """Upload a file chunk to GDC.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            chunk: File chunk data (bytes or file-like object)
            chunk_size: Size of the chunk in bytes
            offset: Byte offset for this chunk
            total_size: Total file size (for Content-Range header)
            progress_callback: Optional callback for progress updates
            
        Returns:
            FileUploadResponse with upload details
        """
        url = f"{self.submission_url}/{project_id}/files/{file_id}"
        
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Length': str(chunk_size)
        }
        
        # Add Content-Range header if offset or total_size provided
        if offset > 0 or total_size:
            end_byte = offset + chunk_size - 1
            content_range = f"bytes {offset}-{end_byte}/"
            content_range += str(total_size) if total_size else "*"
            headers['Content-Range'] = content_range
        
        # Make the upload request
        response = self._make_request(
            "PUT",
            url,
            headers=headers,
            data=chunk,
            stream=True
        )
        
        # Parse response
        data = response.json()
        
        # Call progress callback if provided
        if progress_callback:
            progress_callback(offset + chunk_size, total_size)
        
        return FileUploadResponse(
            file_id=file_id,
            status=data.get("status", "unknown"),
            uploaded_size=offset + chunk_size,
            timestamp=datetime.utcnow(),
            warnings=data.get("warnings", [])
        )
    
    def upload_file(
        self,
        project_id: str,
        file_id: str,
        file_path: Union[str, Path],
        chunk_size: int = 1024 * 1024 * 10,  # 10MB chunks
        resume_from: int = 0,
        progress_callback: Optional[callable] = None
    ) -> FileUploadResponse:
        """Upload a complete file to GDC with automatic chunking.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            file_path: Path to the file to upload
            chunk_size: Size of each chunk in bytes
            resume_from: Byte offset to resume from
            progress_callback: Optional callback for progress updates
            
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
        
        with open(file_path, 'rb') as f:
            if resume_from > 0:
                f.seek(resume_from)
                logger.info(f"Resuming upload from byte {resume_from:,}")
            
            while uploaded_size < file_size:
                # Read chunk
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                actual_chunk_size = len(chunk_data)
                
                # Upload chunk
                last_response = self.upload_file_chunk(
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
    
    def get_file_status(self, project_id: str, file_id: str) -> FileStatus:
        """Get the status of a file in GDC.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            
        Returns:
            FileStatus object with current file status
        """
        url = f"{self.submission_url}/{project_id}/files/{file_id}"
        response = self._make_request("GET", url)
        data = response.json()
        
        return FileStatus(
            file_id=file_id,
            project_id=project_id,
            state=data.get("state", "unknown"),
            uploaded_size=data.get("size", 0),
            md5sum=data.get("md5sum"),
            created_datetime=data.get("created_datetime"),
            updated_datetime=data.get("updated_datetime")
        )
    
    def get_project_info(self, project_id: str) -> ProjectInfo:
        """Get information about a GDC project.
        
        Args:
            project_id: GDC project ID
            
        Returns:
            ProjectInfo object with project details
        """
        url = f"{self.submission_url}/{project_id}"
        response = self._make_request("GET", url)
        data = response.json()
        
        return ProjectInfo(
            project_id=project_id,
            name=data.get("name", project_id),
            program=data.get("program", {}).get("name", "unknown"),
            state=data.get("state", "open")
        )
    
    def delete_file(self, project_id: str, file_id: str) -> Dict[str, Any]:
        """Delete a file from GDC.
        
        Args:
            project_id: GDC project ID
            file_id: GDC file UUID
            
        Returns:
            Dictionary with deletion result
        """
        url = f"{self.submission_url}/{project_id}/files/{file_id}"
        response = self._make_request("DELETE", url)
        return response.json()
    
    def close(self):
        """Close the API client and clean up resources."""
        self.session.close()
        logger.info("GDC API client closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()