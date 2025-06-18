"""Migration examples showing how to update existing code to use new utility modules.

This file demonstrates how to refactor duplicated code patterns found in the
original shell scripts to use the new Python utility modules.
"""

# ============================================================================
# EXAMPLE 1: File Discovery Migration
# ============================================================================

# BEFORE: Duplicated file discovery logic in shell scripts
"""
# From gdc_upload.sh (lines 119-138)
for subdir in "fastq" "uBam" "sequence-files" ""; do
    if [[ -n "$subdir" ]]; then
        test_path="$files_dir/$subdir/$filename"
    else
        test_path="$files_dir/$filename"
    fi
    
    if [[ -f "$test_path" ]]; then
        found_file="$test_path"
        break
    fi
done

if [[ -z "$found_file" ]]; then
    found_file=$(find "$files_dir" -name "$filename" -type f 2>/dev/null | head -1)
fi
"""

# AFTER: Using StandardFileDiscoveryStrategy
from pathlib import Path
from gdc_uploader.core.file_operations import (
    StandardFileDiscoveryStrategy,
    FileSearchConfig
)

def migrate_file_discovery():
    """Example of migrating file discovery logic."""
    # Configure search behavior
    config = FileSearchConfig(
        subdirectories=["fastq", "uBam", "sequence-files"],
        recursive=True,
        require_all_files=True
    )
    
    # Create discovery strategy
    strategy = StandardFileDiscoveryStrategy(config)
    
    # Discover files based on metadata
    base_dir = Path("/path/to/files")
    metadata = {
        "files": [
            {"uuid": "123", "filename": "sample1.fastq"},
            {"uuid": "456", "filename": "sample2.fastq"}
        ]
    }
    
    # This replaces the entire shell loop
    for file_entry in strategy.discover(base_dir, metadata):
        print(f"Found: {file_entry.filename} at {file_entry.path}")


# ============================================================================
# EXAMPLE 2: Progress Tracking Migration
# ============================================================================

# BEFORE: Basic echo statements for progress
"""
echo "Starting upload for $filename (UUID: $uuid)"
echo "Upload completed for $filename"
echo "Failed to upload $filename after $attempts attempts"
"""

# AFTER: Using ThreadSafeProgressTracker
from gdc_uploader.core.progress import (
    ThreadSafeProgressTracker,
    ProgressReporter,
    progress_tracking
)
from gdc_uploader.core.base_uploader import FileEntry

def migrate_progress_tracking():
    """Example of migrating progress tracking."""
    files = [
        FileEntry(uuid="123", filename="sample1.fastq", size=1024*1024*100),
        FileEntry(uuid="456", filename="sample2.fastq", size=1024*1024*200)
    ]
    
    # Simple progress tracking with context manager
    with progress_tracking(files, output_format="human") as tracker:
        for file_entry in files:
            # Start upload
            tracker.mark_file_started(file_entry.uuid)
            
            # Simulate upload with progress updates
            for i in range(0, file_entry.size, 1024*1024*10):
                tracker.update_file_progress(
                    file_entry.uuid,
                    transferred_bytes=i,
                    total_bytes=file_entry.size
                )
                
            # Mark complete
            tracker.mark_file_completed(file_entry.uuid, success=True)


# ============================================================================
# EXAMPLE 3: Retry Logic Migration
# ============================================================================

# BEFORE: Manual retry loops in shell
"""
for attempt in $(seq 1 $max_retries); do
    if upload_file "$file"; then
        echo "Success"
        break
    else
        if [ $attempt -lt $max_retries ]; then
            sleep $((2 ** attempt))
        fi
    fi
done
"""

# AFTER: Using retry decorator
from gdc_uploader.core.retry import retry, RetryConfig, RetryStrategy
import requests

# Simple retry with decorator
@retry(max_attempts=3, strategy=RetryStrategy.EXPONENTIAL)
def upload_file_simple(file_path: str) -> bool:
    """Upload file with automatic retry."""
    response = requests.post("https://api.example.com/upload", 
                           files={"file": open(file_path, "rb")})
    response.raise_for_status()
    return True

# Advanced retry with custom configuration
def upload_file_advanced(file_path: str) -> bool:
    """Upload file with advanced retry configuration."""
    config = RetryConfig(
        max_attempts=5,
        strategy=RetryStrategy.EXPONENTIAL,
        initial_delay=2.0,
        backoff_base=2.0,
        retry_http_codes=[408, 429, 500, 502, 503, 504],
        on_retry_callback=lambda exc, attempt: 
            print(f"Retry {attempt} due to: {exc}")
    )
    
    @retry(config)
    def _do_upload():
        response = requests.post("https://api.example.com/upload",
                               files={"file": open(file_path, "rb")})
        response.raise_for_status()
        return response.json()
    
    return _do_upload()


# ============================================================================
# EXAMPLE 4: Parallel Upload Migration
# ============================================================================

# BEFORE: Using GNU parallel in shell
"""
export -f upload_single_file
cat "$upload_list" | parallel -j $thread_count upload_single_file
"""

# AFTER: Using Python's concurrent.futures with progress tracking
from concurrent.futures import ThreadPoolExecutor, as_completed
from gdc_uploader.core.progress import ThreadSafeProgressTracker
from gdc_uploader.core.retry import retry, RETRY_CONFIG_API_CALLS

