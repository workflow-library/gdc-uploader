#!/usr/bin/env python3
# Backward compatibility wrapper for gdc_yaml2json.py
# This script now calls the Python package
import sys
from gdc_uploader.cli import yaml2json

if __name__ == "__main__":
    yaml2json()