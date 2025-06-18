"""Notebook emitter for generating Quarto notebooks from prompts."""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class NotebookEmitter:
    """Generate Quarto (.qmd) notebooks from parsed prompts."""
    
    def emit(self, prompt_data: Dict[str, Any], output_path: Path) -> None:
        """Generate a Quarto notebook from parsed prompt data.
        
        Args:
            prompt_data: Parsed prompt data from PromptParser
            output_path: Path to write the .qmd file
        """
        notebook_content = self._generate_notebook(prompt_data)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(notebook_content)
            
    def _generate_notebook(self, data: Dict[str, Any]) -> str:
        """Generate Quarto notebook content from prompt data."""
        metadata = data.get('metadata', {})
        inputs = data.get('inputs', [])
        outputs = data.get('outputs', [])
        command = data.get('command', '')
        sections = data.get('sections', {})
        
        lines = []
        
        # YAML frontmatter
        lines.extend([
            '---',
            f'title: "{metadata.get("name", "Tool")} - Tutorial and Documentation"',
            f'author: "GDC Uploader Team"',
            f'date: "{datetime.now().strftime("%Y-%m-%d")}"',
            'format:',
            '  html:',
            '    code-fold: true',
            '    code-tools: true',
            'jupyter: python3',
            '---',
            ''
        ])
        
        # Title and description
        lines.extend([
            f'# {metadata.get("name", "Tool")}',
            '',
            f'{metadata.get("description", "Tool description")}',
            '',
            f'**Version**: {metadata.get("version", "1.0.0")}',
            ''
        ])
        
        # Overview section
        lines.extend([
            '## Overview',
            '',
            'This notebook provides documentation and examples for using the',
            f'{metadata.get("name", "tool")} tool. It demonstrates:',
            '',
            '- How to prepare input files',
            '- How to run the tool',
            '- How to interpret outputs',
            '- Common use cases and troubleshooting',
            ''
        ])
        
        # Installation section
        lines.extend([
            '## Installation',
            '',
            '### Using Docker',
            '',
            '```bash',
            f'docker pull {metadata.get("docker_image", "ghcr.io/open-workflow-library/gdc-uploader:latest")}',
            '```',
            '',
            '### Using Python Package',
            '',
            '```bash',
            'pip install gdc-uploader',
            '```',
            ''
        ])
        
        # Inputs section
        if inputs:
            lines.extend([
                '## Input Requirements',
                '',
                'This tool requires the following inputs:',
                ''
            ])
            
            for inp in inputs:
                lines.append(f'- **{inp["name"]}** ({inp.get("type", "File")}): {inp.get("description", "")}')
            lines.append('')
            
        # Usage section
        lines.extend([
            '## Usage Examples',
            '',
            '### Command Line Usage',
            '',
            '```bash'
        ])
        
        if command:
            # Show example command
            example_cmd = command
            for inp in inputs:
                example_cmd = example_cmd.replace(f'{{{inp["name"]}}}', f'path/to/{inp["name"]}')
            lines.append(example_cmd)
        else:
            lines.append(f'{metadata.get("name", "tool")} --help')
            
        lines.extend(['```', ''])
        
        # Python usage example
        lines.extend([
            '### Python API Usage',
            '',
            '```python',
            'from gdc_uploader import StandardUploader',
            'from pathlib import Path',
            '',
            '# Initialize uploader',
            'uploader = StandardUploader(',
            '    metadata_file=Path("metadata.json"),',
            '    token_file=Path("token.txt"),',
            '    thread_count=4',
            ')',
            '',
            '# Discover and upload files',
            'files = uploader.discover_files(Path("/data/files"))',
            'results = uploader.upload_files(files)',
            '',
            '# Generate report',
            'report = uploader.generate_report(results)',
            'print(report)',
            '```',
            ''
        ])
        
        # Outputs section
        if outputs:
            lines.extend([
                '## Output Description',
                '',
                'The tool produces the following outputs:',
                ''
            ])
            
            for out in outputs:
                lines.append(f'- **{out["name"]}** ({out.get("type", "File")}): {out.get("description", "")}')
            lines.append('')
            
        # Add any additional sections from the prompt
        for section_name, content in sections.items():
            if section_name not in ['Inputs', 'Outputs', 'Command']:
                lines.extend([
                    f'## {section_name}',
                    '',
                    content,
                    ''
                ])
                
        # Troubleshooting section
        lines.extend([
            '## Troubleshooting',
            '',
            '### Common Issues',
            '',
            '1. **Authentication Error**: Ensure your GDC token is valid and not expired',
            '2. **File Not Found**: Check that file paths in metadata match actual file locations',
            '3. **Network Issues**: Verify internet connectivity and GDC API availability',
            '',
            '### Getting Help',
            '',
            'For additional help:',
            '- Check the [GDC Documentation](https://docs.gdc.cancer.gov/)',
            '- Submit issues to the [GitHub repository](https://github.com/open-workflow-library/gdc-uploader)',
            ''
        ])
        
        return '\n'.join(lines)