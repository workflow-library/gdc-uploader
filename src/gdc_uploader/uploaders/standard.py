"""Standard GDC uploader using gdc-client."""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..core.base_uploader import BaseUploader, FileEntry, UploadResult, UploadStatus
from ..core.file_operations import OptimizedFileDiscovery as FileDiscovery
from ..core.progress import ThreadSafeProgressTracker as ProgressTracker
from ..core.retry import RetryManager as RetryHandler
from ..core.exceptions import GDCUploaderError as GDCUploadError

logger = logging.getLogger(__name__)


class StandardUploader(BaseUploader):
    """Standard uploader using gdc-client for parallel uploads."""
    
    def __init__(
        self,
        metadata_file: Path,
        token_file: Path,
        thread_count: int = 8,
        retry_count: int = 3,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.metadata_file = metadata_file
        self.token_file = token_file
        self.thread_count = thread_count
        self.retry_handler = RetryHandler(max_attempts=retry_count)
        self.file_discovery = FileDiscovery()
        
    def discover_files(self, source_path: Path) -> List[FileEntry]:
        """Discover files to upload from metadata."""
        # Load metadata
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
                    
                files.append(file_entry)
                
        return files
        
    def upload_file(self, file_entry: FileEntry, **kwargs) -> UploadResult:
        """Upload a single file using gdc-client."""
        if not file_entry.path or not file_entry.path.exists():
            return UploadResult(
                file_entry=file_entry,
                status=UploadStatus.NOT_FOUND,
                error_message=f"File not found: {file_entry.filename}"
            )
            
        def _upload_attempt():
            cmd = [
                "gdc-client",
                "upload",
                "-t", str(self.token_file),
                "--uuid", file_entry.uuid,
                "--path", str(file_entry.path),
                "--no-file-md5sum"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise GDCUploadError(f"Upload failed: {result.stderr}")
                
            return result
            
        # Use retry handler
        result = UploadResult(file_entry=file_entry, status=UploadStatus.PENDING)
        
        try:
            self.retry_handler.execute(_upload_attempt)
            result.status = UploadStatus.SUCCESS
            result.attempts = self.retry_handler.attempt_count
        except Exception as e:
            result.status = UploadStatus.FAILED
            result.error_message = str(e)
            result.attempts = self.retry_handler.max_attempts
            
        return result
        
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Generate upload report."""
        successful = sum(1 for r in results if r.status == UploadStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == UploadStatus.FAILED)
        not_found = sum(1 for r in results if r.status == UploadStatus.NOT_FOUND)
        
        report = {
            "summary": {
                "total_files": len(results),
                "successful": successful,
                "failed": failed,
                "not_found": not_found,
                "success_rate": successful / len(results) if results else 0
            },
            "details": []
        }
        
        for result in results:
            report["details"].append({
                "uuid": result.file_entry.uuid,
                "filename": result.file_entry.filename,
                "status": result.status.value,
                "attempts": result.attempts,
                "error": result.error_message
            })
            
        return report