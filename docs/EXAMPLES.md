# GDC Uploader Examples

This document provides practical examples for common use cases.

## Basic Examples

### 1. Simple Upload

Upload FASTQ files from a sequencing run:

```bash
# Prepare token
echo "your-gdc-token" > token.txt

# Create metadata
cat > metadata.json << EOF
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample1_R1.fastq.gz",
    "project_id": "TCGA-LUAD"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "file_name": "sample1_R2.fastq.gz",
    "project_id": "TCGA-LUAD"
  }
]
EOF

# Upload
gdc-upload -m metadata.json -t token.txt /data/sequencing/
```

### 2. Parallel Upload with Custom Threads

Upload large BAM files with 8 parallel threads:

```bash
gdc-upload -m metadata.json -t token.txt -j 8 /data/aligned/
```

### 3. Upload with Retries

Upload with 5 retry attempts for unreliable connections:

```bash
gdc-upload -m metadata.json -t token.txt -r 5 /data/
```

## Advanced Examples

### 4. Batch Processing by Project

Split uploads by project ID:

```python
#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict
import subprocess

# Load metadata
with open('all_files.json') as f:
    all_files = json.load(f)

# Group by project
by_project = defaultdict(list)
for file_info in all_files:
    by_project[file_info['project_id']].append(file_info)

# Upload each project separately
for project_id, files in by_project.items():
    print(f"Uploading {len(files)} files for project {project_id}")
    
    # Create project-specific metadata
    metadata_file = f"metadata_{project_id}.json"
    with open(metadata_file, 'w') as f:
        json.dump(files, f, indent=2)
    
    # Upload
    cmd = [
        'gdc-upload',
        '-m', metadata_file,
        '-t', 'token.txt',
        '-j', '4',
        '/data/'
    ]
    subprocess.run(cmd)
```

### 5. Upload with Pre-validation

Validate files exist before starting upload:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def validate_files(metadata_file, data_dir):
    """Validate all files exist before upload."""
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    missing_files = []
    data_path = Path(data_dir)
    
    for item in metadata:
        filename = item['file_name']
        
        # Search in standard locations
        found = False
        for subdir in ['fastq', 'uBam', 'sequence-files', '']:
            if subdir:
                path = data_path / subdir / filename
            else:
                path = data_path / filename
            
            if path.exists():
                found = True
                print(f"✓ Found: {filename} at {path}")
                break
        
        if not found:
            missing_files.append(filename)
            print(f"✗ Missing: {filename}")
    
    if missing_files:
        print(f"\nError: {len(missing_files)} files not found")
        return False
    
    print(f"\nAll {len(metadata)} files found!")
    return True

# Validate then upload
if validate_files('metadata.json', '/data/'):
    import subprocess
    subprocess.run([
        'gdc-upload',
        '-m', 'metadata.json',
        '-t', 'token.txt',
        '/data/'
    ])
else:
    sys.exit(1)
```

### 6. Resume Failed Uploads

Create a script to retry only failed uploads:

```python
#!/usr/bin/env python3
import pandas as pd
import json
import subprocess

# Read upload report
df = pd.read_csv('upload-report.tsv', sep='\t')

# Get failed files
failed = df[df['STATUS'] == 'FAILED']

if len(failed) == 0:
    print("No failed uploads found!")
    exit(0)

print(f"Found {len(failed)} failed uploads")

# Load original metadata
with open('metadata.json') as f:
    all_metadata = json.load(f)

# Create metadata for failed files only
failed_metadata = []
failed_files = set(failed['FILENAME'].values)

for item in all_metadata:
    if item['file_name'] in failed_files:
        failed_metadata.append(item)

# Save failed metadata
with open('retry_metadata.json', 'w') as f:
    json.dump(failed_metadata, f, indent=2)

# Retry upload with more retries
print("Retrying failed uploads...")
subprocess.run([
    'gdc-upload',
    '-m', 'retry_metadata.json',
    '-t', 'token.txt',
    '-r', '5',
    '-j', '2',  # Fewer threads for reliability
    '/data/'
])
```

### 7. Upload with Progress Notification

Send notifications on upload completion:

```python
#!/usr/bin/env python3
import subprocess
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

def send_notification(subject, body):
    """Send email notification."""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'uploader@example.com'
    msg['To'] = 'researcher@example.com'
    
    # Configure your SMTP server
    with smtplib.SMTP('localhost') as s:
        s.send_message(msg)

# Start upload
start_time = datetime.now()
print(f"Starting upload at {start_time}")

result = subprocess.run([
    'gdc-upload',
    '-m', 'metadata.json',
    '-t', 'token.txt',
    '-j', '4',
    '/data/'
], capture_output=True, text=True)

end_time = datetime.now()
duration = end_time - start_time

# Check results
if result.returncode == 0:
    subject = "GDC Upload Completed Successfully"
    body = f"""
Upload completed successfully!

Start time: {start_time}
End time: {end_time}
Duration: {duration}

Check upload-report.tsv for details.
"""
else:
    subject = "GDC Upload Failed"
    body = f"""
Upload failed with errors.

Start time: {start_time}
End time: {end_time}
Duration: {duration}

Error output:
{result.stderr}
"""

