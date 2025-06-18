# Agent 3: Upload Strategy Implementer

You are Agent 3, responsible for refactoring all upload modules to use the common base classes and utilities created by Agents 1 and 2.

## Your Mission

Refactor the four existing upload implementations to inherit from the base uploader class and use shared utilities, eliminating code duplication while preserving all functionality.

## Context

Current upload implementations to refactor:
- `upload.py` - Main parallel upload using gdc-client (237 lines)
- `parallel_api_upload.py` - HTTP API-based parallel uploads (452 lines)
- `spot_upload.py` - Spot instance resilient uploads (357 lines)
- `upload_single.py` - Single file uploads (279 lines)

## Your Tasks

1. **Refactor `upload.py`**
   - Inherit from `BaseUploader`
   - Use shared file discovery from `file_operations.py`
   - Implement retry logic using `retry.py` decorators
   - Use unified progress tracking from `progress.py`

2. **Refactor `parallel_api_upload.py`**
   - Inherit from `BaseUploader`
   - Extract HTTP client logic to use Agent 6's API client
   - Use shared utilities for all common operations
   - Preserve parallel upload performance characteristics

3. **Refactor `spot_upload.py`**
   - Inherit from `BaseUploader`
   - Implement proper resilience patterns for spot instances
   - Use shared retry logic with spot-specific configurations
   - Add proper cleanup on spot termination

4. **Refactor `upload_single.py`**
   - Inherit from `BaseUploader`
   - Simplify as the most basic strategy
   - Reuse all common utilities

5. **Create `src/gdc_uploader/strategies/` directory**
   - Move refactored uploaders into strategies directory
   - Create `__init__.py` with strategy registry
   - Implement strategy selection logic

## Refactoring Guidelines

### Before (example from current code):
```python
# upload.py - duplicated file discovery
for common_dir in ['fastq', 'uBam', 'sequence-files']:
    dir_path = os.path.join(search_dir, common_dir)
    if os.path.isdir(dir_path):
        for file_name in file_names:
            # ... file search logic
```

### After (using shared utilities):
```python
from gdc_uploader.core.base_uploader import BaseUploader
from gdc_uploader.core.file_operations import discover_files

class GdcClientUploader(BaseUploader):
    def discover_files(self, directory: Path, metadata: Dict[str, Any]) -> List[Path]:
        return discover_files(
            directory=directory,
            file_patterns=self._extract_file_patterns(metadata),
            search_subdirs=['fastq', 'uBam', 'sequence-files']
        )
```

## Strategy Pattern Implementation

```python
# src/gdc_uploader/strategies/__init__.py
from typing import Dict, Type
from gdc_uploader.core.base_uploader import BaseUploader

UPLOAD_STRATEGIES: Dict[str, Type[BaseUploader]] = {
    'gdc-client': GdcClientUploader,
    'parallel-api': ParallelApiUploader,
    'spot-resilient': SpotUploader,
    'single-file': SingleFileUploader,
}

def get_uploader(strategy: str, **kwargs) -> BaseUploader:
    """Factory function to get appropriate uploader."""
    if strategy not in UPLOAD_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")
    return UPLOAD_STRATEGIES[strategy](**kwargs)
```

## Dependencies

- **Must wait for Agent 1**: Need base classes and interfaces
- **Must wait for Agent 2**: Need shared utilities
- **Coordinate with Agent 6**: Use API client for HTTP operations

## Backward Compatibility

- Preserve all existing command-line interfaces
- Maintain same output formats
- Keep all existing functionality
- Add compatibility layer if needed

## Success Criteria

- All four uploaders inherit from `BaseUploader`
- Zero code duplication between strategies
- All tests pass with refactored code
- Performance characteristics maintained or improved
- Clean separation between strategies

## Getting Started

1. Wait for Agents 1 and 2 to complete their work
2. Study the base interfaces and available utilities
3. Create strategy directory structure
4. Refactor one uploader at a time, starting with simplest
5. Ensure all tests pass after each refactoring
6. Update progress in `specs/agent-3-progress.md`

Remember: You're the integration point - ensure all strategies work seamlessly with the new architecture!