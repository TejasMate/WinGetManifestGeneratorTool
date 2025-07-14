# WinGet Manifest Generator Tool

[![CI/CD Pipeline](https://github.com/TejasMate/WinGetManifestGeneratorTool/actions/workflows/ci.yml/badge.svg)](https://github.com/TejasMate/WinGetManifestGeneratorTool/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/TejasMate/WinGetManifestGeneratorTool/branch/main/graph/badge.svg)](https://codecov.io/gh/TejasMate/WinGetManifestGeneratorTool)
[![PyPI version](https://badge.fury.io/py/winget-manifest-generator-tool.svg)](https://badge.fury.io/py/winget-manifest-generator-tool)
[![Python Versions](https://img.shields.io/pypi/pyversions/winget-manifest-generator-tool.svg)](https://pypi.org/project/winget-manifest-generator-tool/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Professional generator tool for managing and updating WinGet package manifests with comprehensive monitoring and observability.**

## 🚀 Features

### Core Functionality
- **Automated Package Processing**: Streamlined workflow for updating WinGet package manifests
- **GitHub Integration**: Seamless integration with GitHub repositories and release management
- **Multi-source Support**: Handle packages from various sources and repositories
- **Batch Processing**: Efficiently process multiple packages simultaneously
- **Manifest Generation**: Automated generation of WinGet manifest files

### Enterprise-Grade Monitoring
- **Structured Logging**: JSON-formatted logs with correlation tracking
- **Comprehensive Metrics**: Performance monitoring with counters, gauges, and histograms
- **Health Checks**: Automated system health monitoring and alerting
- **Progress Tracking**: Real-time progress indicators with ETA calculation

### Developer Experience
- **CLI Interface**: Intuitive command-line interface with rich formatting
- **Configuration Management**: Flexible configuration with environment-specific settings
- **Extensible Architecture**: Plugin-friendly design for custom extensions
- **Comprehensive Testing**: Full test suite with unit, integration, and E2E tests

## 📦 Installation

### From PyPI (Recommended)
```bash
pip install winget-manifest-generator-tool
```

### From Source
```bash
git clone https://github.com/TejasMate/WinGetManifestGeneratorTool.git
cd WinGetManifestGeneratorTool
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/TejasMate/WinGetManifestGeneratorTool.git
cd WinGetManifestGeneratorTool
make dev-setup
```

## 🚀 Quick Start

### 1. Configuration
```bash
# Copy example configuration
cp config/config.example.yaml config/config.yaml

# Edit configuration for your environment
wmat config-status
```

### 2. Health Check
```bash
# Verify system health
wmat health
```

### 3. Process Packages
```bash
# Process specific packages
wmat process --packages Microsoft.VSCode --packages Microsoft.PowerToys

# Process all packages (dry run)
wmat process --dry-run

# Process with filtering
wmat process --filter github
```

### 4. Monitor Operations
```bash
# View system metrics
wmat metrics

# Export health report
wmat health --format json > health-report.json
```

## 🔄 Usage

### Professional CLI (Recommended)

The tool now provides a modern CLI interface for streamlined operations:

```bash
# Install the package
pip install -e .

# Check system health
wmat health

# Process packages with monitoring
wmat process --packages Microsoft.VSCode --dry-run

# View system metrics
wmat metrics
```

### Legacy Workflow (Direct Script Execution)

For users familiar with the original workflow, you can run the core scripts directly. The project workflow consists of three main steps:

#### 1. Process WinGet Package Manifests
```bash
python src/winget_automation/PackageProcessor.py
```
This analyzes all package manifests in the WinGet repository, extracts version patterns, and creates CSV files with package information.

#### 2. Analyze GitHub Repositories for Latest Versions
```bash
export```
This checks GitHub repositories for the latest versions of packages and compares them with the versions in WinGet.

#### 3. Generate Update Commands
```bash
python src/winget_automation/KomacCommandsGenerator.py
```
This creates komac update commands for packages that have newer versions available on GitHub.

> **✅ Import Fix Applied**: All scripts now work correctly with both direct execution and module imports.

#### Legacy Workflow with Monitoring
You can enhance the legacy workflow with the new monitoring capabilities:

```bash
# Run with structured logging
PYTHONPATH=src python scripts/test_monitoring.py

# Process with configuration validation
python scripts/test_config.py

# Run the complete legacy workflow with monitoring
python examples/integration_demo.py
```

### Migration Notes

- **Script Paths**: Scripts moved from `src/` to `src/winget_automation/`
- **Import Paths**: Updated for new package structure
- **Configuration**: Enhanced YAML-based configuration system
- **Monitoring**: All operations now include comprehensive monitoring
- **Backwards Compatibility**: Original functionality preserved

## 🏗️ Architecture

```
WinGet Manifest Generator Tool
├── CLI Interface (Rich formatting, Click-based)
├── Configuration Management (YAML-based, environment-aware)
├── Package Processing Engine
│   ├── GitHub Integration
│   ├── Release Detection
│   └── Manifest Generation
├── Monitoring & Observability
│   ├── Structured Logging (JSON, correlation IDs)
│   ├── Metrics Collection (Prometheus-compatible)
│   ├── Health Checks (System, API, Repository)
│   └── Progress Tracking (Real-time, ETA calculation)
└── Utilities & Extensions
```

## 📖 Documentation

- **[User Guide](docs/user-guide/)** - Configuration and usage instructions
- **[Legacy Migration Guide](docs/user-guide/LEGACY_MIGRATION.md)** - Transition from original scripts
- **[API Documentation](docs/api/)** - Detailed API reference
- **[Development Guide](docs/development/)** - Contributing and development setup
- **[Examples](examples/)** - Code examples and integration patterns

## 🛠️ Development

### Prerequisites
- Python 3.8+
- Git
- Make (optional, for convenience commands)

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/TejasMate/WinGetManifestGeneratorTool.git
cd WinGetManifestGeneratorTool

# Setup development environment
make dev-setup

# Run tests
make test

# Run linting and formatting
make check
```

### Project Structure
```
├── src/winget_automation/     # Main package
│   ├── cli.py                 # Command-line interface
│   ├── config/                # Configuration management
│   ├── monitoring/            # Monitoring and observability
│   ├── github/                # GitHub integration
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
├── docs/                      # Documentation
├── scripts/                   # Development scripts
├── examples/                  # Usage examples
└── config/                    # Configuration files
```

### Available Commands
```bash
make help                   # Show all available commands
make test                   # Run test suite
make lint                   # Run code linting
make format                 # Format code
make build                  # Build package
make clean                  # Clean build artifacts
make docs                   # Generate documentation
make demo                   # Run integration demo
```

## 🔧 Configuration

The tool uses YAML-based configuration with environment-specific overrides:

```yaml
# config/config.yaml
github:
  api_url: "https://api.github.com"
  tokens:
    - "your-github-token"
  
processing:
  batch_size: 10
  concurrent_workers: 4
  
monitoring:
  logging:
    level: "INFO"
    structured: true
  health_checks:
    enabled: true
    interval: 60
```

See [Configuration Guide](docs/user-guide/CONFIGURATION.md) for detailed setup instructions.

## 📊 Monitoring

### Structured Logging
```python
from winget_automation.monitoring import get_logger

logger = get_logger(__name__)
logger.info("Processing package", package="Microsoft.VSCode", version="1.85.0")
```

### Metrics Collection
```python
from winget_automation.monitoring import get_metrics_collector, timer

metrics = get_metrics_collector()
metrics.increment_counter("packages.processed")

with timer("api_request_duration"):
    # Your API call here
    pass
```

### Health Monitoring
```bash
# Check system health
wmat health

# Programmatic health checks
from winget_automation.monitoring import check_all_health
health_results = check_all_health()
```

## 🐳 Docker Support

### Development
```bash
# Start development environment
docker-compose up winget-automation

# Run with monitoring
docker-compose up
```

### Production
```bash
# Build production image
docker build --target production -t winget-automation .

# Run container
docker run -v $(pwd)/config:/app/config winget-automation wmat health
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `make test`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Microsoft WinGet team for the package manager
- GitHub for excellent API and platform support
- Python community for amazing libraries and tools

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/TejasMate/WinGetManifestGeneratorTool/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TejasMate/WinGetManifestGeneratorTool/discussions)
- **Documentation**: [docs/](docs/)

---

<div align="center">
  <strong>Made with ❤️ for the WinGet community</strong>
</div>
