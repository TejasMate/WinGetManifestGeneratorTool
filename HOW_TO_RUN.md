# How to Run the WinGet Manifest Generator Tool

This guide provides comprehensive instructions for running the WinGet Manifest Generator Tool in different ways, from quick testing to production usage.

## 📋 Prerequisites

### 1. Python Environment
```bash
# Ensure you have Python 3.8 or higher
python --version

# Install required dependencies
pip install -r requirements.txt

# Or install additional development dependencies
pip install -r requirements-dev.txt
```

### 2. GitHub Tokens (Optional but Recommended)
```bash
# Copy environment template
cp config/config.example.yaml config/config.yaml

# Edit config/config.yaml and add your GitHub tokens:
# github_tokens:
#   - "your_github_token_1"
#   - "your_github_token_2"
```

## 🚀 Quick Start (5 Minutes)

### Option 1: Test with Sample Data (Fastest)
```bash
# Test the new multi-source architecture
python -c "
import sys
sys.path.append('src')
from sources import auto_detect_and_process
result = auto_detect_and_process('https://github.com/microsoft/terminal')
print(f'✅ Detected: {result.identifier} from {result.source_type.value}')
"

# Test with sample CSV data
python src/main.py quick_test/test_input.csv output/test_results.csv
```

### Option 2: Get Started Script (Traditional Workflow)
```bash
# Run the traditional 3-step workflow
python get_started.py --all

# Or run individual steps:
python get_started.py --step 1  # Process packages
python get_started.py --step 2  # Analyze GitHub repos
python get_started.py --step 3  # Generate commands
```

### Option 3: Process Real Data
```bash
# Process the existing package data
python src/main.py data/AllPackageInfo.csv output/processed_packages.csv
```

## 🎯 Running Methods

### Method 1: New Multi-Source Architecture (Recommended)

The restructured tool supports multiple package sources:

```bash
# Basic usage - auto-detects source from URLs
python src/main.py input.csv output.csv

# Process URLs from multiple sources
python -c "
import sys
sys.path.append('src')
from core.processor import create_processor

processor = create_processor()
urls = [
    'https://github.com/microsoft/terminal',     # GitHub
    'https://gitlab.com/inkscape/inkscape',      # GitLab
    'https://sourceforge.net/projects/audacity/' # SourceForge
]
results = processor.process_urls(urls)
print(f'Processed {len(results)} packages')
"
```

### Method 2: Legacy Workflow (Backward Compatible)

For users familiar with the original workflow:

```bash
# Step 1: Process WinGet packages
python src/PackageProcessor.py

# Step 2: Analyze GitHub repositories  
python src/GitHub.py

# Step 3: Generate Komac commands
python src/KomacCommandsGenerator.py
```

### Method 3: Professional CLI (Future Ready)

The project includes a modern CLI interface:

```bash
# Install the package
pip install -e .

# Health check
wmat health

# Process packages with monitoring
wmat process --packages Microsoft.VSCode --dry-run

# View metrics
wmat metrics
```

## 📊 Input/Output Formats

### Input CSV Format
Your input CSV should contain package information. The tool accepts various formats:

```csv
PackageIdentifier,Source,AvailableVersions,VersionFormatPattern,CurrentLatestVersionInWinGet,InstallerURLsCount,LatestVersionURLsInWinGet,URLPatterns,LatestVersionPullRequest
GitHub.microsoft.terminal,github,1.19.10821.0,{Major}.{Minor}.{Build}.{Revision},1.18.3181.0,4,https://github.com/microsoft/terminal/releases/download/v1.19.10821.0/Microsoft.WindowsTerminal_1.19.10821.0_8wekyb3d8bbwe.msixbundle,x64-msixbundle,unknown
```

### Output CSV Format
The tool outputs an enhanced CSV with:
- `Source` column identifying the package source
- Enhanced `URLPatterns` with architecture detection
- Improved version pattern detection
- Package metadata from multiple sources

## 🔧 Configuration Options

### Basic Configuration (config/config.yaml)
```yaml
# GitHub tokens for API access
github_tokens:
  - "your_token_here"

# Processing options
processing:
  async: false        # Enable async processing
  max_workers: 10     # Number of parallel workers
  batch_size: 100     # Batch size for processing

# Source-specific settings
sources:
  github:
    filter:
      min_stars: 0
      exclude_templates: true
  gitlab:
    gitlab_token: "your_gitlab_token"
  sourceforge:
    # No configuration needed
```

### Environment Variables
```bash
# Alternative to config file
export GITHUB_TOKENS="token1,token2"
export GITLAB_TOKEN="your_gitlab_token"
export ASYNC_PROCESSING=true
export MAX_WORKERS=20
```

## 🧪 Testing & Validation

### Quick Tests
```bash
# Test source detection
python -c "
import sys; sys.path.append('src')
from sources import get_registry
print('Available sources:', [s.value for s in get_registry().get_available_sources()])
"

# Test GitHub source
python -c "
import sys; sys.path.append('src')
from sources import create_source, SourceType
source = create_source(SourceType.GITHUB, {})
print('GitHub URL support:', source.is_supported_url('https://github.com/user/repo'))
"

# Test file processing
python src/main.py quick_test/test_input.csv /tmp/test_output.csv
echo "Output files:"
ls -la /tmp/test_output.*
```

