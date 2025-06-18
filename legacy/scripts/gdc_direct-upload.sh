#!/bin/bash
# Backward compatibility wrapper for gdc_direct-upload.sh
# This script now calls the Python package
exec gdc-direct-upload "$@"