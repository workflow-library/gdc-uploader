#!/usr/bin/env python3
"""
Filter GDC metadata JSON file by specific file_name.

This script takes a GDC metadata JSON file and a target filename,
then returns a filtered JSON containing only the matching file entry.
"""

import sys
import json
import os
import argparse
from pathlib import Path


def filter_json_by_filename(input_file, target_filename, output_file=None, pretty=True, strict=False):
    """Filter JSON file to include only entries matching the target filename."""
    
    # Handle stdin
    if input_file == '-':
        json_input = sys.stdin
        input_name = "stdin"
    else:
        if not os.path.exists(input_file):
            print(f"Error: File '{input_file}' not found", file=sys.stderr)
            return False
        json_input = open(input_file, 'r')
        input_name = input_file
    
    # Set output file
    if output_file is None:
        if input_file == '-':
            output_file = '-'
        else:
            # Default: add "_filtered" before .json extension
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_filtered.json"
    
    try:
        # Read JSON file
        data = json.load(json_input)
        
        # Handle both array and object formats
        if isinstance(data, list):
            # Direct array format
            files_array = data
        elif isinstance(data, dict):
            # Object with 'files' property
            if 'files' not in data:
                print("Error: No 'files' array found in JSON object", file=sys.stderr)
                return False
            files_array = data['files']
            if not isinstance(files_array, list):
                print("Error: 'files' must be an array", file=sys.stderr)
                return False
        else:
            print("Error: JSON data must be an array or object", file=sys.stderr)
            return False
        
        print(f"Searching {len(files_array)} files from {input_name} for: {target_filename}")
        
        # Filter files that match the target filename
        matching_files = []
        
        for i, file_obj in enumerate(files_array):
            if not isinstance(file_obj, dict):
                print(f"Warning: Skipping non-object file entry at index {i}", file=sys.stderr)
                continue
            
            if 'file_name' not in file_obj:
                print(f"Warning: Skipping file entry at index {i} - no 'file_name' field", file=sys.stderr)
                continue
            
            file_name = file_obj['file_name']
            
            # Check for match
            if strict:
                # Exact match
                if file_name == target_filename:
                    matching_files.append(file_obj)
                    print(f"Exact match found: {file_name}")
            else:
                # Partial match (case-insensitive)
                if target_filename.lower() in file_name.lower():
                    matching_files.append(file_obj)
                    print(f"Partial match found: {file_name}")
        
        if not matching_files:
            print(f"No files found matching: {target_filename}", file=sys.stderr)
            if not strict:
                print("Try using --strict for exact matching", file=sys.stderr)
            return False
        
        # Create filtered JSON structure matching input format
        if isinstance(data, list):
            # If input was array, output as array
            filtered_data = matching_files
        else:
            # If input was object, output as object
            filtered_data = {
                'files': matching_files
            }
            
            # Add metadata about the filter
            filtered_data['_filter_info'] = {
                'target_filename': target_filename,
                'original_count': len(files_array),
                'filtered_count': len(matching_files),
                'match_type': 'exact' if strict else 'partial'
            }
        
        # Write output
        if output_file == '-':
            if pretty:
                json.dump(filtered_data, sys.stdout, indent=2)
            else:
                json.dump(filtered_data, sys.stdout)
            sys.stdout.write('\n')
        else:
            with open(output_file, 'w') as f:
                if pretty:
                    json.dump(filtered_data, f, indent=2)
                else:
                    json.dump(filtered_data, f)
        
        if output_file != '-':
            print(f"Filtered JSON written to: {output_file}")
        
        print(f"Found {len(matching_files)} matching file(s)")
        return True
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    finally:
        if input_file != '-':
            json_input.close()


def main():
    parser = argparse.ArgumentParser(
        description="Filter GDC metadata JSON file by specific file_name",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    gdc_filter_json.py metadata.json "_1_MP2PRT-GAAEYL-NT1-A-1-0-D-A93A-48.final.bam"
    gdc_filter_json.py metadata.json "sample1.bam" --output filtered.json
    gdc_filter_json.py input.json "GAAEYL" --strict
    cat metadata.json | gdc_filter_json.py - "MP2PRT-GAAEYL" --output filtered.json
    gdc_filter_json.py metadata.json "sample1" --compact

MATCHING:
    By default, uses partial matching (case-insensitive).
    Use --strict for exact filename matching.
    
    Partial: "GAAEYL" matches "_1_MP2PRT-GAAEYL-NT1-A-1-0-D-A93A-48.final.bam"
    Strict: Only exact filename matches are returned

OUTPUT:
    Creates a JSON file with the same structure as input but containing
    only the files that match the target filename. Includes metadata
    about the filtering operation in "_filter_info".

EXIT CODES:
    0    Success - matching files found and written
    1    Error - invalid JSON or file I/O error
    2    Error - no matching files found

DEPENDENCIES:
    - Python 3.6+ (for pathlib)

PURPOSE:
    Extracts specific file metadata from large GDC metadata files for
    targeted processing, validation, or upload operations.
        """
    )
    
    parser.add_argument('input', 
                       help='Input JSON file (use "-" for stdin)')
    parser.add_argument('filename',
                       help='Target file or filename to filter for (automatically extracts basename from file paths)')
    parser.add_argument('--output', '-o', 
                       help='Output JSON file (use "-" for stdout, default: input_filtered.json)')
    parser.add_argument('--strict', action='store_true',
                       help='Use exact filename matching (default: partial matching)')
    parser.add_argument('--compact', action='store_true',
                       help='Compact JSON output (no indentation)')
    
    args = parser.parse_args()
    
    # Extract basename from filename argument (handles both files and strings)
    target_filename = os.path.basename(args.filename)
    
    pretty = not args.compact
    
    if filter_json_by_filename(args.input, target_filename, args.output, pretty, args.strict):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()