# Build stage
FROM mcr.microsoft.com/dotnet/sdk:5.0 AS build
WORKDIR /src

# Copy solution and project files
COPY upload2gdc.sln .
COPY src/upload2gdc/upload2gdc.csproj src/upload2gdc/
COPY tests/gdc-client-simulator/gdc-client-simulator.csproj tests/gdc-client-simulator/

# Restore dependencies
RUN dotnet restore

# Copy source code
COPY src/ src/
COPY tests/ tests/

# Build the application
RUN dotnet build -c Release --no-restore

# Publish the application
RUN dotnet publish src/upload2gdc/upload2gdc.csproj -c Release -o /app/publish --no-restore

# Runtime stage
FROM mcr.microsoft.com/dotnet/runtime:5.0
WORKDIR /app

# Install dependencies for gdc-client
RUN apt-get update && \
    apt-get install -y \
    wget \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install gdc-client
RUN wget https://gdc.cancer.gov/files/public/file/gdc-client_v1.6.1_Ubuntu_x64.zip -O /tmp/gdc-client.zip && \
    unzip /tmp/gdc-client.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/gdc-client && \
    rm /tmp/gdc-client.zip

# Copy published application
COPY --from=build /app/publish .

# Create directories for data and logs
RUN mkdir -p /data /logs /metadata

# Set environment variables
ENV PATH="/usr/local/bin:${PATH}"
