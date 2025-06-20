# Agent: Implement Manifest Parser

## Task Reference
From spec: `gdc_http_upload.md` - Task #1

## Role
Implement JSON parser to extract file metadata from GDC manifest files.

## Context
- Part of GDC HTTP Upload feature
- Manifest format defined in spec's data models section
- Must handle both array and object-wrapped formats

## Requirements from Spec
- Parse JSON manifest file
- Find entry matching given filename
- Extract: id, file_name, file_size, md5sum
- Raise clear error if file not found

## Implementation Guidelines
- Use Python's json module
- Handle malformed JSON gracefully
- Support both `[{...}]` and `{"files": [{...}]}` formats
- Case-sensitive filename matching

## Inputs
- Path to manifest JSON file
- Target filename to search for

## Expected Output
- Dictionary with file metadata
- ValueError with clear message if not found
- JSONDecodeError if manifest invalid

## Success Criteria
- Correctly parses both manifest formats
- Returns all required fields
- Clear error message: "File '{filename}' not found in manifest"
- Handles edge cases (empty manifest, missing fields)