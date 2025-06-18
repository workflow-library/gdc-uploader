"""Single file uploader for targeted uploads."""

from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..core.base_uploader import BaseUploader, FileEntry, UploadResult, UploadStatus
from ..api.client import GDCAPIClient

logger = logging.getLogger(__name__)


class SingleFileUploader(BaseUploader):
    """Uploader for single file uploads."""
    
    def __init__(self, token_file: Path, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize API client
        with open(token_file) as f:
            token = f.read().strip()
        self.api_client = GDCAPIClient(token=token)
        
    def discover_files(self, source_path: Path) -> List[FileEntry]:
        """For single file upload, source_path IS the file."""
        if not source_path.exists():
            return []
            
        # Extract UUID from filename or use a placeholder
        filename = source_path.name
        uuid = filename.split('.')[0] if '.' in filename else filename
        
        return [FileEntry(
            uuid=uuid,
            filename=filename,
            path=source_path,
            size=source_path.stat().st_size
        )]
        
    def upload_file(self, file_entry: FileEntry, **kwargs) -> UploadResult:
        """Upload single file."""
        result = UploadResult(file_entry=file_entry, status=UploadStatus.PENDING)
        
        try:
            # For single file, we might need to create the file record first
            # This is a simplified version - real implementation would check if file exists
            
            with open(file_entry.path, 'rb') as f:
                content = f.read()
                
            # Upload the entire file
            self.api_client.upload_file_simple(
                file_id=file_entry.uuid,
                file_content=content,
                filename=file_entry.filename
            )
            
            result.status = UploadStatus.SUCCESS
            result.bytes_transferred = file_entry.size
            
        except Exception as e:
            result.status = UploadStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Single file upload failed: {e}")
            
        return result
        
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Simple report for single file."""
        if not results:
            return {"status": "no files"}
            
        result = results[0]
        return {
            "file": result.file_entry.filename,
            "uuid": result.file_entry.uuid,
            "status": result.status.value,
            "size": result.file_entry.size,
            "error": result.error_message
        }