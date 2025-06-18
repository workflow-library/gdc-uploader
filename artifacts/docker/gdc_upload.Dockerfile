# Dockerfile for gdc_upload
# Upload genomic data files to the NCI Genomic Data Commons using parallel processing
# Generated from prompt: gdc_upload.md

FROM ubuntu:22.04

# Labels
LABEL maintainer="GDC Uploader Team"
LABEL version="2.0.0"
LABEL description="Upload genomic data files to the NCI Genomic Data Commons using parallel processing"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    python3 \
    python3-pip \
    jq \
    parallel \
    parallel \
    jq && \
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

# Copy and install gdc-uploader package
COPY . /app/
RUN pip3 install -e .

# Set working directory
WORKDIR /data

# Note: No CMD or ENTRYPOINT - will be specified by CWL