"""Command-line interface for GDC Uploader."""

import sys
from pathlib import Path

import click

from .cli.options import (
    FILES_DIR_ARG,
    INPUT_FILE_ARG,
    MANIFEST_FILE_ARG,
    OUTPUT_FILE_ARG,
    TARGET_FILES_ARG,
    TARGET_FILE_ARG,
    TOKEN_FILE_ARG,
    auth_options,
    common_upload_options,
    filter_options,
    json_output_options,
    parallel_options,
    split_options,
    spot_upload_options,
    upload_options,
)
from .cli.validators import GDC_METADATA_FILE, GDC_TOKEN_FILE, RETRY_COUNT, THREAD_COUNT
from .direct_upload import direct_upload
from .parallel_api_upload import parallel_api_upload
from .spot_upload import upload_with_resume
from .upload import upload
from .upload_single import upload_single
from .utils import filter_json, split_json, yaml_to_json


@click.group()
@click.version_option(version="1.0.0", prog_name="gdc-uploader")
@click.pass_context
def main(ctx):
    """GDC Uploader - Tool for uploading genomic data to the NCI Genomic Data Commons.
    
    Use 'gdc-uploader COMMAND --help' for more information on a specific command.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


# Upload command group
@main.group('upload')
@click.pass_context
def upload_group(ctx):
    """Commands for uploading files to GDC."""
    pass


@upload_group.command('standard')
@common_upload_options
@FILES_DIR_ARG
@click.pass_context
def upload_standard_cmd(ctx, metadata, token, threads, retries, files_directory):
    """Upload genomic files to GDC using parallel processing.
    
    This command searches for files in the directory using UUIDs from the metadata,
    then uploads them concurrently using the GDC Data Transfer Tool.
    
    FILES_DIRECTORY is the directory containing the files to upload.
    
    \b
    Example:
        gdc-uploader upload standard -m metadata.json -t token.txt /data/files
    """
    upload(metadata, token, files_directory, threads, retries)


@upload_group.command('direct')
@common_upload_options
@click.pass_context
def upload_direct_cmd(ctx, metadata, token, threads, retries):
    """Direct upload to GDC with minimal configuration.
    
    This simplified workflow expects file paths to be specified
    directly in the metadata JSON file.
    
    \b
    Example:
        gdc-uploader upload direct -m metadata.json -t token.txt
    """
    direct_upload(metadata, token, threads, retries)


@upload_group.command('single')
@auth_options
@click.option(
    "-r", "--retries",
    type=RETRY_COUNT,
    default=3,
    show_default=True,
    help="Number of retry attempts for failed uploads"
)
@TARGET_FILE_ARG
@click.pass_context
def upload_single_cmd(ctx, metadata, token, retries, target_file):
    """Upload a single genomic file to GDC.
    
    TARGET_FILE is the path to the file to upload.
    
    \b
    Example:
        gdc-uploader upload single -m metadata.json -t token.txt file.bam
    """
    upload_single(metadata, token, target_file, retries)


@upload_group.command('spot')
@MANIFEST_FILE_ARG
@TOKEN_FILE_ARG
@TARGET_FILE_ARG
@spot_upload_options
@click.option(
    "--retries",
    type=RETRY_COUNT,
    default=3,
    show_default=True,
    help="Number of retry attempts"
)
@click.pass_context
def upload_spot_cmd(ctx, manifest_file, token_file, target_file, state_file, retries):
    """Upload a file with spot instance resilience.
    
    This command is designed for use on spot instances that may be interrupted.
    It automatically handles resume on restart.
    
    \b
    MANIFEST_FILE is the YAML/JSON manifest containing all files.
    TOKEN_FILE is the GDC authentication token.
    TARGET_FILE is the specific file to upload.
    
    \b
    Example:
        gdc-uploader upload spot manifest.yaml token.txt file.bam
    """
    from .spot_upload import SpotInstanceUploader
    
    uploader = SpotInstanceUploader(
        manifest_file=manifest_file,
        token_file=token_file,
        state_file=state_file,
        retries=retries
    )
    uploader.run(target_file)


@upload_group.command('parallel-api')
@MANIFEST_FILE_ARG
@TOKEN_FILE_ARG
@TARGET_FILES_ARG
@parallel_options
@click.pass_context
def upload_parallel_api_cmd(ctx, manifest_file, token_file, target_files, max_workers):
    """Upload multiple files in parallel using GDC API.
    
    This command uses the same HTTP API method as gdc_upload_single.sh
    but allows multiple concurrent uploads for cost optimization.
    
    \b
    MANIFEST_FILE is the YAML/JSON manifest containing all files.
    TOKEN_FILE is the GDC authentication token.
    TARGET_FILES are the files to upload (space-separated).
    
    \b
    Example:
        gdc-uploader upload parallel-api manifest.yaml token.txt file1.bam file2.bam
    """
    from .parallel_api_upload import ParallelAPIUploader
    
    uploader = ParallelAPIUploader(
        manifest_file=manifest_file,
        token_file=token_file,
        max_workers=max_workers
    )
    uploader.run(list(target_files))


# Utils command group
@main.group()
@click.pass_context
def utils(ctx):
    """Utility commands for data manipulation."""
    pass


@utils.command('yaml2json')
@INPUT_FILE_ARG
@OUTPUT_FILE_ARG
@json_output_options
@click.pass_context
def yaml2json_cmd(ctx, input_file, output_file, validate, compact):
    """Convert YAML metadata to JSON format for GDC uploads.
    
    \b
    INPUT_FILE is the YAML file to convert (use '-' for stdin).
    OUTPUT_FILE is the JSON output file (use '-' for stdout, default: input.json).
    
    \b
    Example:
        gdc-uploader utils yaml2json metadata.yaml metadata.json --validate
    """
    pretty = not compact
    success = yaml_to_json(input_file, output_file, pretty, validate)
    sys.exit(0 if success else 1)


@utils.command('filter-json')
@INPUT_FILE_ARG
@click.argument(
    "output_file",
    type=click.Path(path_type=Path)
)
@filter_options
@click.pass_context
def filter_json_cmd(ctx, input_file, output_file, field, values):
    """Filter JSON array by field values.
    
    \b
    INPUT_FILE is the JSON file to filter.
    OUTPUT_FILE is where to write the filtered JSON.
    
    \b
    Example:
        gdc-uploader utils filter-json data.json filtered.json -f type -v BAM -v FASTQ
    """
    success = filter_json(input_file, output_file, field, list(values))
    sys.exit(0 if success else 1)


@utils.command('split-json')
@INPUT_FILE_ARG
@split_options
@click.pass_context
def split_json_cmd(ctx, input_file, output_dir, field, prefix):
    """Split JSON array into individual files.
    
    \b
    INPUT_FILE is the JSON array file to split.
    
    \b
    Example:
        gdc-uploader utils split-json data.json -o output/ -f id -p item
    """
    success = split_json(input_file, output_dir, field, prefix)
    sys.exit(0 if success else 1)


# Legacy command aliases for backward compatibility
@main.command('upload', hidden=True)
@common_upload_options
@FILES_DIR_ARG
@click.pass_context
def upload_legacy(ctx, metadata, token, threads, retries, files_directory):
    """Legacy alias for 'upload standard' command."""
    ctx.invoke(upload_standard_cmd, 
               metadata=metadata, 
               token=token, 
               threads=threads, 
               retries=retries, 
               files_directory=files_directory)


@main.command('direct-upload', hidden=True)
@common_upload_options
@click.pass_context
def direct_upload_legacy(ctx, metadata, token, threads, retries):
    """Legacy alias for 'upload direct' command."""
    ctx.invoke(upload_direct_cmd,
               metadata=metadata,
               token=token,
               threads=threads,
               retries=retries)


@main.command('upload-single', hidden=True)
@auth_options
@click.option(
    "-r", "--retries",
    type=RETRY_COUNT,
    default=3,
    help="Number of retry attempts for failed uploads"
)
@TARGET_FILE_ARG
@click.pass_context
def upload_single_legacy(ctx, metadata, token, retries, target_file):
    """Legacy alias for 'upload single' command."""
    ctx.invoke(upload_single_cmd,
               metadata=metadata,
               token=token,
               retries=retries,
               target_file=target_file)


@main.command('spot-upload', hidden=True)
@MANIFEST_FILE_ARG
@TOKEN_FILE_ARG
@TARGET_FILE_ARG
@spot_upload_options
@click.option(
    "--retries",
    type=RETRY_COUNT,
    default=3,
    help="Number of retry attempts"
)
@click.pass_context
def spot_upload_legacy(ctx, manifest_file, token_file, target_file, state_file, retries):
    """Legacy alias for 'upload spot' command."""
    ctx.invoke(upload_spot_cmd,
               manifest_file=manifest_file,
               token_file=token_file,
               target_file=target_file,
               state_file=state_file,
               retries=retries)


@main.command('parallel-upload', hidden=True)
@MANIFEST_FILE_ARG
@TOKEN_FILE_ARG
@TARGET_FILES_ARG
@parallel_options
@click.pass_context
def parallel_upload_legacy(ctx, manifest_file, token_file, target_files, max_workers):
    """Legacy alias for 'upload parallel-api' command."""
    ctx.invoke(upload_parallel_api_cmd,
               manifest_file=manifest_file,
               token_file=token_file,
               target_files=target_files,
               max_workers=max_workers)


@main.command('yaml2json', hidden=True)
@INPUT_FILE_ARG
@OUTPUT_FILE_ARG
@json_output_options
@click.pass_context
def yaml2json_legacy(ctx, input_file, output_file, validate, compact):
    """Legacy alias for 'utils yaml2json' command."""
    ctx.invoke(yaml2json_cmd,
               input_file=input_file,
               output_file=output_file,
               validate=validate,
               compact=compact)


@main.command('filter-json', hidden=True)
@INPUT_FILE_ARG
@click.argument(
    "output_file",
    type=click.Path(path_type=Path)
)
@filter_options
@click.pass_context
def filter_json_legacy(ctx, input_file, output_file, field, values):
    """Legacy alias for 'utils filter-json' command."""
    ctx.invoke(filter_json_cmd,
               input_file=input_file,
               output_file=output_file,
               field=field,
               values=values)


@main.command('split-json', hidden=True)
@INPUT_FILE_ARG
@split_options
@click.pass_context
def split_json_legacy(ctx, input_file, output_dir, field, prefix):
    """Legacy alias for 'utils split-json' command."""
    ctx.invoke(split_json_cmd,
               input_file=input_file,
               output_dir=output_dir,
               field=field,
               prefix=prefix)


if __name__ == "__main__":
    main()