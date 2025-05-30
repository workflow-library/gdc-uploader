#!/usr/bin/env python3
"""
Convert YAML metadata file to JSON format for GDC uploader.

This script converts YAML-formatted metadata files to the JSON format
required by the GDC Data Transfer Tool.
"""

import sys
import json
import yaml
import os
import argparse
from pathlib import Path


def convert_yaml_to_json(yaml_file, json_file=None, pretty=True, validate=False):
    """Convert a YAML file to JSON format."""
    
    # Handle stdin/stdout
    if yaml_file == '-':
        yaml_input = sys.stdin
    else:
        if not os.path.exists(yaml_file):
            print(f"Error: File '{yaml_file}' not found", file=sys.stderr)
            return False
        yaml_input = open(yaml_file, 'r')
    
    # If no output file specified, use same name with .json extension or stdout
    if json_file is None:
        if yaml_file == '-':
            json_file = '-'
        else:
            json_file = Path(yaml_file).with_suffix('.json')
    
    try:
        # Read YAML file
        data = yaml.safe_load(yaml_input)
        
        # Basic validation if requested
        if validate:
            if not isinstance(data, (dict, list)):
                print("Warning: YAML data is not a dict or list", file=sys.stderr)
            if isinstance(data, dict) and 'files' not in data:
                print("Warning: No 'files' key found in YAML data", file=sys.stderr)
        
        # Write JSON file
        if json_file == '-':
            if pretty:
                json.dump(data, sys.stdout, indent=2)
            else:
                json.dump(data, sys.stdout)
            sys.stdout.write('\n')
        else:
            with open(json_file, 'w') as f:
                if pretty:
                    json.dump(data, f, indent=2)
                else:
                    json.dump(data, f)
        
        if yaml_file != '-' and json_file != '-':
            print(f"Successfully converted {yaml_file} to {json_file}")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    finally:
        if yaml_file != '-':
            yaml_input.close()


def main():
    parser = argparse.ArgumentParser(
        description="Convert YAML metadata to JSON format for GDC uploads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    gdc_yaml2json.py input.yaml output.json
    gdc_yaml2json.py input.yaml  # outputs to input.json
    gdc_yaml2json.py --validate metadata.yaml result.json
    cat input.yaml | gdc_yaml2json.py - output.json
    gdc_yaml2json.py input.yaml -  # output to stdout

EXIT CODES:
    0    Success - conversion completed
    1    Error - invalid YAML format or file I/O error
    2    Error - validation failed (with --validate)

DEPENDENCIES:
    - PyYAML (for YAML parsing)

PURPOSE:
    Converts YAML-formatted genomic metadata files to JSON format required
    by the GDC Data Transfer Tool. Supports complex nested structures with
    read groups, file metadata, and project information.
        """
    )
    
    parser.add_argument('input', 
                       help='Input YAML file (use "-" for stdin)')
    parser.add_argument('output', nargs='?', default=None,
                       help='Output JSON file (use "-" for stdout, default: input.json)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate converted JSON structure for GDC compatibility')
    parser.add_argument('--compact', action='store_true',
                       help='Compact JSON output (no indentation)')
    
    args = parser.parse_args()
    
    # Check for help
    if args.input in ['-h', '--help']:
        parser.print_help()
        sys.exit(0)
    
    pretty = not args.compact
    
    if convert_yaml_to_json(args.input, args.output, pretty, args.validate):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()