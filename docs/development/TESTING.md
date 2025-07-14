# Testing Guide for WinGet Manifest Generator Tool

This document provides comprehensive information about the testing framework implemented for the WinGet Manifest Generator Tool project.

## Overview

The project now includes a comprehensive testing suite with:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Error Handling**: Comprehensive exception handling
- **Code Documentation**: Detailed docstrings for all components

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── unit/                       # Unit tests
│   ├── test_token_manager.py   # TokenManager unit tests
│   └── test_package_processor.py # PackageProcessor unit tests
├── integration/                # Integration tests
│   └── test_integration.py     # Cross-component integration tests
├── e2e/                       # End-to-end tests
│   └── test_e2e.py            # Complete workflow tests
└── fixtures/                  # Test data and fixtures
```

## Running Tests

### Using the Test Runner Script

The easiest way to run tests is using the provided test runner script:

```bash
# Install dependencies
python run_tests.py install

# Run all tests
python run_tests.py test

# Run specific test types
python run_tests.py test --test-type unit
python run_tests.py test --test-type integration
python run_tests.py test --test-type e2e

# Run with coverage
python run_tests.py test --coverage

# Run tests in parallel
python run_tests.py test --parallel

# Run complete quality suite
python run_tests.py all
```

### Using Makefile

```bash
# Install dependencies
make install

# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-e2e

# Run with coverage
make coverage

# Run linting
make lint

# Format code
make format

# Run all quality checks
make quality
```

### Using pytest directly

```bash
# Install dependencies first
pip install -r src/requirements.txt
pip install pytest pytest-cov pytest-xdist

# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html -v

# Run tests in parallel
pytest tests/ -n auto -v

# Run specific markers
pytest tests/ -m "not slow" -v
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation:

- **TokenManager**: Tests token loading, rotation, and rate limit handling
- **PackageProcessor**: Tests manifest processing, data extraction, and file operations
- **Custom Exceptions**: Tests exception handling and error propagation

```bash
# Run only unit tests
python run_tests.py test --test-type unit
```

### Integration Tests

Integration tests verify that components work together correctly:

- **Package Processing Pipeline**: Tests the complete package processing workflow
- **GitHub API Integration**: Tests GitHub API interactions with mocked responses
- **File I/O Operations**: Tests file reading/writing with real file systems
- **Error Handling**: Tests error propagation across components

```bash
# Run only integration tests
python run_tests.py test --test-type integration
```

### End-to-End Tests

E2E tests simulate real-world usage scenarios:

- **Complete Workflow**: Tests the entire pipeline from manifest processing to output generation
- **Performance Testing**: Tests system behavior under load
- **Error Recovery**: Tests graceful handling of various error conditions
- **Data Consistency**: Tests that data remains consistent across processing steps

```bash
# Run only e2e tests
python run_tests.py test --test-type e2e
```

## Test Markers

The test suite uses pytest markers to categorize tests:

- `unit`: Unit tests
- `integration`: Integration tests  
- `e2e`: End-to-end tests
- `slow`: Tests that take longer to run
- `github_api`: Tests requiring GitHub API access

```bash
# Run fast tests only (exclude slow ones)
pytest tests/ -m "not slow" -v

# Run tests that don't require GitHub API
pytest tests/ -m "not github_api" -v
```

## Test Fixtures

The `conftest.py` file provides reusable fixtures:

- `temp_dir`: Temporary directory for file operations
- `sample_manifest_data`: Sample WinGet manifest data
- `sample_package_dataframe`: Sample package DataFrame
- `mock_github_response`: Mock GitHub API responses
- `mock_token_manager`: Mock TokenManager instance
- `mock_github_api`: Mock GitHub API calls

## Coverage Reporting

Generate coverage reports to track test coverage:

```bash
# Generate HTML coverage report
python run_tests.py coverage

# View coverage report
open htmlcov/index.html
```

Coverage reports show:
- Line coverage for each file
- Missing lines that need test coverage
- Overall coverage percentage

