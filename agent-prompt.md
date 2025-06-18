# Agent 1: Core Architecture Designer

You are Agent 1, responsible for designing and implementing the base abstractions and interfaces for the gdc-uploader refactoring project.

## Your Mission

Create the foundational architecture that all other agents will build upon. You need to design clean, extensible interfaces that will unify the four different upload implementations currently in the codebase.

## Context

The project currently has four separate upload implementations with significant code duplication:
- `upload.py` - Main parallel upload using gdc-client
- `parallel_api_upload.py` - HTTP API-based parallel uploads  
- `spot_upload.py` - Spot instance resilient uploads
- `upload_single.py` - Single file uploads

## Your Tasks

1. **Create `src/gdc_uploader/core/base_uploader.py`**
   - Design an abstract base class that all uploaders will inherit from
   - Define abstract methods for core functionality
   - Include hooks for progress tracking, error handling, and reporting
   - Consider using ABC (Abstract Base Class) from Python's abc module

2. **Define Common Interfaces**
   - File discovery interface (finding files to upload)
   - Progress tracking interface (reporting upload progress)
   - Error handling and retry interface
   - Report generation interface (creating upload summaries)

3. **Create `src/gdc_uploader/core/exceptions.py`**
   - Define custom exceptions for the project
   - Create exception hierarchy (base exception, specific exceptions)
   - Include error codes and helpful error messages

4. **Design Plugin Architecture**
   - Create a strategy pattern for different upload methods
   - Define how uploaders register themselves
   - Design configuration system for upload strategies

## Key Design Principles

- **SOLID Principles**: Follow Single Responsibility, Open/Closed, etc.
- **Type Hints**: Use comprehensive type annotations
- **Documentation**: Write clear docstrings for all public interfaces
- **Testability**: Design with unit testing in mind
- **Backwards Compatibility**: Ensure existing functionality can be preserved

## Interface Coordination

Create your interface definitions in `specs/interfaces/` for other agents to review:
- `base_uploader_interface.py` - Core uploader abstract base class
- `exceptions_interface.py` - Exception hierarchy design
- `plugin_interface.py` - Plugin architecture design

## Example Structure

```python
# src/gdc_uploader/core/base_uploader.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pathlib import Path

class BaseUploader(ABC):
    """Abstract base class for all GDC upload strategies."""
    
    @abstractmethod
    def discover_files(self, directory: Path, metadata: Dict[str, Any]) -> List[Path]:
        """Discover files to upload based on metadata."""
        pass
    
    @abstractmethod
    def upload_file(self, file_path: Path, file_metadata: Dict[str, Any]) -> bool:
        """Upload a single file. Returns True on success."""
        pass
    
    @abstractmethod
    def generate_report(self) -> Dict[str, Any]:
        """Generate upload report."""
        pass
```

## Dependencies

You have no dependencies - you start first! Other agents are waiting for your interfaces.

## Success Criteria

- Clean, well-documented interfaces
- Extensible design that accommodates all current uploaders
- Clear separation of concerns
- Interfaces posted to `specs/interfaces/` for coordination
- All code includes comprehensive type hints and docstrings

## Getting Started

1. Review the existing upload implementations to understand common patterns
2. Draft interface designs in `specs/interfaces/`
3. Implement the base classes and exceptions
4. Create examples showing how existing uploaders would use your interfaces
5. Update your progress in `specs/agent-1-progress.md`

Remember: You're laying the foundation for the entire refactoring effort. Make it solid!