"""CWL emitter for generating CWL tool definitions from prompts."""

from pathlib import Path
from typing import Dict, Any, List


class CWLEmitter:
    """Generate CWL tool definitions from parsed prompts."""
    
    def __init__(self):
        self.cwl_version = "v1.2"
        
    def emit(self, prompt_data: Dict[str, Any], output_path: Path) -> None:
        """Generate a CWL file from parsed prompt data.
        
        Args:
            prompt_data: Parsed prompt data from PromptParser
            output_path: Path to write the CWL file
        """
        cwl_content = self._generate_cwl(prompt_data)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(cwl_content)
            
    def _generate_cwl(self, data: Dict[str, Any]) -> str:
        """Generate CWL content from prompt data."""
        metadata = data.get('metadata', {})
        inputs = data.get('inputs', [])
        outputs = data.get('outputs', [])
        command = data.get('command', '')
        requirements = data.get('requirements', {})
        
        # Build CWL content
        lines = ['#!/usr/bin/env cwl-runner', '']
        
        # Metadata section
        lines.extend([
            '# ' + '=' * 78,
            '# CWL METADATA SECTION',
            '# ' + '=' * 78,
            f'cwlVersion: {self.cwl_version}',
            'class: CommandLineTool',
            f'label: "{metadata.get("name", "Tool")}"',
            'doc: |',
            f'  {metadata.get("description", "Tool description")}',
            f'  ',
            f'  Version: {metadata.get("version", "1.0.0")}',
            f'  Generated from prompt: {metadata.get("name", "unknown")}.md',
            ''
        ])
        
        # Requirements section
        if metadata.get('docker_image') or requirements:
            lines.extend([
                '# ' + '=' * 78,
                '# REQUIREMENTS SECTION',
                '# ' + '=' * 78,
                'requirements:'
            ])
            
            if metadata.get('docker_image'):
                lines.extend([
                    '  DockerRequirement:',
                    f'    dockerPull: "{metadata["docker_image"]}"'
                ])
                
            if requirements.get('ram_min'):
                lines.extend([
                    '  ResourceRequirement:',
                    f'    ramMin: {requirements["ram_min"]}',
                    f'    coresMin: {requirements.get("cores_min", 1)}'
                ])
            lines.append('')
            
        # Base command
        lines.extend([
            '# ' + '=' * 78,
            '# COMMAND SECTION', 
            '# ' + '=' * 78
        ])
        
        # Extract base command from command string
        if command:
            base_cmd = command.split()[0]
            lines.append(f'baseCommand: ["{base_cmd}"]')
        else:
            lines.append(f'baseCommand: ["{metadata.get("name", "tool")}"]')
        lines.append('')
        
        # Inputs section
        if inputs:
            lines.extend([
                '# ' + '=' * 78,
                '# INPUTS SECTION',
                '# ' + '=' * 78,
                'inputs:'
            ])
            
            for inp in inputs:
                lines.extend(self._format_input(inp))
            lines.append('')
            
        # Outputs section
        if outputs:
            lines.extend([
                '# ' + '=' * 78,
                '# OUTPUTS SECTION',
                '# ' + '=' * 78,
                'outputs:'
            ])
            
            for out in outputs:
                lines.extend(self._format_output(out))
                
        return '\n'.join(lines)
        
    def _format_input(self, inp: Dict[str, Any]) -> List[str]:
        """Format a single input specification."""
        lines = [f'  {inp["name"]}:']
        
        # Map types
        cwl_type = self._map_type(inp.get('type', 'File'))
        lines.append(f'    type: {cwl_type}')
        
        # Add input binding if needed
        if inp['name'] in ['metadata_file', 'token_file']:
            prefix = '-m' if inp['name'] == 'metadata_file' else '-t'
            lines.extend([
                '    inputBinding:',
                f'      prefix: {prefix}'
            ])
        elif cwl_type == 'Directory':
            lines.extend([
                '    inputBinding:',
                '      position: 1'
            ])
            
        lines.append(f'    doc: "{inp.get("description", "")}"')
        return lines
        
    def _format_output(self, out: Dict[str, Any]) -> List[str]:
        """Format a single output specification."""
        lines = [f'  {out["name"]}:']
        
        cwl_type = self._map_type(out.get('type', 'File'))
        lines.append(f'    type: {cwl_type}')
        
        # Add output binding
        if out['name'] == 'upload_report':
            lines.extend([
                '    outputBinding:',
                '      glob: "upload-report.tsv"'
            ])
        elif out['name'] == 'log_files':
            lines.extend([
                '    outputBinding:',
                '      glob: "*.log"'
            ])
            
        lines.append(f'    doc: "{out.get("description", "")}"')
        return lines
        
    def _map_type(self, type_str: str) -> str:
        """Map prompt types to CWL types."""
        type_mapping = {
            'file': 'File',
            'directory': 'Directory',
            'string': 'string',
            'int': 'int',
            'boolean': 'boolean',
            'float': 'float'
        }
        return type_mapping.get(type_str.lower(), 'File')