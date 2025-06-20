#!/usr/bin/env python3
"""
GDC HTTP Upload - File uploader with environment-aware progress monitoring.
"""

import json
import os
import sys
from pathlib import Path

import click
import requests

from .validate import validate_manifest, validate_token, find_manifest_entry
from .utils import find_file, chunk_reader


class SimpleProgress:
    """Simple progress reporter for non-interactive environments."""
    
    def __init__(self, total, desc="Progress"):
        self.total = total
        self.current = 0
        self.desc = desc
        self.last_percent = -1
        
    def update(self, n):
        self.current += n
        percent = int(100 * self.current / self.total)
        
        # Only print at 10% intervals to avoid log spam
        if percent >= self.last_percent + 10:
            print(f"{self.desc}: {percent}% ({self.current:,}/{self.total:,} bytes)")
            sys.stdout.flush()
            self.last_percent = percent
    
    def __enter__(self):
        print(f"{self.desc}: 0% (0/{self.total:,} bytes)")
        sys.stdout.flush()
        return self
    
    def __exit__(self, *args):
        if self.last_percent < 100:
            print(f"{self.desc}: 100% ({self.total:,}/{self.total:,} bytes)")
            sys.stdout.flush()


def detect_environment():
    """Detect execution environment."""
    return {
        'is_tty': sys.stdout.isatty(),
        'is_sbp': os.environ.get('SBP_TASK_ID') is not None,
        'is_cwl': os.environ.get('CWL_RUNTIME') is not None,
        'term': os.environ.get('TERM', 'unknown')
    }


def get_progress_handler(total_size, desc="Uploading", mode='auto'):
    """Get appropriate progress handler for the environment."""
    
    if mode == 'none':
        return None
    
    env = detect_environment()
    
    # Force simple progress in non-interactive environments
    use_simple = (
        mode == 'simple' or 
        (mode == 'auto' and (env['is_sbp'] or env['is_cwl'] or not env['is_tty']))
    )
    
    if use_simple:
        return SimpleProgress(total_size, desc)
    else:
        try:
            from tqdm import tqdm
            return tqdm(
                total=total_size, 
                unit='B', 
                unit_scale=True, 
                desc=desc,
                ascii=True if env['term'] == 'unknown' else None
            )
        except ImportError:
            return SimpleProgress(total_size, desc)


def upload_file_with_progress(file_path, file_id, token, chunk_size=8192, progress_mode='auto'):
    """Upload file to GDC with environment-appropriate progress display."""
    url = f"https://api.gdc.cancer.gov/v0/submission/files/{file_id}"
    
    file_size = file_path.stat().st_size
    
    headers = {
        'X-Auth-Token': token,
        'Content-Type': 'application/octet-stream',
        'Content-Length': str(file_size)
    }
    
    # Get appropriate progress handler
    progress = get_progress_handler(file_size, "Uploading", progress_mode)
    
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
@click.option('--token', '-t', required=True, type=click.Path(exists=True),
              help='GDC token file')
@click.option('--progress-mode', '-p',
              type=click.Choice(['auto', 'simple', 'bar', 'none']),
              default='auto',
              help='Progress display mode (auto detects environment)')
def main(manifest, file, token, progress_mode):
    """Upload file to GDC with environment-aware progress monitoring."""
    try:
        # Validate inputs
        click.echo(f"Parsing manifest for '{file}'...")
        manifest_path = Path(manifest)
        token_path = Path(token)
        
        entries = validate_manifest(manifest_path)
        entry = find_manifest_entry(entries, file)
        file_id = entry['id']
        
        # Find actual file
        file_path = find_file(file)
        if not file_path:
            click.echo(f"Error: File '{file}' not found", err=True)
            sys.exit(1)
        
        click.echo(f"Found file: {file_path}")
        click.echo(f"File ID: {file_id}")
        
        # Validate token
        token_value = validate_token(token_path)
        
        # Upload with progress
        click.echo("Starting upload...")
        result = upload_file_with_progress(
            file_path, 
            file_id, 
            token_value,
            progress_mode=progress_mode
        )
        
        click.echo(f"✓ Upload successful!")
        click.echo(f"Response: {json.dumps(result, indent=2)}")
        
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        click.echo(f"Upload failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()