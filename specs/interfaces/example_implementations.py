"""Example implementations showing how existing uploaders would use the new interfaces.

This file demonstrates how the four different upload implementations would be
refactored to use the new base classes and plugin architecture.
"""

import subprocess
import shutil
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import the core interfaces
from src.gdc_uploader.core import (
    BaseUploader, FileEntry, UploadResult, UploadStatus,
    StandardFileDiscovery, UploadProgress
)
from src.gdc_uploader.core.plugins import (
    UploaderPlugin, UploaderConfig, UploaderType,
    register_uploader, Features, ConfigSchema
)
from src.gdc_uploader.core.exceptions import (
    UploadFailedError, MissingDependencyError
)


logger = logging.getLogger(__name__)


# Example 1: Parallel GDC Client Uploader (main upload.py replacement)

@register_uploader(UploaderType.PARALLEL_GDC_CLIENT)
class ParallelGDCClientPlugin(UploaderPlugin):
    """Plugin for parallel uploads using GNU parallel and gdc-client."""
    
    def get_config(self) -> UploaderConfig:
        return UploaderConfig(
            name="Parallel GDC Client Uploader",
            uploader_type=UploaderType.PARALLEL_GDC_CLIENT,
            description="Uses GNU parallel with gdc-client for concurrent uploads",
            supported_features=[
                Features.PARALLEL_UPLOAD,
                Features.RETRY_LOGIC,
                Features.PROGRESS_TRACKING,
                Features.GDC_CLIENT_UPLOAD,
                Features.BATCH_UPLOAD,
                Features.RESUME_CAPABILITY
            ],
            priority=100,  # High priority as it's the default
            config_schema=ConfigSchema.create_schema(
                max_parallel_uploads=ConfigSchema.integer_property(
                    "Maximum number of parallel uploads",
                    default=4,
                    minimum=1,
                    maximum=32
                ),
                use_resume=ConfigSchema.boolean_property(
                    "Enable resume capability",
                    default=True
                )
            )
        )
    
    def create_uploader(self, **kwargs) -> BaseUploader:
        return ParallelGDCClientUploader(**kwargs)
    
    def validate_environment(self) -> bool:
        return (
            shutil.which('gdc-client') is not None and
            shutil.which('parallel') is not None and
            shutil.which('jq') is not None
        )
    
    def get_required_dependencies(self) -> List[str]:
        return ['gdc-client', 'parallel', 'jq']


