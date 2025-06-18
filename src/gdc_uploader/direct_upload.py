"""GDC Direct Upload module for simplified parallel uploads."""

import json
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import click
from tqdm import tqdm


class GDCDirectUploader:
    """Handle direct uploads to GDC with minimal configuration."""
    
    def __init__(self, metadata_file: Path, token_file: Path, threads: int = 4, retries: int = 3):
        """Initialize the direct uploader.
        
        Args:
            metadata_file: Path to GDC metadata JSON file
            token_file: Path to GDC authentication token file
            threads: Number of parallel upload threads
            retries: Number of retry attempts for failed uploads
        """
        self.metadata_file = metadata_file
        self.token_file = token_file
        self.threads = threads
        self.retries = retries
        self.logger = self._setup_logging()
        
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
        
        return logger
        
    def upload_file(self, uuid: str, filename: str) -> Tuple[str, str, bool]:
        """Upload a single file to GDC.
        
        Args:
            uuid: GDC UUID for the file
            filename: Path to the file to upload
            
        Returns:
            Tuple of (uuid, filename, success)
        """
        self.logger.info(f"Starting upload: {filename} (UUID: {uuid})")
        
        file_path = Path(filename)
        if not file_path.exists():
            self.logger.error(f"File not found: {filename}")
            return (uuid, filename, False)
            
        # Prepare upload command
        file_dir = file_path.parent
        log_file = f"upload-{uuid}.log"
        
        cmd = [
            "gdc-client", "upload",
            "-t", str(self.token_file),
            uuid,
            "--log-file", log_file,
            "--upload-part-size", "1073741824",
            "-n", "8",
            "--resume"
        ]
        
        # Run upload with retries
        for attempt in range(self.retries):
            try:
                # Run gdc-client from the file's directory
                result = subprocess.run(
                    cmd,
                    cwd=str(file_dir),
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.logger.info(f"Success: {filename}")
                return (uuid, filename, True)
                
            except subprocess.CalledProcessError as e:
                if attempt < self.retries - 1:
                    self.logger.warning(f"Upload failed (attempt {attempt + 1}/{self.retries}): {filename}")
                    continue
                else:
                    self.logger.error(f"Failed after {self.retries} attempts: {filename}")
                    return (uuid, filename, False)
                    
    def run(self) -> None:
        """Run the direct upload process."""
        # Load metadata
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            if not isinstance(metadata, list):
                metadata = [metadata]
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            sys.exit(3)
            
        self.logger.info(f"Starting parallel uploads with {self.threads} threads...")
        
        # Prepare upload tasks
        upload_tasks = []
        for item in metadata:
            uuid = item.get('id', item.get('uuid'))
            filename = item.get('file_name', item.get('filename'))
            if uuid and filename:
                upload_tasks.append((uuid, filename))
                
        # Run uploads in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.upload_file, uuid, filename): (uuid, filename)
                for uuid, filename in upload_tasks
            }
            
            # Process results with progress bar
            with tqdm(total=len(futures), desc="Uploading files") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    pbar.update(1)
                    
        # Summary
        successful = sum(1 for r in results if r[2])
        failed = sum(1 for r in results if not r[2])
        
        self.logger.info("Upload complete!")
        self.logger.info(f"Successful uploads: {successful}")
        self.logger.info(f"Failed uploads: {failed}")
        
        # Exit with appropriate code
        if failed > 0:
            sys.exit(2)


def direct_upload(metadata_file: Path, token_file: Path, 
                 threads: int = 4, retries: int = 3) -> None:
    """Direct upload to GDC with minimal configuration.
    
    Args:
        metadata_file: Path to GDC metadata JSON file
        token_file: Path to GDC authentication token file
        threads: Number of parallel upload threads
        retries: Number of retry attempts for failed uploads
    """
    uploader = GDCDirectUploader(metadata_file, token_file, threads, retries)
    uploader.run()