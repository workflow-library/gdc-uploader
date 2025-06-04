#!/bin/bash
# Simple GDC upload script using parallel execution

set -e

# Parse arguments
METADATA_FILE=""
TOKEN_FILE=""
THREADS=4
RETRIES=3

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--metadata)
            METADATA_FILE="$2"
            shift 2
            ;;
        -t|--token)
            TOKEN_FILE="$2"
            shift 2
            ;;
        -j|--threads)
            THREADS="$2"
            shift 2
            ;;
        -r|--retries)
            RETRIES="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$METADATA_FILE" ]] || [[ -z "$TOKEN_FILE" ]]; then
    echo "Usage: $0 -m <metadata.json> -t <token.txt> [-j threads] [-r retries]"
    exit 1
fi

# Function to upload a single file
upload_file() {
    local uuid=$1
    local filename=$2
    local token_file=$3
    
    echo "[$(date)] Starting upload: $filename (UUID: $uuid)"
    
    # Change to file directory (gdc-client requirement)
    local file_dir=$(dirname "$filename")
    local file_base=$(basename "$filename")
    
    (cd "$file_dir" && gdc-client upload -t "$token_file" "$uuid" --log-file "upload-$uuid.log" --upload-part-size 1073741824 -n 8 --resume)
    
    if [ $? -eq 0 ]; then
        echo "[$(date)] Success: $filename"
    else
        echo "[$(date)] Failed: $filename"
        return 1
    fi
}

# Export function for parallel
export -f upload_file

# Extract file info and run parallel uploads
echo "Starting parallel uploads with $THREADS threads..."

jq -r '.[] | "\(.id) \(.file_name)"' "$METADATA_FILE" | \
parallel -j "$THREADS" --retries "$RETRIES" --colsep ' ' \
    upload_file {1} {2} "$TOKEN_FILE"

echo "Upload complete!"