class ParallelGDCClientUploader(BaseUploader):
    """Implementation of parallel uploads using GNU parallel."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_discovery = StandardFileDiscovery()
        self.use_resume = kwargs.get('use_resume', True)
    
    def discover_files(self) -> List[FileEntry]:
        """Discover files using standard discovery strategy."""
        return list(self.file_discovery.discover(self.base_directory, self.metadata))
    
    def validate_files(self, files: List[FileEntry]) -> List[FileEntry]:
        """Validate that files exist and are accessible."""
        validated = []
        for file_entry in files:
            if file_entry.path and file_entry.path.exists():
                # Update size if not set
                if file_entry.size is None:
                    file_entry.size = file_entry.path.stat().st_size
                validated.append(file_entry)
            else:
                logger.warning(f"File not found: {file_entry.filename} ({file_entry.uuid})")
        return validated
    
    def upload_file(self, file_entry: FileEntry) -> UploadResult:
        """Upload a single file using gdc-client."""
        start_time = time.time()
        result = UploadResult(
            file_entry=file_entry,
            status=UploadStatus.PENDING,
            start_time=start_time
        )
        
        for attempt in range(1, self.retry_count + 1):
            try:
                result.attempts = attempt
                
                # Build gdc-client command
                cmd = self.get_upload_command(file_entry)
                
                # Execute upload
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                
                if process.returncode == 0:
                    result.status = UploadStatus.SUCCESS
                    result.end_time = time.time()
                    result.bytes_transferred = file_entry.size
                    logger.info(f"Successfully uploaded {file_entry.filename}")
                    break
                else:
                    raise UploadFailedError(
                        file_entry.filename,
                        file_entry.uuid,
                        process.stderr or "Unknown error",
                        attempts=attempt
                    )
                    
            except Exception as e:
                result.error_message = str(e)
                if attempt == self.retry_count:
                    result.status = UploadStatus.FAILED
                    result.end_time = time.time()
                    logger.error(f"Failed to upload {file_entry.filename}: {e}")
                else:
                    logger.warning(f"Attempt {attempt} failed for {file_entry.filename}, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return result
    
    def upload_batch(self, files: List[FileEntry]) -> List[UploadResult]:
        """Upload multiple files in parallel using GNU parallel."""
        if self.thread_count == 1:
            # Sequential upload
            return [self.upload_file(f) for f in files]
        
        # Create upload commands file
        commands_file = Path("upload_commands.txt")
        with open(commands_file, 'w') as f:
            for file_entry in files:
                cmd = ' '.join(self.get_upload_command(file_entry))
                f.write(f"{cmd}\\n")
        
        # Run parallel
        parallel_cmd = [
            'parallel',
            '-j', str(self.thread_count),
            '--joblog', 'parallel.log',
            '--resume' if self.use_resume else '--no-resume',
            '-a', str(commands_file)
        ]
        
        process = subprocess.run(parallel_cmd, capture_output=True, text=True)
        
        # Parse results from joblog
        results = []
        with open('parallel.log', 'r') as f:
            lines = f.readlines()[1:]  # Skip header
            for i, line in enumerate(lines):
                parts = line.strip().split('\\t')
                exit_code = int(parts[6])
                
                file_entry = files[i]
                result = UploadResult(
                    file_entry=file_entry,
                    status=UploadStatus.SUCCESS if exit_code == 0 else UploadStatus.FAILED,
                    attempts=1
                )
                results.append(result)
        
        # Cleanup
        commands_file.unlink()
        Path('parallel.log').unlink()
        
        return results
    
    def get_upload_command(self, file_entry: FileEntry) -> List[str]:
        """Get gdc-client upload command."""
        cmd = [
            'gdc-client',
            'upload',
            '-t', str(self.token_file),
            '-i', file_entry.uuid,
            str(file_entry.path)
        ]
        
        if self.use_resume:
            cmd.append('--resume')
            
        return cmd
    
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Generate upload report."""
        success_count = sum(1 for r in results if r.status == UploadStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == UploadStatus.FAILED)
        
        report = {
            'summary': {
                'total_files': len(results),
                'successful': success_count,
                'failed': failed_count,
                'start_time': min(r.start_time for r in results if r.start_time),
                'end_time': max(r.end_time for r in results if r.end_time)
            },
            'files': []
        }
        
        for result in results:
            report['files'].append({
                'uuid': result.file_entry.uuid,
                'filename': result.file_entry.filename,
                'path': str(result.file_entry.path) if result.file_entry.path else None,
                'status': result.status.value,
                'attempts': result.attempts,
                'error': result.error_message
            })
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save report as TSV file."""
        with open(output_path, 'w') as f:
            f.write("UUID\\tFILENAME\\tPATH\\tSTATUS\\n")
            for file_info in report['files']:
                f.write(f"{file_info['uuid']}\\t")
                f.write(f"{file_info['filename']}\\t")
                f.write(f"{file_info['path'] or 'N/A'}\\t")
                f.write(f"{file_info['status']}\\n")


# Example 2: Single File Uploader (upload_single.py replacement)

@register_uploader(UploaderType.SINGLE_FILE)
class SingleFilePlugin(UploaderPlugin):
    """Plugin for single file uploads with real-time progress."""
    
    def get_config(self) -> UploaderConfig:
        return UploaderConfig(
            name="Single File Uploader",
            uploader_type=UploaderType.SINGLE_FILE,
            description="Uploads single files with real-time progress monitoring",
            supported_features=[
                Features.SINGLE_FILE_UPLOAD,
                Features.REAL_TIME_PROGRESS,
                Features.RETRY_LOGIC,
                Features.GDC_CLIENT_UPLOAD
            ],
            priority=50,
            config_schema=ConfigSchema.create_schema(
                show_progress=ConfigSchema.boolean_property(
                    "Display real-time progress",
                    default=True
                )
            )
        )
    
    def create_uploader(self, **kwargs) -> BaseUploader:
        return SingleFileUploader(**kwargs)
    
    def validate_environment(self) -> bool:
        return shutil.which('gdc-client') is not None
    
    def get_required_dependencies(self) -> List[str]:
        return ['gdc-client']


class SingleFileUploader(BaseUploader):
    """Implementation for single file uploads with progress monitoring."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.show_progress = kwargs.get('show_progress', True)
        # Force thread_count to 1 for single file uploads
        self.thread_count = 1
    
    def discover_files(self) -> List[FileEntry]:
        """For single file uploader, expect only one file in metadata."""
        entries = self._parse_metadata()
        if len(entries) > 1:
            logger.warning(f"Single file uploader found {len(entries)} files, using first one")
        return entries[:1]
    
    def validate_files(self, files: List[FileEntry]) -> List[FileEntry]:
        """Validate the single file."""
        if not files:
            return []
        
        file_entry = files[0]
        if not file_entry.path or not file_entry.path.exists():
            # Try to find the file
            for path in self.base_directory.rglob(file_entry.filename):
                if path.is_file():
                    file_entry.path = path
                    break
        
        if file_entry.path and file_entry.path.exists():
            file_entry.size = file_entry.path.stat().st_size
            return [file_entry]
        
        return []
    
    def upload_file(self, file_entry: FileEntry) -> UploadResult:
        """Upload with real-time progress monitoring."""
        result = UploadResult(
            file_entry=file_entry,
            status=UploadStatus.IN_PROGRESS,
            start_time=time.time()
        )
        
        # Start progress monitor in background
        if self.show_progress:
            progress_monitor = SingleFileProgressMonitor(file_entry, self.token_file)
            progress_monitor.start_monitoring(file_entry)
        
        try:
            # Run upload
            cmd = self.get_upload_command(file_entry)
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                result.status = UploadStatus.SUCCESS
                result.bytes_transferred = file_entry.size
            else:
                result.status = UploadStatus.FAILED
                result.error_message = process.stderr
                
        finally:
            if self.show_progress:
                progress_monitor.stop_monitoring()
            result.end_time = time.time()
        
        return result
    
    def upload_batch(self, files: List[FileEntry]) -> List[UploadResult]:
        """Single file uploader only handles one file at a time."""
        if files:
            return [self.upload_file(files[0])]
        return []
    
    def get_upload_command(self, file_entry: FileEntry) -> List[str]:
        """Get gdc-client command for single file."""
        return [
            'gdc-client',
            'upload',
            '-t', str(self.token_file),
            '-i', file_entry.uuid,
            str(file_entry.path),
            '--log-file', f'upload-{file_entry.uuid}.log'
        ]
    
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Generate report for single file upload."""
        if not results:
            return {'files': []}
        
        result = results[0]
        return {
            'file': {
                'uuid': result.file_entry.uuid,
                'filename': result.file_entry.filename,
                'size': result.file_entry.size,
                'status': result.status.value,
                'duration': result.duration,
                'transfer_rate': (
                    result.bytes_transferred / result.duration 
                    if result.duration and result.bytes_transferred else 0
                )
            }
        }
    
    def save_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save single file report."""
        with open(output_path, 'w') as f:
            if 'file' in report:
                file_info = report['file']
                f.write("UUID\\tFILENAME\\tSIZE\\tSTATUS\\tDURATION\\n")
                f.write(f"{file_info['uuid']}\\t")
                f.write(f"{file_info['filename']}\\t")
                f.write(f"{file_info['size']}\\t")
                f.write(f"{file_info['status']}\\t")
                f.write(f"{file_info.get('duration', 'N/A')}\\n")


