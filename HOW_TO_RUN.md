# How to Run WinGet Manifest Automation Tool

This guide explains how to run the enhanced WinGet Manifest Automation Tool with its new multi-source architecture and improved filtering capabilities.

## 📋 Prerequisites

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/TejasMate/WinGetManifestAutomationTool.git
cd WinGetManifestAutomationTool

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
cp .env.example .env
# Edit .env with your GitHub token:
# GITHUB_TOKEN=your_github_token_here
```

### 2. Configuration
The project uses a unified configuration system in `config/config.yaml`. The default configuration should work for most cases.

## 🚀 Running the Project

### Method 1: Sequential Execution (Traditional Way)

This is the traditional three-step workflow you mentioned:

#### Step 1: Package Processing
```bash
cd src
python PackageProcessor.py
```
**What it does:**
- Processes WinGet package manifests with optimized workflow
- Extracts package information and metadata efficiently  
- Generates comprehensive package analysis data
- Outputs: `data/AllPackageInfo.csv` (includes package names + analysis)
- Outputs: `data/OpenPRs.csv` (open pull requests)
- **Note**: PackageNames.csv is no longer generated (redundant)

#### Step 2: GitHub Analysis
```bash
cd src
python GitHub.py
```
**What it does:**
- Analyzes GitHub repositories for package updates
- Fetches latest release information
- Matches URLs and versions
- Applies enhanced filtering with individual CSV outputs
- Outputs: Multiple filtered CSV files and FilteringSummary.md

#### Step 3: Komac Commands Generation
```bash
cd src
python KomacCommandsGenerator.py
```
**What it does:**
- Generates komac update commands for valid packages
- Creates batch update scripts
- Outputs: `komac_update_commands_github.txt`

### Method 2: Using the Legacy Workflow Script

Run the complete workflow in one command:

```bash
python examples/legacy_workflow.py
```

### Method 3: Using Individual Components

#### For GitHub Package Processing Only:
```bash
cd src
python -c "
from GitHub import main
main()
"
```

#### For Enhanced Filtering with CSV Outputs:
```bash
cd src
python -c "
from github.Filter import process_filters
process_filters('data/GitHubPackageInfo_CleanedURLs.csv', 'data/filtered_output')
"
```

## 📁 Output Files Structure

After running the complete workflow, you'll have:

```
data/
├── AllPackageInfo.csv                    # Complete package data (names + analysis)
├── OpenPRs.csv                          # Open pull requests info
├── github/
│   ├── GitHubPackageInfo_Filter1.csv    # After Filter 1
│   ├── GitHubPackageInfo_Filter2.csv    # After Filter 2
│   ├── ...                              # After each filter
│   ├── GitHubPackageInfo_Filter8.csv    # Final filtered packages
│   ├── Filter1_Removed.csv              # Packages removed by Filter 1
│   ├── Filter2_Removed.csv              # Packages removed by Filter 2
│   ├── ...                              # Removed by each filter
│   ├── Filter8_Removed.csv              # Packages removed by Filter 8
│   ├── RemovedRows.csv                   # All removed packages combined
│   ├── FilteringSummary.md               # Comprehensive filter report
│   └── komac_update_commands_github.txt # Final komac commands
```

## 🔍 Enhanced Filtering Features

The new filtering system provides detailed analysis:

### Individual Filter Analysis
Each filter now saves removed packages to separate CSV files:
- **Filter1_Removed.csv** - No GitHub release found
- **Filter2_Removed.csv** - No GitHub download URLs
- **Filter3_Removed.csv** - Has open pull requests
- **Filter4_Removed.csv** - No architecture/extension data
- **Filter5_Removed.csv** - URLs already match WinGet
- **Filter5_5_Removed.csv** - GitHub URLs match any WinGet version
- **Filter6_Removed.csv** - Versions match exactly
- **Filter7_Removed.csv** - Versions match after normalization
- **Filter8_Removed.csv** - URL counts don't match

### Summary Report
The `FilteringSummary.md` file provides:
- Overall statistics (retention rate, total removed)
- Detailed breakdown by each filter
- List of all generated files
- Usage instructions

## 🛠️ Advanced Usage

### Using the Multi-Source Architecture

The project now supports multiple package sources:

```bash
cd src
python -c "
from core.package_sources import PackageSourceRegistry
from sources.github_source import GitHubPackageSource

# Register and use GitHub source
registry = PackageSourceRegistry()
github_source = GitHubPackageSource()
registry.register_source('github', github_source)

# Process packages from GitHub
packages = github_source.get_packages(['Microsoft.VSCode'])
"
```

### Configuration Customization

Edit `config/config.yaml` to customize:
- Output directories
- Processing parameters
- GitHub API settings
- Logging configuration

### Testing the Enhanced Filter

Run with test data:
```bash
cd src/github
python Filter.py
```

This will create test data and demonstrate the enhanced filtering capabilities.

## 🔧 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the correct directory and have installed dependencies
2. **GitHub API Rate Limits**: Check your GitHub token and rate limit status
3. **Missing Files**: Ensure previous steps completed successfully before running next step
4. **Permission Errors**: Check file permissions in output directories

### Debug Mode

Enable detailed logging by setting log level in config:
```yaml
logging:
  level: DEBUG
```

### Health Checks

Run system health checks:
```bash
python -c "
from winget_automation.monitoring import check_all_health
print(check_all_health())
"
```

## 📊 Monitoring and Metrics

The enhanced system provides comprehensive monitoring:

- **Structured Logging**: All operations are logged with correlation IDs
- **Progress Tracking**: Real-time progress indicators
- **Health Monitoring**: Automated system health checks
- **Performance Metrics**: Processing time and success rates

## 🎯 Next Steps

After running the workflow:

1. **Review FilteringSummary.md** - Understand what packages were filtered and why
2. **Check Individual Filter Files** - Analyze specific categories of removed packages
3. **Run Komac Commands** - Use the generated commands to update WinGet packages
4. **Monitor Results** - Track success rates and adjust filters if needed

## 📚 Additional Resources

- **Configuration Guide**: `docs/CONFIGURATION.md`
- **Architecture Overview**: `docs/development/MULTI_SOURCE_ARCHITECTURE.md`
- **Testing Guide**: `docs/development/TESTING.md`
- **Legacy Migration**: `docs/user-guide/LEGACY_MIGRATION.md`
