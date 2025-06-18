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

# Download and install gdc-client
RUN wget https://gdc.cancer.gov/files/public/file/gdc-client_v1.6.1_Ubuntu_x64.zip -O /tmp/gdc-client.zip && \
    unzip /tmp/gdc-client.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/gdc-client && \
    rm /tmp/gdc-client.zip

# Copy Python package files
COPY pyproject.toml setup.py requirements.txt /app/
COPY src/ /app/src/

# Install the gdc-uploader package
WORKDIR /app
RUN pip3 install --no-cache-dir -e .

# Copy shell script wrappers for backward compatibility
COPY cwl/*.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh

# Create directories for data and logs
RUN mkdir -p /data /logs /metadata

# Set environment variables
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /data