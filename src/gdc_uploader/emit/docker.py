"""Docker emitter for generating Dockerfiles from prompts."""

from pathlib import Path
from typing import Dict, Any, List


class DockerEmitter:
    """Generate Dockerfiles from parsed prompts."""
    
    def emit(self, prompt_data: Dict[str, Any], output_path: Path) -> None:
        """Generate a Dockerfile from parsed prompt data.
        
        Args:
            prompt_data: Parsed prompt data from PromptParser
            output_path: Path to write the Dockerfile
        """
        dockerfile_content = self._generate_dockerfile(prompt_data)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(dockerfile_content)
            
    def _generate_dockerfile(self, data: Dict[str, Any]) -> str:
        """Generate Dockerfile content from prompt data."""
        metadata = data.get('metadata', {})
        requirements = data.get('requirements', {})
        
        lines = []
        
        # Header comment
        lines.extend([
            f'# Dockerfile for {metadata.get("name", "tool")}',
            f'# {metadata.get("description", "")}',
            f'# Generated from prompt: {metadata.get("name", "unknown")}.md',
            ''
        ])
        
        # Base image
        base_image = requirements.get('base_image', 'ubuntu:22.04')
        lines.append(f'FROM {base_image}')
        lines.append('')
        
        # Labels
        lines.extend([
            '# Labels',
            f'LABEL maintainer="GDC Uploader Team"',
            f'LABEL version="{metadata.get("version", "1.0.0")}"',
            f'LABEL description="{metadata.get("description", "")}"',
            ''
        ])
        
        # Install system dependencies
        lines.extend([
            '# Install system dependencies',
            'RUN apt-get update && apt-get install -y \\'
        ])
        
        # Default system packages
        system_packages = [
            'wget',
            'curl', 
            'python3',
            'python3-pip',
            'jq',
            'parallel'
        ]
        
        # Add any additional packages from requirements
        if 'system_packages' in requirements:
            system_packages.extend(requirements['system_packages'])
            
        for i, pkg in enumerate(system_packages):
            if i < len(system_packages) - 1:
                lines.append(f'    {pkg} \\')
            else:
                lines.append(f'    {pkg} && \\')
        
        lines.extend([
            '    apt-get clean && \\',
            '    rm -rf /var/lib/apt/lists/*',
            ''
        ])
        
        # Install gdc-client if needed
        if metadata.get('name', '').startswith('gdc'):
            lines.extend([
                '# Install gdc-client',
                'RUN wget https://gdc.cancer.gov/files/public/file/gdc-client_v1.6.1_Ubuntu_x64.zip && \\',
                '    unzip gdc-client_v1.6.1_Ubuntu_x64.zip && \\',
                '    mv gdc-client /usr/local/bin/ && \\',
                '    chmod +x /usr/local/bin/gdc-client && \\',
                '    rm gdc-client_v1.6.1_Ubuntu_x64.zip',
                ''
            ])
            
        # Python dependencies
        if 'python_packages' in requirements or metadata.get('name') == 'gdc_upload':
            lines.extend([
                '# Install Python dependencies',
                'COPY requirements.txt /tmp/',
                'RUN pip3 install --no-cache-dir -r /tmp/requirements.txt',
                ''
            ])
            
        # Copy application files
        lines.extend([
            '# Copy application files',
            'WORKDIR /app',
            ''
        ])
        
        # For gdc_upload, copy the package
        if metadata.get('name') == 'gdc_upload':
            lines.extend([
                '# Copy and install gdc-uploader package',
                'COPY . /app/',
                'RUN pip3 install -e .',
                ''
            ])
        else:
            # Copy scripts
            lines.extend([
                '# Copy scripts',
                f'COPY scripts/{metadata.get("name", "tool")}.sh /app/',
                f'RUN chmod +x /app/{metadata.get("name", "tool")}.sh',
                ''
            ])
            
        # Set working directory
        lines.extend([
            '# Set working directory',
            'WORKDIR /data',
            ''
        ])
        
        # Note: No CMD or ENTRYPOINT per project requirements
        lines.append('# Note: No CMD or ENTRYPOINT - will be specified by CWL')
        
        return '\n'.join(lines)