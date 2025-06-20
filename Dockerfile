FROM python:3.11-slim

# Install the package and dependencies
WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /data

# Set working directory
WORKDIR /data

# No ENTRYPOINT or CMD for CWL compatibility