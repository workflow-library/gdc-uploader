# Filename Requirements for GDC Uploader

## Issue

The current implementation of the GDC uploader expects filenames to follow a specific TracSeq naming convention with at least 4 underscore-separated parts.

## Expected Filename Format

The code in `Util.cs` line 81 expects filenames like:

```
YYMMDD_INSTRUMENT_RUN_FLOWCELL_*.fastq.gz
```

Example: `210115_UNC52-A00817_0168_BH5WFMDRXY_1_ATCTGACGAA-CCGGATAGTT_S1_L001_R1_001.fastq.gz`

Where the first 4 underscore-separated parts form the "runId":
- Part 1: Date (YYMMDD)
- Part 2: Instrument ID
- Part 3: Run number
- Part 4: Flowcell ID

## Error

If your filenames don't have at least 4 underscore-separated parts, you'll get:

```
Unhandled exception. System.IndexOutOfRangeException: Index was outside the bounds of the array.
   at upload2gdc.Util.ReportOnFilesReady(String basePath) in /src/src/upload2gdc/Util.cs:line 67
```

## Solutions

### Option 1: Use TracSeq-compatible filenames

Rename your files to match the expected format with at least 4 underscore-separated parts.

### Option 2: Use simulator mode for testing

When using `--sim` flag, ensure your test files still follow the naming convention.

### Option 3: Apply the patch

Apply the patch in `patches/fix-filename-parsing.patch` to handle different filename formats:

```bash
cd /src
patch -p1 < /patches/fix-filename-parsing.patch
```

### Option 4: Use provided sample files

Use the metadata files in this directory:
- `sample-gdc-metadata-tracseq-format.json` - Follows TracSeq naming convention
- `simulator-compatible-metadata.json` - Simplified names that still work

## File Organization

The code also expects files to be organized in specific directories:
- FASTQ files: `{basePath}/fastq/`
- BAM files: `{basePath}/uBam/{runId}/`

Where `{basePath}` is the value passed to `--files` parameter.