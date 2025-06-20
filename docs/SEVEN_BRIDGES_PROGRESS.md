# Progress Display on Seven Bridges Platform

## Potential Issues

1. **Terminal Detection**: `tqdm` auto-detects if it's running in a terminal. In SBP's execution environment, it might fall back to basic output.

2. **Output Buffering**: SBP might buffer stdout, causing progress updates to appear all at once instead of real-time.

3. **ANSI Escape Codes**: The progress bar uses terminal control codes that might not render correctly in SBP's logs.

4. **Log Aggregation**: SBP aggregates logs, which might interfere with carriage returns (`\r`) used by progress bars.

## Solutions

### 1. Force Simple Progress Output

Create an environment-aware progress reporter:

```python
import os
import sys

def get_progress_callback(total_size, desc="Uploading"):
    """Get appropriate progress callback for the environment."""
    
    # Check if running in SBP or other non-interactive environment
    is_sbp = os.environ.get('SBP_TASK_ID') is not None
    is_cwl = os.environ.get('CWL_RUNTIME') is not None
    is_interactive = sys.stdout.isatty()
    
    if is_sbp or is_cwl or not is_interactive:
        # Use simple percentage-based progress for SBP
        return SimpleProgress(total_size, desc)
    else:
        # Use tqdm for interactive terminals
        from tqdm import tqdm
        return tqdm(total=total_size, unit='B', unit_scale=True, desc=desc)

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
        return self
    
    def __exit__(self, *args):
        if self.last_percent < 100:
            print(f"{self.desc}: 100% ({self.total:,}/{self.total:,} bytes)")
            sys.stdout.flush()
```

### 2. Add Progress Mode Option

Add a CLI flag to control progress display:

```python
@click.command()
@click.option('--progress-mode', 
              type=click.Choice(['auto', 'simple', 'bar', 'none']),
              default='auto',
              help='Progress display mode')
def main(manifest, file, token, progress_mode):
    """Upload file with configurable progress display."""
    
    if progress_mode == 'auto':
        # Auto-detect environment
        use_simple = not sys.stdout.isatty()
    elif progress_mode == 'simple':
        use_simple = True
    elif progress_mode == 'bar':
        use_simple = False
    else:  # none
        use_simple = None
```

### 3. CWL-Specific Modifications

Update the CWL to set environment variables:

```yaml
requirements:
  - class: EnvVarRequirement
    envDef:
      PROGRESS_MODE: simple
      CWL_RUNTIME: "true"
```

### 4. Testing Script for SBP

Create a test script to verify progress display:

```python
#!/usr/bin/env python3
"""Test progress display in different environments."""

import os
import sys
import time

print(f"Environment checks:")
print(f"- Is TTY: {sys.stdout.isatty()}")
print(f"- SBP_TASK_ID: {os.environ.get('SBP_TASK_ID', 'Not set')}")
print(f"- TERM: {os.environ.get('TERM', 'Not set')}")
print(f"- Stdout encoding: {sys.stdout.encoding}")

print("\nTesting progress displays:")

# Test 1: Simple percentage
print("\n1. Simple percentage progress:")
for i in range(0, 101, 10):
    print(f"Progress: {i}%")
    sys.stdout.flush()
    time.sleep(0.1)

# Test 2: Carriage return progress
print("\n2. Carriage return progress:")
for i in range(0, 101, 10):
    print(f"\rProgress: {i}%", end='')
    sys.stdout.flush()
    time.sleep(0.1)
print()  # New line

# Test 3: tqdm
try:
    from tqdm import tqdm
    print("\n3. tqdm progress:")
    for i in tqdm(range(10), desc="Testing"):
        time.sleep(0.1)
except Exception as e:
    print(f"tqdm failed: {e}")
```

## Recommended Approach

1. **Default to simple progress in CWL environments**
2. **Use 10% increment logging to avoid log spam**
3. **Always flush stdout after progress updates**
4. **Provide --progress-mode flag for manual override**
5. **Test in actual SBP environment before production use**

## Example Implementation

```python
def upload_file_with_progress(file_path, file_id, token, chunk_size=8192, progress_mode='auto'):
    """Upload file with environment-appropriate progress display."""
    
    file_size = file_path.stat().st_size
    
    # Determine progress display mode
    if progress_mode == 'none':
        progress = None
    elif progress_mode == 'simple' or (progress_mode == 'auto' and not sys.stdout.isatty()):
        progress = SimpleProgress(file_size, "Uploading")
    else:
        from tqdm import tqdm
        progress = tqdm(total=file_size, unit='B', unit_scale=True, desc="Uploading")
    
    # ... rest of upload code
```