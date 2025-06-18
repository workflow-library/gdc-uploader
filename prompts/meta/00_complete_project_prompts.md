# Complete Project Prompts - GDC Uploader

This document defines all prompts needed to recreate the entire GDC Uploader project from scratch using only markdown prompts.

## Overview

The GDC Uploader project can be fully regenerated from a series of markdown prompts that define:
- Infrastructure and framework code
- Core modules and utilities
- API clients and models
- Upload strategies
- Command-line tools
- Tests and documentation

## Prompt Categories

### 1. Meta/Infrastructure Prompts (in `prompts/meta/`)
- **00_complete_project_prompts.md** - This file - master index of all prompts
- **00_project_setup.md** - Initialize project structure, dependencies, and configuration
- **01_init_project_structure.md** - (Already exists) Create directory layout
- **02_emit_all_artifacts.md** - (Already exists) Generate artifacts from prompts
- **03_parser_infrastructure.md** - Create the parser module for reading prompts
- **04_emitter_infrastructure.md** - Create the emitter modules for generating artifacts
- **05_cli_infrastructure.md** - Create CLI framework and reusable options

### 2. Core Module Prompts (in `prompts/core/`)
- **base_uploader.md** - Abstract base class defining uploader interface
- **exceptions.md** - Complete exception hierarchy for error handling
- **file_operations.md** - File discovery, validation, and manipulation utilities
- **progress_tracking.md** - Progress monitoring, reporting, and visualization
- **retry_logic.md** - Retry mechanisms with configurable backoff strategies
- **utils.md** - General utility functions (logging, config, helpers)

### 3. API Module Prompts (in `prompts/api/`)
- **api_client.md** - GDC API client with rate limiting and connection pooling
- **api_models.md** - Pydantic models for type-safe API interactions
- **api_exceptions.md** - API-specific exception classes
- **api_auth.md** - Authentication, token management, and validation
- **api_async.md** - Asynchronous API client implementation

### 4. Uploader Strategy Prompts (in `prompts/uploaders/`)
- **standard_uploader.md** - Standard gdc-client based parallel uploader
- **api_uploader.md** - Direct API upload using HTTP chunks
- **spot_uploader.md** - Spot instance aware uploader with checkpointing
- **single_file_uploader.md** - Optimized single file upload strategy

### 5. Tool Prompts (in `prompts/tools/`)
- **gdc_upload.md** - (Already exists) Main parallel upload tool
- **gdc_direct_upload.md** - Simplified direct upload variant
- **gdc_yaml2json.md** - (Already exists) YAML to JSON metadata converter
- **gdc_filter_json.md** - Filter JSON metadata by filename
- **gdc_split_json.md** - Split JSON metadata into individual files
- **gdc_metadata_generate.md** - Generate GDC metadata from file lists
- **gdc_upload_single.md** - Single file upload tool

### 6. Testing Prompts (in `prompts/tests/`)
- **test_infrastructure.md** - pytest setup and test utilities
- **unit_tests.md** - Unit tests for all modules
- **integration_tests.md** - End-to-end integration tests
- **cwl_tests.md** - CWL workflow validation tests

### 7. Documentation Prompts (in `prompts/docs/`)
- **readme.md** - Generate main README.md
- **architecture.md** - System architecture documentation
- **api_docs.md** - API reference documentation
- **examples.md** - Usage examples and tutorials
- **troubleshooting.md** - Common issues and solutions

## Standard Prompt Structure

Each prompt follows this template:

```markdown
---
name: component_name
version: 1.0.0
description: Brief description of the component
type: [infrastructure|module|tool|test|doc]
dependencies: 
  - dependency1
  - dependency2
outputs:
  - type: python
    path: src/gdc_uploader/module.py
  - type: cwl
    path: cwl/tool.cwl
  - type: docker
    path: docker/Dockerfile
  - type: notebook
    path: notebooks/tutorial.qmd
---

# Component Name

## Purpose
Detailed description of what this component does and why it's needed.

## Requirements
- Requirement 1
- Requirement 2
- External dependencies

## Inputs
- input1: Description (type)
- input2: Description (type)

## Outputs
- output1: Description (type)
- output2: Description (type)

## Implementation

### Python Code
```python
# Complete implementation
```

### Shell Script
```bash
# Shell commands if needed
```

## Command
```bash
command-to-run --arg1 {input1} --arg2 {input2}
```

## Configuration
```yaml
config:
  key: value
