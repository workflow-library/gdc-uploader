# Changelog

All notable changes to the GDC Uploader project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-17

### Added
- Complete Python package refactoring from shell scripts
- Progress bars for file uploads using tqdm
- Python API for programmatic usage
- Comprehensive documentation (API, Examples, Troubleshooting)
- Type hints for better code clarity
- Concurrent uploads using ThreadPoolExecutor
- Better error handling and logging
- Requirements.txt for dependency management
- Setup.py and pyproject.toml for pip installation

### Changed
- Migrated from bash scripts to Python modules:
  - `gdc_upload.sh` → `src/gdc_uploader/upload.py`
  - `gdc_direct-upload.sh` → `src/gdc_uploader/direct_upload.py` 
  - `gdc_upload_single.sh` → `src/gdc_uploader/upload_single.py`
- Moved Dockerfile to root directory
- Updated CWL files to use Python CLI commands
- Improved file discovery algorithm
- Enhanced logging with both console and file output

### Deprecated
- Shell script implementations (wrapper scripts provided for compatibility)

### Removed
- C# application components
- Complex wrapper application architecture

### Fixed
- File path handling in Seven Bridges environment
- Unicode handling in metadata files
- Memory usage with large file uploads

### Security
- No credentials stored in code
- Token file permissions validation

## [0.9.0] - 2024-01-10

### Changed
- Switched from C# wrapper to direct gdc-client usage
- Simplified architecture to shell scripts
- Added GNU parallel for concurrent uploads

## [0.8.0] - 2023-12-15

### Added
- CWL workflow definitions
- Docker support
- Seven Bridges platform compatibility

## [0.7.0] - 2023-11-20

### Added
- Initial C# application wrapper
- Basic upload functionality
- GDC API integration