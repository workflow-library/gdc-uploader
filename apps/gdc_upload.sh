#!/bin/bash
# GDC Upload Wrapper for CWL
# This script provides the interface between CWL and the direct gdc-client uploads

set -e

# Initialize variables
METADATA_FILE=""
TOKEN_FILE=""
THREADS=4
RETRIES=3
FILES_DIR=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m)
            METADATA_FILE="$2"
            shift 2
            ;;
        -t)
            TOKEN_FILE="$2"
            shift 2
            ;;
        -j)
            THREADS="$2"
            shift 2
            ;;
        -r)
            RETRIES="$2"
            shift 2
            ;;
        *)
            # Assume it's the files directory if not a flag
            if [[ -d "$1" ]]; then
                FILES_DIR="$1"
            fi
            shift
            ;;
    esac
done

# Validate required inputs
if [[ -z "$METADATA_FILE" ]]; then
    echo "Error: Metadata file is required (-m flag)"
    exit 1
fi

if [[ -z "$TOKEN_FILE" ]]; then
    echo "Error: Token file is required (-t flag)"
    exit 1
fi

# Function to upload a single file
upload_file() {
    local uuid=$1
    local filename=$2
    local token_file=$3
    local files_dir=$4
    
    echo "[$(date)] Starting upload: $filename (UUID: $uuid)"
    
    # Search for the file in various locations
    local found_file=""
    
    # Check in subdirectories first (fastq/, uBam/, sequence-files/)
    for subdir in "fastq" "uBam" "sequence-files" ""; do
        if [[ -n "$subdir" ]]; then
            test_path="$files_dir/$subdir/$filename"
        else
            test_path="$files_dir/$filename"
        fi
        
        if [[ -f "$test_path" ]]; then
            found_file="$test_path"
            break
        fi
    done
    
    # If not found, search recursively
    if [[ -z "$found_file" ]]; then
        found_file=$(find "$files_dir" -name "$filename" -type f 2>/dev/null | head -1)
    fi
    
    if [[ -n "$found_file" ]]; then
        # Change to file directory (gdc-client requirement)
        local file_dir=$(dirname "$found_file")
        local file_base=$(basename "$found_file")
        
        echo "[$(date)] Found file at: $found_file"
        
        # Run gdc-client from the file's directory
        (cd "$file_dir" && gdc-client upload -t "$token_file" "$uuid" --log-file "upload-$uuid.log" 2>&1)
        
        if [ $? -eq 0 ]; then
            echo "[$(date)] Success: $filename"
            echo -e "$uuid\t$filename\t$found_file\tSUCCESS" >> upload-report.tsv
        else
            echo "[$(date)] Failed: $filename"
            echo -e "$uuid\t$filename\t$found_file\tFAILED" >> upload-report.tsv
            return 1
        fi
    else
        echo "[$(date)] File not found: $filename"
        echo -e "$uuid\t$filename\tNOT_FOUND\tFAILED" >> upload-report.tsv
        return 1
    fi
}

# Export function for parallel
export -f upload_file

# Initialize report
echo -e "UUID\tFILENAME\tPATH\tSTATUS" > upload-report.tsv

# If no files directory specified, try to find it
if [[ -z "$FILES_DIR" ]]; then
    # Look for common directory names
    for dir in "." "./test-data" "./data" "./files"; do
        if [[ -d "$dir" ]]; then
            FILES_DIR="$dir"
            break
        fi
    done
fi

if [[ -z "$FILES_DIR" ]]; then
    echo "Error: Could not find files directory"
    exit 1
fi

echo "Starting parallel uploads with $THREADS threads..."
echo "Metadata file: $METADATA_FILE"
echo "Token file: $TOKEN_FILE"
echo "Files directory: $FILES_DIR"
echo "Retries: $RETRIES"

# Extract file info and run parallel uploads
jq -r '.[] | "\(.id) \(.file_name)"' "$METADATA_FILE" | \
parallel -j "$THREADS" --retries "$RETRIES" --colsep ' ' \
    upload_file {1} {2} "$TOKEN_FILE" "$FILES_DIR"

echo "Upload complete!"
echo "Results saved to: upload-report.tsv"

# Copy any log files to current directory
find "$FILES_DIR" -name "upload-*.log" -type f -exec cp {} . \; 2>/dev/null || true