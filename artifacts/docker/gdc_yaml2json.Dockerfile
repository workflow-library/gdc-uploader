# Dockerfile for gdc_yaml2json
# Convert YAML metadata files to JSON format required by GDC
# Generated from prompt: gdc_yaml2json.md

FROM ubuntu:22.04

# Labels
LABEL maintainer="GDC Uploader Team"
LABEL version="1.0.0"
LABEL description="Convert YAML metadata files to JSON format required by GDC"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    python3 \
    python3-pip \
    jq \
    parallel && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install gdc-client
RUN wget https://gdc.cancer.gov/files/public/file/gdc-client_v1.6.1_Ubuntu_x64.zip && \
    unzip gdc-client_v1.6.1_Ubuntu_x64.zip && \
    mv gdc-client /usr/local/bin/ && \
    chmod +x /usr/local/bin/gdc-client && \
    rm gdc-client_v1.6.1_Ubuntu_x64.zip

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy application files
WORKDIR /app

# Copy scripts
COPY scripts/gdc_yaml2json.sh /app/
RUN chmod +x /app/gdc_yaml2json.sh

# Set working directory
WORKDIR /data

# Note: No CMD or ENTRYPOINT - will be specified by CWL