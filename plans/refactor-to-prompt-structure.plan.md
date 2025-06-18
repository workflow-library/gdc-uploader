# Refactor to Prompt-Based Structure Plan

**Date**: 2024-06-18
**Goal**: Refactor GDC Uploader to use prompt-based scientific workflow structure

## Summary

Transform the GDC Uploader project from its current structure to a prompt-first architecture where markdown prompts are the source of truth for generating CWL files, Dockerfiles, and Quarto notebooks. Focus on the main `gdc-upload` tool while maintaining backward compatibility.

## Assumptions

1. Existing CWL files and scripts will be preserved in a legacy directory
2. The main Docker image (ghcr.io/open-workflow-library/gdc-uploader:latest) will continue to work
3. Python package structure will be enhanced, not replaced
4. Focus is on `gdc-upload` as the primary interface

## Constraints

1. No Jinja2 or templating engines - use plain Python string formatting
2. All notebooks must be .qmd format, not .ipynb
3. Must maintain compatibility with existing CLI commands
4. Generated artifacts go in `artifacts/` directory

## Steps

### 1. Create Core Infrastructure
```bash
# Create parser module
touch src/gdc_uploader/parser.py

# Create emit package
mkdir -p src/gdc_uploader/emit
touch src/gdc_uploader/emit/__init__.py
touch src/gdc_uploader/emit/cwl.py
touch src/gdc_uploader/emit/docker.py
touch src/gdc_uploader/emit/notebook.py

# Create artifact directories
mkdir -p artifacts/cwl
mkdir -p artifacts/docker
mkdir -p artifacts/notebooks

# Create plans directory (already exists)
mkdir -p plans
```

### 2. Implement Parser Module
- Create `src/gdc_uploader/parser.py` with functions to:
  - Parse markdown files with YAML frontmatter
  - Extract tool metadata (name, version, description)
  - Extract input/output specifications
  - Extract command blocks
  - Extract documentation sections
  - Return structured dictionary

### 3. Implement Emitters
- `cwl.py`: Generate CWL v1.2 files from parsed prompts
- `docker.py`: Generate Dockerfiles with all dependencies
- `notebook.py`: Generate Quarto notebooks with documentation and examples

### 4. Create Tool Prompts
Primary tools to create prompts for:
- `gdc_upload.md` - Main upload tool (from gdc_upload.cwl/sh)
- `gdc_direct_upload.md` - Direct upload variant
- `gdc_yaml2json.md` - YAML to JSON converter
- `gdc_filter_json.md` - JSON filtering tool
- `gdc_split_json.md` - JSON splitting tool
- `gdc_metadata_generate.md` - Metadata generation
- `gdc_upload_single.md` - Single file upload

### 5. Move Legacy Files
```bash
# Create legacy directories
mkdir -p legacy/cwl
mkdir -p legacy/scripts

# Move CWL files
mv cwl/*.cwl legacy/cwl/

# Move scripts
mv cwl/*.sh legacy/scripts/
mv cwl/*.py legacy/scripts/

# Keep Dockerfile in cwl directory for now
```

### 6. Update CLI
- Add new commands to `src/gdc_uploader/cli.py`:
  - `gdc-uploader emit` - Generate artifacts from prompts
  - `gdc-uploader validate` - Validate prompt files
  - Keep existing upload commands unchanged

### 7. Clean Up
- Remove `specs/agent-*-progress.md` files
- Remove `specs/coordination/` directory
- Remove any `.gitignore.agent` files
- Update documentation

## Code References

Example prompt structure:
```markdown
---
name: gdc_upload
version: 2.0.0
description: Upload genomic data files to GDC
docker_image: ghcr.io/open-workflow-library/gdc-uploader:latest
---

# GDC Upload Tool

## Inputs
- metadata_file: GDC metadata JSON file
- token_file: GDC authentication token
- files_directory: Directory containing files to upload

## Command
```bash
gdc-upload -m {metadata_file} -t {token_file} {files_directory}
```

## Documentation
...
```

## Success Metrics

1. All existing CWL tools have corresponding prompt files
2. Running `gdc-uploader emit` generates all artifacts
3. Generated CWL files are functionally equivalent to originals
4. CLI commands continue to work as before
5. Documentation is updated and accurate

## Rollback Plan

If issues arise:
1. Legacy files are preserved in `legacy/` directory
2. Git history allows full reversion
3. Docker image remains unchanged
4. Python package can be reinstalled from previous version