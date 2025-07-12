# Examples

This directory contains example scripts and configurations demonstrating how to use the WinGet Manifest Generator Tool.

## Available Examples

### Basic Usage
- `integration_demo.py` - Complete integration example showing all features
- `legacy_workflow.py` - Backward-compatible three-step workflow runner
- `simple_package_update.py` - Basic package update workflow
- `batch_processing.py` - Processing multiple packages

### Configuration Examples
- `config_examples/` - Sample configuration files for different environments
- `monitoring_setup.py` - Setting up monitoring and observability
- `github_integration.py` - GitHub API integration examples

### Advanced Use Cases
- `custom_filters.py` - Creating custom package filters
- `plugin_example.py` - Custom plugin development
- `automation_workflow.py` - Automated CI/CD integration

## Usage

Run examples from the project root directory:

```bash
# Run the complete integration demo
python examples/integration_demo.py

# Test monitoring setup
python examples/monitoring_setup.py

# Legacy workflow for existing users
python examples/legacy_workflow.py run        # Complete workflow
python examples/legacy_workflow.py package    # Just package processing
python examples/legacy_workflow.py github     # Just GitHub analysis
python examples/legacy_workflow.py commands   # Just command generation
```

### Legacy Workflow Migration

The `legacy_workflow.py` script provides backward compatibility for users familiar with the original command sequence:

```bash
# Original commands (still work):
python src/winget_automation/PackageProcessor.py
python src/winget_automation/GitHub.py
python src/winget_automation/KomacCommandsGenerator.py

# New workflow runner (recommended for existing users):
python examples/legacy_workflow.py run
```

This bridge script adds:
- Health checks before execution
- Progress tracking and monitoring
- Better error handling
- Structured logging
- While maintaining familiar workflow patterns

## Prerequisites

Make sure you have:
1. Installed the package: `pip install -e .`
2. Configured the tool: See `docs/user-guide/CONFIGURATION.md`
3. Set up required tokens and credentials

## Contributing Examples

When adding new examples:
1. Include clear documentation and comments
2. Add a README section describing the example
3. Test with the current version of the tool
4. Follow the existing code style
