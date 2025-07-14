# Configuration Management System

## Overview

The WinGet Manifest Generator Tool now includes a comprehensive configuration management system that provides:

- **Environment-specific configurations** (development, staging, production)
- **Configuration validation** using schemas
- **Multiple configuration sources** (files, environment variables)
- **Configuration merging and inheritance**
- **Type-safe configuration access**

## Quick Start

### Basic Usage

```python
from src.config import get_config, get_config_manager

# Get a specific configuration value
github_tokens = get_config('github.tokens', [])

# Get the complete configuration
config = get_config()

# Use the configuration manager directly
manager = get_config_manager()
config = manager.load_config()
```

### Environment Setup

1. **Set environment**: `export WINGET_ENV=development`
2. **Set GitHub tokens**: `export TOKEN_1=your_github_token_here`
3. **Customize settings**: Edit `config/development.yaml`

## Configuration Structure

### Environment Files

- `config/development.yaml` - Development environment (debug enabled, verbose logging)
- `config/staging.yaml` - Staging environment (moderate settings)
- `config/production.yaml` - Production environment (optimized performance)
- `config/config.yaml` - Base configuration (shared settings)

### Configuration Sections

#### Logging
```yaml
logging:
  level: DEBUG              # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/app.log"      # Log file path (null for console only)
  max_size: 10              # Maximum log file size in MB
  backup_count: 5           # Number of backup log files
```

#### GitHub API
```yaml
github:
  tokens: []                # GitHub API tokens (set via environment)
  api_url: "https://api.github.com"
  per_page: 100
  retry_attempts: 3
  retry_delay: 1.0
  rate_limit_buffer: 100
```

#### Package Processing
```yaml
package_processing:
  winget_repo_path: "winget-pkgs"
  output_directory: "data"
  file_patterns:
    - "*.installer.yaml"
  max_workers: 4            # Number of parallel workers
  batch_size: 100           # Packages per batch
  timeout: 300              # Timeout in seconds
```

#### Filtering
```yaml
filtering:
  blocked_packages: []      # Packages to exclude
  allowed_architectures:
    - "x64"
    - "x86"
    - "arm64"
  allowed_extensions:
    - "msi"
    - "exe"
    - "zip"
  min_download_count: 0
  max_package_age_days: 365
```

#### Output
```yaml
output:
  formats:
    - "csv"
    - "json"
  compression: "gzip"       # none, gzip, bz2, xz
  include_metadata: true
  timestamp_format: "%Y%m%d_%H%M%S"
```

#### Performance
```yaml
performance:
  cache_enabled: true
  cache_ttl: 3600          # Cache TTL in seconds
  memory_limit_mb: 1024
  enable_profiling: false
```

## Environment Variables

The system supports environment variable overrides:

| Environment Variable | Configuration Key | Description |
|---------------------|-------------------|-------------|
| `WINGET_ENV` | N/A | Environment selection (development/staging/production) |
| `TOKEN_1`, `TOKEN_2`, ... | `github.tokens` | GitHub API tokens |
| `LOG_LEVEL` | `logging.level` | Logging level |
| `LOG_FILE` | `logging.file` | Log file path |
| `MAX_WORKERS` | `package_processing.max_workers` | Number of workers |
| `BATCH_SIZE` | `package_processing.batch_size` | Batch size |
| `TIMEOUT` | `package_processing.timeout` | Operation timeout |
| `CACHE_ENABLED` | `performance.cache_enabled` | Enable/disable cache |
| `DEBUG` | `debug` | Debug mode |

## Integration Examples

### PackageProcessor Integration

```python
from src.config import get_config

class PackageProcessor:
    def __init__(self):
        # Get configuration values
        self.winget_repo_path = get_config("package_processing.winget_repo_path", "winget-pkgs")
        self.output_directory = get_config("package_processing.output_directory", "data")
        self.max_workers = get_config("package_processing.max_workers", 4)
        self.batch_size = get_config("package_processing.batch_size", 100)
        self.timeout = get_config("package_processing.timeout", 300)
        
        # Setup logging
        log_level = get_config("logging.level", "INFO")
        logging.getLogger().setLevel(getattr(logging, log_level))
```

### GitHub Module Integration

