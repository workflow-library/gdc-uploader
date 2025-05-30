# GDC Uploader Documentation

Welcome to the GDC Uploader documentation. This tool manages uploads of genomic sequence data files to the NIH Genomic Data Commons.

## Documentation Structure

### 📘 [Usage Guide](usage/)
- [CWL Commands Reference](usage/cwl-commands.md) - Complete command-line reference

### 🔧 [Technical Documentation](technical/)
- [Architecture Overview](technical/architecture.md) - System design and components

### 🧪 [Testing Documentation](testing/)
- [Test Report](testing/test-report.md) - Comprehensive testing results and methodology

## Quick Links

- **Main README**: [../README.md](../README.md) - Project overview and quick start
- **Developer Guide**: [../CLAUDE.md](../CLAUDE.md) - Development guidelines and conventions
- **Test Scripts**: [../tests/scripts/](../tests/scripts/) - Automated test scripts

## Common Tasks

### Upload Files to GDC
```bash
cwltool cwl/gdc_upload.cwl \
  --metadata_file metadata.json \
  --files_directory /path/to/files \
  --token_file token.txt
```

### Run Tests
```bash
./tests/scripts/test-cwl.sh
```

### Build Docker Image
```bash
cd cwl && docker build -f gdc.Dockerfile -t gdc-uploader:latest .
```

## Getting Help

- Check the [CWL Commands Reference](usage/cwl-commands.md) for detailed parameter descriptions
- Review the [Architecture Overview](technical/architecture.md) for system understanding
- See the [Test Report](testing/test-report.md) for known issues and limitations

## Contributing

When updating documentation:
1. Keep examples current with the codebase
2. Test all command examples
3. Update version numbers when applicable
4. Follow the existing documentation style