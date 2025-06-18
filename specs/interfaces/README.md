# Shared Interface Definitions

This directory contains interface definitions that multiple agents need to coordinate on.

## Files
- base_uploader_interface.py - Abstract base class for all uploaders (Agent 1)
- file_operations_interface.py - File discovery and validation interfaces (Agent 2)
- progress_interface.py - Progress tracking interfaces (Agent 2)
- api_client_interface.py - GDC API client interfaces (Agent 6)

## Guidelines
1. Define interfaces before implementation
2. Use type hints for clarity
3. Document expected behavior
4. Version interfaces if breaking changes needed
