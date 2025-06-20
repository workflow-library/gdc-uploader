#!/usr/bin/env python3
"""
GDC HTTP Upload - File uploader with environment-aware progress monitoring.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import click
import requests

from .validate import validate_manifest, validate_token, find_manifest_entry
from .utils import find_file, chunk_reader

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


class Logger:
    """Handles output to both console and optional log file."""
    
    def __init__(self, log_file=None, append=False):
        self.log_file = log_file
        self.file_handle = None
        if log_file:
            mode = 'a' if append else 'w'
            self.file_handle = open(log_file, mode, encoding='utf-8')
            self._write_header()
    
    def _write_header(self):
        """Write header with timestamp to log file."""
        if self.file_handle:
            self.file_handle.write(f"\n{'='*60}\n")
            self.file_handle.write(f"GDC Upload Log - {datetime.now().isoformat()}\n")
            self.file_handle.write(f"{'='*60}\n\n")
            self.file_handle.flush()
    
    def echo(self, message, err=False, to_console=True):
        """Write message to console and/or log file."""
        if to_console:
            click.echo(message, err=err)
        
        if self.file_handle:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if err:
                self.file_handle.write(f"[{timestamp}] ERROR: {message}\n")
            else:
                self.file_handle.write(f"[{timestamp}] {message}\n")
            self.file_handle.flush()
    
    def write_json(self, data, label="Response"):
        """Write JSON data with proper formatting."""
        json_str = json.dumps(data, indent=2)
        self.echo(f"{label}: {json_str}")
    
    def close(self):
        """Close the log file."""
        if self.file_handle:
            self.file_handle.write(f"\n{'='*60}\n")
            self.file_handle.write(f"Log ended at {datetime.now().isoformat()}\n")
            self.file_handle.write(f"{'='*60}\n")
            self.file_handle.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SimpleProgress:
    """Simple progress reporter for non-interactive environments."""
    
    def __init__(self, total, desc="Progress", logger=None):
        self.total = total
        self.current = 0
        self.desc = desc
        self.last_percent = -1
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_update_bytes = 0
        self.logger = logger
        
    def update(self, n):
        self.current += n
        percent = 100 * self.current / self.total
        
        # Print at 0.25% intervals for ~400 updates on very large files
        if percent >= self.last_percent + 0.25:
            current_time = time.time()
            
            # Calculate average speed since start
            elapsed = current_time - self.start_time
            avg_speed_mbps = (self.current / (1024 * 1024)) / elapsed if elapsed > 0 else 0
            
            # Format sizes in GB
            current_gb = self.current / (1024**3)
            total_gb = self.total / (1024**3)
            
            message = f"{self.desc}: {percent:.2f}% ({current_gb:.2f}/{total_gb:.2f} GB) - {avg_speed_mbps:.2f} MB/s"
            if self.logger:
                self.logger.echo(message, to_console=True)
            else:
                print(message)
                sys.stdout.flush()
            
            self.last_percent = percent
            self.last_update_time = current_time
            self.last_update_bytes = self.current
    
    def __enter__(self):
        total_gb = self.total / (1024**3)
        message = f"{self.desc}: 0.00% (0.00/{total_gb:.2f} GB)"
        if self.logger:
            self.logger.echo(message, to_console=True)
        else:
            print(message)
            sys.stdout.flush()
        return self
    
    def __exit__(self, *args):
        if self.last_percent < 100:
            total_gb = self.total / (1024**3)
            elapsed = time.time() - self.start_time
            avg_speed_mbps = (self.total / (1024 * 1024)) / elapsed if elapsed > 0 else 0
            message = f"{self.desc}: 100.00% ({total_gb:.2f}/{total_gb:.2f} GB) - {avg_speed_mbps:.2f} MB/s"
            if self.logger:
                self.logger.echo(message, to_console=True)
            else:
                print(message)
                sys.stdout.flush()


def detect_environment():
    """Detect execution environment."""
    return {
        'is_tty': sys.stdout.isatty(),
        'is_sbp': os.environ.get('SBP_TASK_ID') is not None,
        'is_cwl': os.environ.get('CWL_RUNTIME') is not None,
        'term': os.environ.get('TERM', 'unknown')
    }


def get_progress_handler(total_size, desc="Uploading", mode='auto', logger=None):
    """Get appropriate progress handler for the environment."""
    
    if mode == 'none':
        return None
    
    env = detect_environment()
    
    # Force simple progress in non-interactive environments
    use_simple = (
        mode == 'simple' or 
        (mode == 'auto' and (env['is_sbp'] or env['is_cwl'] or not env['is_tty']))
    )
    
    if use_simple or tqdm is None:
        return SimpleProgress(total_size, desc, logger=logger)
    else:
        return tqdm(
            total=total_size, 
            unit='B', 
            unit_scale=True, 
            desc=desc,
            ascii=True if env['term'] == 'unknown' else None
        )


def upload_file_with_progress(file_path, file_id, token, chunk_size=8192, progress_mode='auto', logger=None):
    """Upload file to GDC with environment-appropriate progress display."""
    url = f"https://api.gdc.cancer.gov/v0/submission/files/{file_id}"
    
    file_size = file_path.stat().st_size
    
    headers = {
        'X-Auth-Token': token,
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(file_size)
    }
    
    # Get appropriate progress handler
    progress = get_progress_handler(file_size, "Uploading", progress_mode, logger=logger)
    
    try:
        with open(file_path, 'rb') as f:
            if progress:
                with progress as pbar:
                    response = requests.put(
                        url,
                        headers=headers,
                        data=chunk_reader(f, chunk_size, lambda n: pbar.update(n)),
                        stream=True
                    )
            else:
                # No progress display
                response = requests.put(
                    url,
                    headers=headers,
                    data=chunk_reader(f, chunk_size),
                    stream=True
                )
            
            response.raise_for_status()
            return response.json()
    except Exception:
        # Ensure progress is cleaned up on error
        if progress and hasattr(progress, '__exit__'):
            progress.__exit__(None, None, None)
        raise


@click.command()
@click.option('--manifest', '-m', required=True, type=click.Path(exists=True), 
              help='GDC manifest JSON file')
@click.option('--file', '-f', required=True, help='Target filename to upload')
@click.option('--file-path', type=click.Path(exists=True),
              help='Actual path to the file (if different from filename)')
@click.option('--token', '-t', required=True, type=click.Path(exists=True),
              help='GDC token file')
@click.option('--progress-mode', '-p',
              type=click.Choice(['auto', 'simple', 'bar', 'none']),
              default='auto',
              help='Progress display mode (auto detects environment)')
@click.option('--output', '-o', type=click.Path(),
              help='Save output to log file (default: no file output)')
@click.option('--append', is_flag=True,
              help='Append to output file instead of overwriting')
def main(manifest, file, file_path, token, progress_mode, output, append):
    """Upload file to GDC with environment-aware progress monitoring."""
    with Logger(output, append) as logger:
        try:
            # Validate inputs
            logger.echo(f"Parsing manifest for '{file}'...")
            manifest_path = Path(manifest)
            token_path = Path(token)
            
            # Log upload parameters
            if logger.file_handle:
                logger.echo(f"Manifest: {manifest}")
                logger.echo(f"Target file: {file}")
                logger.echo(f"Token file: {token}")
                logger.echo(f"Progress mode: {progress_mode}")
                logger.echo("")
            
            entries = validate_manifest(manifest_path)
            entry = find_manifest_entry(entries, file)
            file_id = entry['id']
            
            # Find actual file
            if file_path:
                # Use provided file path
                actual_file_path = Path(file_path)
            else:
                # Search for file by name
                actual_file_path = find_file(file)
                if not actual_file_path:
                    logger.echo(f"Error: File '{file}' not found", err=True)
                    sys.exit(1)
            
            logger.echo(f"Found file: {actual_file_path}")
            logger.echo(f"File ID: {file_id}")
            logger.echo(f"File size: {actual_file_path.stat().st_size:,} bytes")
            
            # Validate token
            token_value = validate_token(token_path)
            
            # Upload with progress
            logger.echo("Starting upload...")
            result = upload_file_with_progress(
                actual_file_path, 
                file_id, 
                token_value,
                progress_mode=progress_mode,
                logger=logger
            )
            
            logger.echo(f"✓ Upload successful!")
            logger.write_json(result, "Response")
        
        except ValueError as e:
            logger.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            logger.echo(f"Upload failed: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            logger.echo(f"Unexpected error: {e}", err=True)
            sys.exit(1)


if __name__ == '__main__':
    main()