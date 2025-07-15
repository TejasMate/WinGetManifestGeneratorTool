# Quick Start Guide - How to Run the Project

## 🚀 Multiple Ways to Run the WinGet Manifest Automation Tool

### 1. 🎯 **Recommended: Using get_started.py (New)**

#### Run Complete Workflow (All 3 Steps)
```bash
python get_started.py --all
```

#### Run Individual Steps
```bash
# Step 1: Package Processing
python get_started.py --step 1

# Step 2: GitHub Analysis (with enhanced filtering)
python get_started.py --step 2  

# Step 3: Komac Command Generation
python get_started.py --step 3
```

### 2. 🔧 **Using Makefile (Easiest)**

#### Complete Workflow
```bash
make run-all          # Run all 3 steps with progress tracking
make run-legacy       # Traditional sequential execution
```

#### Individual Steps  
```bash
make run-step1        # Package Processing
make run-step2        # GitHub Analysis
make run-step3        # Komac Generation
```

#### Direct Component Access
```bash
make run-processor    # Just PackageProcessor.py
make run-github       # Just GitHub.py
make run-komac        # Just KomacCommandsGenerator.py
```

#### Testing & Demo
```bash
make test-filter      # Test enhanced filtering
make demo-filter      # Filtering demonstration
make setup-env        # Setup .env file
make check-config     # Verify configuration
```

### 3. 📋 **Traditional Sequential Method (Original)**

Run each step manually in order:

```bash
# Step 1: Package Processing
cd src
python PackageProcessor.py

# Step 2: GitHub Analysis  
python GitHub.py

# Step 3: Komac Generation
python KomacCommandsGenerator.py
```

### 4. 🔄 **Using Legacy Workflow Script**

```bash
python examples/legacy_workflow.py
```

### 5. 🎮 **Interactive Component Testing**

#### Test Enhanced Filtering
```bash
cd src/github
python Filter.py
```

#### Test Specific Components
```bash
cd src
python -c "
from GitHub import main
main()
"
```

## 📊 What Each Step Does

### Step 1: PackageProcessor.py
- **Input**: WinGet package manifests
- **Process**: Extracts package metadata and information
- **Output**: `data/AllPackageInfo.csv`
- **Duration**: ~2-5 minutes

### Step 2: GitHub.py  
- **Input**: Package data from Step 1
- **Process**: 
  - Fetches GitHub release information
  - Applies 8 enhanced filters
  - Saves removed packages to individual CSV files
  - Generates comprehensive filtering report
- **Outputs**: 
  - `GitHubPackageInfo_Filter1.csv` through `GitHubPackageInfo_Filter8.csv`
  - `Filter1_Removed.csv` through `Filter8_Removed.csv`
  - `RemovedRows.csv` (all removed packages)
  - `FilteringSummary.md` (detailed report)
- **Duration**: ~5-15 minutes

### Step 3: KomacCommandsGenerator.py
- **Input**: Final filtered packages from Step 2
- **Process**: Generates komac update commands
- **Output**: `komac_update_commands_github.txt`
- **Duration**: ~1-2 minutes

## 🎯 Recommended Workflow

**For first-time users:**
```bash
# 1. Setup environment
make setup-env
# Edit .env with your GitHub token

# 2. Verify configuration  
make check-config

# 3. Run complete workflow
make run-all
```

**For regular use:**
```bash
# Quick complete run
python get_started.py --all

# Or step by step for debugging
python get_started.py --step 1
python get_started.py --step 2  
python get_started.py --step 3
```

## 📈 Enhanced Filtering Features

The new filtering system provides detailed insights:

- **Individual CSV files** for each filter's removed packages
- **Descriptive reasons** for why packages were filtered
- **Comprehensive summary report** with statistics
- **Granular analysis** capabilities

## 🔍 Monitoring & Analysis

After running, check these key files:

1. **`FilteringSummary.md`** - Overall filtering statistics
2. **`Filter1_Removed.csv` to `Filter8_Removed.csv`** - Packages removed by each filter
3. **`RemovedRows.csv`** - All removed packages with reasons
4. **`komac_update_commands_github.txt`** - Final update commands

## 🛠️ Troubleshooting

### Common Issues
- **Import errors**: Make sure you're in the project root directory
- **GitHub rate limits**: Check your token in `.env` file
- **Missing dependencies**: Run `pip install -r requirements.txt`

### Getting Help
```bash
python get_started.py --help
make help
```

This enhanced system provides much better visibility into the package processing pipeline while maintaining backward compatibility with the original workflow.
