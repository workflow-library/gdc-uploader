#!/usr/bin/env python3
"""
GDC HTTP Upload - File uploader with environment-aware progress monitoring.
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

import click
import requests

from .validate import validate_manifest, validate_token, find_manifest_entry
from .utils import find_file

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
        
        # For files > 20GB, update every 0.25%, otherwise every 1.25%
        twenty_gb = 20 * 1024 * 1024 * 1024
        update_interval = 0.25 if self.total > twenty_gb else 1.25
        
        if percent >= self.last_percent + update_interval:
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


def check_file_exists(url, token, logger=None):
    """Check if file already exists in GDC."""
    headers = {
        'x-auth-token': token
    }
    
    try:
        # Try HEAD request first (more efficient)
        response = requests.head(url, headers=headers)
        if response.status_code == 200:
            return True, "File already exists in GDC"
        elif response.status_code == 404:
            return False, "File not found"
        else:
            # Try GET for more info
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return True, "File already exists in GDC"
            else:
                return False, f"Status {response.status_code}: {response.reason}"
    except Exception as e:
        if logger:
            logger.echo(f"Warning: Could not check file existence: {e}")
        return None, str(e)


def upload_file_with_progress(file_path, file_id, token, chunk_size=8*1024*1024, progress_mode='auto', logger=None, program=None, project=None):
    """Upload file to GDC with environment-appropriate progress display."""
    if program and project:
        url = f"https://api.gdc.cancer.gov/v0/submission/{program}/{project}/files/{file_id}"
    else:
        url = f"https://api.gdc.cancer.gov/v0/submission/files/{file_id}"
    
    file_size = file_path.stat().st_size
    
    headers = {
        'x-auth-token': token
    }
    
    # Log request details for debugging
    if logger:
        logger.echo(f"Upload URL: {url}")
        logger.echo(f"File size: {file_size} bytes ({file_size / (1024**3):.2f} GB)")
        logger.echo(f"Token (first 10 chars): {token[:10]}...")
        
        # Log the equivalent curl command
        logger.echo("")
        logger.echo("Equivalent curl command:")
        logger.echo(f'curl --header "x-auth-token: $token" --request PUT -T "{file_path}" "{url}"')
        logger.echo("")
    
    # Check if file already exists
    exists, message = check_file_exists(url, token, logger)
    if exists:
        if logger:
            logger.echo(f"⚠️  Warning: {message}")
            logger.echo("File may have already been uploaded. Attempting upload anyway...")
    elif exists is False and logger:
        logger.echo(f"File status: {message}")
    
    # Use curl for upload since it works where requests fails
    if logger:
        logger.echo("Using curl for upload...")
    
    # Prepare curl command - exactly as provided by user
    curl_cmd = [
        'curl',
        '--header', f'x-auth-token: {token}',
        '--request', 'PUT',
        '-T', str(file_path),
        url
    ]
    
    # Determine if we should show progress
    # Always show progress unless explicitly disabled with 'none'
    show_progress = progress_mode != 'none'
    
    if show_progress:
        # For non-TTY environments, use curl with custom progress parsing
        import re
        
        # Use curl's progress output that works in all environments
        curl_cmd.extend(['-#'])  # Simple progress bar
        
        # Run curl with real-time output processing
        process = subprocess.Popen(
            curl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Initialize progress tracking
        progress = SimpleProgress(file_size, "Uploading", logger=logger)
        last_percent = -1
        
        # For files > 20GB, update every 0.25%, otherwise every 1.25%
        twenty_gb = 20 * 1024 * 1024 * 1024
        update_interval = 0.25 if file_size > twenty_gb else 1.25
        
        with progress:
            # Read stderr (where curl sends progress)
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                    
                # Parse curl progress: ######################################################################## 100.0%
                if '#' in line:
                    # Count the number of # characters
                    hash_count = line.count('#')
                    # Each # represents roughly 1.25% (80 chars = 100%)
                    percent = min(hash_count * 1.25, 100)
                    
                    if percent >= last_percent + update_interval:
                        # Update progress based on percentage
                        bytes_done = int(file_size * percent / 100)
                        bytes_to_update = bytes_done - progress.current
                        if bytes_to_update > 0:
                            progress.update(bytes_to_update)
                        last_percent = percent
            
            # Get the output
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr or "Unknown error"
                raise Exception(f"Curl failed: {error_msg}")
            
            # Success
            if logger:
                logger.echo("✓ Upload completed successfully")
            
            # Try to parse response as JSON
            output = stdout.strip()
            try:
                if output:
                    return json.loads(output)
                else:
                    return {"status": "success"}
            except json.JSONDecodeError:
                return {"status": "success", "response": output}
    
    else:
        # No progress display
        try:
            # Run curl command without progress
            result = subprocess.run(
                curl_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                raise Exception(f"Curl failed: {error_msg}")
            
            # Success
            if logger:
                logger.echo("✓ Upload completed successfully")
            
            # Try to parse response as JSON
            output = result.stdout.strip()
            try:
                if output:
                    return json.loads(output)
                else:
                    return {"status": "success"}
            except json.JSONDecodeError:
                return {"status": "success", "response": output}
        
        except Exception as e:
            if logger:
                logger.echo(f"Upload error: {e}", err=True)
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
@click.option('--legacy-endpoint', is_flag=True,
              help='Use legacy endpoint without program/project in URL')
def main(manifest, file, file_path, token, progress_mode, output, append, legacy_endpoint):
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
            
            # Extract program and project from manifest entry
            program = entry.get('program')
            project = entry.get('project')
            project_id = entry.get('project_id')
            
            # If project_id is provided but not program/project, try to parse it
            if project_id and not (program and project):
                if '-' in project_id:
                    parts = project_id.split('-', 1)
                    if len(parts) == 2:
                        program = parts[0]
                        project = parts[1]
            
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
            
            # Determine upload URL
            if legacy_endpoint or not (program and project):
                if not legacy_endpoint:
                    logger.echo("Warning: No program/project found in manifest, using legacy endpoint")
                upload_url = f"https://api.gdc.cancer.gov/v0/submission/files/{file_id}"
            else:
                logger.echo(f"Program: {program}, Project: {project}")
                upload_url = f"https://api.gdc.cancer.gov/v0/submission/{program}/{project}/files/{file_id}"
            
            # Upload with progress
            logger.echo("Starting upload...")
            
            # Use legacy endpoint if requested or if program/project not found
            if legacy_endpoint or not (program and project):
                result = upload_file_with_progress(
                    actual_file_path, 
                    file_id, 
                    token_value,
                    progress_mode=progress_mode,
                    logger=logger
                )
            else:
                result = upload_file_with_progress(
                    actual_file_path, 
                    file_id, 
                    token_value,
                    progress_mode=progress_mode,
                    logger=logger,
                    program=program,
                    project=project
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