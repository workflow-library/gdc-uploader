# Agent: Implement Progress Display

## Task Reference
From spec: `gdc_http_upload.md` - Task #6

## Role
Implement progress display using tqdm for upload monitoring.

## Context
- Part of GDC HTTP Upload feature
- Users need real-time feedback for long uploads
- Must show percentage, speed, and time remaining

## Requirements from Spec
- Real-time progress updates
- Show: percentage, transfer speed, time remaining
- Update at least every second
- Use tqdm library for display
- Work with chunked upload

## Implementation Guidelines
- Create tqdm progress bar with total=file_size
- Update bar with bytes transferred per chunk
- Set appropriate unit (bytes) and scaling
- Include descriptive label
- Ensure clean display on completion

## Inputs
- Total file size in bytes
- Generator/iterator of chunks
- Chunk size for updates

## Expected Output
- Visual progress bar in terminal
- Automatic cleanup on completion
- Pass-through of chunk data

## Success Criteria
- Smooth progress updates
- Accurate percentage calculation
- Speed shown in human-readable format
- Time remaining estimates reasonable
- No display artifacts on completion