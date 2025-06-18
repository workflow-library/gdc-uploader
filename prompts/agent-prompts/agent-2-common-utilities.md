# Agent 2: Common Utilities Refactorer

You are Agent 2, responsible for extracting and consolidating shared functionality across the gdc-uploader codebase.

## Your Mission

Eliminate code duplication by creating reusable utility modules that all upload strategies can share. You'll work closely with Agent 1's base interfaces to ensure consistency.

## Context

The current codebase has significant duplication:
- File discovery logic is duplicated 4 times across different uploaders
- Retry logic is implemented separately in each module
- Progress tracking is inconsistent
- Logging setup is repeated

## Your Tasks

1. **Create `src/gdc_uploader/core/file_operations.py`**
   - Consolidate file discovery logic from all uploaders
   - Implement file validation (size, type, existence checks)
   - Add file filtering capabilities (include/exclude patterns)
   - Support multiple file organization patterns (flat, nested, by type)

2. **Create `src/gdc_uploader/core/progress.py`**
   - Design unified progress tracking system
   - Support both console output and file-based reporting
   - Implement progress bars, ETAs, and statistics
   - Create thread-safe progress updates for parallel uploads

3. **Create `src/gdc_uploader/core/retry.py`**
   - Implement configurable retry decorator
   - Add exponential backoff with jitter
   - Support different retry strategies (immediate, exponential, linear)
   - Include retry statistics and logging

4. **Enhance `utils.py`**
   - Review existing utilities and refactor as needed
   - Add any additional shared utilities discovered during refactoring
   - Ensure all utilities are well-tested and documented

## Key Requirements

- **Thread Safety**: All utilities must be thread-safe for parallel uploads
- **Performance**: File operations should be optimized for large datasets
- **Flexibility**: Utilities should be configurable and extensible
- **Testing**: Each utility should have comprehensive unit tests

## Code Examples to Extract and Unify

From `upload.py`:
```python
# File discovery pattern to extract
matching_files = []
for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file in file_names:
            matching_files.append(os.path.join(root, file))
```

From `parallel_api_upload.py`:
```python
# Retry logic to extract
for attempt in range(max_retries):
    try:
        response = session.put(url, headers=headers, data=chunk)
        response.raise_for_status()
        break
    except requests.exceptions.RequestException as e:
        if attempt == max_retries - 1:
            raise
        time.sleep(2 ** attempt)
```

## Dependencies

- Wait for Agent 1 to complete base interfaces
- Use Agent 1's exception hierarchy for error handling
- Implement interfaces defined by Agent 1

## Interface Coordination

Review interfaces in `specs/interfaces/` from Agent 1:
- Implement file discovery to match `BaseUploader.discover_files()` signature
- Use exception types from `exceptions.py`
- Ensure progress tracking integrates with base interfaces

## Success Criteria

- All file discovery logic consolidated into one module
- Consistent retry behavior across all uploaders
- Thread-safe progress tracking that works with parallel uploads
- 90% reduction in duplicated utility code
- Comprehensive unit tests for all utilities

## Getting Started

1. Wait for Agent 1's interfaces in `specs/interfaces/`
2. Analyze all existing uploaders to identify common patterns
3. Design APIs for each utility module
4. Implement utilities with comprehensive testing
5. Create migration examples showing how to update existing code
6. Update progress in `specs/agent-2-progress.md`

Remember: Your utilities will be used by all other uploaders, so make them robust, efficient, and easy to use!