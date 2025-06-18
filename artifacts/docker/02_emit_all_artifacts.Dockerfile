# Dockerfile for tool
# 
# Generated from prompt: unknown.md

FROM ubuntu:22.04

# Labels
LABEL maintainer="GDC Uploader Team"
LABEL version="1.0.0"
LABEL description=""

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

# Copy application files
WORKDIR /app

# Copy scripts
COPY scripts/tool.sh /app/
RUN chmod +x /app/tool.sh

# Set working directory
WORKDIR /data

# Note: No CMD or ENTRYPOINT - will be specified by CWL