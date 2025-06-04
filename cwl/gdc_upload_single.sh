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
    - curl (for API uploads)
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
if ! command -v curl &> /dev/null; then
    echo "Error: curl not found. Please ensure curl is installed." >&2
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
# Handle both array format and object with 'files' property
FILE_UUID=$(jq -r --arg filename "$TARGET_BASENAME" '
  if type == "array" then
    .[] | 
    select(.file_name == $filename or .local_file_path == $filename) | 
    .id
  elif type == "object" and has("files") then
    .files[] | 
    select(.file_name == $filename or .local_file_path == $filename) | 
    .id
  else
    empty
  end
' "$METADATA_FILE")

if [[ -z "$FILE_UUID" || "$FILE_UUID" == "null" ]]; then
    echo "Error: No UUID found for file '$TARGET_BASENAME' in metadata" >&2
    echo "Available files in metadata:" >&2
    jq -r 'if type == "array" then .[].file_name elif type == "object" and has("files") then .files[].file_name else empty end' "$METADATA_FILE" >&2
    exit 1
fi

echo "Found UUID: $FILE_UUID"

# Extract project ID from metadata
PROJECT_ID=$(jq -r --arg filename "$TARGET_BASENAME" '
  if type == "array" then
    .[] | 
    select(.file_name == $filename or .local_file_path == $filename) | 
    .project_id
  elif type == "object" and has("files") then
    .files[] | 
    select(.file_name == $filename or .local_file_path == $filename) | 
    .project_id
  else
    empty
  end
' "$METADATA_FILE")

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "null" ]]; then
    echo "Error: No project_id found for file '$TARGET_BASENAME' in metadata" >&2
    exit 1
fi

echo "Project ID: $PROJECT_ID"

# Convert project ID format if needed (MP2PRT-EC -> MP2PRT/EC)
PROJECT_PATH=$(echo "$PROJECT_ID" | sed 's/-/\//')
echo "Project path for API: $PROJECT_PATH"

# Read token from file
TOKEN=$(cat "$TOKEN_FILE")

