# WinGet Manifest Automation Tool

## Overview

This project is designed to automate the process of analyzing and updating packages in the Microsoft WinGet package repository. It provides tools for processing package manifests, analyzing version patterns, and generating update commands for packages with new versions available on GitHub.

## Project Structure

```
├── README.md                  # Basic usage instructions
├── package_blocklist.json     # List of packages to exclude from processing
├── src/                       # Source code directory
│   ├── PackageProcessor.py    # Main package processing functionality
│   ├── GitHub.py              # GitHub integration and analysis pipeline
│   ├── KomacCommandsGenerator.py # Generates komac update commands
│   ├── github/                # GitHub-specific modules
│   │   ├── Filter.py          # Filtering logic for GitHub packages
│   │   ├── GitHubPackageProcessor.py # GitHub package version analysis
│   │   └── MatchSimilarURLs.py # URL pattern matching and processing
│   └── utils/                 # Utility modules
│       ├── token_manager.py   # GitHub API token rotation and management
│       ├── unified_utils.py   # Common utilities for YAML and GitHub operations
│       └── version_pattern_utils.py # Version pattern detection and analysis
└── winget-pkgs/              # Cloned WinGet packages repository
```

## Prerequisites

- Python 3.8 or higher
- Git
- GitHub API tokens (for accessing GitHub API)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/tejasmate/winget-manifest-automation.git
   cd winget-manifest-automation
   ```

2. Clone the WinGet packages repository:
   ```bash
   git clone --depth=1 --branch="main" https://github.com/microsoft/winget-pkgs.git
   ```

3. Install required dependencies:
   ```bash
   pip install polars requests pyyaml
   ```

4. Set up GitHub API tokens as environment variables:
   ```bash
   # You can set multiple tokens for rotation
   export TOKEN_1=your_github_token_1
   export TOKEN_2=your_github_token_2
   # etc.
   ```

## Usage

The project workflow consists of three main steps:

1. Process WinGet package manifests:
   ```bash
   python src/PackageProcessor.py
   ```
   This analyzes all package manifests in the WinGet repository, extracts version patterns, and creates CSV files with package information.

2. Analyze GitHub repositories for latest versions:
   ```bash
   python src/GitHub.py
   ```
   This checks GitHub repositories for the latest versions of packages and compares them with the versions in WinGet.

3. Generate update commands:
   ```bash
   python src/KomacCommandsGenerator.py
   ```
   This creates komac update commands for packages that have newer versions available on GitHub.

## Core Components

### PackageProcessor

The `PackageProcessor` class is responsible for:
- Scanning the WinGet repository for package manifests
- Extracting package identifiers and version information
- Analyzing version patterns and installer URLs
- Generating CSV files with package information

### GitHub Integration

The GitHub integration components handle:
- Connecting to GitHub API to retrieve release information
- Analyzing version patterns in GitHub releases
- Matching GitHub URLs with WinGet package URLs
- Filtering packages based on various criteria

### Token Manager

The `TokenManager` class provides:
- Rotation of GitHub API tokens to avoid rate limiting
- Tracking of rate limit status for each token
- Automatic selection of available tokens

### Komac Commands Generator

The `KomacCommandsGenerator` creates commands for the komac tool to update packages with new versions available on GitHub.

## Data Flow

1. Package manifests are processed from the WinGet repository
2. Package information is saved to CSV files in the `data` directory
3. GitHub analysis is performed on packages with GitHub URLs
4. Filtered results are saved to CSV files
5. Komac update commands are generated for packages with newer versions

## Configuration

### package_blocklist.json

This file contains a list of package identifiers that should be excluded from processing. You can add or remove packages from this list as needed.

### Environment Variables

- `TOKEN_1`, `TOKEN_2`, etc.: GitHub API tokens for accessing the GitHub API

## Troubleshooting

### Rate Limiting

If you encounter GitHub API rate limiting issues:
- Add more GitHub API tokens to increase the available request quota
- Reduce the number of packages processed in a single run
- Implement longer delays between API requests

### Missing Dependencies

If you encounter import errors, ensure all required packages are installed:
```bash
pip install polars requests pyyaml
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