class SingleFileProgressMonitor:
    """Progress monitor for single file uploads."""
    
    def __init__(self, file_entry: FileEntry, token_file: Path):
        self.file_entry = file_entry
        self.token_file = token_file
        self.monitoring = False
    
    def start_monitoring(self, file_entry: FileEntry) -> None:
        """Start monitoring upload progress."""
        self.monitoring = True
        # In real implementation, this would parse gdc-client logs
        # or use API to get progress information
    
    def stop_monitoring(self) -> None:
        """Stop monitoring progress."""
        self.monitoring = False
    
    def get_progress(self) -> Optional[UploadProgress]:
        """Get current progress (simplified)."""
        # This would parse actual progress from gdc-client logs
        return None


# Example 3: API Parallel Uploader (parallel_api_upload.py replacement)

@register_uploader(UploaderType.API_PARALLEL)
class APIParallelPlugin(UploaderPlugin):
    """Plugin for parallel uploads using HTTP API."""
    
    def get_config(self) -> UploaderConfig:
        return UploaderConfig(
            name="API Parallel Uploader",
            uploader_type=UploaderType.API_PARALLEL,
            description="Uses HTTP API for parallel uploads without gdc-client",
            supported_features=[
                Features.PARALLEL_UPLOAD,
                Features.API_UPLOAD,
                Features.BATCH_UPLOAD,
                Features.PROGRESS_TRACKING,
                Features.RETRY_LOGIC
            ],
            priority=75,
            config_schema=ConfigSchema.create_schema(
                api_endpoint=ConfigSchema.string_property(
                    "GDC API endpoint URL",
                    default="https://api.gdc.cancer.gov"
                ),
                chunk_size=ConfigSchema.integer_property(
                    "Upload chunk size in MB",
                    default=50,
                    minimum=1,
                    maximum=500
                )
            )
        )
    
    def create_uploader(self, **kwargs) -> BaseUploader:
        return APIParallelUploader(**kwargs)
    
    def validate_environment(self) -> bool:
        # Only requires Python standard library
        return True
    
    def get_required_dependencies(self) -> List[str]:
        return []  # No external dependencies


