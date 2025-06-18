# Multi-Agent Codebase Improvement Plan for GDC-Uploader

## Overview

This document outlines a strategy for using multiple AI agents to work simultaneously on improving and refactoring the gdc-uploader codebase. The project has ~3,300 lines of code with clear module boundaries, making it ideal for parallel agent work.

## Current State Analysis

### Architecture Issues
1. **Four separate upload implementations** with overlapping functionality:
   - `upload.py` - Main parallel upload using gdc-client
   - `parallel_api_upload.py` - HTTP API-based parallel uploads
   - `spot_upload.py` - Spot instance resilient uploads
   - `upload_single.py` - Single file uploads

2. **Code duplication** across modules:
   - CLI option definitions repeated in 9 commands
   - File discovery logic duplicated 4 times
   - Retry logic implemented separately in each uploader
   - Logging setup repeated in multiple places

3. **Lack of abstraction**:
   - No base uploader interface
   - No shared utilities for common operations
   - Direct coupling between CLI and implementation

## Multi-Agent Task Distribution

### Agent 1: Core Architecture Designer
**Goal**: Design and implement base abstractions and interfaces

**Tasks**:
1. Create `src/gdc_uploader/core/base_uploader.py` with abstract base class
2. Define common interfaces for:
   - File discovery
   - Progress tracking
   - Error handling and retries
   - Report generation
3. Create `src/gdc_uploader/core/exceptions.py` for unified error handling
4. Design plugin architecture for different upload strategies

**Dependencies**: None (starts first)

### Agent 2: Common Utilities Refactorer
**Goal**: Extract and consolidate shared functionality

**Tasks**:
1. Create `src/gdc_uploader/core/file_operations.py`:
   - Consolidate file discovery logic
   - Implement file validation
   - Add file filtering capabilities
2. Create `src/gdc_uploader/core/progress.py`:
   - Unified progress tracking
   - Console and file-based reporting
3. Create `src/gdc_uploader/core/retry.py`:
   - Configurable retry decorator
   - Exponential backoff implementation
4. Enhance `utils.py` with additional shared utilities

**Dependencies**: Agent 1's base interfaces

### Agent 3: Upload Strategy Implementer
**Goal**: Refactor upload modules to use common base

**Tasks**:
1. Refactor `upload.py` to inherit from base uploader
2. Refactor `parallel_api_upload.py` to use shared components
3. Refactor `spot_upload.py` with proper resilience patterns
4. Refactor `upload_single.py` as a simple strategy
5. Create `src/gdc_uploader/strategies/` directory for organization

**Dependencies**: Agents 1 and 2's work

### Agent 4: CLI Modernizer
**Goal**: Simplify and consolidate CLI using Click best practices

**Tasks**:
1. Create `src/gdc_uploader/cli/options.py` with shared option definitions
2. Refactor `cli.py` to use:
   - Click command groups
   - Option inheritance
   - Proper context passing
3. Implement command aliases for backward compatibility
4. Add rich terminal output support
5. Create `src/gdc_uploader/cli/validators.py` for input validation

**Dependencies**: Can start immediately

### Agent 5: Testing Infrastructure Builder
**Goal**: Create comprehensive Python test suite

**Tasks**:
1. Set up pytest framework with proper fixtures
2. Create unit tests for each core module:
   - `tests/unit/core/test_base_uploader.py`
   - `tests/unit/core/test_file_operations.py`
   - `tests/unit/strategies/test_*.py`
3. Add integration tests for upload workflows
4. Create mock GDC API for testing
5. Add test coverage reporting
6. Update GitHub Actions for automated testing

**Dependencies**: Waits for Agents 1-3 to establish structure

### Agent 6: API Client Developer
**Goal**: Create proper HTTP API client abstraction

**Tasks**:
1. Create `src/gdc_uploader/api/client.py`:
   - Wrap GDC API interactions
   - Add proper session management
   - Implement rate limiting
   - Add comprehensive error handling
2. Create `src/gdc_uploader/api/models.py` for API data models
3. Add authentication token management
4. Implement connection pooling for performance

**Dependencies**: Can start immediately

### Agent 7: Documentation Updater
**Goal**: Update all documentation to reflect new architecture

**Tasks**:
1. Update README.md with new structure
2. Create architecture diagrams
3. Write migration guide from old to new structure
4. Update CWL workflow documentation
5. Create API reference documentation
6. Add inline code documentation (docstrings)

**Dependencies**: Waits for all other agents

## Implementation Strategy

### Phase 1: Foundation (Agents 1, 2, 4, 6)
- Establish core abstractions
- Build shared utilities
- Modernize CLI
- Create API client

### Phase 2: Refactoring (Agent 3)
- Migrate upload implementations
- Ensure backward compatibility
- Validate functionality

### Phase 3: Quality (Agents 5, 7)
- Add comprehensive testing
- Update documentation
- Performance optimization

## Success Criteria

1. **Code Quality**:
   - Eliminate 90% of code duplication
   - Achieve 80%+ test coverage
   - Pass all linting and type checking

2. **Architecture**:
   - Clear separation of concerns
   - Pluggable upload strategies
   - Consistent error handling

3. **Maintainability**:
   - Comprehensive documentation
   - Clear upgrade path
   - Easy to add new features

## Risk Mitigation

1. **Backward Compatibility**:
   - Maintain shell script wrappers
   - Keep CWL interfaces unchanged
   - Provide compatibility layer for old CLI

2. **Testing**:
   - Each agent tests their changes
   - Integration tests after each phase
   - Staging environment validation

3. **Coordination**:
   - Clear interface definitions upfront
   - Regular sync points between agents
   - Shared design documents

## Timeline Estimate

- **Phase 1**: 2-3 days (parallel work)
- **Phase 2**: 2 days (sequential)
- **Phase 3**: 2 days (parallel)
- **Total**: ~1 week with 7 agents working in parallel

## Next Steps

1. Review and approve this plan
2. Set up agent coordination mechanism
3. Create shared design documents
4. Begin Phase 1 implementation
5. Regular progress reviews

## Agent Coordination Protocol

Each agent should:
1. Create a branch named `agent-N-description`
2. Document their changes in `specs/agent-N-progress.md`
3. Create PRs for review when complete
4. Coordinate on shared interfaces via comments