send_notification(subject, body)
```

## Docker Examples

### 8. Docker with Volume Mounts

```bash
# Basic Docker usage
docker run -it --rm \
  -v $(pwd)/data:/data:ro \
  -v $(pwd)/metadata.json:/work/metadata.json:ro \
  -v $(pwd)/token.txt:/work/token.txt:ro \
  -v $(pwd)/output:/output \
  -w /output \
  ghcr.io/open-workflow-library/gdc-uploader:latest \
  gdc-upload -m /work/metadata.json -t /work/token.txt /data
```

### 9. Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  gdc-uploader:
    image: ghcr.io/open-workflow-library/gdc-uploader:latest
    volumes:
      - ./data:/data:ro
      - ./metadata:/metadata:ro
      - ./output:/output
    working_dir: /output
    command: >
      gdc-upload
      -m /metadata/metadata.json
      -t /metadata/token.txt
      -j 4
      /data
    environment:
      - LOG_LEVEL=INFO
```

Run with:
```bash
docker-compose up
```

## CWL Examples

### 10. Basic CWL Usage

```bash
# Using cwltool
cwltool \
  --outdir ./cwl-output \
  cwl/gdc_upload.cwl \
  --metadata_file metadata.json \
  --files_directory /data/sequencing \
  --token_file token.txt \
  --thread_count 4 \
  --retry_count 3
```

### 11. CWL with Custom Parameters

Create a job file `upload-job.yml`:

```yaml
metadata_file:
  class: File
  path: ./metadata.json

files_directory:
  class: Directory
  path: /data/sequencing

token_file:
  class: File
  path: ./token.txt

thread_count: 8
retry_count: 5
```

Run with:
```bash
cwltool --outdir ./output cwl/gdc_upload.cwl upload-job.yml
```

## YAML to JSON Examples

### 12. Convert YAML Metadata

Create YAML metadata `metadata.yaml`:

```yaml
- id: 550e8400-e29b-41d4-a716-446655440000
  file_name: sample1.fastq.gz
  project_id: TCGA-LUAD
  experimental_strategy: RNA-Seq
  data_type: Unaligned Reads
  
- id: 550e8400-e29b-41d4-a716-446655440001
  file_name: sample2.fastq.gz
  project_id: TCGA-LUAD
  experimental_strategy: RNA-Seq
  data_type: Unaligned Reads
```

Convert to JSON:
```bash
gdc-yaml2json metadata.yaml metadata.json --validate
```

### 13. Batch YAML Conversion

Convert multiple YAML files:

```bash
#!/bin/bash
for yaml_file in metadata/*.yaml; do
    json_file="${yaml_file%.yaml}.json"
    echo "Converting $yaml_file to $json_file"
    gdc-yaml2json "$yaml_file" "$json_file" --validate
done
```

## Integration Examples

### 14. Nextflow Integration

Create a Nextflow process:

```groovy
process uploadToGDC {
    input:
    path metadata
    path token
    path data_dir
    
    output:
    path "upload-report.tsv"
    
    script:
    """
    gdc-upload \
        -m ${metadata} \
        -t ${token} \
        -j ${params.threads} \
        ${data_dir}
    """
}
```

### 15. Snakemake Integration

Add to `Snakefile`:

```python
rule upload_to_gdc:
    input:
        metadata="metadata.json",
        token="token.txt",
        data_dir="data/"
    output:
        report="upload-report.tsv"
    threads: 4
    shell:
        """
        gdc-upload \
            -m {input.metadata} \
            -t {input.token} \
            -j {threads} \
            {input.data_dir}
        """
```

## Monitoring Examples

### 16. Real-time Progress Monitoring

```python
#!/usr/bin/env python3
import subprocess
import threading
import time
from pathlib import Path

def monitor_uploads():
    """Monitor upload progress in real-time."""
    while not stop_monitoring.is_set():
        # Count log files
        logs = list(Path('.').glob('upload-*.log'))
        print(f"\rActive uploads: {len(logs)}", end='', flush=True)
        time.sleep(1)

# Start monitoring in background
stop_monitoring = threading.Event()
monitor_thread = threading.Thread(target=monitor_uploads)
monitor_thread.start()

# Run upload
try:
    subprocess.run([
        'gdc-upload',
        '-m', 'metadata.json',
        '-t', 'token.txt',
        '/data/'
    ])
finally:
    stop_monitoring.set()
    monitor_thread.join()
    print("\nUpload completed!")
```

### 17. Generate Upload Summary

```python
#!/usr/bin/env python3
import pandas as pd
from datetime import datetime

# Read upload report
df = pd.read_csv('upload-report.tsv', sep='\t')

# Generate summary
total = len(df)
successful = len(df[df['STATUS'] == 'SUCCESS'])
failed = len(df[df['STATUS'] == 'FAILED'])

print(f"""
Upload Summary Report
Generated: {datetime.now()}
{'=' * 40}
Total files:      {total}
Successful:       {successful} ({successful/total*100:.1f}%)
Failed:           {failed} ({failed/total*100:.1f}%)
{'=' * 40}
""")

if failed > 0:
    print("Failed uploads:")
    for _, row in df[df['STATUS'] == 'FAILED'].iterrows():
        print(f"  - {row['FILENAME']} (UUID: {row['UUID']})")
```