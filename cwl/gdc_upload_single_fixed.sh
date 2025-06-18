#!/bin/bash
# GDC Single File Upload with Fixed Progress Monitoring

set -e

show_help() {
    cat << EOF
GDC Single File Uploader - Upload a single genomic file to NIH Genomic Data Commons

USAGE:
    gdc_upload_single_fixed.sh [OPTIONS] FILE_PATH

OPTIONS:
    -m, --metadata FILE     Path to GDC metadata JSON file (required)
    -t, --token FILE        Path to GDC authentication token file (required)
    -r, --retries N         Number of retry attempts for failed uploads (default: 3)
    -h, --help              Show this help message
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
            if [[ -f "$1" ]]; then
                TARGET_FILE="$1"
            fi
            shift
            ;;
    esac
done

# Validate required inputs
if [[ -z "$METADATA_FILE" ]] || [[ -z "$TOKEN_FILE" ]] || [[ -z "$TARGET_FILE" ]]; then
    echo "Error: Missing required parameters" >&2
    show_help
    exit 1
fi

echo "Starting GDC single file upload..."
echo "Metadata: $METADATA_FILE"
echo "Token: $TOKEN_FILE"
echo "Target file: $TARGET_FILE"

# Get file info
TARGET_BASENAME=$(basename "$TARGET_FILE")
FILE_SIZE=$(stat -c%s "$TARGET_FILE" 2>/dev/null || stat -f%z "$TARGET_FILE")
FILE_SIZE_GB=$(awk "BEGIN {printf \"%.2f\", $FILE_SIZE / 1073741824}")

# Extract metadata
FILE_UUID=$(jq -r --arg filename "$TARGET_BASENAME" '
  if type == "array" then
    .[] | select(.file_name == $filename) | .id
  elif type == "object" and has("files") then
    .files[] | select(.file_name == $filename) | .id
  else empty end
' "$METADATA_FILE")

PROJECT_ID=$(jq -r --arg filename "$TARGET_BASENAME" '
  if type == "array" then
    .[] | select(.file_name == $filename) | .project_id
  elif type == "object" and has("files") then
    .files[] | select(.file_name == $filename) | .project_id
  else empty end
' "$METADATA_FILE")

if [[ -z "$FILE_UUID" ]] || [[ -z "$PROJECT_ID" ]]; then
    echo "Error: No metadata found for file '$TARGET_BASENAME'" >&2
    exit 1
fi

echo "Found UUID: $FILE_UUID"
echo "Project ID: $PROJECT_ID"
echo "File size: ${FILE_SIZE_GB} GB"

PROJECT_PATH=$(echo "$PROJECT_ID" | sed 's/-/\//')
TOKEN=$(cat "$TOKEN_FILE")

# Function to monitor upload progress using lsof
monitor_upload_progress() {
    local pid=$1
    local file_path=$2
    local file_size=$3
    local start_time=$4
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting progress monitor for PID $pid"
    
    while kill -0 $pid 2>/dev/null; do
        # Get bytes read by curl process using lsof
        if command -v lsof >/dev/null 2>&1; then
            # Try to get file offset from lsof
            bytes_read=$(lsof -p $pid 2>/dev/null | grep -E "(REG|${TARGET_BASENAME})" | awk '{print $7}' | grep -E '^[0-9]+$' | sort -n | tail -1)
            
            if [[ -n "$bytes_read" ]] && [[ "$bytes_read" =~ ^[0-9]+$ ]]; then
                percent=$((bytes_read * 100 / file_size))
                bytes_read_gb=$(awk "BEGIN {printf \"%.2f\", $bytes_read / 1073741824}")
                
                current_time=$(date +%s)
                elapsed=$((current_time - start_time))
                
                if [[ $elapsed -gt 0 ]] && [[ $bytes_read -gt 0 ]]; then
                    speed_mbps=$(awk "BEGIN {printf \"%.1f\", ($bytes_read / 1048576) / $elapsed}")
                    
                    if [[ $percent -gt 0 ]] && [[ $percent -lt 100 ]]; then
                        eta_seconds=$((elapsed * (100 - percent) / percent))
                        eta_min=$((eta_seconds / 60))
                        eta_sec=$((eta_seconds % 60))
                        
                        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload progress: ${percent}% (${bytes_read_gb}/${FILE_SIZE_GB} GB) Speed: ${speed_mbps} MB/s ETA: ${eta_min}m ${eta_sec}s"
                    else
                        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload progress: ${percent}% (${bytes_read_gb}/${FILE_SIZE_GB} GB) Speed: ${speed_mbps} MB/s"
                    fi
                fi
            fi
        else
            # Fallback: just show time elapsed
            current_time=$(date +%s)
            elapsed=$((current_time - start_time))
            elapsed_min=$((elapsed / 60))
            elapsed_sec=$((elapsed % 60))
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload in progress... (elapsed: ${elapsed_min}m ${elapsed_sec}s)"
        fi
        
        sleep 30
    done
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Progress monitor stopped"
}

# Perform upload with retries
UPLOAD_SUCCESS=false

for attempt in $(seq 1 $RETRIES); do
    echo "Upload attempt $attempt of $RETRIES..."
    UPLOAD_START=$(date +%s)
    
    # Start curl in background to get PID
    curl --header "x-auth-token: $TOKEN" \
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
         --silent \
         "https://api.gdc.cancer.gov/v0/submission/$PROJECT_PATH/files/$FILE_UUID" > http_status.txt 2>curl_stderr.log &
    
    CURL_PID=$!
    echo "Started upload process with PID: $CURL_PID"
    
    # Start progress monitor
    monitor_upload_progress $CURL_PID "$TARGET_FILE" $FILE_SIZE $UPLOAD_START &
    MONITOR_PID=$!
    
    # Wait for curl to complete
    wait $CURL_PID
    CURL_EXIT_CODE=$?
    
    # Stop monitor
    kill $MONITOR_PID 2>/dev/null || true
    
    # Read HTTP status
    HTTP_STATUS=$(cat http_status.txt 2>/dev/null || echo "000")
    
    UPLOAD_END=$(date +%s)
    DURATION=$((UPLOAD_END - UPLOAD_START))
    DURATION_MIN=$((DURATION / 60))
    DURATION_SEC=$((DURATION % 60))
    
    if [[ $CURL_EXIT_CODE -eq 0 ]] && [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]; then
        echo "Upload completed successfully!"
        echo "HTTP status: $HTTP_STATUS"
        echo "Duration: ${DURATION_MIN}m ${DURATION_SEC}s"
        
        if [[ $DURATION -gt 0 ]]; then
            AVG_SPEED_MB=$(awk "BEGIN {printf \"%.2f\", ($FILE_SIZE / 1048576) / $DURATION}")
            echo "Average speed: ${AVG_SPEED_MB} MB/s"
        fi
        
        UPLOAD_SUCCESS=true
        break
    else
        echo "Upload failed on attempt $attempt"
        echo "HTTP status: $HTTP_STATUS"
        echo "Curl exit code: $CURL_EXIT_CODE"
        
        if [[ -f curl_stderr.log ]]; then
            echo "Curl errors:"
            cat curl_stderr.log
        fi
        
        if [[ $attempt -lt $RETRIES ]]; then
            echo "Retrying in 30 seconds..."
            sleep 30
        fi
    fi
done

# Generate report
cat > upload-report.tsv << EOF
file_name	file_uuid	file_path	status	attempts
$TARGET_BASENAME	$FILE_UUID	$TARGET_FILE	$(if $UPLOAD_SUCCESS; then echo "success"; else echo "failed"; fi)	$attempt
EOF

# Cleanup
rm -f http_status.txt curl_stderr.log

if $UPLOAD_SUCCESS; then
    echo "File upload completed successfully!"
    exit 0
else
    echo "File upload failed after $RETRIES attempts" >&2
    exit 2
fi