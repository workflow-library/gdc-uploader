"""GDC Upload module for uploading genomic files to NIH Genomic Data Commons."""

import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from tqdm import tqdm


class GDCUploader:
    """Handle uploads of genomic files to GDC using parallel processing."""
    
    def __init__(self, metadata_file: Path, token_file: Path, threads: int = 4, retries: int = 3):
        """Initialize the GDC uploader.
        
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
        
    def load_metadata(self) -> List[Dict[str, str]]:
        """Load and parse the GDC metadata JSON file.
        
        Returns:
            List of file metadata dictionaries
        """
        try:
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
            return metadata if isinstance(metadata, list) else [metadata]
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            raise
            
    def find_file(self, filename: str, files_dir: Path) -> Optional[Path]:
        """Search for a file in various locations.
        
        Args:
            filename: Name of the file to find
            files_dir: Base directory to search in
            
        Returns:
            Path to the found file or None
        """
        # Check in subdirectories first
        subdirs = ['fastq', 'uBam', 'sequence-files', '']
        
        for subdir in subdirs:
            if subdir:
                test_path = files_dir / subdir / filename
            else:
                test_path = files_dir / filename
                
            if test_path.exists() and test_path.is_file():
                return test_path
                
        # If not found, search recursively
        for path in files_dir.rglob(filename):
            if path.is_file():
                return path
                
        return None
        
    def upload_file(self, uuid: str, filename: str, files_dir: Path) -> Tuple[str, str, str, str]:
        """Upload a single file to GDC.
        
        Args:
            uuid: GDC UUID for the file
            filename: Name of the file to upload
            files_dir: Base directory containing files
            
        Returns:
            Tuple of (uuid, filename, path, status)
        """
        self.logger.info(f"Starting upload: {filename} (UUID: {uuid})")
        
        # Find the file
        found_file = self.find_file(filename, files_dir)
        
        if not found_file:
            self.logger.error(f"File not found: {filename}")
            return (uuid, filename, "NOT_FOUND", "FAILED")
            
        self.logger.info(f"Found file at: {found_file}")
        
        # Prepare upload command
        file_dir = found_file.parent
        log_file = Path.cwd() / f"upload-{uuid}.log"
        
        cmd = [
            "gdc-client", "upload",
            "-t", str(self.token_file),
            "--path", ".",
            uuid,
            "--log-file", str(log_file),
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
                return (uuid, filename, str(found_file), "SUCCESS")
                
            except subprocess.CalledProcessError as e:
                if attempt < self.retries - 1:
                    self.logger.warning(f"Upload failed (attempt {attempt + 1}/{self.retries}): {filename}")
                    continue
                else:
                    self.logger.error(f"Failed after {self.retries} attempts: {filename}")
                    self.logger.error(f"Error: {e.stderr}")
                    return (uuid, filename, str(found_file), "FAILED")
                    
    def run(self, files_dir: Path) -> None:
        """Run the parallel upload process.
        
        Args:
            files_dir: Directory containing files to upload
        """
        # Load metadata
        metadata = self.load_metadata()
        
        self.logger.info(f"Starting parallel uploads with {self.threads} threads...")
        self.logger.info(f"Metadata file: {self.metadata_file}")
        self.logger.info(f"Token file: {self.token_file}")
        self.logger.info(f"Files directory: {files_dir}")
        self.logger.info(f"Retries: {self.retries}")
        
        # Prepare upload tasks
        upload_tasks = []
        for item in metadata:
            uuid = item.get('id', item.get('uuid'))
            filename = item.get('file_name', item.get('filename'))
            if uuid and filename:
                upload_tasks.append((uuid, filename))
                
        # Create report file
        report_file = Path("upload-report.tsv")
        with open(report_file, 'w') as f:
            f.write("UUID\tFILENAME\tPATH\tSTATUS\n")
            
        # Run uploads in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.upload_file, uuid, filename, files_dir): (uuid, filename)
                for uuid, filename in upload_tasks
            }
            
            # Process results with progress bar
            with tqdm(total=len(futures), desc="Uploading files") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    
                    # Write to report
                    with open(report_file, 'a') as f:
                        f.write("\t".join(result) + "\n")
                        
                    pbar.update(1)
                    
        # Summary
        successful = sum(1 for r in results if r[3] == "SUCCESS")
        failed = sum(1 for r in results if r[3] == "FAILED")
        
        self.logger.info("Upload complete!")
        self.logger.info(f"Successful uploads: {successful}")
        self.logger.info(f"Failed uploads: {failed}")
        self.logger.info(f"Results saved to: {report_file}")
        
        # Exit with appropriate code
        if failed > 0:
            sys.exit(2)


def upload(metadata_file: Path, token_file: Path, files_dir: Path, 
          threads: int = 4, retries: int = 3) -> None:
    """Upload genomic files to GDC using parallel processing.
    
    Args:
        metadata_file: Path to GDC metadata JSON file
        token_file: Path to GDC authentication token file
        files_dir: Directory containing files to upload
        threads: Number of parallel upload threads
        retries: Number of retry attempts for failed uploads
    """
    uploader = GDCUploader(metadata_file, token_file, threads, retries)
    uploader.run(files_dir)