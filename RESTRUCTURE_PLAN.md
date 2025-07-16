# Source Directory Restructure Plan

## Current Issues
1. GitHub-specific code (`GitHub.py`, `github/`) at top level mixes with multi-source architecture
2. Legacy files (`GitHub.py`, `KomacCommandsGenerator.py`, `PackageProcessor.py`) need integration into source-based system
3. Missing standardized interfaces for new sources (SourceForge, GitLab, etc.)

## Proposed Structure

```
src/
├── __init__.py
├── main.py                     # Main entry point (replaces GitHub.py)
├── exceptions.py               # Keep as-is
├── config/                     # Configuration management
│   ├── __init__.py
│   ├── settings.py
│   └── validation.py
├── core/                       # Core framework
│   ├── __init__.py
│   ├── interfaces.py           # Abstract base classes and protocols
│   ├── package_sources.py      # Base source implementation
│   ├── processor.py            # Main processor (evolved from PackageProcessor.py)
│   ├── manifest_generator.py   # Komac command generation
│   ├── pipeline.py             # Processing pipeline orchestration
│   └── constants.py
├── sources/                    # Source-specific implementations
│   ├── __init__.py
│   ├── base/                   # Base classes for sources
│   │   ├── __init__.py
│   │   ├── source_base.py
│   │   ├── url_matcher.py
│   │   └── filter_base.py
│   ├── github/                 # GitHub source
│   │   ├── __init__.py
│   │   ├── github_source.py    # Main GitHub implementation
│   │   ├── processors.py       # GitHub-specific processors
│   │   ├── filters.py          # GitHub filtering logic
│   │   ├── url_matcher.py      # GitHub URL matching
│   │   └── pr_searcher.py      # PR search functionality
│   ├── gitlab/                 # GitLab source
│   │   ├── __init__.py
│   │   ├── gitlab_source.py
│   │   ├── processors.py
│   │   ├── filters.py
│   │   └── url_matcher.py
│   ├── sourceforge/            # SourceForge source
│   │   ├── __init__.py
│   │   ├── sourceforge_source.py
│   │   ├── processors.py
│   │   ├── filters.py
│   │   └── url_matcher.py
│   └── registry.py             # Source registry and factory
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── token_manager.py        # Keep as-is
│   ├── unified_utils.py        # Keep as-is
│   ├── file_utils.py
│   └── validation.py
└── monitoring/                 # Monitoring and logging
    ├── __init__.py
    ├── metrics.py
    └── logging_setup.py
```

## Migration Steps

1. **Create new source structure** - Move GitHub code to sources/github/
2. **Create unified processor** - Evolve PackageProcessor.py to work with multiple sources
3. **Create main entry point** - Replace GitHub.py with main.py
4. **Implement source registry** - Factory pattern for source creation
5. **Add new sources** - Implement GitLab, SourceForge following the pattern
6. **Update configuration** - Extend config to support multiple sources
7. **Update tests** - Migrate and expand test coverage

## Benefits

1. **Scalability** - Easy to add new sources (Bitbucket, custom repos, etc.)
2. **Maintainability** - Clear separation of concerns
3. **Testability** - Each source can be tested independently
4. **Consistency** - All sources follow the same interface
5. **Flexibility** - Can process multiple sources simultaneously
6. **Legacy Support** - Gradual migration path from current code
