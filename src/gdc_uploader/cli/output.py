"""Rich terminal output support for GDC Uploader."""

import time
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Custom theme for GDC Uploader
GDC_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "bold magenta",
    "muted": "dim white",
})

# Global console instance
console = Console(theme=GDC_THEME)


def print_header():
    """Print the GDC Uploader header."""
    header = Panel.fit(
        "[bold cyan]GDC Uploader[/bold cyan]\n"
        "Tool for uploading genomic data to the NCI Genomic Data Commons",
        border_style="blue",
    )
    console.print(header)


def print_info(message: str):
    """Print an info message."""
    console.print(f"[info]ℹ[/info] {message}")


def print_success(message: str):
    """Print a success message."""
    console.print(f"[success]✓[/success] {message}")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[warning]⚠[/warning] {message}")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[error]✗[/error] {message}")


def create_upload_progress() -> Progress:
    """Create a progress bar for file uploads."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def create_simple_progress() -> Progress:
    """Create a simple progress bar for tasks."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.1f}%",
        console=console,
        transient=True,
    )


class UploadTracker:
    """Track and display upload progress."""
    
    def __init__(self, total_files: int):
        self.total_files = total_files
        self.completed_files = 0
        self.failed_files = 0
        self.progress = create_upload_progress()
        self.overall_task: Optional[TaskID] = None
        self.file_tasks = {}
        
    def __enter__(self):
        self.progress.__enter__()
        self.overall_task = self.progress.add_task(
            f"Overall Progress (0/{self.total_files})", 
            total=self.total_files
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.__exit__(exc_type, exc_val, exc_tb)
        
    def add_file(self, file_name: str, file_size: int) -> TaskID:
        """Add a file to track."""
        task_id = self.progress.add_task(file_name, total=file_size)
        self.file_tasks[file_name] = task_id
        return task_id
        
    def update_file(self, file_name: str, completed: int):
        """Update file upload progress."""
        if file_name in self.file_tasks:
            self.progress.update(self.file_tasks[file_name], completed=completed)
            
    def complete_file(self, file_name: str, success: bool = True):
        """Mark a file as completed."""
        if success:
            self.completed_files += 1
        else:
            self.failed_files += 1
            
        self.progress.update(
            self.overall_task,
            advance=1,
            description=f"Overall Progress ({self.completed_files}/{self.total_files})"
        )
        
        if file_name in self.file_tasks:
            self.progress.remove_task(self.file_tasks[file_name])
            del self.file_tasks[file_name]


def display_upload_summary(results: List[dict]):
    """Display a summary table of upload results."""
    table = Table(title="Upload Summary", show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Time", justify="right")
    table.add_column("Size", justify="right")
    
    total_size = 0
    total_time = 0
    success_count = 0
    
    for result in results:
        status = result.get('status', 'unknown')
        if status == 'success':
            status_display = "[success]✓ Success[/success]"
            success_count += 1
        elif status == 'failed':
            status_display = "[error]✗ Failed[/error]"
        else:
            status_display = "[warning]? Unknown[/warning]"
            
        time_str = f"{result.get('time', 0):.1f}s"
        size = result.get('size', 0)
        size_str = format_bytes(size)
        
        table.add_row(
            result.get('file', 'Unknown'),
            status_display,
            time_str,
            size_str
        )
        
        total_size += size
        total_time += result.get('time', 0)
    
    # Add summary row
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{success_count}/{len(results)} Success[/bold]",
        f"[bold]{total_time:.1f}s[/bold]",
        f"[bold]{format_bytes(total_size)}[/bold]",
        style="bold",
    )
    
    console.print(table)
    
    # Print summary statistics
    if success_count == len(results):
        print_success(f"All {len(results)} files uploaded successfully!")
    elif success_count > 0:
        print_warning(f"{success_count} of {len(results)} files uploaded successfully")
    else:
        print_error("No files were uploaded successfully")


def display_file_discovery_results(found_files: List[str], missing_files: List[str]):
    """Display file discovery results."""
    if found_files:
        print_success(f"Found {len(found_files)} files")
        
    if missing_files:
        print_warning(f"Missing {len(missing_files)} files")
        if len(missing_files) <= 10:
            for file in missing_files:
                console.print(f"  [muted]- {file}[/muted]")
        else:
            console.print(f"  [muted](showing first 10 of {len(missing_files)})[/muted]")
            for file in missing_files[:10]:
                console.print(f"  [muted]- {file}[/muted]")


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def create_validation_report(errors: List[str], warnings: List[str]):
    """Create a validation report panel."""
    content = []
    
    if errors:
        content.append("[error]Errors:[/error]")
        for error in errors:
            content.append(f"  ✗ {error}")
            
    if warnings:
        if content:
            content.append("")
        content.append("[warning]Warnings:[/warning]")
        for warning in warnings:
            content.append(f"  ⚠ {warning}")
            
    if not content:
        content.append("[success]✓ No validation issues found[/success]")
        
    panel = Panel(
        "\n".join(content),
        title="Validation Report",
        border_style="yellow" if warnings else "red" if errors else "green",
    )
    
    console.print(panel)


class TaskProgress:
    """Context manager for showing task progress."""
    
    def __init__(self, description: str, total: Optional[int] = None):
        self.description = description
        self.total = total
        self.progress = create_simple_progress()
        self.task_id: Optional[TaskID] = None
        
    def __enter__(self):
        self.progress.__enter__()
        self.task_id = self.progress.add_task(self.description, total=self.total)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=self.total or 100)
        self.progress.__exit__(exc_type, exc_val, exc_tb)
        
    def update(self, advance: int = 1, description: Optional[str] = None):
        """Update the progress."""
        if self.task_id is not None:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self.progress.update(self.task_id, **kwargs)