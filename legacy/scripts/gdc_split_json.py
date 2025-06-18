#!/usr/bin/env python3
"""
Split GDC metadata JSON file by file_name into individual JSON files.

This script takes a GDC metadata JSON file containing multiple files
and creates separate JSON files for each file_name entry.
"""

import sys
import json
import os
import argparse
from pathlib import Path
import re


def sanitize_filename(filename):
    """Sanitize filename for use as output filename."""
    # Remove or replace characters that aren't filesystem-safe
    # Keep alphanumeric, dots, hyphens, underscores
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


def split_json_by_filename(input_file, output_dir=None, prefix="", suffix="", pretty=True):
    """Split JSON file by file_name into separate files."""
    
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
    
    # Set output directory
    if output_dir is None:
        if input_file == '-':
            output_dir = '.'
        else:
            output_dir = Path(input_file).parent
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Read JSON file
        data = json.load(json_input)
        
        # Validate structure
        if not isinstance(data, dict):
            print("Error: JSON data must be an object", file=sys.stderr)
            return False
        
        if 'files' not in data:
            print("Error: No 'files' array found in JSON", file=sys.stderr)
            return False
        
        files_array = data['files']
        if not isinstance(files_array, list):
            print("Error: 'files' must be an array", file=sys.stderr)
            return False
        
        print(f"Processing {len(files_array)} files from {input_name}")
        
        created_files = []
        
        # Process each file
        for i, file_obj in enumerate(files_array):
            if not isinstance(file_obj, dict):
                print(f"Warning: Skipping non-object file entry at index {i}", file=sys.stderr)
                continue
            
            if 'file_name' not in file_obj:
                print(f"Warning: Skipping file entry at index {i} - no 'file_name' field", file=sys.stderr)
                continue
            
            file_name = file_obj['file_name']
            
            # Create sanitized output filename
            sanitized_name = sanitize_filename(file_name)
            output_filename = f"{prefix}{sanitized_name}{suffix}.json"
            output_file_path = output_path / output_filename
            
            # Create new JSON structure with single file
            single_file_data = {
                'files': [file_obj]
            }
            
            # Write individual file
            with open(output_file_path, 'w') as f:
                if pretty:
                    json.dump(single_file_data, f, indent=2)
                else:
                    json.dump(single_file_data, f)
            
            created_files.append(output_file_path)
            print(f"Created: {output_file_path}")
        
        print(f"\nSuccessfully created {len(created_files)} JSON files in {output_path}")
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
        description="Split GDC metadata JSON file by file_name into individual JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    gdc_split_json.py metadata.json
    gdc_split_json.py metadata.json --output-dir ./split-files/
    gdc_split_json.py input.json --prefix "file_" --suffix "_metadata"
    cat metadata.json | gdc_split_json.py - --output-dir ./output/
    gdc_split_json.py metadata.json --compact

OUTPUT:
    Creates one JSON file per file_name entry in the input.
    Each output file contains a single file entry in the same format
    as the original (with "files" array containing one object).

FILENAME SANITIZATION:
    File names are sanitized for filesystem compatibility:
    - Non-alphanumeric characters become underscores
    - Multiple underscores are collapsed
    - Leading/trailing underscores are removed

EXIT CODES:
    0    Success - all files created
    1    Error - invalid JSON or file I/O error
    2    Error - invalid input structure

DEPENDENCIES:
    - Python 3.6+ (for pathlib)

PURPOSE:
    Splits large GDC metadata files into individual files for per-file
    processing, upload tracking, or workflow distribution.
        """
    )
    
    parser.add_argument('input', 
                       help='Input JSON file (use "-" for stdin)')
    parser.add_argument('--output-dir', '-o', 
                       help='Output directory (default: same as input file)')
    parser.add_argument('--prefix', '-p', default='',
                       help='Prefix for output filenames')
    parser.add_argument('--suffix', '-s', default='',
                       help='Suffix for output filenames (before .json)')
    parser.add_argument('--compact', action='store_true',
                       help='Compact JSON output (no indentation)')
    
    args = parser.parse_args()
    
    pretty = not args.compact
    
    if split_json_by_filename(args.input, args.output_dir, args.prefix, args.suffix, pretty):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()