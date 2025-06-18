"""Utility functions for GDC Uploader."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


def yaml_to_json(yaml_file: Union[str, Path], json_file: Optional[Union[str, Path]] = None, 
                 pretty: bool = True, validate: bool = False) -> bool:
    """Convert a YAML file to JSON format.
    
    Args:
        yaml_file: Input YAML file path or '-' for stdin
        json_file: Output JSON file path or '-' for stdout (default: same name with .json)
        pretty: Pretty-print JSON output
        validate: Validate the converted data structure
        
    Returns:
        True if successful, False otherwise
    """
    # Handle stdin/stdout
    if str(yaml_file) == '-':
        yaml_input = sys.stdin
    else:
        yaml_path = Path(yaml_file)
        if not yaml_path.exists():
            print(f"Error: File '{yaml_file}' not found", file=sys.stderr)
            return False
        yaml_input = open(yaml_path, 'r')
    
    # If no output file specified, use same name with .json extension or stdout
    if json_file is None:
        if str(yaml_file) == '-':
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
        if str(json_file) == '-':
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
        
        if str(yaml_file) != '-' and str(json_file) != '-':
            print(f"Successfully converted {yaml_file} to {json_file}")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    finally:
        if str(yaml_file) != '-' and hasattr(yaml_input, 'close'):
            yaml_input.close()


def filter_json(input_file: Union[str, Path], output_file: Union[str, Path],
                filter_field: str, filter_values: List[str]) -> bool:
    """Filter JSON array by field values.
    
    Args:
        input_file: Input JSON file path
        output_file: Output JSON file path
        filter_field: Field name to filter by
        filter_values: List of values to match
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            print(f"Error: Input JSON must be an array", file=sys.stderr)
            return False
            
        # Filter data
        filtered = [
            item for item in data
            if filter_field in item and str(item[filter_field]) in filter_values
        ]
        
        # Write output
        with open(output_file, 'w') as f:
            json.dump(filtered, f, indent=2)
            
        print(f"Filtered {len(data)} items to {len(filtered)} items")
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def split_json(input_file: Union[str, Path], output_dir: Union[str, Path] = ".",
               split_field: str = "id", prefix: str = "split") -> bool:
    """Split JSON array into individual files.
    
    Args:
        input_file: Input JSON file path
        output_dir: Directory to write split files
        split_field: Field to use for naming split files
        prefix: Prefix for output filenames
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            print(f"Error: Input JSON must be an array", file=sys.stderr)
            return False
            
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Split data into individual files
        for i, item in enumerate(data):
            if split_field in item:
                filename = f"{prefix}_{item[split_field]}.json"
            else:
                filename = f"{prefix}_{i:04d}.json"
                
            output_file = output_path / filename
            with open(output_file, 'w') as f:
                json.dump(item, f, indent=2)
                
        print(f"Split {len(data)} items into individual files in {output_dir}")
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False