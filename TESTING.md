# Testing and CI/CD Guide for HyperKey

## Overview

This guide explains how to write unit tests, run tests locally, and understand the CI/CD pipeline that runs automatically on GitHub.

## Setup

### 1. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

This installs:
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **pytest-xdist**: Parallel test execution

### 2. Project Structure

```
hyperkey/
├── scripts/              # Main application code
│   ├── pipeline.py      # Core pipeline module
│   ├── load_data.py     # Data loading
│   ├── report.py        # Report generation
│   └── ...
├── tests/               # Test files (NEW)
│   ├── __init__.py
│   ├── test_pipeline.py # Tests for pipeline.py
│   ├── test_load_data.py
│   └── ...
├── conftest.py          # Pytest fixtures and configuration (NEW)
├── pytest.ini           # Pytest settings (NEW)
└── requirements-dev.txt # Development dependencies (NEW)
```

## Running Tests Locally

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage Report

```bash
pytest --cov=scripts --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test File

```bash
pytest tests/test_pipeline.py
```

### Run Specific Test Function

```bash
pytest tests/test_pipeline.py::TestHelperFunctions::test_get_date_stamp
```

### Run Tests in Parallel

```bash
pytest -n auto
```

### Run Tests by Marker

```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### View Test Results with Verbose Output

```bash
pytest -v
```

## Writing Unit Tests

### Basic Test Structure

```python
import pytest
from pathlib import Path
from scripts.pipeline import my_function

class TestMyFunctionality:
    """Group related tests together in a class."""

    def test_basic_functionality(self):
        """Test basic behavior."""
        result = my_function("input")
        assert result == "expected_output"

    def test_edge_case(self):
        """Test edge cases."""
        result = my_function("")
        assert result is None

    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    def test_with_multiple_inputs(self, input, expected):
        """Test with multiple input/output pairs."""
        assert my_function(input) == expected
```

### Using Fixtures

Fixtures are reusable test utilities defined in `conftest.py`:

```python
def test_with_temp_directory(temp_dir):
    """Use the temporary directory fixture."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()

def test_with_sig_file(sample_sig_file):
    """Use the sample .sig file fixture."""
    wavelengths, reflectance = parse_sig_file(sample_sig_file)
    assert len(wavelengths) > 0
```

Available fixtures in `conftest.py`:
- `temp_dir`: Temporary directory (auto-cleaned)
- `sample_sig_file`: Sample .sig file for testing
- `sample_metadata_csv`: Sample CSV metadata file
- `project_root`: Path to project root
- `data_dir`: Path to data directory

### Testing with Mocks

```python
from unittest.mock import Mock, patch

def test_function_with_mock(mocker):
    """Test function that uses external dependencies."""
    # Mock a function
    mock_func = mocker.patch('scripts.pipeline.external_function')
    mock_func.return_value = "mocked_value"
    
    result = my_function_that_calls_external()
    assert result == "expected"
    mock_func.assert_called_once()
```

### Test Markers

Mark tests with categories:

```python
@pytest.mark.unit
def test_simple_function():
    pass

@pytest.mark.integration
def test_with_files():
    pass

@pytest.mark.slow
def test_heavy_computation():
    pass

@pytest.mark.cli
def test_command_line():
    pass
```

## Understanding the CI/CD Pipeline

### Automated Workflows (`.github/workflows/`)

Two main workflows run automatically on every push and pull request:

#### 1. **tests.yml** - Unit Tests and Coverage
- **Triggers**: Push to `main`/`develop`, Pull Requests
- **Tests Against**: Python 3.9, 3.10, 3.11, 3.12
- **Steps**:
  1. Checkout code
  2. Setup Python
  3. Cache dependencies (faster runs)
  4. Install dev dependencies
  5. Run pytest with coverage
  6. Upload coverage to Codecov
  7. Archive test results as artifacts

**What happens if tests fail:**
- PR cannot be merged
- The failure is displayed on the PR
- Check the GitHub Actions logs for details

#### 2. **lint.yml** - Code Quality
- **Triggers**: Same as tests
- **Tools**:
  - **Black**: Code formatting checker
  - **isort**: Import sorting checker
  - **Flake8**: Style guide enforcement
  - **Pylint**: Code analysis

**What happens if linting fails:**
- Shows warnings in the PR but doesn't block merge (configurable)

### Viewing CI/CD Results

1. **On GitHub**: Go to Actions tab → Click workflow run
2. **On PR**: Check "Checks" section for status
3. **Artifacts**: Download coverage reports (htmlcov/)

### Local CI Emulation

To test if your code will pass CI before pushing:

```bash
# Run tests exactly as CI does
pytest --cov=scripts --cov-report=xml

# Check code formatting
black scripts/ tests/
isort scripts/ tests/

# Check linting
flake8 scripts/ tests/
```

## Example Test Cases

See `tests/test_pipeline.py` for complete examples:

- **Helper Functions**: `TestHelperFunctions` class
- **Filepath Building**: `TestBuildFilepath` class
- **File Parsing**: `TestParseSigFile` class
- **Output Configuration**: `TestParseOutputTarget` class

## Coverage Requirements

The project generates coverage reports showing:
- **Line coverage**: % of code lines executed
- **Branch coverage**: % of conditional branches tested
- **Missing lines**: Which lines aren't covered

### Viewing Coverage

```bash
# Terminal report
pytest --cov=scripts --cov-report=term-missing

# HTML report (open in browser)
pytest --cov=scripts --cov-report=html
open htmlcov/index.html
```

### Coverage Goals

- Aim for **>80% coverage** for critical modules
- 100% coverage not realistic or necessary
- Focus on testing important logic paths

## Best Practices

1. **Test Names are Documentation**
   ```python
   # Good ✓
   def test_parse_sig_file_with_valid_content()
   
   # Bad ✗
   def test_sig()
   ```

2. **Arrange-Act-Assert Pattern**
   ```python
   def test_something():
       # Arrange
       input_data = "test"
       
       # Act
       result = function(input_data)
       
       # Assert
       assert result == "expected"
   ```

3. **One Assertion Per Test** (when possible)
   - Easier to debug
   - Clearer what failed

4. **Test Edge Cases**
   ```python
   def test_with_empty_input()
   def test_with_none_input()
   def test_with_large_input()
   ```

5. **Use Parametrize for Variations**
   ```python
   @pytest.mark.parametrize("input,expected", [
       ("a", 1), ("b", 2), ("c", 3)
   ])
   def test_function(input, expected):
       assert function(input) == expected
   ```

## Troubleshooting

### Tests Won't Run

```bash
# Verify pytest installation
pytest --version

# Reinstall dependencies
pip install --force-reinstall -r requirements-dev.txt
```

### Import Errors in Tests

Ensure `conftest.py` properly adds scripts to path. Check:
```python
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
```

### Coverage Reports Missing

```bash
# Ensure coverage package is installed
pip install coverage

# Regenerate with verbose output
pytest -v --cov=scripts --cov-report=html
```

### CI Fails but Local Tests Pass

- Might be Python version specific
- Check CI logs for the failing Python version
- Test locally with that version:
  ```bash
  python3.9 -m pytest
  ```

## Next Steps

1. **Add more tests** for `load_data.py`, `report.py`, etc.
2. **Set coverage threshold**: Require minimum coverage % in CI
3. **Add pre-commit hooks**: Run tests before committing
4. **Document test data**: Create examples for each test
5. **Integration tests**: Test full pipeline with real data

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/python-testing/)
