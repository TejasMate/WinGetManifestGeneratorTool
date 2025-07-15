# Multi-Source Package Architecture Migration Guide

This document outlines the refactoring of the WinGet Manifest Automation Tool to support multiple package sources beyond GitHub.

## 🎯 Objectives

1. **Extensibility**: Easy addition of new package sources (GitLab, SourceForge, Bitbucket, etc.)
2. **Consistency**: Unified interface across all package sources
3. **Maintainability**: Clean separation of concerns and modular design
4. **Backward Compatibility**: Existing GitHub functionality remains unchanged
5. **Future-Proofing**: Architecture ready for additional sources

## 🏗️ New Architecture Overview

### Core Components

```
src/
├── core/
│   ├── package_sources.py     # Abstract interfaces and base classes
│   └── multi_source_processor.py  # Main processor using new architecture
├── sources/
│   ├── __init__.py           # Package sources module
│   ├── github_source.py      # GitHub implementation
│   ├── gitlab_source.py      # GitLab implementation (placeholder)
│   └── sourceforge_source.py # SourceForge implementation (placeholder)
└── [existing structure remains]
```

### Key Design Patterns

1. **Strategy Pattern**: Different package sources implement the same interface
2. **Factory Pattern**: Dynamic creation of appropriate source handlers
3. **Registry Pattern**: Central registration and discovery of sources
4. **Adapter Pattern**: Unified data structures across different APIs

## 📋 Implementation Details

### 1. Core Interfaces (`src/core/package_sources.py`)

```python
class IPackageSource(Protocol):
    """Interface that all package sources must implement."""
    
    def can_handle_url(self, url: str) -> bool:
        """Check if this source can handle the given URL."""
        
    def extract_repository_info(self, url: str) -> Optional[RepositoryInfo]:
        """Extract repository information from URL."""
        
    def get_latest_release(self, repo_info: RepositoryInfo) -> Optional[ReleaseInfo]:
        """Get the latest release information."""
        
    def get_package_metadata(self, url: str) -> Optional[PackageMetadata]:
        """Get comprehensive package metadata."""
```

### 2. Standardized Data Structures

```python
@dataclass
class ReleaseInfo:
    """Standard release information across all package sources."""
    version: str
    tag_name: str
    download_urls: List[str]
    release_date: Optional[str] = None
    # ... other fields

@dataclass
class RepositoryInfo:
    """Standard repository information across all package sources."""
    source_type: PackageSourceType
    username: str
    repository_name: str
    base_url: str
    # ... other fields

@dataclass
class PackageMetadata:
    """Comprehensive package metadata from any source."""
    identifier: str
    name: str
    repository_info: RepositoryInfo
    latest_release: Optional[ReleaseInfo] = None
    # ... other fields
```

### 3. Source Implementations

#### GitHub Source (`src/sources/github_source.py`)
- ✅ **Implemented**: Full GitHub API integration
- Uses existing `GitHubAPI` and `TokenManager`
- Handles GitHub-specific URL patterns and data formats
- Supports rate limiting and token rotation

#### GitLab Source (`src/sources/gitlab_source.py`)
- 🚧 **Placeholder**: Ready for implementation
- Supports GitLab.com and custom GitLab instances
- Handles nested group structures
- Ready for GitLab API integration

#### SourceForge Source (`src/sources/sourceforge_source.py`)
- 🚧 **Placeholder**: Ready for implementation
- Handles SourceForge project URLs
- Ready for SourceForge REST API integration
- Supports file listing and download URLs

## 🔄 Migration Strategy

### Phase 1: Foundation (✅ Complete)
- [x] Create core interfaces and base classes
- [x] Implement GitHub source using existing code
- [x] Create package source registry and factory
- [x] Build multi-source processor framework

### Phase 2: Integration (🚧 Current)
- [ ] Update existing GitHub.py to use new architecture
- [ ] Migrate PackageProcessor.py to multi-source processor
- [ ] Add configuration support for multiple sources
- [ ] Update tests to cover new architecture

### Phase 3: Extension (🔮 Future)
- [ ] Implement GitLab API integration
- [ ] Implement SourceForge API integration
- [ ] Add Bitbucket support
- [ ] Add custom source support

## 🔧 Usage Examples

