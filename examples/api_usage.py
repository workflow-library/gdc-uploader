#!/usr/bin/env python3
"""Example usage of the GDC API Client library.

This script demonstrates various features of the GDC API client including:
- Basic file upload
- Batch uploads
- Progress tracking
- Error handling
- Async operations
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import GDC API client components
from gdc_uploader.api import (
    GDCAPIClient,
    AsyncGDCAPIClient,
    TokenManager,
    GDCAuthenticationError,
    GDCRateLimitError,
    GDCUploadError,
    FileUploadRequest,
    BatchUploadRequest
)


def basic_upload_example():
    """Demonstrate basic file upload."""
    logger.info("Starting basic upload example")
    
    # Create token manager from file
    token_manager = TokenManager.from_file("token.txt")
    
    # Create API client
    with GDCAPIClient(
        token=token_manager.get_token(),
        rate_limit=10.0,
        max_retries=3
    ) as client:
        # Define upload parameters
        project_id = "TCGA-LUAD"
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        file_path = "test-data/sample.bam"
        
        # Upload with progress tracking
        def progress_callback(uploaded: int, total: int):
            pct = (uploaded / total) * 100 if total > 0 else 0
            logger.info(f"Upload progress: {uploaded:,}/{total:,} bytes ({pct:.1f}%)")
        
        try:
            response = client.upload_file(
                project_id=project_id,
                file_id=file_id,
                file_path=file_path,
                chunk_size=5 * 1024 * 1024,  # 5MB chunks
                progress_callback=progress_callback
            )
            
            logger.info(f"Upload completed successfully!")
            logger.info(f"Status: {response.status}")
            logger.info(f"Uploaded size: {response.uploaded_size:,} bytes")
            
        except GDCUploadError as e:
            logger.error(f"Upload failed: {e}")
            logger.error(f"Uploaded {e.uploaded_bytes} of {e.total_bytes} bytes")


def resumable_upload_example():
    """Demonstrate resumable upload."""
    logger.info("Starting resumable upload example")
    
    token_manager = TokenManager.from_file("token.txt")
    
    with GDCAPIClient(token=token_manager.get_token()) as client:
        project_id = "TCGA-LUAD"
        file_id = "550e8400-e29b-41d4-a716-446655440000"
        file_path = "test-data/large-file.bam"
        
        # Check current upload status
        try:
            status = client.get_file_status(project_id, file_id)
            logger.info(f"Current file status: {status.state}")
            logger.info(f"Already uploaded: {status.uploaded_size:,} bytes")
            
            # Resume upload from last position
            response = client.upload_file(
                project_id=project_id,
                file_id=file_id,
                file_path=file_path,
                resume_from=status.uploaded_size or 0
            )
            
            logger.info(f"Upload resumed and completed!")
            
        except Exception as e:
            logger.error(f"Resumable upload failed: {e}")


async def async_upload_example():
    """Demonstrate async file upload."""
    logger.info("Starting async upload example")
    
    token_manager = TokenManager.from_file("token.txt")
    
    async with AsyncGDCAPIClient(token_manager) as client:
        # Single file upload
        response = await client.upload_file(
            project_id="TCGA-LUAD",
            file_id="async-file-uuid",
            file_path="test-data/async-sample.bam"
        )
        
        logger.info(f"Async upload completed: {response.status}")


async def batch_upload_example():
    """Demonstrate batch upload of multiple files."""
    logger.info("Starting batch upload example")
    
    token_manager = TokenManager.from_file("token.txt")
    
    # Prepare list of files to upload
    files_to_upload = [
        ("file-uuid-1", "test-data/file1.bam"),
        ("file-uuid-2", "test-data/file2.bam"),
        ("file-uuid-3", "test-data/file3.bam"),
        ("file-uuid-4", "test-data/file4.bam"),
    ]
    
    # Create batch request
    batch_request = BatchUploadRequest(
        project_id="TCGA-LUAD",
        files=[
            FileUploadRequest(
                file_id=file_id,
                project_id="TCGA-LUAD",
                file_path=Path(file_path),
                file_size=Path(file_path).stat().st_size if Path(file_path).exists() else 1000000
            )
            for file_id, file_path in files_to_upload
        ],
        parallel_uploads=3  # Upload 3 files concurrently
    )
    
    async with AsyncGDCAPIClient(token_manager) as client:
        # Progress callback for batch
        async def batch_progress(completed: int, total: int):
            logger.info(f"Batch progress: {completed}/{total} files completed")
        
        try:
            batch_response = await client.batch_upload(
                batch_request,
                progress_callback=batch_progress
            )
            
            logger.info(f"Batch upload completed!")
            logger.info(f"Total files: {batch_response.total_files}")
            logger.info(f"Successful: {batch_response.successful}")
            logger.info(f"Failed: {batch_response.failed}")
            logger.info(f"Success rate: {batch_response.success_rate:.1f}%")
            logger.info(f"Duration: {batch_response.duration_seconds:.1f} seconds")
            
            # Check individual results
            for result in batch_response.results:
                if result.has_errors:
                    logger.error(f"File {result.file_id} failed: {result.errors}")
                else:
                    logger.info(f"File {result.file_id} uploaded successfully")
                    
        except Exception as e:
            logger.error(f"Batch upload failed: {e}")


def error_handling_example():
    """Demonstrate comprehensive error handling."""
    logger.info("Starting error handling example")
    
    token_manager = TokenManager.from_file("token.txt")
    
    with GDCAPIClient(token=token_manager.get_token()) as client:
        try:
            # Attempt upload
            response = client.upload_file(
                project_id="TCGA-LUAD",
                file_id="test-file-uuid",
                file_path="test-data/sample.bam"
            )
            
        except GDCAuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            # Could refresh token and retry
            
        except GDCRateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            logger.info(f"Retry after {e.retry_after} seconds")
            # Could wait and retry
            
        except GDCUploadError as e:
            logger.error(f"Upload error: {e}")
            logger.error(f"File ID: {e.file_id}")
            logger.error(f"Progress: {e.uploaded_bytes}/{e.total_bytes} bytes")
            # Could resume from last position
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")


async def streaming_upload_example():
    """Demonstrate streaming upload from generator."""
    logger.info("Starting streaming upload example")
    
    token_manager = TokenManager.from_file("token.txt")
    
    async def file_chunk_generator(file_path: Path, chunk_size: int = 1024 * 1024):
        """Generate file chunks asynchronously."""
        import aiofiles
        
        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                # Could process/transform chunk here
    
    async with AsyncGDCAPIClient(token_manager) as client:
        file_path = Path("test-data/large-file.bam")
        file_size = file_path.stat().st_size if file_path.exists() else None
        
        response = await client.stream_upload(
            project_id="TCGA-LUAD",
            file_id="stream-file-uuid",
            stream=file_chunk_generator(file_path),
            total_size=file_size
        )
        
        logger.info(f"Streaming upload completed: {response.status}")


def token_management_example():
    """Demonstrate various token management options."""
    logger.info("Starting token management example")
    
    # From file
    try:
        token_mgr_file = TokenManager.from_file("token.txt")
        logger.info("Token loaded from file")
    except Exception as e:
        logger.error(f"Failed to load token from file: {e}")
    
    # From environment
    try:
        token_mgr_env = TokenManager.from_environment("GDC_TOKEN")
        logger.info("Token loaded from environment")
    except Exception as e:
        logger.error(f"Failed to load token from environment: {e}")
    
    # From string (not recommended for production)
    token_mgr_static = TokenManager.from_token("your-token-here")
    
    # With caching and validation
    with GDCAPIClient(token=token_mgr_file.get_token()) as client:
        cached_token_mgr = token_mgr_file.with_caching(validation_client=client)
        logger.info("Token manager with caching created")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("GDC API Client Examples")
    print("="*60 + "\n")
    
    # Run synchronous examples
    try:
        basic_upload_example()
        print("\n" + "-"*60 + "\n")
        
        resumable_upload_example()
        print("\n" + "-"*60 + "\n")
        
        error_handling_example()
        print("\n" + "-"*60 + "\n")
        
        token_management_example()
        print("\n" + "-"*60 + "\n")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
    
    # Run asynchronous examples
    print("\nRunning async examples...")
    print("-"*60 + "\n")
    
    try:
        asyncio.run(async_upload_example())
        print("\n" + "-"*60 + "\n")
        
        asyncio.run(batch_upload_example())
        print("\n" + "-"*60 + "\n")
        
        asyncio.run(streaming_upload_example())
        
    except Exception as e:
        logger.error(f"Async example failed: {e}")
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == "__main__":
    main()