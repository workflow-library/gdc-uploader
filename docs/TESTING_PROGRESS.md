# Testing Progress Bars and Progress Messages

This guide explains how to test progress tracking functionality in the GDC Uploader.

## Overview

Progress bars present unique testing challenges because they involve:
- Real-time updates during I/O operations
- External dependencies (tqdm library)
- Visual output that needs to be captured
- Timing-dependent behavior

## Testing Strategies

### 1. Mock the Progress Bar Library

The primary approach is to mock `tqdm` and capture its interactions:

```python
from unittest.mock import patch, MagicMock

progress_updates = []

with patch('gdc_uploader.upload.tqdm') as mock_tqdm:
    mock_pbar = MagicMock()
    mock_pbar.update = lambda n: progress_updates.append(n)
    mock_tqdm.return_value.__enter__.return_value = mock_pbar
    
    # Run upload code
    upload_file_with_progress(...)
    
    # Verify progress
    assert sum(progress_updates) == file_size
```

### 2. Test Progress Callbacks

Test the underlying callback mechanism:

```python
from gdc_uploader.utils import chunk_reader

callback_sizes = []
chunks = list(chunk_reader(
    file_obj,
    chunk_size=1000,
    callback=lambda size: callback_sizes.append(size)
))

assert sum(callback_sizes) == total_size
```

### 3. Capture CLI Output

Use Click's testing utilities to capture console output:

```python
from click.testing import CliRunner

runner = CliRunner()
result = runner.invoke(main, ['--file', 'test.txt'])

assert "Starting upload..." in result.output
assert "✓ Upload successful!" in result.output
```

### 4. Integration Testing

Test realistic scenarios with timing:

```python
def test_real_time_progress(tmp_path):
    progress_events = []
    start_time = time.time()
    
    def track_progress(size):
        progress_events.append({
            'size': size,
            'time': time.time() - start_time
        })
    
    # Verify progress happens over time
    for event in progress_events:
        assert event['time'] >= 0
```

## Key Testing Patterns

### Verify Total Progress

Always ensure the sum of progress updates equals the expected total:

```python
assert sum(progress_updates) == file_size
```

### Test Chunk Boundaries

Verify progress updates match chunk sizes:

```python
for update in progress_updates[:-1]:
    assert update == chunk_size
# Last chunk may be smaller
assert progress_updates[-1] <= chunk_size
```

### Test Error Handling

Ensure progress bars are properly closed on errors:

```python
mock_pbar.__exit__ = MagicMock()

with pytest.raises(Exception):
    upload_file_with_progress(...)

mock_pbar.__exit__.assert_called()
```

### Test Different Scenarios

- Empty files
- Large files
- Various chunk sizes
- Network interruptions
- Concurrent uploads

## Running Progress Tests

```bash
# Run all progress tests
pytest tests/unit/test_upload.py -v

# Run with coverage
pytest tests/unit/test_upload.py --cov=gdc_uploader.upload

# Run integration tests
pytest tests/integration/test_progress_integration.py -v
```

## Visual Testing

For manual verification of progress display:

```python
# Create a test script
from gdc_uploader import upload_file_with_progress
from pathlib import Path

# Create large test file
test_file = Path("large_test.bin")
test_file.write_bytes(b"X" * (10 * 1024 * 1024))  # 10MB

# Run with real progress bar
upload_file_with_progress(
    test_file,
    "test-id",
    "test-token",
    chunk_size=1024 * 100  # 100KB chunks
)
```

## Common Issues

1. **Progress bar not updating**: Check that the data generator is being consumed
2. **Incorrect totals**: Verify file size calculation is correct
3. **Missing updates**: Ensure callbacks are properly wired
4. **Test flakiness**: Add proper synchronization for concurrent tests

## Best Practices

1. Always mock external HTTP calls
2. Use deterministic test data sizes
3. Test both success and failure scenarios
4. Verify progress bar cleanup in all code paths
5. Test with various chunk sizes to ensure correctness