### Basic Usage
```python
from src.sources import get_package_metadata_for_url

# Works with any supported source
metadata = get_package_metadata_for_url("https://github.com/microsoft/PowerToys")
metadata = get_package_metadata_for_url("https://gitlab.com/inkscape/inkscape")
metadata = get_package_metadata_for_url("https://sourceforge.net/projects/7zip/")
```

### Advanced Usage
```python
from src.sources import PackageSourceManager
from src.core.multi_source_processor import MultiSourcePackageProcessor

# Initialize manager with configuration
manager = PackageSourceManager(config)

# Process multiple URLs
processor = MultiSourcePackageProcessor()
results = processor.process_package_urls([
    "https://github.com/user/repo1",
    "https://gitlab.com/user/repo2",
    "https://sourceforge.net/projects/project3/"
])
```

### Source-Specific Operations
```python
from src.sources import get_package_source_manager
from src.core.package_sources import PackageSourceType

manager = get_package_source_manager()

# Get GitHub-specific functionality
github_source = manager.get_source_by_type(PackageSourceType.GITHUB)
filtered_urls = github_source.get_architecture_specific_urls(repo_info, "x64")
```

## 📊 Benefits of New Architecture

### 1. **Extensibility**
- Adding new sources requires only implementing the `IPackageSource` interface
- No changes needed to existing code
- Registry automatically discovers new sources

### 2. **Consistency**
- All sources return standardized `PackageMetadata`
- Unified error handling and logging
- Consistent configuration patterns

### 3. **Maintainability**
- Clear separation between source-specific and general logic
- Single responsibility principle for each source
- Easy testing of individual components

### 4. **Performance**
- Parallel processing across different sources
- Source-specific optimizations
- Efficient URL routing to appropriate handlers

### 5. **Configuration**
- Source-specific configuration sections
- Runtime source enabling/disabling
- Credential management per source

## 🧪 Testing Strategy

### Unit Tests
```python
def test_github_source():
    source = GitHubPackageSource()
    assert source.can_handle_url("https://github.com/user/repo")
    
def test_package_metadata_standardization():
    # Test that all sources return consistent metadata format
    pass
```

### Integration Tests
```python
def test_multi_source_processing():
    processor = MultiSourcePackageProcessor()
    urls = ["github.com/user/repo", "gitlab.com/user/repo"]
    results = processor.process_package_urls(urls)
    assert len(results) == 2
```

## 🚀 Future Enhancements

### Additional Sources
- **Bitbucket**: Git hosting with API support
- **Azure DevOps**: Microsoft's Git hosting
- **Custom Git**: Generic Git repository support
- **Package Managers**: NPM, PyPI, NuGet integration

### Advanced Features
- **Source Priorities**: Prefer certain sources over others
- **Fallback Mechanisms**: Try multiple sources for the same package
- **Caching**: Cache metadata across sources
- **Analytics**: Track source usage and performance

### Configuration Enhancements
```yaml
package_sources:
  github:
    enabled: true
    tokens: ["token1", "token2"]
    rate_limit_buffer: 100
  gitlab:
    enabled: true
    instances: ["gitlab.com", "custom.gitlab.com"]
    tokens: {"gitlab.com": "token"}
  sourceforge:
    enabled: false
  priorities: ["github", "gitlab", "sourceforge"]
```

## 📝 Migration Checklist

### For Developers
- [ ] Review new interfaces in `src/core/package_sources.py`
- [ ] Understand the factory and registry patterns
- [ ] Update existing code to use `PackageSourceManager`
- [ ] Add tests for new functionality

### For New Source Implementation
- [ ] Inherit from `BasePackageSource`
- [ ] Implement all required interface methods
- [ ] Register with `PackageSourceFactory`
- [ ] Add configuration support
- [ ] Write comprehensive tests

### For Configuration
- [ ] Add source-specific configuration sections
- [ ] Update `.env.example` with new source tokens
- [ ] Document configuration options
- [ ] Test with different source combinations

## 🔗 Related Documentation
- [Configuration Guide](../user-guide/CONFIGURATION.md)
- [Development Guide](../development/)
- [API Documentation](../api/)
- [Testing Guide](../development/TESTING.md)

---

This architecture provides a solid foundation for expanding beyond GitHub while maintaining code quality and consistency. The modular design ensures that each source can be developed and maintained independently while providing a unified experience for users.
