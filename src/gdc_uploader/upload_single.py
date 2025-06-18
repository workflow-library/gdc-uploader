"""GDC Single File Upload module for uploading individual files to GDC."""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import click
import requests
from tqdm import tqdm


class GDCSingleUploader:
    """Handle single file uploads to GDC using the API."""
    
    def __init__(self, metadata_file: Path, token_file: Path, retries: int = 3):
        """Initialize the single file uploader.
        
        Args:
            metadata_file: Path to GDC metadata JSON file
            token_file: Path to GDC authentication token file
            retries: Number of retry attempts for failed uploads
        """
        self.metadata_file = metadata_file
        self.token_file = token_file
        self.retries = retries
        self.logger = self._setup_logging()
        self.api_base = "https://api.gdc.cancer.gov/v0/submission"
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handlers
        fh_stdout = logging.FileHandler('gdc-upload-stdout.log')
        fh_stdout.setLevel(logging.INFO)
        fh_stdout.setFormatter(formatter)
        logger.addHandler(fh_stdout)
        
        fh_stderr = logging.FileHandler('gdc-upload-stderr.log')
        fh_stderr.setLevel(logging.ERROR)
        fh_stderr.setFormatter(formatter)
        logger.addHandler(fh_stderr)
        
        return logger
        
    def load_metadata(self, target_filename: str) -> Optional[Dict[str, str]]:
        """Load metadata for a specific file.
        
        Args:
            target_filename: Name of the file to find metadata for
            
        Returns:
            Metadata dictionary for the file or None
        """
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
                
            # Handle both array format and object with 'files' property
            if isinstance(metadata, list):
                items = metadata
            elif isinstance(metadata, dict) and 'files' in metadata:
                items = metadata['files']
            else:
                items = [metadata]
                
            # Find matching file
            for item in items:
                file_name = item.get('file_name', item.get('filename', ''))
                local_path = item.get('local_file_path', '')
                
                if file_name == target_filename or local_path == target_filename:
                    return {
                        'uuid': item.get('id', item.get('uuid')),
                        'project_id': item.get('project_id'),
                        'file_name': file_name
                    }
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            return None
            
    def load_token(self) -> str:
        """Load the authentication token.
        
        Returns:
            Authentication token string
        """
        with open(self.token_file, 'r') as f:
            return f.read().strip()
            
    def upload_file_with_progress(self, file_path: Path, uuid: str, 
                                 project_id: str, token: str) -> bool:
        """Upload a file with progress tracking.
        
        Args:
            file_path: Path to the file to upload
            uuid: GDC UUID for the file
            project_id: GDC project ID
            token: Authentication token
            
        Returns:
            True if successful, False otherwise
        """
        # Convert project ID format (MP2PRT-EC -> MP2PRT/EC)
        project_path = project_id.replace('-', '/')
        url = f"{self.api_base}/{project_path}/files/{uuid}"
        
        file_size = file_path.stat().st_size
        file_size_gb = file_size / (1024 ** 3)
        
        self.logger.info(f"Uploading to: {url}")
        self.logger.info(f"File size: {file_size_gb:.2f} GB")
        
        headers = {
            'x-auth-token': token,
            'Content-Type': 'application/octet-stream'
        }
        
        # Upload with progress bar
        with open(file_path, 'rb') as f:
            with tqdm(total=file_size, unit='B', unit_scale=True, 
                     desc=f"Uploading {file_path.name}") as pbar:
                
                def upload_callback(monitor):
                    """Callback to update progress bar."""
                    pbar.update(monitor.bytes_read - pbar.n)
                
                # Use requests-toolbelt for upload progress monitoring
                try:
                    from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
                    
                    # Use streaming upload for progress tracking
                    response = requests.put(
                        url,
                        data=f,
                        headers=headers,
                        timeout=(60, None),  # 60s connect timeout, no read timeout
                        stream=True
                    )
                    
                except ImportError:
                    # Fallback without progress if requests-toolbelt not available
                    self.logger.warning("requests-toolbelt not available, uploading without detailed progress")
                    response = requests.put(
                        url,
                        data=f,
                        headers=headers,
                        timeout=(60, None)
                    )
                    
        return response.status_code in [200, 201, 202]
        
    def upload_file(self, target_file: Path) -> bool:
        """Upload a single file to GDC.
        
        Args:
            target_file: Path to the file to upload
            
        Returns:
            True if successful, False otherwise
        """
        target_basename = target_file.name
        self.logger.info(f"Looking for file: {target_basename}")
        
        # Load metadata for the file
        file_metadata = self.load_metadata(target_basename)
        if not file_metadata:
            self.logger.error(f"No metadata found for file '{target_basename}'")
            return False
            
        uuid = file_metadata['uuid']
        project_id = file_metadata['project_id']
        
        self.logger.info(f"Found UUID: {uuid}")
        self.logger.info(f"Project ID: {project_id}")
        
        # Load token
        token = self.load_token()
        
        # Perform upload with retries
        for attempt in range(1, self.retries + 1):
            self.logger.info(f"Upload attempt {attempt} of {self.retries}...")
            start_time = time.time()
            
            try:
                success = self.upload_file_with_progress(
                    target_file, uuid, project_id, token
                )
                
                if success:
                    elapsed = time.time() - start_time
                    elapsed_min = int(elapsed // 60)
                    elapsed_sec = int(elapsed % 60)
                    
                    self.logger.info("Upload completed successfully!")
                    self.logger.info(f"Total time: {elapsed_min}m {elapsed_sec}s")
                    
                    # Calculate average speed
                    if elapsed > 0:
                        file_size = target_file.stat().st_size
                        avg_speed_mb = (file_size / (1024 ** 2)) / elapsed
                        self.logger.info(f"Average speed: {avg_speed_mb:.2f} MB/s")
                        
                    return True
                    
            except Exception as e:
                self.logger.error(f"Upload failed on attempt {attempt}: {e}")
                
            if attempt < self.retries:
                self.logger.info("Retrying in 5 seconds...")
                time.sleep(5)
                
        return False
        
    def run(self, target_file: Path) -> None:
        """Run the single file upload process.
        
        Args:
            target_file: Path to the file to upload
        """
        self.logger.info("Starting GDC single file upload...")
        self.logger.info(f"Metadata: {self.metadata_file}")
        self.logger.info(f"Token: {self.token_file}")
        self.logger.info(f"Target file: {target_file}")
        self.logger.info(f"Retries: {self.retries}")
        
        # Perform upload
        success = self.upload_file(target_file)
        
        # Generate upload report
        target_basename = target_file.name
        file_metadata = self.load_metadata(target_basename)
        uuid = file_metadata['uuid'] if file_metadata else 'UNKNOWN'
        
        with open('upload-report.tsv', 'w') as f:
            f.write("file_name\tfile_uuid\tfile_path\tstatus\tattempts\n")
            status = "success" if success else "failed"
            f.write(f"{target_basename}\t{uuid}\t{target_file}\t{status}\t{self.retries}\n")
            
        self.logger.info("Upload report generated:")
        with open('upload-report.tsv', 'r') as f:
            self.logger.info(f.read())
            
        if success:
            self.logger.info("File upload completed successfully!")
            sys.exit(0)
        else:
            self.logger.error(f"File upload failed after {self.retries} attempts")
            sys.exit(2)


def upload_single(metadata_file: Path, token_file: Path, target_file: Path, 
                 retries: int = 3) -> None:
    """Upload a single file to GDC.
    
    Args:
        metadata_file: Path to GDC metadata JSON file
        token_file: Path to GDC authentication token file
        target_file: Path to the file to upload
        retries: Number of retry attempts for failed uploads
    """
    uploader = GDCSingleUploader(metadata_file, token_file, retries)
    uploader.run(target_file)