### Full Test Suite
```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/
```

## 📈 Performance & Monitoring

### Async Processing (For Large Datasets)
```python
import asyncio
from src.core.processor import create_processor

config = {
    'processing': {
        'async': True,
        'max_workers': 20,
        'batch_size': 50
    }
}

processor = create_processor(config)
result = processor.process_csv('large_input.csv', 'output.csv')
```

### Monitoring
```bash
# Check system health
python -c "
import sys; sys.path.append('src')
from monitoring.health import HealthChecker
health = HealthChecker()
print('System health:', health.check_system_health())
"

# View processing metrics
python scripts/test_monitoring.py
```

## 🚨 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure src is in Python path
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python your_script.py
```

**2. GitHub Rate Limiting**
```bash
# Add multiple GitHub tokens to config.yaml
# The tool automatically rotates tokens
```

**3. Missing Dependencies**
```bash
# Install all dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

**4. CSV Format Issues**
```bash
# Validate CSV format
python -c "
import polars as pl
df = pl.read_csv('your_file.csv')
print('Columns:', df.columns)
print('Shape:', df.shape)
"
```

### Getting Help

**Check Configuration**
```bash
python -c "
import sys; sys.path.append('src')
from config import get_config
config = get_config()
print('Configuration loaded successfully')
print('GitHub tokens configured:', len(config.get('github_tokens', [])))
"
```

**Verbose Logging**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python src/main.py input.csv output.csv
```

## 📚 Example Workflows

### Workflow 1: Quick Package Analysis
```bash
# Create a simple input file
echo "PackageIdentifier,URL
GitHub.microsoft.terminal,https://github.com/microsoft/terminal
GitHub.microsoft.vscode,https://github.com/microsoft/vscode" > my_packages.csv

# Process it
python src/main.py my_packages.csv results.csv

# View results
head -5 results.csv
```

### Workflow 2: Multi-Source Processing
```bash
# Process packages from different sources
python -c "
import sys; sys.path.append('src')
from core.processor import create_processor

urls = [
    'https://github.com/microsoft/terminal',
    'https://gitlab.com/gitlab-org/gitlab',
    'https://sourceforge.net/projects/audacity/'
]

processor = create_processor()
packages = processor.process_urls(urls)

for pkg in packages:
    print(f'{pkg.identifier} ({pkg.source_type.value}) - {len(pkg.latest_release.download_urls) if pkg.latest_release else 0} URLs')
"
```

### Workflow 3: Batch Processing with Configuration
```bash
# Create custom config
cat > my_config.yaml << EOF
sources:
  github:
    github_tokens: ["your_token"]
    filter:
      min_stars: 10
processing:
  async: true
  max_workers: 15
EOF

# Process with custom config
python src/main.py data/AllPackageInfo.csv output/results.csv --config my_config.yaml
```

## ✅ Verified Working Examples

Here are tested examples that you can run immediately:

### 1. **Quick Multi-Source Test** (30 seconds)
```bash
# Create test input
echo "PackageIdentifier,URL
GitHub.microsoft.terminal,https://github.com/microsoft/terminal
GitHub.microsoft.vscode,https://github.com/microsoft/vscode
GitLab.inkscape.inkscape,https://gitlab.com/inkscape/inkscape" > test_urls.csv

# Process with new multi-source architecture
python src/main.py test_urls.csv -o results.csv

# View results
head -5 results.csv
cat results.summary.txt
```

**Expected Output:**
- ✅ Detects GitHub and GitLab sources automatically
- ✅ Creates enhanced CSV with Source column
- ✅ Generates processing summary

### 2. **Source Registry Test** (10 seconds)
```bash
# Check available sources
python -c "
import sys; sys.path.append('src')
from sources import get_registry
print('✅ Available sources:', [s.value for s in get_registry().get_available_sources()])
"

# Test auto-detection
python -c "
import sys; sys.path.append('src') 
from sources import auto_detect_and_process
result = auto_detect_and_process('https://github.com/microsoft/terminal')
print(f'✅ Detected: {result.identifier} from {result.source_type.value}')
"
```

**Expected Output:**
```
✅ Available sources: ['github', 'gitlab', 'sourceforge']
✅ Detected: GitHub.microsoft.terminal from github
```

### 3. **Legacy Workflow Test** (1 minute)
```bash
# Run traditional 3-step workflow
python get_started.py --step 1  # Process packages
python get_started.py --step 2  # GitHub analysis  
python get_started.py --step 3  # Generate commands

# Or all at once
python get_started.py --all
```

### 4. **Configuration Test**
```bash
# Check configuration loading
python -c "
import sys; sys.path.append('src')
from config import get_config
config = get_config()
print('✅ Configuration loaded')
print('GitHub tokens configured:', len(config.get('github_tokens', [])))
"
```

---

**🎉 You're ready to run the WinGet Manifest Generator Tool!**

Start with the Quick Start section, then explore the different methods based on your needs. The tool is designed to be both powerful and easy to use, supporting everything from quick tests to large-scale production processing.
