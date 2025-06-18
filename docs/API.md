# GDC Uploader Python API Documentation

This document provides detailed information about using the GDC Uploader as a Python library.

## Installation

```bash
pip install gdc-uploader
```

## Core Classes

### GDCUploader

The main class for uploading files with file discovery capabilities.

```python
from gdc_uploader import GDCUploader
from pathlib import Path

uploader = GDCUploader(
    metadata_file=Path("metadata.json"),
    token_file=Path("token.txt"),
    threads=4,
    retries=3
)
```

#### Parameters

- `metadata_file` (Path): Path to GDC metadata JSON file
- `token_file` (Path): Path to GDC authentication token file
- `threads` (int): Number of parallel upload threads (default: 4)
- `retries` (int): Number of retry attempts for failed uploads (default: 3)

#### Methods

##### `run(files_dir: Path) -> None`

Executes the upload process.

```python
uploader.run(files_dir=Path("/data/sequencing/"))
```

##### `load_metadata() -> List[Dict[str, str]]`

Loads and parses the metadata file.

```python
metadata = uploader.load_metadata()
for item in metadata:
    print(f"File: {item['file_name']}, UUID: {item['id']}")
```

##### `find_file(filename: str, files_dir: Path) -> Optional[Path]`

Searches for a file in various standard locations.

```python
file_path = uploader.find_file("sample.fastq.gz", Path("/data"))
if file_path:
    print(f"Found at: {file_path}")
```

### GDCDirectUploader

Simplified uploader for when file paths are specified in metadata.

```python
from gdc_uploader.direct_upload import GDCDirectUploader

uploader = GDCDirectUploader(
    metadata_file=Path("metadata.json"),
    token_file=Path("token.txt"),
    threads=4,
    retries=3
)
uploader.run()
```

### GDCSingleUploader

For uploading individual files.

```python
from gdc_uploader.upload_single import GDCSingleUploader

uploader = GDCSingleUploader(
    metadata_file=Path("metadata.json"),
    token_file=Path("token.txt"),
    retries=3
)
uploader.run(target_file=Path("sample.bam"))
```

## Utility Functions

### yaml_to_json

Convert YAML metadata to JSON format.

```python
from gdc_uploader.utils import yaml_to_json

success = yaml_to_json(
    yaml_file="metadata.yaml",
    json_file="metadata.json",
    pretty=True,
    validate=True
)
```

#### Parameters

- `yaml_file` (Union[str, Path]): Input YAML file or '-' for stdin
- `json_file` (Optional[Union[str, Path]]): Output JSON file or '-' for stdout
- `pretty` (bool): Pretty-print JSON output (default: True)
- `validate` (bool): Validate the converted data structure (default: False)

### filter_json

Filter JSON array by field values.

```python
from gdc_uploader.utils import filter_json

success = filter_json(
    input_file="all_files.json",
    output_file="filtered_files.json",
    filter_field="project_id",
    filter_values=["TCGA-LUAD", "TCGA-LUSC"]
)
```

### split_json

Split JSON array into individual files.

```python
from gdc_uploader.utils import split_json

success = split_json(
    input_file="metadata.json",
    output_dir="split_files/",
    split_field="id",
    prefix="file"
)
```

## Examples

### Example 1: Basic Upload

```python
from pathlib import Path
from gdc_uploader import GDCUploader

# Setup
metadata_file = Path("metadata.json")
token_file = Path("token.txt")
files_dir = Path("/data/sequencing/")

# Create uploader
uploader = GDCUploader(
    metadata_file=metadata_file,
    token_file=token_file,
    threads=8,
    retries=3
)

# Run upload
try:
    uploader.run(files_dir)
except Exception as e:
    print(f"Upload failed: {e}")
```

### Example 2: Custom File Search

```python
from pathlib import Path
from gdc_uploader import GDCUploader

class CustomUploader(GDCUploader):
    def find_file(self, filename: str, files_dir: Path) -> Optional[Path]:
        """Custom file search logic."""
        # First try the default search
        result = super().find_file(filename, files_dir)
        if result:
            return result
            
        # Try custom locations
        custom_paths = [
            files_dir / "custom" / filename,
            files_dir / "archive" / filename,
        ]
        
        for path in custom_paths:
            if path.exists():
                return path
                
        return None

# Use custom uploader
uploader = CustomUploader(metadata_file, token_file)
uploader.run(files_dir)
```

### Example 3: Progress Monitoring

```python
import logging
from pathlib import Path
from gdc_uploader import GDCUploader

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create uploader with custom logger
uploader = GDCUploader(metadata_file, token_file)

# Monitor progress
uploader.run(files_dir)
```

### Example 4: Batch Processing

```python
from pathlib import Path
from gdc_uploader import GDCUploader
from gdc_uploader.utils import split_json

# Split large metadata file
split_json(
    input_file="large_metadata.json",
    output_dir="batch_files/",
    split_field="project_id"
)

# Process each batch
batch_dir = Path("batch_files/")
for batch_file in batch_dir.glob("*.json"):
    print(f"Processing batch: {batch_file}")
    
    uploader = GDCUploader(
        metadata_file=batch_file,
        token_file=Path("token.txt"),
        threads=4
    )
    
    try:
        uploader.run(Path("/data/"))
    except Exception as e:
        print(f"Batch {batch_file} failed: {e}")
        continue
```

## Error Handling

The library uses standard Python exceptions:

```python
try:
    uploader = GDCUploader(metadata_file, token_file)
    uploader.run(files_dir)
except FileNotFoundError as e:
    print(f"File not found: {e}")
except json.JSONDecodeError as e:
    print(f"Invalid JSON in metadata: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Logging

The library uses Python's standard logging module:

```python
import logging

# Enable debug logging
logging.getLogger('gdc_uploader').setLevel(logging.DEBUG)

# Log to file
handler = logging.FileHandler('upload.log')
logging.getLogger('gdc_uploader').addHandler(handler)
```

## Thread Safety

The uploader uses ThreadPoolExecutor for concurrent uploads. Each file upload is independent and thread-safe.

## Performance Tips

1. **Optimal Thread Count**: Use 4-8 threads for best performance
2. **File Organization**: Keep files in standard directories (fastq/, uBam/) for faster discovery
3. **Batch Processing**: Split large uploads into smaller batches
4. **Network**: Ensure stable, high-bandwidth connection to GDC

## Integration with Other Tools

### Pandas Integration

```python
import pandas as pd
from gdc_uploader import GDCUploader

# Load metadata from CSV
df = pd.read_csv("file_list.csv")
metadata = df.to_dict('records')

# Save as JSON
with open("metadata.json", "w") as f:
    json.dump(metadata, f)

# Upload
uploader = GDCUploader("metadata.json", "token.txt")
uploader.run("/data/")
```

### Async Wrapper

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from gdc_uploader import GDCUploader

async def async_upload(metadata_file, token_file, files_dir):
    loop = asyncio.get_event_loop()
    uploader = GDCUploader(metadata_file, token_file)
    
    # Run in thread pool
    with ThreadPoolExecutor() as executor:
        await loop.run_in_executor(executor, uploader.run, files_dir)

# Use in async context
asyncio.run(async_upload("metadata.json", "token.txt", "/data/"))
```