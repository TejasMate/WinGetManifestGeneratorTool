# Migration Guide: Multi-Source Architecture

## Overview
The WinGet Manifest Generator Tool has been restructured to support multiple package sources (GitHub, GitLab, SourceForge, etc.) through a unified architecture.

## Key Changes

### 1. New Entry Point
- **Old**: `python src/GitHub.py`
- **New**: `python src/main.py`

### 2. Source-Based Architecture
- Packages are now processed through source-specific implementations
- Each source (GitHub, GitLab, SourceForge) has its own module
- Unified interface for all sources

### 3. Configuration
- New YAML-based configuration system
- Source-specific settings
- See `config/config.multi-source.example.yaml`

### 4. Directory Structure
```
src/
├── main.py              # New entry point
├── core/                # Core processing logic
│   └── processor.py     # Unified processor
├── sources/             # Source implementations
│   ├── github/          # GitHub source
│   ├── gitlab/          # GitLab source
│   └── sourceforge/     # SourceForge source
└── utils/               # Utilities
```

## Migration Steps

1. **Update scripts**: Replace `GitHub.py` calls with `main.py`
2. **Update imports**: Use new module paths
3. **Configure sources**: Set up `config/config.yaml`
4. **Test functionality**: Verify processing works with new structure

## Backward Compatibility

Legacy files are marked as `.deprecated` and can be removed after migration testing.

## Benefits

- **Scalability**: Easy to add new sources
- **Maintainability**: Clear separation of concerns
- **Flexibility**: Process multiple sources simultaneously
- **Extensibility**: Plugin-like architecture for sources
