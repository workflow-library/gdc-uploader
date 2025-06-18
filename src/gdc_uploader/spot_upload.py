"""GDC Uploader optimized for spot instances with automatic resume capability."""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Union

import yaml


class SpotInstanceUploader:
    """GDC uploader designed for interruptible spot instances."""
    
    def __init__(self, manifest_file: Path, token_file: Path, 
                 state_file: Optional[Path] = None, retries: int = 3):
        """Initialize the spot instance uploader.
        
        Args:
            manifest_file: Path to YAML or JSON manifest file
            token_file: Path to GDC authentication token file
            state_file: Path to save upload state (for resume)
            retries: Number of retry attempts
        """
        self.manifest_file = manifest_file
        self.token_file = token_file
        self.state_file = state_file or Path("upload_state.json")
        self.retries = retries
        self.logger = self._setup_logging()
        self._setup_signal_handlers()
        
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
        
        # File handler
        fh = logging.FileHandler('spot-upload.log')
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger
        
    def _setup_signal_handlers(self):
        """Set up graceful shutdown on spot instance termination."""
        def signal_handler(signum, frame):
            self.logger.warning(f"Received signal {signum}. Saving state and exiting...")
            self._save_state({"interrupted": True, "signal": signum})
            sys.exit(0)
            
        # Handle spot instance termination signals
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
    def _load_manifest(self) -> Dict:
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
            
    def _filter_manifest(self, target_filename: str) -> Optional[Dict]:
        """Filter manifest for specific file."""
        manifest_data = self._load_manifest()
        
        # Search for exact filename match
        for item in manifest_data:
            file_name = item.get('file_name', item.get('filename', ''))
            if file_name == target_filename:
                return item
                
        # Try matching just the basename if full path was provided
        target_basename = Path(target_filename).name
        for item in manifest_data:
            file_name = item.get('file_name', item.get('filename', ''))
            if Path(file_name).name == target_basename:
                return item
                
        return None
        
    def _save_state(self, state: Dict):
        """Save current upload state for resume."""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
        self.logger.info(f"State saved to {self.state_file}")
        
    def _load_state(self) -> Optional[Dict]:
        """Load previous upload state if exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load state file: {e}")
        return None
        
    def upload_file(self, file_path: Path, metadata: Dict) -> bool:
        """Upload a single file using gdc-client with resume support.
        
        Args:
            file_path: Path to the file to upload
            metadata: Metadata dictionary for the file
            
        Returns:
            True if successful, False otherwise
        """
        uuid = metadata.get('id', metadata.get('uuid'))
        if not uuid:
            self.logger.error("No UUID found in metadata")
            return False
            
        # Save state before starting
        self._save_state({
            "file": str(file_path),
            "uuid": uuid,
            "metadata": metadata,
            "status": "uploading",
            "timestamp": time.time()
        })
        
        # Prepare gdc-client command
        cmd = [
            "gdc-client", "upload",
            "-t", str(self.token_file),
            "--path", str(file_path.parent),  # Directory containing the file
            uuid,
            "--log-file", f"gdc-upload-{uuid}.log",
            "--upload-part-size", "1073741824",  # 1GB chunks
            "-n", "8",  # 8 parallel threads
            "--resume",  # Enable resume
            "--no-related-files",  # Don't look for related files
            "--no-verify"  # Skip verification for speed (optional)
        ]
        
        self.logger.info(f"Starting upload: {file_path.name} (UUID: {uuid})")
        self.logger.info(f"Command: {' '.join(cmd)}")
        
        # Run upload with retries
        for attempt in range(1, self.retries + 1):
            self.logger.info(f"Upload attempt {attempt} of {self.retries}")
            
            try:
                # Check if spot instance termination is imminent
                if self._check_spot_termination():
                    self.logger.warning("Spot instance termination detected. Saving state...")
                    self._save_state({
                        "file": str(file_path),
                        "uuid": uuid,
                        "metadata": metadata,
                        "status": "interrupted",
                        "attempt": attempt,
                        "timestamp": time.time()
                    })
                    return False
                    
                # Run gdc-client
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                self.logger.info("Upload completed successfully!")
                self._save_state({
                    "file": str(file_path),
                    "uuid": uuid,
                    "metadata": metadata,
                    "status": "completed",
                    "timestamp": time.time()
                })
                
                # Clean up state file after successful upload
                if self.state_file.exists():
                    self.state_file.unlink()
                    
                return True
                
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Upload failed on attempt {attempt}: {e}")
                self.logger.error(f"stderr: {e.stderr}")
                
                if attempt < self.retries:
                    wait_time = min(60 * attempt, 300)  # Max 5 min wait
                    self.logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    self._save_state({
                        "file": str(file_path),
                        "uuid": uuid,
                        "metadata": metadata,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": time.time()
                    })
                    return False
                    
    def _check_spot_termination(self) -> bool:
        """Check if spot instance is about to be terminated.
        
        AWS posts a termination notice to instance metadata service.
        """
        try:
            # Check AWS spot instance termination notice
            response = subprocess.run(
                ["curl", "-s", "-m", "1", 
                 "http://169.254.169.254/latest/meta-data/spot/instance-action"],
                capture_output=True,
                text=True
            )
            
            if response.returncode == 0 and response.stdout.strip():
                return True
                
        except Exception:
            pass
            
        return False
        
    def run(self, target_file: Path) -> None:
        """Run the upload process for a specific file.
        
        Args:
            target_file: Path to the file to upload
        """
        self.logger.info(f"Starting spot-resilient upload process")
        self.logger.info(f"Manifest: {self.manifest_file}")
        self.logger.info(f"Target file: {target_file}")
        
        # Check for previous state
        previous_state = self._load_state()
        if previous_state and previous_state.get('status') == 'completed':
            self.logger.info("Previous upload completed successfully. Nothing to do.")
            return
            
        if previous_state and previous_state.get('status') in ['uploading', 'interrupted']:
            self.logger.info(f"Resuming previous upload: {previous_state}")
            
        # Filter manifest for target file
        target_basename = target_file.name
        metadata = self._filter_manifest(target_basename)
        
        if not metadata:
            self.logger.error(f"No metadata found for file: {target_basename}")
            sys.exit(1)
            
        self.logger.info(f"Found metadata: {metadata}")
        
        # Verify file exists
        if not target_file.exists():
            self.logger.error(f"File not found: {target_file}")
            sys.exit(1)
            
        # Check file size
        file_size = target_file.stat().st_size
        file_size_gb = file_size / (1024 ** 3)
        self.logger.info(f"File size: {file_size_gb:.2f} GB")
        
        # Perform upload
        success = self.upload_file(target_file, metadata)
        
        if success:
            self.logger.info("Upload completed successfully!")
            sys.exit(0)
        else:
            self.logger.error("Upload failed!")
            sys.exit(2)


def upload_with_resume(manifest_file: Union[str, Path], 
                      token_file: Union[str, Path],
                      target_file: Union[str, Path],
                      state_file: Optional[Union[str, Path]] = None) -> None:
    """Upload a file to GDC with automatic resume capability.
    
    Designed for use on spot instances that may be interrupted.
    
    Args:
        manifest_file: Path to YAML or JSON manifest containing all files
        token_file: Path to GDC authentication token
        target_file: Path to the specific file to upload
        state_file: Optional path to save upload state (default: upload_state.json)
        
    Example:
        upload_with_resume(
            manifest_file="manifest.yaml",
            token_file="token.txt",
            target_file="/data/sample.bam"
        )
    """
    uploader = SpotInstanceUploader(
        manifest_file=Path(manifest_file),
        token_file=Path(token_file),
        state_file=Path(state_file) if state_file else None
    )
    
    uploader.run(Path(target_file))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upload a file to GDC with spot instance resilience"
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
        "target_file",
        help="Path to the file to upload"
    )
    parser.add_argument(
        "--state-file",
        default="upload_state.json",
        help="Path to save upload state (default: upload_state.json)"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of retry attempts (default: 3)"
    )
    
    args = parser.parse_args()
    
    upload_with_resume(
        manifest_file=args.manifest_file,
        token_file=args.token_file,
        target_file=args.target_file,
        state_file=args.state_file
    )