# Perform upload with retries using direct API
UPLOAD_SUCCESS=false
for attempt in $(seq 1 $RETRIES); do
    echo "Upload attempt $attempt of $RETRIES..."
    echo "Uploading to: https://api.gdc.cancer.gov/v0/submission/$PROJECT_PATH/files/$FILE_UUID"
    
    # Get file size for progress reporting
    FILE_SIZE=$(stat -c%s "$TARGET_FILE" 2>/dev/null || stat -f%z "$TARGET_FILE" 2>/dev/null || echo "0")
    FILE_SIZE_GB=$(awk "BEGIN {printf \"%.2f\", $FILE_SIZE / 1073741824}")
    echo "File size: ${FILE_SIZE_GB} GB"
    
    # Start upload
    echo "Starting upload..."
    UPLOAD_START=$(date +%s)
    
    # Create progress tracking files in current directory
    PROGRESS_FILE="curl-progress-$FILE_UUID.txt"
    UPLOAD_MARKER=".upload-active-$FILE_UUID"
    touch "$UPLOAD_MARKER"
    
    # Debug output
    echo "Current working directory: $(pwd)"
    echo "Creating progress files in: $(pwd)"
    
    # Start progress monitor in background
    (
        LAST_PERCENT=0
        LAST_UPDATE=0
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Progress monitor started" >> "progress-monitor-$FILE_UUID.log"
        
        while [[ -f "$UPLOAD_MARKER" ]]; do
            sleep 2
            
            if [[ -f "$PROGRESS_FILE" ]]; then
                # Debug: show file size
                FILE_SIZE_BYTES=$(stat -c%s "$PROGRESS_FILE" 2>/dev/null || echo "0")
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Progress file size: $FILE_SIZE_BYTES bytes" >> "progress-monitor-$FILE_UUID.log"
                
                # Read the last line of progress
                PROGRESS_LINE=$(tail -1 "$PROGRESS_FILE" 2>/dev/null || echo "")
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Progress line: $PROGRESS_LINE" >> "progress-monitor-$FILE_UUID.log"
                
                # Parse curl's progress format: "% Total    % Received % Xferd  Average Speed"
                # Example: " 23 1024M   23  235M    0     0  12.5M      0  0:01:21  0:00:18  0:01:03 13.1M"
                if [[ "$PROGRESS_LINE" =~ ^[[:space:]]*([0-9]+)[[:space:]] ]]; then
                    PERCENT="${BASH_REMATCH[1]}"
                    
                    # Get current time
                    CURRENT_TIME=$(date +%s)
                    
                    # Update every 30 seconds or when progress changes by 5%
                    if [[ $((CURRENT_TIME - LAST_UPDATE)) -ge 30 ]] || [[ $((PERCENT - LAST_PERCENT)) -ge 5 ]]; then
                        ELAPSED=$((CURRENT_TIME - UPLOAD_START))
                        ELAPSED_MIN=$((ELAPSED / 60))
                        ELAPSED_SEC=$((ELAPSED % 60))
                        
                        # Calculate ETA if we have progress
                        if [[ $PERCENT -gt 0 ]]; then
                            TOTAL_TIME_EST=$((ELAPSED * 100 / PERCENT))
                            REMAINING=$((TOTAL_TIME_EST - ELAPSED))
                            REMAINING_MIN=$((REMAINING / 60))
                            REMAINING_SEC=$((REMAINING % 60))
                            
                            UPLOADED_GB=$(awk "BEGIN {printf \"%.2f\", $FILE_SIZE_GB * $PERCENT / 100}")
                            
                            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload progress: ${PERCENT}% complete (${UPLOADED_GB} of ${FILE_SIZE_GB} GB) - elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s, ETA: ${REMAINING_MIN}m ${REMAINING_SEC}s"
                        else
                            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload in progress... (elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s)"
                        fi
                        
                        LAST_UPDATE=$CURRENT_TIME
                        LAST_PERCENT=$PERCENT
                    fi
                fi
            else
                # No progress file yet or no valid progress line - show heartbeat every 30 seconds
                CURRENT_TIME=$(date +%s)
                if [[ $((CURRENT_TIME - LAST_UPDATE)) -ge 30 ]]; then
                    ELAPSED=$((CURRENT_TIME - UPLOAD_START))
                    ELAPSED_MIN=$((ELAPSED / 60))
                    ELAPSED_SEC=$((ELAPSED % 60))
                    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload initializing... (elapsed: ${ELAPSED_MIN}m ${ELAPSED_SEC}s)"
                    LAST_UPDATE=$CURRENT_TIME
                fi
            fi
        done
        
        # Clean up
        rm -f "$PROGRESS_FILE"
    ) &
    PROGRESS_PID=$!
    
    # Run curl with progress output to file
    echo "Uploading ${FILE_SIZE_GB} GB file..."
    echo "Progress will be written to: $PROGRESS_FILE"
    echo "Files being created:"
    echo "  - $PROGRESS_FILE (curl progress output)"
    echo "  - $UPLOAD_MARKER (upload active marker)"
    echo "  - progress-monitor-$FILE_UUID.log (debug log)"
    echo "  - upload-$FILE_UUID.log (curl response)"
    
    # Use curl with progress output redirected to our progress file
    # Note: --progress-bar shows # progress bar, -# is shorthand
    # We use stderr redirection (2>) to capture the progress
    HTTP_STATUS=$(curl --header "x-auth-token: $TOKEN" \
            --output "upload-$FILE_UUID.log" \
            --request PUT \
            --upload-file "$TARGET_FILE" \
            --fail \
            --continue-at - \
            --connect-timeout 60 \
            --max-time 0 \
            --retry 3 \
            --retry-delay 10 \
            --write-out "%{http_code}" \
            -# \
            "https://api.gdc.cancer.gov/v0/submission/$PROJECT_PATH/files/$FILE_UUID" 2>"$PROGRESS_FILE")
    
    CURL_EXIT_CODE=$?
    
    # Clean up marker and kill progress monitor
    rm -f "$UPLOAD_MARKER" "$PROGRESS_FILE"
    kill $PROGRESS_PID 2>/dev/null || true
    wait $PROGRESS_PID 2>/dev/null || true
    
    # Check results
    if [[ $CURL_EXIT_CODE -eq 0 ]] && [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]; then
        UPLOAD_END=$(date +%s)
        TOTAL_TIME=$((UPLOAD_END - UPLOAD_START))
        TOTAL_MIN=$((TOTAL_TIME / 60))
        TOTAL_SEC=$((TOTAL_TIME % 60))
        
        echo "Upload completed successfully!"
        echo "HTTP status: $HTTP_STATUS"
        echo "Total time: ${TOTAL_MIN}m ${TOTAL_SEC}s"
        
        # Calculate average speed
        if [[ $TOTAL_TIME -gt 0 ]]; then
            AVG_SPEED_MB=$(awk "BEGIN {printf \"%.2f\", ($FILE_SIZE / 1048576) / $TOTAL_TIME}")
            echo "Average speed: ${AVG_SPEED_MB} MB/s"
        fi
        
        UPLOAD_SUCCESS=true
        echo "Upload successful on attempt $attempt"
        break
    else
        echo "Upload failed on attempt $attempt"
        if [[ "$HTTP_STATUS" != "" ]]; then
            echo "HTTP status: $HTTP_STATUS"
        fi
        if [[ $CURL_EXIT_CODE -ne 0 ]]; then
            echo "Curl exit code: $CURL_EXIT_CODE"
        fi
        
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

# No cleanup needed for direct API upload

if $UPLOAD_SUCCESS; then
    echo "File upload completed successfully!"
    exit 0
else
    echo "File upload failed after $RETRIES attempts" >&2
    exit 2
fi