```python
from src.config import get_config

class GitHubAPI:
    def __init__(self):
        self.tokens = get_config("github.tokens", [])
        self.api_url = get_config("github.api_url", "https://api.github.com")
        self.per_page = get_config("github.per_page", 100)
        self.retry_attempts = get_config("github.retry_attempts", 3)
        self.retry_delay = get_config("github.retry_delay", 1.0)
```

### Token Manager Integration

```python
from src.config import get_config

class TokenManager:
    def __init__(self):
        self.tokens = get_config("github.tokens", [])
        self.rate_limit_buffer = get_config("github.rate_limit_buffer", 100)
        self.retry_attempts = get_config("github.retry_attempts", 3)
```

## Advanced Usage

### Runtime Configuration Modification

```python
from src.config import get_config_manager

manager = get_config_manager()

# Get current value
current_batch_size = manager.get("package_processing.batch_size")

# Modify configuration at runtime
manager.set("package_processing.batch_size", 200)

# Add custom configuration
manager.set("custom.my_setting", "custom_value")
```

### Configuration Validation

```python
from src.config import get_config_manager

manager = get_config_manager()

# Validate current configuration
is_valid, errors = manager.validate_config()
if not is_valid:
    print("Configuration errors:", errors)

# Validate custom configuration
custom_config = {"logging": {"level": "INFO"}}
is_valid, errors = manager.validate_config(custom_config)
```

### Environment Information

```python
from src.config import get_config_manager

manager = get_config_manager()
env_info = manager.get_environment_info()

print(f"Environment: {env_info['environment']}")
print(f"Config path: {env_info['config_path']}")
print(f"Config files: {env_info['config_files_found']}")
```

## Configuration Loading Order

The system loads configuration in the following order (later sources override earlier ones):

1. **Environment defaults** - Based on selected environment
2. **Base configuration file** - `config/config.yaml`
3. **Environment-specific file** - `config/{environment}.yaml`
4. **Environment variables** - Override any file-based settings

## Best Practices

### Development
- Use `development` environment for local development
- Enable debug mode and verbose logging
- Use smaller batch sizes for faster iteration
- Disable caching for fresh data

### Production
- Use `production` environment for deployment
- Set appropriate log levels (WARNING or ERROR)
- Optimize worker counts and batch sizes
- Enable caching for performance
- Set GitHub tokens via environment variables

### Security
- Never commit GitHub tokens to configuration files
- Use environment variables for sensitive data
- Restrict file permissions on configuration files
- Use different tokens for different environments

## Troubleshooting

### Configuration Not Loading
1. Check environment variable `WINGET_ENV`
2. Verify configuration file paths
3. Check file permissions
4. Validate YAML/JSON syntax

### Validation Errors
1. Check required fields are present
2. Verify data types match schema
3. Check value ranges and constraints
4. Review allowed values for enums

### Environment Variables Not Working
1. Verify environment variable names
2. Check variable values and types
3. Restart application after setting variables
4. Use `env | grep TOKEN` to verify token variables

## Schema Reference

The configuration system uses a comprehensive validation schema that checks:

- **Data types** (string, integer, float, boolean, list, dict)
- **Required fields** and optional fields
- **Value ranges** and constraints
- **Allowed values** for enumerated fields
- **String patterns** and length limits
- **List constraints** (min/max items, item validation)
- **Nested object validation**

See `src/config/schema.py` for the complete schema definition.

## Testing

The configuration system includes comprehensive unit tests:

```bash
# Run configuration tests
python -m pytest tests/unit/test_config.py -v

# Run configuration demo
python test_config.py

# Run integration demo
python integration_demo.py
```

## Migration Guide

To migrate existing code to use the configuration system:

1. **Replace hardcoded values**:
   ```python
   # Before
   self.max_workers = 4
   
   # After
   self.max_workers = get_config("package_processing.max_workers", 4)
   ```

2. **Update initialization**:
   ```python
   # Before
   def __init__(self, repo_path="winget-pkgs"):
       self.repo_path = repo_path
   
   # After
   def __init__(self):
       self.repo_path = get_config("package_processing.winget_repo_path", "winget-pkgs")
   ```

3. **Configure logging**:
   ```python
   # Before
   logging.basicConfig(level=logging.INFO)
   
   # After
   log_level = get_config("logging.level", "INFO")
   logging.basicConfig(level=getattr(logging, log_level))
   ```

4. **Use environment-specific settings**:
   - Create environment-specific configuration files
   - Set `WINGET_ENV` environment variable
   - Configure GitHub tokens via environment variables
