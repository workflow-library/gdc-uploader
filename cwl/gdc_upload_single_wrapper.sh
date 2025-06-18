#!/bin/bash
# Wrapper script that can use either the shell or Python implementation
# This maintains backward compatibility while allowing future migration

# Check if we should use Python implementation (via environment variable)
if [[ "${USE_PYTHON_IMPLEMENTATION}" == "true" ]]; then
    # Use the Python implementation
    exec gdc-uploader upload-single "$@"
else
    # Use the original shell script implementation
    # This is the current default to maintain compatibility
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    exec "$SCRIPT_DIR/gdc_upload_single.sh" "$@"
fi