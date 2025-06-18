"""Spot instance aware uploader with resume capability."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import pickle

from ..core.base_uploader import BaseUploader, FileEntry, UploadResult, UploadStatus
from ..api.client import GDCAPIClient
from ..core.file_operations import OptimizedFileDiscovery as FileDiscovery
from ..core.progress import ThreadSafeProgressTracker as ProgressTracker

logger = logging.getLogger(__name__)


class SpotUploader(BaseUploader):
    """Uploader designed for spot instances with interruption handling."""
    
    def __init__(
        self,
        metadata_file: Path,
        token_file: Path,
        checkpoint_file: Path = Path("upload_checkpoint.pkl"),
        **kwargs
    ):
        super().__init__(**kwargs)
        self.metadata_file = metadata_file
        self.checkpoint_file = checkpoint_file
        self.file_discovery = FileDiscovery()
        
        # Initialize API client
        with open(token_file) as f:
            token = f.read().strip()
        self.api_client = GDCAPIClient(token=token)
        
        # Load checkpoint if exists
        self.completed_files = set()
        self._load_checkpoint()
        
    def _load_checkpoint(self):
        """Load checkpoint from disk if it exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                    self.completed_files = checkpoint.get('completed_files', set())
                    logger.info(f"Loaded checkpoint with {len(self.completed_files)} completed files")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
                
    def _save_checkpoint(self):
        """Save current progress to checkpoint."""
        checkpoint = {
            'completed_files': self.completed_files
        }
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint, f)
            
    def discover_files(self, source_path: Path) -> List[FileEntry]:
        """Discover files, excluding already completed ones."""
        with open(self.metadata_file) as f:
            metadata = json.load(f)
            
        files = []
        for item in metadata:
            if 'file_name' in item and 'id' in item:
                # Skip if already completed
                if item['id'] in self.completed_files:
                    logger.info(f"Skipping completed file: {item['file_name']}")
                    continue
                    
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
        """Upload file with checkpoint support."""
        # Use API uploader's logic for actual upload
        result = UploadResult(file_entry=file_entry, status=UploadStatus.PENDING)
        
        if not file_entry.path or not file_entry.path.exists():
            result.status = UploadStatus.NOT_FOUND
            result.error_message = f"File not found: {file_entry.filename}"
            return result
            
        try:
            # Upload using API client
            with open(file_entry.path, 'rb') as f:
                content = f.read()
                
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
            logger.error(f"Upload failed for {file_entry.filename}: {e}")
        
        # If successful, add to completed set and save checkpoint
        if result.status == UploadStatus.SUCCESS:
            self.completed_files.add(file_entry.uuid)
            self._save_checkpoint()
            
        return result
        
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Generate report including checkpoint info."""
        report = super().generate_report(results)
        report["checkpoint_info"] = {
            "checkpoint_file": str(self.checkpoint_file),
            "previously_completed": len(self.completed_files),
            "can_resume": True
        }
        return report