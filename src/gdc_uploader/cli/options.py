"""Reusable CLI options and decorators for GDC Uploader."""

from functools import wraps
from pathlib import Path
from typing import Callable

import click


def auth_options(f: Callable) -> Callable:
    """Add authentication options to a command."""
    @click.option(
        "-m", "--metadata",
        type=click.Path(exists=True, path_type=Path),
        required=True,
        help="Path to GDC metadata JSON file"
    )
    @click.option(
        "-t", "--token",
        type=click.Path(exists=True, path_type=Path),
        required=True,
        help="Path to GDC authentication token file"
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def upload_options(f: Callable) -> Callable:
    """Add upload configuration options to a command."""
    @click.option(
        "-j", "--threads",
        type=int,
        default=4,
        show_default=True,
        help="Number of parallel upload threads"
    )
    @click.option(
        "-r", "--retries",
        type=int,
        default=3,
        show_default=True,
        help="Number of retry attempts for failed uploads"
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def common_upload_options(f: Callable) -> Callable:
    """Combine auth and upload options for upload commands."""
    f = auth_options(f)
    f = upload_options(f)
    return f


def spot_upload_options(f: Callable) -> Callable:
    """Add spot instance specific options."""
    @click.option(
        "--state-file",
        type=click.Path(path_type=Path),
        default="upload_state.json",
        show_default=True,
        help="Path to save upload state for resume"
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def json_output_options(f: Callable) -> Callable:
    """Add JSON output formatting options."""
    @click.option(
        "--validate",
        is_flag=True,
        help="Validate converted JSON structure for GDC compatibility"
    )
    @click.option(
        "--compact",
        is_flag=True,
        help="Compact JSON output (no indentation)"
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def parallel_options(f: Callable) -> Callable:
    """Add parallel processing options."""
    @click.option(
        "--max-workers",
        type=int,
        default=2,
        show_default=True,
        help="Maximum concurrent uploads"
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def filter_options(f: Callable) -> Callable:
    """Add filtering options for JSON operations."""
    @click.option(
        "-f", "--field",
        required=True,
        help="Field name to filter by"
    )
    @click.option(
        "-v", "--values",
        multiple=True,
        required=True,
        help="Values to match (can be specified multiple times)"
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def split_options(f: Callable) -> Callable:
    """Add JSON splitting options."""
    @click.option(
        "-o", "--output-dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=".",
        show_default=True,
        help="Directory to write split files"
    )
    @click.option(
        "-f", "--field",
        default="id",
        show_default=True,
        help="Field to use for naming split files"
    )
    @click.option(
        "-p", "--prefix",
        default="split",
        show_default=True,
        help="Prefix for output filenames"
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


# Common argument types
FILES_DIR_ARG = click.argument(
    "files_directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path)
)

TARGET_FILE_ARG = click.argument(
    "target_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path)
)

INPUT_FILE_ARG = click.argument(
    "input_file",
    type=click.Path(exists=True, path_type=Path)
)

OUTPUT_FILE_ARG = click.argument(
    "output_file",
    type=click.Path(path_type=Path),
    required=False
)

MANIFEST_FILE_ARG = click.argument(
    "manifest_file",
    type=click.Path(exists=True, path_type=Path)
)

TOKEN_FILE_ARG = click.argument(
    "token_file",
    type=click.Path(exists=True, path_type=Path)
)

TARGET_FILES_ARG = click.argument(
    "target_files",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path)
)