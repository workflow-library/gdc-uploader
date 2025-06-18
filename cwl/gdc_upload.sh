#!/bin/bash
# Backward compatibility wrapper for gdc_upload.sh
# This script now calls the Python package
exec gdc-upload "$@"