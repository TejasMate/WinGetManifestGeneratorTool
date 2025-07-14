# Scripts

This directory contains utility scripts for development, testing, and maintenance.

## Available Scripts

### Data Processing Scripts
- `organize_removed_rows.py` - Organize filtered data by filter reason (wrapper for Filter.py functionality)

### Testing Scripts
- `test_monitoring.py` - Comprehensive monitoring system test
- `test_config.py` - Configuration system validation
- `test_legacy_compatibility.py` - Legacy code compatibility tests
- `run_tests.py` - Test runner with coverage reporting

### Development Scripts
- `setup_dev.py` - Development environment setup
- `lint.py` - Code linting and formatting
- `build.py` - Package building and distribution

### Maintenance Scripts
- `cleanup.py` - Clean up temporary files and caches
- `update_deps.py` - Update dependencies

## Primary Filtering & Analysis

The main filtering and analysis functionality is located in:
**`src/winget_automation/github/Filter.py`**

This module provides:
- `process_filters()` - Core filtering logic for 8 different filters
- `analyze_filter_patterns()` - Statistical analysis of filter results
- `organize_removed_rows_by_filter()` - Organization by filter categories
- `process_filters_with_analysis()` - Combined filtering and analysis workflow

## Usage

Run scripts from the project root directory:

```bash
# Organize existing filtered data
python scripts/organize_removed_rows.py

# Run filtering with analysis (from Python)
python -c "from src.winget_automation.github.Filter import process_filters_with_analysis; process_filters_with_analysis('data/input.csv', 'data', True)"

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
