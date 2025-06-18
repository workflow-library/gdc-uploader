"""Parser for markdown prompt files.

This module parses markdown files with YAML frontmatter to extract
tool specifications for generating CWL, Docker, and notebook artifacts.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml


class PromptParser:
    """Parse markdown prompt files into structured data."""
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        """Reset parser state."""
        self.metadata = {}
        self.sections = {}
        self.inputs = []
        self.outputs = []
        self.command = None
        self.requirements = {}
        
    def parse_file(self, filepath: Path) -> Dict[str, Any]:
        """Parse a markdown prompt file.
        
        Args:
            filepath: Path to the markdown file
            
        Returns:
            Dictionary containing parsed prompt data
        """
        self.reset()
        
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Extract frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if frontmatter_match:
            self.metadata = yaml.safe_load(frontmatter_match.group(1))
            content = content[frontmatter_match.end():]
            
        # Parse sections
        self._parse_sections(content)
        
        # Extract specific components
        self._extract_inputs()
        self._extract_outputs()
        self._extract_command()
        self._extract_requirements()
        
        return {
            'metadata': self.metadata,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'command': self.command,
            'requirements': self.requirements,
            'sections': self.sections
        }
        
    def _parse_sections(self, content: str):
        """Parse markdown sections."""
        # Split by headers
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    self.sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                level = len(re.match(r'^#+', line).group())
                title = line.strip('#').strip()
                current_section = title
                current_content = []
            else:
                current_content.append(line)
                
        # Save last section
        if current_section:
            self.sections[current_section] = '\n'.join(current_content).strip()
            
    def _extract_inputs(self):
        """Extract input specifications from sections."""
        if 'Inputs' in self.sections:
            content = self.sections['Inputs']
            # Parse bullet points or structured format
            for line in content.split('\n'):
                if line.strip().startswith('-'):
                    # Parse format: - name: description (type)
                    match = re.match(r'-\s+(\w+):\s+(.+?)(?:\s+\((\w+)\))?$', line.strip())
                    if match:
                        name, description, input_type = match.groups()
                        self.inputs.append({
                            'name': name,
                            'description': description,
                            'type': input_type or 'File'
                        })
                        
    def _extract_outputs(self):
        """Extract output specifications from sections."""
        if 'Outputs' in self.sections:
            content = self.sections['Outputs']
            for line in content.split('\n'):
                if line.strip().startswith('-'):
                    match = re.match(r'-\s+(\w+):\s+(.+?)(?:\s+\((\w+)\))?$', line.strip())
                    if match:
                        name, description, output_type = match.groups()
                        self.outputs.append({
                            'name': name,
                            'description': description,
                            'type': output_type or 'File'
                        })
                        
    def _extract_command(self):
        """Extract command from code blocks."""
        if 'Command' in self.sections:
            content = self.sections['Command']
            # Look for code block
            code_match = re.search(r'```(?:bash|sh)?\n(.*?)\n```', content, re.DOTALL)
            if code_match:
                self.command = code_match.group(1).strip()
            else:
                # Try to extract command directly
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                if lines:
                    self.command = lines[0]
                    
    def _extract_requirements(self):
        """Extract requirements from sections or metadata."""
        # Check metadata first
        if 'requirements' in self.metadata:
            self.requirements.update(self.metadata['requirements'])
            
        # Check for Requirements section
        if 'Requirements' in self.sections:
            content = self.sections['Requirements']
            # Parse key: value pairs
            for line in content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    self.requirements[key.strip()] = value.strip()


def parse_prompt(filepath: Path) -> Dict[str, Any]:
    """Convenience function to parse a prompt file.
    
    Args:
        filepath: Path to the markdown prompt file
        
    Returns:
        Parsed prompt data as a dictionary
    """
    parser = PromptParser()
    return parser.parse_file(filepath)