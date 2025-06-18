"""API-based GDC uploader using direct HTTP uploads."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..core.base_uploader import BaseUploader, FileEntry, UploadResult, UploadStatus
from ..core.file_operations import OptimizedFileDiscovery as FileDiscovery
from ..core.progress import ThreadSafeProgressTracker as ProgressTracker
from ..api.client import GDCAPIClient
from ..api.exceptions import GDCAPIException

logger = logging.getLogger(__name__)


class APIUploader(BaseUploader):
    """Uploader using direct GDC API calls."""
    
    def __init__(
        self,
        metadata_file: Path,
        token_file: Path,
        thread_count: int = 8,
        chunk_size: int = 10 * 1024 * 1024,  # 10MB chunks
        **kwargs
    ):
        super().__init__(**kwargs)
        self.metadata_file = metadata_file
        self.thread_count = thread_count
        self.chunk_size = chunk_size
        self.file_discovery = FileDiscovery()
        
        # Initialize API client
        with open(token_file) as f:
            token = f.read().strip()
        self.api_client = GDCAPIClient(token=token, max_retries=3)
        
    def discover_files(self, source_path: Path) -> List[FileEntry]:
        """Discover files to upload from metadata."""
        with open(self.metadata_file) as f:
            metadata = json.load(f)
            
        files = []
        for item in metadata:
            if 'file_name' in item and 'id' in item:
                file_entry = FileEntry(
                    uuid=item['id'],
                    filename=item['file_name'],
                    size=item.get('file_size'),
                    md5sum=item.get('md5sum'),
                    metadata=item
                )
                
                # Find the actual file
                found_files = self.file_discovery.find_files(
                    root_path=source_path,
                    patterns=[file_entry.filename]
                )
                
                if found_files:
                    file_entry.path = found_files[0]
                    if not file_entry.size:
                        file_entry.size = found_files[0].stat().st_size
                    
                files.append(file_entry)
                
        return files
        
    def upload_file(self, file_entry: FileEntry, **kwargs) -> UploadResult:
        """Upload a single file using API."""
        result = UploadResult(file_entry=file_entry, status=UploadStatus.PENDING)
        
        if not file_entry.path or not file_entry.path.exists():
            result.status = UploadStatus.NOT_FOUND
            result.error_message = f"File not found: {file_entry.filename}"
            return result
            
        try:
            # Initialize upload
            upload_response = self.api_client.initiate_upload(
                file_id=file_entry.uuid,
                file_size=file_entry.size
            )
            
            # Upload file in chunks
            with open(file_entry.path, 'rb') as f:
                progress = ProgressTracker(
                    total=file_entry.size,
                    description=f"Uploading {file_entry.filename}"
                )
                
                offset = 0
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                        
                    self.api_client.upload_file_chunk(
                        file_id=file_entry.uuid,
                        chunk=chunk,
                        chunk_size=len(chunk),
                        offset=offset
                    )
                    
                    offset += len(chunk)
                    progress.update(len(chunk))
                    
                progress.close()
                
            # Complete upload
            self.api_client.complete_upload(file_id=file_entry.uuid)
            
            result.status = UploadStatus.SUCCESS
            result.bytes_transferred = file_entry.size
            
        except GDCAPIException as e:
            result.status = UploadStatus.FAILED
            result.error_message = str(e)
            logger.error(f"API upload failed for {file_entry.filename}: {e}")
            
        except Exception as e:
            result.status = UploadStatus.FAILED
            result.error_message = f"Unexpected error: {str(e)}"
            logger.exception(f"Unexpected error uploading {file_entry.filename}")
            
        return result
        
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Generate upload report."""
        successful = sum(1 for r in results if r.status == UploadStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == UploadStatus.FAILED)
        not_found = sum(1 for r in results if r.status == UploadStatus.NOT_FOUND)
        
        total_bytes = sum(
            r.bytes_transferred for r in results 
            if r.bytes_transferred is not None
        )
        
        report = {
            "summary": {
                "total_files": len(results),
                "successful": successful,
                "failed": failed,
                "not_found": not_found,
                "success_rate": successful / len(results) if results else 0,
                "total_bytes_transferred": total_bytes
            },
            "details": []
        }
        
        for result in results:
            report["details"].append({
                "uuid": result.file_entry.uuid,
                "filename": result.file_entry.filename,
                "status": result.status.value,
                "bytes_transferred": result.bytes_transferred,
                "error": result.error_message
            })
            
        return report