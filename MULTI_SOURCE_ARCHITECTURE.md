# Multi-Source Architecture - Implementation Complete

## Overview

The WinGet Manifest Generator Tool has been successfully restructured to support multiple package sources (GitHub, GitLab, SourceForge, and more) using a modern, extensible architecture.

## New Structure

```
src/
├── main.py                     # Main entry point (replaces GitHub.py)
├── sources/                    # Multi-source framework
│   ├── __init__.py            # Source registry and factory
│   ├── base/                  # Base classes and interfaces
│   │   ├── __init__.py        # Core interfaces and data models
│   │   ├── url_matcher.py     # Base URL matching logic
│   │   └── filter_base.py     # Base filtering logic
│   ├── github/                # GitHub source implementation
│   │   ├── __init__.py
│   │   └── github_source.py   # Full GitHub integration
│   ├── gitlab/                # GitLab source implementation
│   │   ├── __init__.py
│   │   └── gitlab_source.py   # GitLab API integration
│   ├── sourceforge/           # SourceForge source implementation
│   │   ├── __init__.py
│   │   └── sourceforge_source.py
│   └── registry.py            # Source factory and registry
├── core/                      # Core processing framework
│   ├── processor.py           # Unified package processor
│   └── ...                    # Other core modules
├── utils/                     # Utility modules
│   ├── file_utils.py         # File operations
│   └── ...
└── monitoring/               # Logging and monitoring
    └── logging_setup.py      # Centralized logging
```

## Key Features

### 1. **Multi-Source Support**
- **GitHub**: Full API integration with token management
- **GitLab**: Ready for API integration (gitlab.com and self-hosted)
- **SourceForge**: Project detection and basic metadata extraction
- **Extensible**: Easy to add new sources (Bitbucket, custom repos, etc.)

### 2. **Unified Processing**
```python
from src.sources import auto_detect_and_process, create_source, SourceType

# Auto-detect source and process
metadata = auto_detect_and_process("https://github.com/user/repo")

# Create specific source
github_source = create_source(SourceType.GITHUB, config)
metadata = github_source.extract_package_info("https://github.com/user/repo")
```

### 3. **Enhanced URL Pattern Extraction**
- Detects architectures: `x64`, `x86`, `arm64`, `arm`
- Extracts extensions: `exe`, `msi`, `zip`, `7z`, etc.
- Identifies keywords: `setup`, `installer`, `portable`, `windows`
- Handles complex URLs including `/download` endpoints

### 4. **Improved CSV Output**
All processing now outputs standardized CSV with these columns:
- `PackageIdentifier`: Unique identifier (e.g., "GitHub.owner.repo")
- `Source`: Source type (github, gitlab, sourceforge)
- `AvailableVersions`: Latest version information
- `VersionFormatPattern`: Detected version pattern
- `CurrentLatestVersionInWinGet`: Integration with WinGet API
- `InstallerURLsCount`: Number of installer URLs found
- `LatestVersionURLsInWinGet`: Download URLs for latest version
- `URLPatterns`: Extracted patterns (e.g., "x64-exe,setup-x86-msi")
- `LatestVersionPullRequest`: PR status tracking

## Usage Examples

### Command Line
```bash
# Process a CSV file
python src/main.py data/input.csv output/results.csv

# Process with specific configuration
python src/main.py data/input.csv --config config/multi-source.yaml
```

### Programmatic Usage
```python
from src.core.processor import create_processor
from src.sources import SourceType

# Create processor with configuration
config = {
    'sources': {
        'github': {'github_tokens': ['your_token_here']},
        'gitlab': {'gitlab_token': 'your_token_here'},
        'sourceforge': {}
    },
    'processing': {'async': True, 'max_workers': 10}
}

processor = create_processor(config)

# Process URLs directly
urls = [
    "https://github.com/microsoft/terminal",
    "https://gitlab.com/inkscape/inkscape", 
    "https://sourceforge.net/projects/audacity/"
]

packages = processor.process_urls(urls)

# Process CSV file
result_file = processor.process_csv("input.csv", "output.csv")
```

### Adding New Sources
```python
from src.sources.base import BasePackageSource, SourceType

class BitbucketSource(BasePackageSource):
    @property
    def source_type(self) -> SourceType:
        return SourceType.BITBUCKET
    
    def is_supported_url(self, url: str) -> bool:
        return 'bitbucket.org' in url.lower()
    
    def extract_package_info(self, url: str) -> Optional[PackageMetadata]:
        # Implementation here
        pass

# Register the new source
from src.sources import register_source
register_source(SourceType.BITBUCKET, BitbucketSource)
```

## Configuration

Create `config/config.multi-source.yaml`:
```yaml
sources:
  github:
    github_tokens: ["token1", "token2"]  # Multiple tokens for rate limiting
    filter:
      min_stars: 10
      exclude_templates: true
      exclude_archived: true
  
  gitlab:
    gitlab_token: "your_gitlab_token"
    gitlab_instances: ["gitlab.com", "gitlab.example.com"]
  
  sourceforge:
    filter:
      exclude_templates: true

processing:
  async: true
  max_workers: 10
  batch_size: 100

logging:
  level: "INFO"
  file_logging: true
```

## Migration from Legacy Code

The restructure maintains backward compatibility while providing a clear migration path:

1. **Legacy files moved to `legacy/` directory**
2. **Main entry point**: `src/main.py` replaces `GitHub.py`
3. **Unified processor**: `src/core/processor.py` replaces `PackageProcessor.py`
4. **Source-specific logic**: Moved to `src/sources/github/`

### Migration Steps
1. Update import statements:
   ```python
   # Old
   from GitHub import process_packages
   from PackageProcessor import PackageProcessor
   
   # New
   from src.main import main
   from src.core.processor import create_processor
   ```

2. Update configuration files to use new format
3. Test with your existing data files

## Performance Improvements

1. **Efficient GitHub Detection**: Uses `Source` column to filter GitHub packages (3,433 out of 8,379 total)
2. **Parallel Processing**: Async and multi-threaded options
3. **Smart Rate Limiting**: Token rotation and backoff strategies
4. **Batched Processing**: Configurable batch sizes for large datasets

## Testing

```bash
# Run basic tests
python -m pytest tests/

# Test specific source
python -c "from src.sources import create_source, SourceType; 
           source = create_source(SourceType.GITHUB); 
           print(source.extract_package_info('https://github.com/microsoft/terminal'))"

# Test migration
python scripts/migrate_to_multi_source.py --dry-run
```

## Benefits of New Architecture

1. **Scalability**: Easy to add new sources without changing core logic
2. **Maintainability**: Clear separation of concerns
3. **Testability**: Each source can be tested independently  
4. **Flexibility**: Can process multiple sources simultaneously
5. **Performance**: Optimized processing with async support
6. **Extensibility**: Plugin-like architecture for sources

## Future Enhancements

1. **Additional Sources**: Bitbucket, custom Git repositories, package managers
2. **Advanced Filtering**: ML-based package quality assessment
3. **Real-time Processing**: Webhook integrations for live updates
4. **API Integration**: Direct WinGet repository integration
5. **Web Interface**: Dashboard for monitoring and management

The new architecture provides a solid foundation for extending the tool to support any package source while maintaining high performance and reliability.
