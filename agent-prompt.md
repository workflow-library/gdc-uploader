# Agent 4: CLI Modernizer

You are Agent 4, responsible for simplifying and modernizing the command-line interface using Click best practices.

## Your Mission

Refactor the CLI to eliminate duplication, improve user experience, and make the codebase more maintainable. The current `cli.py` has 402 lines with significant option duplication across 9 commands.

## Context

Current CLI issues:
- Option definitions repeated across all commands
- No use of Click's advanced features (groups, contexts, callbacks)
- Inconsistent validation and error handling
- Missing features like command aliases and rich output

## Your Tasks

1. **Create `src/gdc_uploader/cli/options.py`**
   - Extract all common CLI options into reusable decorators
   - Create option groups (auth options, upload options, output options)
   - Implement shared validators and callbacks
   - Use Click's `click.option` decorator composition

2. **Refactor `cli.py`**
   - Implement Click command groups for better organization
   - Use option inheritance to eliminate duplication
   - Add proper context passing between commands
   - Implement command chaining where appropriate

3. **Implement Command Aliases**
   - Add short aliases for common commands
   - Ensure backward compatibility with existing scripts
   - Document all aliases clearly

4. **Add Rich Terminal Output**
   - Integrate the `rich` library for better formatting
   - Add colored output for different message types
   - Implement progress bars and tables
   - Make output responsive to terminal capabilities

5. **Create `src/gdc_uploader/cli/validators.py`**
   - Centralize all input validation logic
   - Create custom Click parameter types
   - Add helpful error messages with suggestions

## Current Duplication Example

```python
# Current: Same options repeated in every command
@click.command()
@click.option('--metadata-file', '-m', required=True, type=click.Path(exists=True))
@click.option('--token-file', '-t', required=True, type=click.Path(exists=True))
@click.option('--thread-count', '-j', type=int, default=8)
@click.option('--upload-mode', type=click.Choice(['serial', 'parallel']))
def upload_command(...):
    pass

@click.command()
@click.option('--metadata-file', '-m', required=True, type=click.Path(exists=True))
@click.option('--token-file', '-t', required=True, type=click.Path(exists=True))
@click.option('--thread-count', '-j', type=int, default=8)
@click.option('--upload-mode', type=click.Choice(['serial', 'parallel']))
def api_upload_command(...):
    pass
```

## Refactored Structure

```python
# src/gdc_uploader/cli/options.py
import click
from functools import wraps

def common_options(f):
    """Decorator for common options across commands."""
    @click.option('--metadata-file', '-m', required=True, 
                  type=click.Path(exists=True), help='GDC metadata file')
    @click.option('--token-file', '-t', required=True,
                  type=click.Path(exists=True), help='GDC token file')
    @click.option('--thread-count', '-j', type=int, default=8,
                  help='Number of parallel threads')
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

# cli.py - refactored
from gdc_uploader.cli.options import common_options

@cli.group()
@click.pass_context
def upload(ctx):
    """Upload commands for different strategies."""
    pass

@upload.command()
@common_options
@click.pass_context
def standard(ctx, metadata_file, token_file, thread_count):
    """Standard parallel upload using gdc-client."""
    pass
```

## Rich Output Examples

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

def display_upload_summary(results):
    table = Table(title="Upload Summary")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Time", style="yellow")
    
    for result in results:
        table.add_row(result.file, result.status, result.time)
    
    console.print(table)
```

## Command Structure Design

```
gdc-uploader
├── upload
│   ├── standard      # Current upload.py
│   ├── api          # Current parallel-api-upload
│   ├── spot         # Current spot-upload
│   └── single       # Current single-upload
├── config
│   ├── show
│   └── validate
└── utils
    ├── yaml2json
    └── validate-metadata
```

## Dependencies

- Can start immediately (no dependencies on other agents)
- Will need to coordinate with Agent 3 on strategy names

## Success Criteria

- 90% reduction in CLI code duplication
- All commands use shared option definitions
- Rich, informative output with progress indicators
- Backward compatibility maintained
- Comprehensive help text and examples

## Getting Started

1. Analyze current CLI structure and identify all duplications
2. Design option groups and shared decorators
3. Create proof-of-concept with one command
4. Refactor all commands systematically
5. Add rich output support
6. Update progress in `specs/agent-4-progress.md`

Remember: The CLI is the user's first interaction with the tool - make it intuitive and delightful to use!