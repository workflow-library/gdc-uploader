"""Parallel GDC API uploader for multiple BAM files using direct HTTP API."""

import concurrent.futures
import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml
import requests
from tqdm import tqdm


class ParallelAPIUploader:
    """Upload multiple files in parallel using GDC HTTP API."""
    
    def __init__(self, manifest_file: Path, token_file: Path, 
                 max_workers: int = 2, retries: int = 3):
        """Initialize the parallel API uploader.
        
        Args:
            manifest_file: Path to YAML or JSON manifest file
            token_file: Path to GDC authentication token file
            max_workers: Maximum concurrent uploads
            retries: Number of retry attempts per file
        """
        self.manifest_file = manifest_file
        self.token_file = token_file
        self.max_workers = max_workers
        self.retries = retries
        self.api_base = "https://api.gdc.cancer.gov/v0/submission"
        self.logger = self._setup_logging()
        self.active_uploads = {}
        self.upload_lock = threading.Lock()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Console handler with custom format
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(threadName)-10s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        fh = logging.FileHandler('parallel-api-upload.log')
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger
        
    def _load_manifest(self) -> List[Dict]:
        """Load manifest from YAML or JSON file."""
        with open(self.manifest_file, 'r') as f:
            if self.manifest_file.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
                
        # Normalize to list format
        if isinstance(data, dict) and 'files' in data:
            return data['files']
        elif isinstance(data, list):
            return data
        else:
            return [data]
            
    def _load_token(self) -> str:
        """Load authentication token."""
        with open(self.token_file, 'r') as f:
            return f.read().strip()
            
    def _find_metadata_for_file(self, target_filename: str, manifest_data: List[Dict]) -> Optional[Dict]:
        """Find metadata for a specific file."""
        target_basename = Path(target_filename).name
        
        for item in manifest_data:
            file_name = item.get('file_name', item.get('filename', ''))
            if Path(file_name).name == target_basename:
                return item
                
        return None
        
    def _monitor_upload_progress(self, file_path: Path, uuid: str, stop_event: threading.Event):
        """Monitor upload progress in a separate thread."""
        progress_file = Path(f"curl-progress-{uuid}.txt")
        upload_start = time.time()
        last_update = 0
        last_percent = 0
        file_size = file_path.stat().st_size
        file_size_gb = file_size / (1024 ** 3)
        
        while not stop_event.is_set():
            time.sleep(2)
            
            current_time = time.time()
            elapsed = current_time - upload_start
            
            if progress_file.exists():
                try:
                    # Read last line of progress file
                    with open(progress_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            progress_line = lines[-1].strip()
                            
                            # Parse curl progress format
                            if progress_line and progress_line[0].isdigit():
                                parts = progress_line.split()
                                if parts:
                                    try:
                                        percent = int(parts[0])
                                        
                                        # Update progress
                                        if current_time - last_update >= 30 or percent - last_percent >= 5:
                                            elapsed_min = int(elapsed // 60)
                                            elapsed_sec = int(elapsed % 60)
                                            
                                            if percent > 0:
                                                eta = (elapsed / percent) * (100 - percent)
                                                eta_min = int(eta // 60)
                                                eta_sec = int(eta % 60)
                                                
                                                uploaded_gb = file_size_gb * percent / 100
                                                speed_mbps = (uploaded_gb * 1024) / elapsed if elapsed > 0 else 0
                                                
                                                self.logger.info(
                                                    f"{file_path.name}: {percent}% "
                                                    f"({uploaded_gb:.1f}/{file_size_gb:.1f} GB) "
                                                    f"Speed: {speed_mbps:.1f} MB/s "
                                                    f"ETA: {eta_min}m {eta_sec}s"
                                                )
                                            else:
                                                self.logger.info(
                                                    f"{file_path.name}: Upload starting... "
                                                    f"({elapsed_min}m {elapsed_sec}s)"
                                                )
                                                
                                            last_update = current_time
                                            last_percent = percent
                                            
                                    except (ValueError, IndexError):
                                        pass
                                        
                except Exception as e:
                    self.logger.debug(f"Error reading progress: {e}")
                    
            else:
                # No progress file yet
                if current_time - last_update >= 30:
                    elapsed_min = int(elapsed // 60)
                    elapsed_sec = int(elapsed % 60)
                    self.logger.info(
                        f"{file_path.name}: Initializing upload... "
                        f"({elapsed_min}m {elapsed_sec}s)"
                    )
                    last_update = current_time
                    
    def upload_file_api(self, file_path: Path, metadata: Dict) -> Tuple[str, bool, float]:
        """Upload a single file using the GDC HTTP API.
        
        Returns:
            Tuple of (filename, success, duration_hours)
        """
        uuid = metadata.get('id', metadata.get('uuid'))
        project_id = metadata.get('project_id')
        
        if not uuid or not project_id:
            self.logger.error(f"Missing UUID or project_id for {file_path.name}")
            return (file_path.name, False, 0)
            
        # Convert project ID format
        project_path = project_id.replace('-', '/')
        url = f"{self.api_base}/{project_path}/files/{uuid}"
        
        file_size = file_path.stat().st_size
        file_size_gb = file_size / (1024 ** 3)
        
        self.logger.info(f"Starting upload: {file_path.name} ({file_size_gb:.2f} GB)")
        self.logger.info(f"UUID: {uuid}")
        self.logger.info(f"URL: {url}")
        
        token = self._load_token()
        start_time = time.time()
        
        # Track active upload
        with self.upload_lock:
            self.active_uploads[uuid] = file_path.name
            
        # Start progress monitor
        stop_monitor = threading.Event()
        monitor_thread = threading.Thread(
            target=self._monitor_upload_progress,
            args=(file_path, uuid, stop_monitor),
            name=f"Monitor-{file_path.name[:8]}"
        )
        monitor_thread.start()
        
        # Prepare curl command (similar to the shell script)
        progress_file = f"curl-progress-{uuid}.txt"
        marker_file = f".upload-active-{uuid}"
        log_file = f"upload-{uuid}.log"
        
        # Create marker
        Path(marker_file).touch()
        
        cmd = [
            "curl",
            "--header", f"x-auth-token: {token}",
            "--output", log_file,
            "--request", "PUT",
            "--upload-file", str(file_path),
            "--fail",
            "--continue-at", "-",
            "--connect-timeout", "60",
            "--max-time", "0",  # No timeout for large files
            "--retry", "3",
            "--retry-delay", "10",
            "--write-out", "%{http_code}",
            "-#",  # Progress bar
            url
        ]
        
        success = False
        
        for attempt in range(1, self.retries + 1):
            if attempt > 1:
                self.logger.info(f"{file_path.name}: Retry attempt {attempt}/{self.retries}")
                
            try:
                # Run curl with progress output
                with open(progress_file, 'w') as progress_out:
                    result = subprocess.run(
                        cmd,
                        stderr=progress_out,
                        capture_output=True,
                        text=True
                    )
                    
                http_status = result.stdout.strip()
                
                if result.returncode == 0 and http_status.startswith('2'):
                    duration = time.time() - start_time
                    duration_hours = duration / 3600
                    
                    self.logger.info(
                        f"{file_path.name}: Upload completed successfully! "
                        f"Duration: {duration_hours:.2f} hours"
                    )
                    success = True
                    break
                else:
                    self.logger.error(
                        f"{file_path.name}: Upload failed - "
                        f"HTTP {http_status}, Exit code: {result.returncode}"
                    )
                    
                    if attempt < self.retries:
                        wait_time = min(60 * attempt, 300)
                        self.logger.info(f"{file_path.name}: Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        
            except Exception as e:
                self.logger.error(f"{file_path.name}: Exception during upload: {e}")
                
            finally:
                # Clean up progress tracking files
                for temp_file in [progress_file, marker_file]:
                    try:
                        Path(temp_file).unlink()
                    except:
                        pass
                        
        # Stop monitor
        stop_monitor.set()
        monitor_thread.join(timeout=5)
        
        # Remove from active uploads
        with self.upload_lock:
            self.active_uploads.pop(uuid, None)
            
        duration = time.time() - start_time
        duration_hours = duration / 3600
        
        return (file_path.name, success, duration_hours)
        
    def run(self, target_files: List[Path]) -> None:
        """Run parallel uploads for multiple files.
        
        Args:
            target_files: List of file paths to upload
        """
        self.logger.info(f"Starting parallel upload process")
        self.logger.info(f"Max concurrent uploads: {self.max_workers}")
        self.logger.info(f"Files to upload: {len(target_files)}")
        
        # Load manifest once
        manifest_data = self._load_manifest()
        
        # Prepare upload tasks
        upload_tasks = []
        for file_path in target_files:
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                continue
                
            metadata = self._find_metadata_for_file(str(file_path), manifest_data)
            if not metadata:
                self.logger.error(f"No metadata found for: {file_path.name}")
                continue
                
            upload_tasks.append((file_path, metadata))
            
        if not upload_tasks:
            self.logger.error("No valid files to upload")
            return
            
        # Summary report
        report_data = []
        total_start = time.time()
        
        # Run uploads in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.upload_file_api, file_path, metadata): file_path
                for file_path, metadata in upload_tasks
            }
            
            # Process results
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    filename, success, duration_hours = future.result()
                    report_data.append({
                        'filename': filename,
                        'success': success,
                        'duration_hours': duration_hours,
                        'cost_estimate': duration_hours * 0.17  # c5.xlarge hourly rate
                    })
                except Exception as e:
                    self.logger.error(f"Exception for {file_path}: {e}")
                    report_data.append({
                        'filename': file_path.name,
                        'success': False,
                        'duration_hours': 0,
                        'cost_estimate': 0
                    })
                    
        # Generate summary report
        total_duration = time.time() - total_start
        total_hours = total_duration / 3600
        
        successful = sum(1 for r in report_data if r['success'])
        failed = len(report_data) - successful
        
        self.logger.info("="*60)
        self.logger.info("UPLOAD SUMMARY REPORT")
        self.logger.info("="*60)
        self.logger.info(f"Total files: {len(report_data)}")
        self.logger.info(f"Successful: {successful}")
        self.logger.info(f"Failed: {failed}")
        self.logger.info(f"Total duration: {total_hours:.2f} hours")
        self.logger.info(f"Parallel efficiency: {sum(r['duration_hours'] for r in report_data) / total_hours:.1f}x")
        self.logger.info("-"*60)
        
        # Write detailed report
        with open('parallel-upload-report.tsv', 'w') as f:
            f.write("filename\tsuccess\tduration_hours\tcost_estimate\n")
            for item in report_data:
                f.write(f"{item['filename']}\t{item['success']}\t"
                       f"{item['duration_hours']:.2f}\t${item['cost_estimate']:.2f}\n")
                       
        self.logger.info("Detailed report saved to: parallel-upload-report.tsv")


def parallel_api_upload(manifest_file: Union[str, Path],
                       token_file: Union[str, Path],
                       target_files: List[Union[str, Path]],
                       max_workers: int = 2) -> None:
    """Upload multiple files in parallel using GDC HTTP API.
    
    Args:
        manifest_file: Path to YAML or JSON manifest
        token_file: Path to GDC token
        target_files: List of files to upload
        max_workers: Maximum concurrent uploads
        
    Example:
        parallel_api_upload(
            "manifest.yaml",
            "token.txt",
            ["file1.bam", "file2.bam", "file3.bam"],
            max_workers=4
        )
    """
    uploader = ParallelAPIUploader(
        manifest_file=Path(manifest_file),
        token_file=Path(token_file),
        max_workers=max_workers
    )
    
    file_paths = [Path(f) for f in target_files]
    uploader.run(file_paths)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upload multiple files in parallel using GDC API"
    )
    parser.add_argument(
        "manifest_file",
        help="Path to YAML or JSON manifest file"
    )
    parser.add_argument(
        "token_file",
        help="Path to GDC token file"
    )
    parser.add_argument(
        "target_files",
        nargs='+',
        help="Files to upload"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=2,
        help="Maximum concurrent uploads (default: 2)"
    )
    
    args = parser.parse_args()
    
    parallel_api_upload(
        args.manifest_file,
        args.token_file,
        args.target_files,
        args.max_workers
    )