## Error Handling Testing

The test suite includes comprehensive error handling tests:

1. **Custom Exceptions**: All custom exceptions are tested for proper instantiation and message formatting
2. **Error Propagation**: Tests verify that errors are properly caught and re-raised with additional context
3. **Graceful Degradation**: Tests ensure the system handles errors gracefully without crashing
4. **Recovery Scenarios**: Tests verify the system can recover from errors when possible

## Performance Testing

Performance tests are included to ensure the system scales appropriately:

```bash
# Run performance tests (marked as slow)
pytest tests/ -m "slow" -v

# Run benchmark tests if available
pytest tests/ -m "benchmark" --benchmark-only
```

## Code Quality Checks

### Linting

```bash
# Run linting checks
python run_tests.py lint

# Or using make
make lint
```

### Type Checking

```bash
# Run type checking
python run_tests.py typecheck

# Or using make
make typecheck
```

### Code Formatting

```bash
# Check code formatting
python run_tests.py format --format-check

# Format code
python run_tests.py format

# Or using make
make format-check  # Check only
make format        # Format code
```

## Continuous Integration

The test suite is designed to work with CI/CD systems:

```bash
# Run CI-friendly test command
python run_tests.py all --quiet --output test-report.html

# Generate junit XML for CI systems
pytest tests/ --junit-xml=test-results.xml --cov=src --cov-report=xml -v
```

## Writing New Tests

### Unit Test Template

```python
"""Unit tests for YourComponent."""

import pytest
from unittest.mock import Mock, patch

from src.your_module import YourComponent
from src.exceptions import YourCustomException


class TestYourComponent:
    """Test cases for YourComponent."""
    
    def test_your_method_success(self):
        """Test successful execution of your_method."""
        component = YourComponent()
        result = component.your_method("test_input")
        assert result == "expected_output"
    
    def test_your_method_failure(self):
        """Test error handling in your_method."""
        component = YourComponent()
        with pytest.raises(YourCustomException):
            component.your_method("invalid_input")
```

### Integration Test Template

```python
"""Integration tests for YourComponent."""

import pytest
from pathlib import Path

from src.your_module import YourComponent


@pytest.mark.integration
class TestYourComponentIntegration:
    """Integration tests for YourComponent."""
    
    def test_component_integration(self, temp_dir):
        """Test component integration with file system."""
        component = YourComponent()
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        result = component.process_file(test_file)
        assert result is not None
```

## Best Practices

1. **Test Naming**: Use descriptive test names that explain what is being tested
2. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
3. **Mocking**: Use mocks for external dependencies to ensure tests are isolated
4. **Error Testing**: Always test both success and failure scenarios
5. **Documentation**: Include docstrings explaining the purpose of each test
6. **Fixtures**: Use fixtures for common test setup to avoid code duplication

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure `PYTHONPATH` includes the project root
2. **Token Errors**: Tests use mock tokens by default, ensure test environment is set up correctly
3. **File Permission Errors**: Temporary directories should have proper permissions
4. **Slow Tests**: Use the `--markers "not slow"` flag to skip slow tests during development

### Debug Mode

Run tests with additional debugging information:

```bash
# Run with debugging output
pytest tests/ -v -s --tb=long

# Run specific test with debugging
pytest tests/unit/test_token_manager.py::TestTokenManager::test_specific_method -v -s
```

### Test Data

Test data and fixtures are stored in `tests/fixtures/`. Add new test data files here and reference them in your tests.

## Environment Variables for Testing

The test suite uses these environment variables:

- `TOKEN_1`, `TOKEN_2`: Mock GitHub tokens for testing
- `PYTHONPATH`: Should include the project root directory

These are automatically set by the test runner scripts.

## Contributing to Tests

When adding new features:

1. Write unit tests for individual components
2. Add integration tests for component interactions
3. Include error handling tests
4. Update documentation if needed
5. Ensure all tests pass before submitting changes

For more information, see the main README.md file.
