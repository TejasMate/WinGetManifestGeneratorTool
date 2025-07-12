# Scripts

This directory contains utility scripts for development, testing, and maintenance.

## Available Scripts

### Testing Scripts
- `test_monitoring.py` - Comprehensive monitoring system test
- `test_config.py` - Configuration system validation
- `run_tests.py` - Test runner with coverage reporting

### Development Scripts
- `setup_dev.py` - Development environment setup
- `lint.py` - Code linting and formatting
- `build.py` - Package building and distribution

### Maintenance Scripts
- `cleanup.py` - Clean up temporary files and caches
- `update_deps.py` - Update dependencies

## Usage

Run scripts from the project root directory:

```bash
# Test the monitoring system
python scripts/test_monitoring.py

# Run all tests with coverage
python scripts/run_tests.py

# Setup development environment
python scripts/setup_dev.py
```

## Requirements

Most scripts require the development dependencies. Install them with:

```bash
pip install -r requirements-dev.txt
```
