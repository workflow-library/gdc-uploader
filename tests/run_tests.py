#!/usr/bin/env python3
"""Test runner for GDC uploader utility modules."""

import sys
import pytest
import logging
from pathlib import Path

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    """Run all tests."""
    logging.basicConfig(level=logging.INFO)
    
    # Test arguments
    args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--cov=gdc_uploader.core",  # Coverage for core modules
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html",  # Generate HTML coverage report
        str(Path(__file__).parent / "unit"),  # Test directory
    ]
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    # Run tests
    exit_code = pytest.main(args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())