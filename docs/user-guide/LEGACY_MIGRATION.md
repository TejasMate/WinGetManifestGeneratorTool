# Legacy Workflow Migration Guide

This guide helps existing users transition from the original scripts to the new professional structure while maintaining familiar workflows.

## Quick Reference

### Original Commands (✅ Now Working)
```bash
python src/winget_automation/PackageProcessor.py
python src/winget_automation/GitHub.py
python src/winget_automation/KomacCommandsGenerator.py
```

> **✅ Fixed**: Import errors resolved - all original scripts now work correctly with direct execution.

### New Legacy Workflow Runner (Recommended)
```bash
python examples/legacy_workflow.py run        # Complete workflow
python examples/legacy_workflow.py package    # Just package processing
python examples/legacy_workflow.py github     # Just GitHub analysis
python examples/legacy_workflow.py commands   # Just command generation
```

### Modern Professional CLI (Best Experience)
```bash
wmat health              # Check system status
wmat process --dry-run   # Process with monitoring
wmat config-status       # View configuration
wmat metrics            # System metrics
```

## Migration Benefits

| Feature | Original Scripts | Legacy Runner | Modern CLI |
|---------|------------------|---------------|------------|
| Basic Functionality | ✅ | ✅ | ✅ |
| Health Checks | ❌ | ✅ | ✅ |
| Progress Tracking | ❌ | ✅ | ✅ |
| Structured Logging | ❌ | ✅ | ✅ |
| Error Recovery | ❌ | ✅ | ✅ |
| Professional UI | ❌ | ⚠️ | ✅ |
| Configuration Management | ❌ | ✅ | ✅ |
| Monitoring Integration | ❌ | ✅ | ✅ |

## Migration Paths

### Path 1: Immediate Benefits (No Learning Curve)
Use the legacy workflow runner to get monitoring and health checks with familiar commands:

```bash
# Replace this:
python src/winget_automation/PackageProcessor.py
python src/winget_automation/GitHub.py
python src/winget_automation/KomacCommandsGenerator.py

# With this:
python examples/legacy_workflow.py run
```

### Path 2: Gradual Migration (Recommended)
Start learning the modern CLI while keeping legacy as backup:

```bash
# Learn the new commands gradually
wmat health                        # Check if everything is working
wmat config-status                 # Understand your configuration
wmat process --dry-run             # Test processing without changes
wmat metrics                       # See system performance

# Fall back to legacy when needed
python examples/legacy_workflow.py run
```

### Path 3: Full Migration (Best Long-term)
Switch to the modern CLI for all operations:

```bash
# Daily workflow becomes:
wmat health && wmat process --filter github
```

## Troubleshooting

### If Original Scripts Fail
```bash
# Check system status
wmat health

# Use legacy runner with monitoring
python examples/legacy_workflow.py run
```

### If Legacy Runner Fails
```bash
# Fall back to original scripts
python src/winget_automation/PackageProcessor.py
python src/winget_automation/GitHub.py
python src/winget_automation/KomacCommandsGenerator.py
```

### If Modern CLI Fails
```bash
# Reinstall package
pip install -e .

# Check installation
wmat --help
```

## Key Improvements in New Structure

1. **Health Monitoring**: Every operation now includes health checks
2. **Progress Tracking**: See real-time progress for long operations
3. **Error Handling**: Better error messages and recovery suggestions
4. **Configuration Management**: Centralized, validated configuration
5. **Structured Logging**: Detailed logs for debugging and auditing
6. **Professional Interface**: Rich terminal UI with colors and formatting

## Configuration Notes

The new structure uses `config/config.yaml` for settings. Your existing workflow will work with minimal configuration:

```yaml
# Minimal config for legacy workflow compatibility
github:
  token: "your_github_token"
  
processing:
  max_packages: 1000
  
monitoring:
  enabled: true
  log_level: "INFO"
```

## Support

- Original scripts will continue to work indefinitely
- Legacy workflow runner bridges old and new approaches
- Modern CLI provides the best experience for new workflows
- All three approaches can coexist and be used interchangeably

Choose the approach that best fits your current needs and comfort level!
