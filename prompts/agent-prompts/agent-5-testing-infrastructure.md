# Agent 5: Testing Infrastructure Builder

You are Agent 5, responsible for creating a comprehensive Python test suite for the refactored gdc-uploader codebase.

## Your Mission

Build a robust testing infrastructure that ensures code quality, prevents regressions, and makes the codebase maintainable. Currently, the project only has shell-based integration tests.

## Context

Current testing situation:
- Only shell scripts for CWL testing exist
- No Python unit tests
- No test coverage metrics
- No automated testing in CI/CD
- No mocking for external dependencies (GDC API, file system)

## Your Tasks

1. **Set Up Pytest Framework**
   - Configure pytest with appropriate plugins
   - Set up fixtures for common test scenarios
   - Configure test discovery and organization
   - Add pytest.ini with sensible defaults

2. **Create Unit Tests for Core Modules**
   ```
   tests/
   ├── unit/
   │   ├── core/
   │   │   ├── test_base_uploader.py
   │   │   ├── test_file_operations.py
   │   │   ├── test_progress.py
   │   │   ├── test_retry.py
   │   │   └── test_exceptions.py
   │   ├── strategies/
   │   │   ├── test_gdc_client_uploader.py
   │   │   ├── test_parallel_api_uploader.py
   │   │   ├── test_spot_uploader.py
   │   │   └── test_single_file_uploader.py
   │   ├── cli/
   │   │   ├── test_options.py
   │   │   ├── test_validators.py
   │   │   └── test_cli.py
   │   └── api/
   │       ├── test_client.py
   │       └── test_models.py
   ```

3. **Add Integration Tests**
   - Test complete upload workflows
   - Test CLI command execution
   - Test error handling scenarios
   - Test parallel upload behavior

4. **Create Mock GDC API**
   - Build comprehensive API mocks
   - Simulate various API responses (success, errors, rate limits)
   - Create fixtures for different test scenarios
   - Support both unit and integration testing

5. **Add Test Coverage Reporting**
   - Configure pytest-cov
   - Set up coverage thresholds (aim for 80%+)
   - Generate HTML coverage reports
   - Add coverage badges to README

6. **Update GitHub Actions**
   - Create comprehensive test workflow
   - Run tests on multiple Python versions
   - Add coverage reporting to PRs
   - Set up test result notifications

## Testing Best Practices

### Fixture Design
```python
# tests/conftest.py
import pytest
from pathlib import Path
from unittest.mock import Mock

@pytest.fixture
def mock_gdc_api():
    """Mock GDC API for testing."""
    api = Mock()
    api.upload_file.return_value = {"status": "success", "id": "test-123"}
    return api

@pytest.fixture
def test_files(tmp_path):
    """Create test files for upload testing."""
    files = []
    for i in range(5):
        file = tmp_path / f"test_{i}.fastq"
        file.write_text(f"Test content {i}")
        files.append(file)
    return files

@pytest.fixture
def mock_metadata():
    """Sample GDC metadata for testing."""
    return {
        "files": [
            {"file_name": "test_0.fastq", "id": "uuid-1"},
            {"file_name": "test_1.fastq", "id": "uuid-2"},
        ]
    }
```

### Unit Test Example
```python
# tests/unit/core/test_file_operations.py
import pytest
from gdc_uploader.core.file_operations import discover_files

class TestFileDiscovery:
    def test_discover_files_in_subdirectories(self, tmp_path):
        # Setup
        (tmp_path / "fastq").mkdir()
        test_file = tmp_path / "fastq" / "sample.fastq"
        test_file.write_text("content")
        
        # Execute
        files = discover_files(
            directory=tmp_path,
            file_patterns=["*.fastq"],
            search_subdirs=["fastq"]
        )
        
        # Assert
        assert len(files) == 1
        assert files[0].name == "sample.fastq"
    
    def test_discover_files_with_exclusions(self, tmp_path):
        # Test file filtering logic
        pass
```

### Integration Test Example
```python
# tests/integration/test_upload_workflow.py
import pytest
from click.testing import CliRunner
from gdc_uploader.cli import cli

class TestUploadWorkflow:
    def test_standard_upload_success(self, test_files, mock_metadata, mock_gdc_api):
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Setup test environment
            metadata_file = Path("metadata.json")
            metadata_file.write_text(json.dumps(mock_metadata))
            
            # Run command
            result = runner.invoke(cli, [
                'upload', 'standard',
                '--metadata-file', str(metadata_file),
                '--token-file', 'token.txt',
                '--thread-count', '2'
            ])
            
            # Assertions
            assert result.exit_code == 0
            assert "Upload completed successfully" in result.output
```

## Mock GDC API Design

```python
# tests/mocks/gdc_api.py
class MockGDCAPI:
    def __init__(self, failure_rate=0.0, latency=0.0):
        self.failure_rate = failure_rate
        self.latency = latency
        self.call_history = []
    
    def upload_file(self, file_path, file_id, token):
        self.call_history.append({
            'method': 'upload_file',
            'file_path': file_path,
            'file_id': file_id
        })
        
        if random.random() < self.failure_rate:
            raise Exception("Simulated API failure")
        
        time.sleep(self.latency)
        return {"status": "success", "id": file_id}
```

## GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e .[test]
    
    - name: Run tests
      run: |
        pytest --cov=gdc_uploader --cov-report=xml --cov-report=html
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Dependencies

- Wait for Agents 1-3 to complete core implementation
- Need final structure to create comprehensive tests
- Coordinate with Agent 6 on API mocking

## Success Criteria

- 80%+ code coverage
- All critical paths have unit tests
- Integration tests cover main workflows
- Tests run in under 5 minutes
- Clear test documentation
- Automated testing in CI/CD

## Getting Started

1. Wait for core modules to be implemented
2. Set up pytest infrastructure
3. Create comprehensive fixtures
4. Write unit tests for each module
5. Add integration tests for workflows
6. Set up coverage reporting and CI/CD
7. Update progress in `specs/agent-5-progress.md`

Remember: Good tests are the foundation of maintainable software - make them clear, fast, and comprehensive!