```

## Usage Examples
```python
# Example usage
```

## Testing
```python
# Test cases
```

## Error Handling
- Error case 1: How to handle
- Error case 2: How to handle

## Performance Considerations
- Optimization 1
- Optimization 2
```

## Implementation Phases

### Phase 1: Infrastructure (Dependencies: none)
1. 00_project_setup.md
2. 03_parser_infrastructure.md
3. 04_emitter_infrastructure.md
4. 05_cli_infrastructure.md

### Phase 2: Core Modules (Dependencies: Phase 1)
1. exceptions.md
2. utils.md
3. base_uploader.md
4. file_operations.md
5. progress_tracking.md
6. retry_logic.md

### Phase 3: API Modules (Dependencies: Phase 2)
1. api_exceptions.md
2. api_models.md
3. api_auth.md
4. api_client.md
5. api_async.md

### Phase 4: Uploaders (Dependencies: Phase 2, 3)
1. standard_uploader.md
2. api_uploader.md
3. spot_uploader.md
4. single_file_uploader.md

### Phase 5: Tools (Dependencies: Phase 4)
1. gdc_upload.md
2. gdc_direct_upload.md
3. gdc_yaml2json.md
4. gdc_filter_json.md
5. gdc_split_json.md
6. gdc_metadata_generate.md
7. gdc_upload_single.md

### Phase 6: Testing (Dependencies: Phase 5)
1. test_infrastructure.md
2. unit_tests.md
3. integration_tests.md
4. cwl_tests.md

### Phase 7: Documentation (Dependencies: All phases)
1. readme.md
2. architecture.md
3. api_docs.md
4. examples.md
5. troubleshooting.md

## Dependency Graph

```
Phase 1: Infrastructure
    ├── Phase 2: Core Modules
    │   ├── Phase 3: API Modules
    │   └── Phase 4: Uploaders
    │       └── Phase 5: Tools
    │           └── Phase 6: Testing
    └── Phase 7: Documentation
```

## Usage Instructions

### To Generate Entire Project

1. Ensure all prompts are created in their respective directories
2. Run the emitter on all prompts:
   ```bash
   gdc-uploader emit --prompts-dir prompts --output-dir . --force
   ```

### To Generate Specific Components

1. Generate only infrastructure:
   ```bash
   gdc-uploader emit --prompts-dir prompts/meta --output-dir .
   ```

2. Generate only tools:
   ```bash
   gdc-uploader emit --prompts-dir prompts/tools --output-dir artifacts
   ```

### To Validate Prompts

```bash
# Validate all prompts
find prompts -name "*.md" -exec gdc-uploader validate {} \;

# Validate specific prompt
gdc-uploader validate prompts/tools/gdc_upload.md
```

## Key Benefits

1. **Complete Reproducibility**: Entire project can be regenerated from prompts
2. **Single Source of Truth**: All logic defined in markdown prompts
3. **Automatic Consistency**: Generated artifacts always match prompt definitions
4. **Built-in Documentation**: Every component is self-documenting
5. **Version Control Friendly**: Track changes at the semantic level
6. **Modular Architecture**: Each component is independent and reusable
7. **Multiple Output Formats**: Generate Python, CWL, Docker, and docs from one source

## Prompt Creation Guidelines

1. **Self-Contained**: Each prompt must contain all information needed
2. **Clear Dependencies**: Explicitly list all dependencies
3. **Complete Implementation**: Include full code, not snippets
4. **Comprehensive Testing**: Include test cases in the prompt
5. **Error Handling**: Document all error cases and handling
6. **Examples**: Provide clear usage examples
7. **Performance Notes**: Include optimization considerations

## Next Steps

1. Create all prompt files following the structure above
2. Implement prompts in dependency order
3. Test each component as it's generated
4. Validate complete system integration
5. Document any deviations or enhancements

This master prompt serves as the blueprint for recreating the entire GDC Uploader project from prompts alone.