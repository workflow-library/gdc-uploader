#!/bin/bash
# GDC Single File Upload Wrapper for CWL
# This script uploads a single file to GDC using metadata and token

set -e

show_help() {
    cat << EOF
GDC Single File Uploader - Upload a single genomic file to NIH Genomic Data Commons

USAGE:
    gdc_upload_single.sh [OPTIONS] FILE_PATH

DESCRIPTION:
    Uploads a single genomic sequence file to the GDC.
    Requires GDC metadata JSON and authentication token.
    
    This script takes a single file and uploads it using the GDC Data Transfer Tool.
    The metadata JSON should contain information for the specific file being uploaded.

OPTIONS:
    -m, --metadata FILE     Path to GDC metadata JSON file (required)
    -t, --token FILE        Path to GDC authentication token file (required)
    -r, --retries N         Number of retry attempts for failed uploads (default: 3)
    -h, --help              Show this help message

EXAMPLES:
    gdc_upload_single.sh -m metadata.json -t token.txt sample.bam
    gdc_upload_single.sh -m meta.json -t auth.txt -r 5 data.fastq.gz

EXIT CODES:
    0    Success - file uploaded successfully
    1    Error - missing required parameters or files
    2    Error - upload failed after retries
    3    Error - invalid metadata or authentication

DEPENDENCIES:
    - gdc-client (GDC Data Transfer Tool)
    - jq (JSON processor)

OUTPUT:
    - upload-report.tsv: Summary of upload attempt
    - upload-*.log: Upload log for the file
    - gdc-upload-stdout.log: Standard output
    - gdc-upload-stderr.log: Standard error
EOF
}

# Initialize variables
METADATA_FILE=""
TOKEN_FILE=""
RETRIES=3
TARGET_FILE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -m|--metadata)
            METADATA_FILE="$2"
            shift 2
            ;;
        -t|--token)
            TOKEN_FILE="$2"
            shift 2
            ;;
        -r|--retries)
            RETRIES="$2"
            shift 2
            ;;
        *)
            # Assume it's the target file if not a flag
            if [[ -f "$1" ]]; then
                TARGET_FILE="$1"
            else
                echo "Warning: File '$1' not found or not a regular file"
            fi
            shift
            ;;
    esac
done

# Validate required inputs
if [[ -z "$METADATA_FILE" ]]; then
    echo "Error: Metadata file is required (-m flag)" >&2
    exit 1
fi

if [[ -z "$TOKEN_FILE" ]]; then
    echo "Error: Token file is required (-t flag)" >&2
    exit 1
fi

if [[ -z "$TARGET_FILE" ]]; then
    echo "Error: Target file is required as positional argument" >&2
    exit 1
fi

# Check if files exist
if [[ ! -f "$METADATA_FILE" ]]; then
    echo "Error: Metadata file '$METADATA_FILE' not found" >&2
    exit 1
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
    echo "Error: Token file '$TOKEN_FILE' not found" >&2
    exit 1
fi

if [[ ! -f "$TARGET_FILE" ]]; then
    echo "Error: Target file '$TARGET_FILE' not found" >&2
    exit 1
fi

# Check if required tools are available
if ! command -v gdc-client &> /dev/null; then
    echo "Error: gdc-client not found. Please ensure GDC Data Transfer Tool is installed." >&2
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq not found. Please ensure jq is installed." >&2
    exit 1
fi

echo "Starting GDC single file upload..."
echo "Metadata: $METADATA_FILE"
echo "Token: $TOKEN_FILE"
echo "Target file: $TARGET_FILE"
echo "Retries: $RETRIES"

# Get the basename of the target file for matching
TARGET_BASENAME=$(basename "$TARGET_FILE")
echo "Looking for file: $TARGET_BASENAME"

# Extract file UUID from metadata based on filename
FILE_UUID=$(jq -r --arg filename "$TARGET_BASENAME" '
  .files[] | 
  select(.file_name == $filename or .local_file_path == $filename) | 
  .id
' "$METADATA_FILE")

if [[ -z "$FILE_UUID" || "$FILE_UUID" == "null" ]]; then
    echo "Error: No UUID found for file '$TARGET_BASENAME' in metadata" >&2
    echo "Available files in metadata:" >&2
    jq -r '.files[].file_name' "$METADATA_FILE" >&2
    exit 1
fi

echo "Found UUID: $FILE_UUID"

# Create a temporary directory for upload
UPLOAD_DIR=$(mktemp -d)
echo "Using temporary directory: $UPLOAD_DIR"

# Copy the file to upload directory with its original name
cp "$TARGET_FILE" "$UPLOAD_DIR/$TARGET_BASENAME"

# Create upload manifest for gdc-client
cat > "$UPLOAD_DIR/manifest.txt" << EOF
id	filename	md5	size	state
$FILE_UUID	$TARGET_BASENAME		upload
EOF

echo "Created upload manifest:"
cat "$UPLOAD_DIR/manifest.txt"

# Perform upload with retries
UPLOAD_SUCCESS=false
for attempt in $(seq 1 $RETRIES); do
    echo "Upload attempt $attempt of $RETRIES..."
    
    if gdc-client upload \
        --manifest "$UPLOAD_DIR/manifest.txt" \
        --token-file "$TOKEN_FILE" \
        --path "$UPLOAD_DIR" \
        --log-file "upload-$FILE_UUID.log" \
        --verbose; then
        
        UPLOAD_SUCCESS=true
        echo "Upload successful on attempt $attempt"
        break
    else
        echo "Upload failed on attempt $attempt"
        if [[ $attempt -lt $RETRIES ]]; then
            echo "Retrying in 5 seconds..."
            sleep 5
        fi
    fi
done

# Generate upload report
cat > upload-report.tsv << EOF
file_name	file_uuid	file_path	status	attempts
$TARGET_BASENAME	$FILE_UUID	$TARGET_FILE	$(if $UPLOAD_SUCCESS; then echo "success"; else echo "failed"; fi)	$attempt
EOF

echo "Upload report generated:"
cat upload-report.tsv

# Cleanup
rm -rf "$UPLOAD_DIR"

if $UPLOAD_SUCCESS; then
    echo "File upload completed successfully!"
    exit 0
else
    echo "File upload failed after $RETRIES attempts" >&2
    exit 2
fi