class APIParallelUploader(BaseUploader):
    """Implementation using direct HTTP API calls."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_endpoint = kwargs.get('api_endpoint', 'https://api.gdc.cancer.gov')
        self.chunk_size = kwargs.get('chunk_size', 50) * 1024 * 1024  # Convert to bytes
    
    def discover_files(self) -> List[FileEntry]:
        """Discover files for API upload."""
        return list(StandardFileDiscovery().discover(self.base_directory, self.metadata))
    
    def validate_files(self, files: List[FileEntry]) -> List[FileEntry]:
        """Validate files and check API requirements."""
        validated = []
        for file_entry in files:
            if file_entry.path and file_entry.path.exists():
                file_entry.size = file_entry.path.stat().st_size
                # API uploads might have size restrictions
                if file_entry.size < 5 * 1024 * 1024 * 1024:  # 5GB limit example
                    validated.append(file_entry)
                else:
                    logger.warning(f"File too large for API upload: {file_entry.filename}")
            else:
                logger.warning(f"File not found: {file_entry.filename}")
        return validated
    
    def upload_file(self, file_entry: FileEntry) -> UploadResult:
        """Upload file using HTTP API."""
        # This is a simplified example - real implementation would use
        # requests or urllib to make actual API calls
        result = UploadResult(
            file_entry=file_entry,
            status=UploadStatus.PENDING,
            start_time=time.time()
        )
        
        try:
            # Simulate API upload
            logger.info(f"Uploading {file_entry.filename} via API")
            time.sleep(0.1)  # Simulate upload time
            
            result.status = UploadStatus.SUCCESS
            result.bytes_transferred = file_entry.size
            
        except Exception as e:
            result.status = UploadStatus.FAILED
            result.error_message = str(e)
        
        result.end_time = time.time()
        return result
    
    def upload_batch(self, files: List[FileEntry]) -> List[UploadResult]:
        """Upload files in parallel using thread pool."""
        if self.thread_count == 1:
            return [self.upload_file(f) for f in files]
        
        results = []
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            future_to_file = {
                executor.submit(self.upload_file, f): f for f in files
            }
            
            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)
                
                # Report progress
                if self._progress_callback:
                    progress = UploadProgress(
                        file_entry=result.file_entry,
                        bytes_transferred=result.bytes_transferred or 0,
                        total_bytes=result.file_entry.size or 0,
                        elapsed_time=result.duration or 0,
                        transfer_rate=0
                    )
                    self._report_progress(progress)
        
        return results
    
    def get_upload_command(self, file_entry: FileEntry) -> List[str]:
        """API uploader doesn't use commands."""
        return []
    
    def generate_report(self, results: List[UploadResult]) -> Dict[str, Any]:
        """Generate API upload report."""
        return {
            'api_endpoint': self.api_endpoint,
            'uploads': [
                {
                    'uuid': r.file_entry.uuid,
                    'filename': r.file_entry.filename,
                    'status': r.status.value,
                    'duration': r.duration,
                    'error': r.error_message
                }
                for r in results
            ]
        }
    
    def save_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Save API upload report as JSON."""
        if output_path.suffix == '.tsv':
            # Convert to TSV format for compatibility
            with open(output_path, 'w') as f:
                f.write("UUID\\tFILENAME\\tSTATUS\\n")
                for upload in report.get('uploads', []):
                    f.write(f"{upload['uuid']}\\t{upload['filename']}\\t{upload['status']}\\n")
        else:
            # Save as JSON
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)


# Example usage demonstrating the plugin system

def example_usage():
    """Demonstrate how to use the plugin system."""
    from src.gdc_uploader.core.plugins import UploaderRegistry
    
    # Get the registry
    registry = UploaderRegistry()
    
    # List available plugins
    print("Available uploaders:")
    for config in registry.list_plugins():
        print(f"  - {config.name} ({config.uploader_type.value})")
        print(f"    Features: {', '.join(config.supported_features)}")
    
    # Get the best uploader for parallel uploads
    best_type = registry.get_best_uploader([Features.PARALLEL_UPLOAD])
    if best_type:
        print(f"\\nBest uploader for parallel uploads: {best_type.value}")
    
    # Create an uploader instance
    metadata = {"test-uuid": {"file_name": "test.bam"}}
    uploader = registry.create_uploader(
        best_type,
        metadata=metadata,
        token_file=Path("token.txt"),
        base_directory=Path("/data"),
        thread_count=4
    )
    
    # Run the upload
    results = uploader.run()
    
    # Check results
    for result in results:
        print(f"{result.file_entry.filename}: {result.status.value}")


if __name__ == "__main__":
    example_usage()