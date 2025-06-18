#!/bin/bash
# GDC S3 Streaming Upload - Uploads directly from S3 without copying to disk

set -e

show_help() {
    cat << EOF
GDC S3 Streaming Uploader - Upload from S3 to GDC without local copy

USAGE:
    gdc_s3_stream_upload.sh [OPTIONS] S3_URL

DESCRIPTION:
    Streams a file directly from S3 to GDC without copying to local disk.
    Requires GDC metadata JSON and authentication token.

OPTIONS:
    -m, --metadata FILE     Path to GDC metadata JSON file (required)
    -t, --token FILE        Path to GDC authentication token file (required)
    -f, --filename NAME     Filename to match in metadata (if different from S3)
    -r, --retries N         Number of retry attempts (default: 3)
    -h, --help              Show this help message

EXAMPLES:
    gdc_s3_stream_upload.sh -m metadata.json -t token.txt s3://bucket/file.bam
    gdc_s3_stream_upload.sh -m meta.json -t auth.txt -f sample.bam s3://bucket/renamed.bam

EXIT CODES:
    0    Success
    1    Error - missing parameters or authentication
    2    Error - upload failed
    3    Error - S3 access failed
EOF
}

# Initialize variables
METADATA_FILE=""
TOKEN_FILE=""
FILENAME=""
RETRIES=3
S3_URL=""

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
        -f|--filename)
            FILENAME="$2"
            shift 2
            ;;
        -r|--retries)
            RETRIES="$2"
            shift 2
            ;;
        *)
            S3_URL="$1"
            shift
            ;;
    esac
done

# Validate inputs
if [[ -z "$METADATA_FILE" ]] || [[ -z "$TOKEN_FILE" ]] || [[ -z "$S3_URL" ]]; then
    echo "Error: Missing required parameters" >&2
    show_help
    exit 1
fi

# Extract filename from S3 URL if not provided
if [[ -z "$FILENAME" ]]; then
    FILENAME=$(basename "$S3_URL")
fi

echo "Starting GDC S3 streaming upload..."
echo "Metadata: $METADATA_FILE"
echo "Token: $TOKEN_FILE"
echo "S3 URL: $S3_URL"
echo "Filename: $FILENAME"

# Extract metadata
FILE_UUID=$(jq -r --arg filename "$FILENAME" '
  if type == "array" then
    .[] | select(.file_name == $filename) | .id
  elif type == "object" and has("files") then
    .files[] | select(.file_name == $filename) | .id
  else empty end
' "$METADATA_FILE")

PROJECT_ID=$(jq -r --arg filename "$FILENAME" '
  if type == "array" then
    .[] | select(.file_name == $filename) | .project_id
  elif type == "object" and has("files") then
    .files[] | select(.file_name == $filename) | .project_id
  else empty end
' "$METADATA_FILE")

if [[ -z "$FILE_UUID" ]] || [[ -z "$PROJECT_ID" ]]; then
    echo "Error: No metadata found for file '$FILENAME'" >&2
    exit 1
fi

echo "Found UUID: $FILE_UUID"
echo "Project ID: $PROJECT_ID"

# Convert project ID format
PROJECT_PATH=$(echo "$PROJECT_ID" | sed 's/-/\//')
echo "Project path: $PROJECT_PATH"

# Read token
TOKEN=$(cat "$TOKEN_FILE")

# Get file size from S3
echo "Getting file size from S3..."
FILE_SIZE=$(aws s3api head-object --bucket "${S3_URL#s3://}" --query ContentLength --output text 2>/dev/null || echo "0")
FILE_SIZE_GB=$(awk "BEGIN {printf \"%.2f\", $FILE_SIZE / 1073741824}")
echo "File size: ${FILE_SIZE_GB} GB"

# Perform streaming upload
UPLOAD_SUCCESS=false
for attempt in $(seq 1 $RETRIES); do
    echo "Upload attempt $attempt of $RETRIES..."
    
    # Use AWS CLI to stream from S3 directly to curl
    # This avoids copying the file to disk
    UPLOAD_START=$(date +%s)
    
    # Create named pipe for progress monitoring
    PROGRESS_PIPE="/tmp/upload-progress-$$.fifo"
    mkfifo "$PROGRESS_PIPE"
    
    # Monitor progress in background
    (
        while IFS= read -r line; do
            if [[ "$line" =~ ^[0-9]+ ]]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload progress: $line"
            fi
        done < "$PROGRESS_PIPE"
    ) &
    MONITOR_PID=$!
    
    # Stream from S3 to GDC
    HTTP_STATUS=$(aws s3 cp "$S3_URL" - | \
        pv -s "$FILE_SIZE" -f 2>"$PROGRESS_PIPE" | \
        curl --header "x-auth-token: $TOKEN" \
            --output "upload-$FILE_UUID.log" \
            --request PUT \
            --data-binary @- \
            --fail \
            --connect-timeout 60 \
            --max-time 0 \
            --retry 3 \
            --retry-delay 10 \
            --write-out "%{http_code}" \
            "https://api.gdc.cancer.gov/v0/submission/$PROJECT_PATH/files/$FILE_UUID")
    
    CURL_EXIT_CODE=$?
    
    # Clean up
    kill $MONITOR_PID 2>/dev/null || true
    rm -f "$PROGRESS_PIPE"
    
    UPLOAD_END=$(date +%s)
    DURATION=$((UPLOAD_END - UPLOAD_START))
    
    if [[ $CURL_EXIT_CODE -eq 0 ]] && [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]; then
        echo "Upload completed successfully!"
        echo "HTTP status: $HTTP_STATUS"
        echo "Duration: $((DURATION / 60)) minutes"
        UPLOAD_SUCCESS=true
        break
    else
        echo "Upload failed on attempt $attempt"
        echo "HTTP status: $HTTP_STATUS"
        echo "Curl exit code: $CURL_EXIT_CODE"
        
        if [[ $attempt -lt $RETRIES ]]; then
            echo "Retrying in 30 seconds..."
            sleep 30
        fi
    fi
done

# Generate report
cat > upload-report.tsv << EOF
file_name	file_uuid	s3_url	status	attempts
$FILENAME	$FILE_UUID	$S3_URL	$(if $UPLOAD_SUCCESS; then echo "success"; else echo "failed"; fi)	$attempt
EOF

if $UPLOAD_SUCCESS; then
    echo "S3 streaming upload completed successfully!"
    exit 0
else
    echo "S3 streaming upload failed after $RETRIES attempts" >&2
    exit 2
fi