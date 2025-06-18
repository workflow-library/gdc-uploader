"""Simplified command-line interface for GDC Uploader."""

import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from .uploaders import StandardUploader, APIUploader, SpotUploader, SingleFileUploader
from .cli.options import auth_options, upload_options, common_upload_options as common_options
from .core.utils import setup_logging
from .parser import parse_prompt
from .emit import CWLEmitter, DockerEmitter, NotebookEmitter

console = Console()


@click.group()
@click.version_option(version="2.0.0", prog_name="gdc-uploader")
@click.pass_context
def cli(ctx):
    """GDC Uploader - Simplified tool for uploading genomic data to GDC."""
    ctx.ensure_object(dict)
    setup_logging()


@cli.command()
@common_options
@auth_options
@upload_options
@click.argument('source_path', type=click.Path(exists=True, path_type=Path))
def upload(metadata, token, threads, retries, source_path, **kwargs):
    """Standard upload using gdc-client."""
    uploader = StandardUploader(
        metadata_file=metadata,
        token_file=token,
        thread_count=threads,
        retry_count=retries
    )
    
    with console.status("Discovering files..."):
        files = uploader.discover_files(source_path)
        console.print(f"Found {len(files)} files to upload")
    
    # Upload files
    results = []
    with Progress() as progress:
        task = progress.add_task("Uploading files...", total=len(files))
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = {
                executor.submit(uploader.upload_file, f): f 
                for f in files
            }
            
            for future in futures:
                result = future.result()
                results.append(result)
                progress.update(task, advance=1)
    
    # Generate and display report
    report = uploader.generate_report(results)
    display_report(report)
    
    # Save report
    with open("upload-report.json", "w") as f:
        json.dump(report, f, indent=2)
    

@cli.command()
@common_options
@auth_options
@upload_options
@click.option('--chunk-size', type=int, default=10485760, help='Upload chunk size in bytes')
@click.argument('source_path', type=click.Path(exists=True, path_type=Path))
def api_upload(metadata, token, threads, chunk_size, source_path, **kwargs):
    """Upload using direct API calls."""
    uploader = APIUploader(
        metadata_file=metadata,
        token_file=token,
        thread_count=threads,
        chunk_size=chunk_size
    )
    
    with console.status("Discovering files..."):
        files = uploader.discover_files(source_path)
        console.print(f"Found {len(files)} files to upload")
    
    # Upload files
    results = []
    with Progress() as progress:
        task = progress.add_task("Uploading files...", total=len(files))
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = {
                executor.submit(uploader.upload_file, f): f 
                for f in files
            }
            
            for future in futures:
                result = future.result()
                results.append(result)
                progress.update(task, advance=1)
    
    # Generate and display report
    report = uploader.generate_report(results)
    display_report(report)
    

def display_report(report: dict):
    """Display upload report in a nice table."""
    table = Table(title="Upload Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    summary = report["summary"]
    table.add_row("Total Files", str(summary["total_files"]))
    table.add_row("Successful", str(summary["successful"]))
    table.add_row("Failed", str(summary["failed"]))
    table.add_row("Not Found", str(summary["not_found"]))
    table.add_row("Success Rate", f"{summary['success_rate']:.1%}")
    
    console.print(table)
    
    # Show failures if any
    failures = [d for d in report["details"] if d["status"] != "SUCCESS"]
    if failures:
        console.print("\n[red]Failed uploads:[/red]")
        for failure in failures:
            console.print(f"  • {failure['filename']}: {failure['error']}")


@cli.command()
@click.argument('yaml_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output JSON file')
def yaml2json(yaml_file, output):
    """Convert YAML metadata to JSON format."""
    from .core.utils import yaml_to_json
    
    result = yaml_to_json(yaml_file)
    
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        console.print(f"Converted {yaml_file} -> {output}")
    else:
        console.print(json.dumps(result, indent=2))


@cli.command()
@click.option('--prompts-dir', '-p', type=click.Path(exists=True, path_type=Path), 
              default='prompts', help='Directory containing prompt files')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              default='artifacts', help='Output directory for artifacts')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing artifacts')
def emit(prompts_dir, output_dir, force):
    """Generate CWL, Docker, and notebook artifacts from prompts."""
    prompts_path = Path(prompts_dir)
    output_path = Path(output_dir)
    
    # Find all prompt files
    prompt_files = list(prompts_path.glob('*.md'))
    
    if not prompt_files:
        console.print(f"[red]No prompt files found in {prompts_dir}[/red]")
        return
        
    console.print(f"Found {len(prompt_files)} prompt files")
    
    # Initialize emitters
    cwl_emitter = CWLEmitter()
    docker_emitter = DockerEmitter()
    notebook_emitter = NotebookEmitter()
    
    # Process each prompt
    with Progress() as progress:
        task = progress.add_task("Generating artifacts...", total=len(prompt_files))
        
        for prompt_file in prompt_files:
            console.print(f"\nProcessing: {prompt_file.name}")
            
            try:
                # Parse prompt
                prompt_data = parse_prompt(prompt_file)
                tool_name = prompt_data['metadata'].get('name', prompt_file.stem)
                
                # Generate artifacts
                cwl_path = output_path / 'cwl' / f'{tool_name}.cwl'
                if not cwl_path.exists() or force:
                    cwl_emitter.emit(prompt_data, cwl_path)
                    console.print(f"  ✓ Generated: {cwl_path}")
                else:
                    console.print(f"  - Skipped: {cwl_path} (exists)")
                    
                docker_path = output_path / 'docker' / f'{tool_name}.Dockerfile'
                if not docker_path.exists() or force:
                    docker_emitter.emit(prompt_data, docker_path)
                    console.print(f"  ✓ Generated: {docker_path}")
                else:
                    console.print(f"  - Skipped: {docker_path} (exists)")
                    
                notebook_path = output_path / 'notebooks' / f'{tool_name}.qmd'
                if not notebook_path.exists() or force:
                    notebook_emitter.emit(prompt_data, notebook_path)
                    console.print(f"  ✓ Generated: {notebook_path}")
                else:
                    console.print(f"  - Skipped: {notebook_path} (exists)")
                    
            except Exception as e:
                console.print(f"  [red]✗ Error: {str(e)}[/red]")
                
            progress.update(task, advance=1)
            
    console.print(f"\n[green]Artifact generation complete![/green]")
    console.print(f"Output directory: {output_path}")


@cli.command()
@click.argument('prompt_file', type=click.Path(exists=True, path_type=Path))
def validate(prompt_file):
    """Validate a prompt file."""
    try:
        prompt_data = parse_prompt(Path(prompt_file))
        
        # Check required fields
        metadata = prompt_data.get('metadata', {})
        required_fields = ['name', 'version', 'description']
        
        missing = [f for f in required_fields if f not in metadata]
        if missing:
            console.print(f"[yellow]Warning: Missing metadata fields: {', '.join(missing)}[/yellow]")
            
        # Display parsed data
        table = Table(title="Prompt Validation Results")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Name", metadata.get('name', 'N/A'))
        table.add_row("Version", metadata.get('version', 'N/A'))
        table.add_row("Description", metadata.get('description', 'N/A')[:50] + '...')
        table.add_row("Docker Image", metadata.get('docker_image', 'N/A'))
        table.add_row("Inputs", str(len(prompt_data.get('inputs', []))))
        table.add_row("Outputs", str(len(prompt_data.get('outputs', []))))
        table.add_row("Has Command", "Yes" if prompt_data.get('command') else "No")
        
        console.print(table)
        console.print("[green]✓ Prompt file is valid[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {str(e)}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    cli()