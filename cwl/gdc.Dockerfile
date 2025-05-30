FROM ubuntu:20.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    wget \
    unzip \
    ca-certificates \
    curl \
    jq \
    parallel \
    bash \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install PyYAML

# Download and install gdc-client
RUN wget https://gdc.cancer.gov/files/public/file/gdc-client_v1.6.1_Ubuntu_x64.zip -O /tmp/gdc-client.zip && \
    unzip /tmp/gdc-client.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/gdc-client && \
    rm /tmp/gdc-client.zip

# Copy scripts from cwl directory
COPY gdc_upload.sh gdc_direct-upload.sh gdc_yaml2json.py /app/scripts/
RUN chmod +x /app/scripts/*.sh

# Create directories for data and logs
RUN mkdir -p /data /logs /metadata

# Set environment variables
ENV PATH="/usr/local/bin:/app/scripts:${PATH}"

WORKDIR /app