class ParallelUploader:
    """Example of parallel upload implementation."""
    
    def __init__(self, thread_count: int = 4):
        self.thread_count = thread_count
        self.tracker = ThreadSafeProgressTracker()
        
    @retry(RETRY_CONFIG_API_CALLS)
    def upload_single_file(self, file_entry: FileEntry) -> bool:
        """Upload a single file with retry."""
        self.tracker.mark_file_started(file_entry.uuid)
        
        try:
            # Simulate upload
            import time
            time.sleep(1)  # Replace with actual upload logic
            
            self.tracker.mark_file_completed(file_entry.uuid, success=True)
            return True
            
        except Exception as e:
            self.tracker.mark_file_completed(
                file_entry.uuid, 
                success=False, 
                error=str(e)
            )
            raise
            
    def upload_parallel(self, files: List[FileEntry]) -> Dict[str, bool]:
        """Upload files in parallel."""
        self.tracker.start()
        self.tracker.initialize_files(files)
        
        results = {}
        
        try:
            with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
                # Submit all uploads
                future_to_file = {
                    executor.submit(self.upload_single_file, f): f
                    for f in files
                }
                
                # Process completed uploads
                for future in as_completed(future_to_file):
                    file_entry = future_to_file[future]
                    try:
                        success = future.result()
                        results[file_entry.uuid] = success
                    except Exception as e:
                        results[file_entry.uuid] = False
                        print(f"Failed to upload {file_entry.filename}: {e}")
                        
        finally:
            self.tracker.stop()
            
        return results


# ============================================================================
# EXAMPLE 5: Report Generation Migration
# ============================================================================

# BEFORE: Manual TSV generation in shell
"""
echo -e "uuid\tfilename\tpath\tstatus" > "$report_file"
echo -e "$uuid\t$filename\t$file_path\t$status" >> "$report_file"
"""

# AFTER: Using report generation utilities
from gdc_uploader.core.utils import generate_tsv_report, generate_json_report
from gdc_uploader.core.progress import create_upload_report
from pathlib import Path

def migrate_report_generation():
    """Example of migrating report generation."""
    # Collect results during upload
    results = []
    
    # Add upload results
    results.append({
        "uuid": "123",
        "filename": "sample1.fastq",
        "status": "SUCCESS",
        "size": 1024*1024*100,
        "duration": 45.2,
        "rate_mbps": 17.8
    })
    
    results.append({
        "uuid": "456", 
        "filename": "sample2.fastq",
        "status": "FAILED",
        "error": "Connection timeout"
    })
    
    # Generate TSV report (similar to shell output)
    generate_tsv_report(
        results,
        Path("upload-report.tsv"),
        columns=["uuid", "filename", "status", "error"]
    )
    
    # Generate JSON report with metadata
    generate_json_report(
        results,
        Path("upload-report.json"),
        metadata={
            "upload_date": "2024-01-01",
            "total_files": 2,
            "successful": 1,
            "failed": 1
        }
    )


# ============================================================================
# EXAMPLE 6: Complete Upload Workflow Migration
# ============================================================================

from gdc_uploader.core.utils import (
    load_metadata,
    validate_metadata_structure,
    load_token,
    check_system_requirements,
    setup_logging
)

class MigratedGDCUploader:
    """Complete example of migrated GDC uploader."""
    
    def __init__(self, metadata_path: str, token_path: str, base_dir: str,
                 thread_count: int = 4, retry_count: int = 3):
        """Initialize uploader with configuration."""
        # Setup logging
        setup_logging(log_level="INFO", log_file=Path("upload.log"))
        
        # Load and validate inputs
        self.metadata = load_metadata(metadata_path)
        validate_metadata_structure(self.metadata)
        self.token = load_token(token_path)
        self.base_dir = Path(base_dir)
        
        # Check system
        sys_info = check_system_requirements()
        print(f"System: {sys_info['platform']}, "
              f"CPUs: {sys_info['cpu_count']}, "
              f"Memory: {sys_info['memory_available_gb']}GB")
        
        # Initialize components
        self.file_discovery = StandardFileDiscoveryStrategy()
        self.progress_tracker = ThreadSafeProgressTracker()
        self.thread_count = thread_count
        self.retry_count = retry_count
        
    def run(self):
        """Run the complete upload workflow."""
        # 1. Discover files
        print("Discovering files...")
        files = list(self.file_discovery.discover(self.base_dir, self.metadata))
        print(f"Found {len(files)} files to upload")
        
        # 2. Upload with progress tracking
        with progress_tracking(files) as tracker:
            uploader = ParallelUploader(self.thread_count)
            results = uploader.upload_parallel(files)
            
        # 3. Generate reports
        print("Generating reports...")
        final_results = []
        for file_entry in files:
            final_results.append({
                "uuid": file_entry.uuid,
                "filename": file_entry.filename,
                "path": str(file_entry.path),
                "status": "SUCCESS" if results.get(file_entry.uuid) else "FAILED"
            })
            
        generate_tsv_report(final_results, Path("upload-report.tsv"))
        generate_json_report(final_results, Path("upload-report.json"))
        
        print("Upload complete!")
        

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Example 1: Simple file discovery
    print("=== File Discovery Example ===")
    migrate_file_discovery()
    
    # Example 2: Progress tracking
    print("\n=== Progress Tracking Example ===")
    migrate_progress_tracking()
    
    # Example 3: Report generation
    print("\n=== Report Generation Example ===")
    migrate_report_generation()
    
    # Example 4: Complete workflow
    print("\n=== Complete Workflow Example ===")
    # uploader = MigratedGDCUploader(
    #     metadata_path="metadata.json",
    #     token_path="token.txt",
    #     base_dir="/data/files",
    #     thread_count=4
    # )
    # uploader.run()