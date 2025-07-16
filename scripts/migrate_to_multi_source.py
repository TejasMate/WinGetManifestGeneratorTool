"""
Migration Script for WinGet Manifest Generator Tool Restructure.

This script helps migrate from the old structure to the new multi-source architecture.
"""

import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class MigrationHelper:
    """Helper class for migrating to the new structure."""
    
    def __init__(self, root_dir: Path = None):
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        self.src_dir = self.root_dir / "src"
        self.backup_dir = self.root_dir / "legacy_backup"
        
    def run_migration(self, create_backup: bool = True) -> bool:
        """Run the complete migration process."""
        try:
            logger.info("Starting migration to new multi-source structure")
            
            if create_backup:
                self._create_backup()
            
            # Step 1: Move legacy GitHub files
            self._migrate_github_files()
            
            # Step 2: Update imports in remaining files
            self._update_imports()
            
            # Step 3: Create example configuration
            self._create_example_config()
            
            # Step 4: Update documentation
            self._update_documentation()
            
            logger.info("Migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def _create_backup(self):
        """Create backup of existing files."""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        self.backup_dir.mkdir(parents=True)
        
        # Backup legacy files that will be moved/modified
        legacy_files = [
            "src/GitHub.py",
            "src/PackageProcessor.py", 
            "src/KomacCommandsGenerator.py",
            "src/github/",
        ]
        
        for file_path in legacy_files:
            full_path = self.root_dir / file_path
            if full_path.exists():
                backup_path = self.backup_dir / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                if full_path.is_file():
                    shutil.copy2(full_path, backup_path)
                else:
                    shutil.copytree(full_path, backup_path)
                
                logger.info(f"Backed up: {file_path}")
    
    def _migrate_github_files(self):
        """Migrate existing GitHub files to new structure."""
        # GitHub-specific files are already moved in the restructure
        # The new github_source.py integrates the functionality
        
        # Mark old files as deprecated
        deprecated_files = [
            self.src_dir / "GitHub.py",
            self.src_dir / "github" / "GitHubPackageProcessor.py",
            self.src_dir / "github" / "MatchSimilarURLs.py",
            self.src_dir / "github" / "Filter.py",
        ]
        
        for file_path in deprecated_files:
            if file_path.exists():
                deprecated_path = file_path.with_suffix(f"{file_path.suffix}.deprecated")
                if not deprecated_path.exists():
                    shutil.move(file_path, deprecated_path)
                    logger.info(f"Marked as deprecated: {file_path}")
    
    def _update_imports(self):
        """Update imports in files that reference the old structure."""
        # Files that might need import updates
        files_to_update = [
            self.root_dir / "examples" / "*.py",
            self.root_dir / "scripts" / "*.py",
            self.root_dir / "tests" / "**" / "*.py",
        ]
        
        # This would require more sophisticated parsing and replacement
        # For now, just log the files that need attention
        import_mappings = {
            "from src.GitHub": "from src.main",
            "from src.PackageProcessor": "from src.core.processor",
            "from src.github.GitHubPackageProcessor": "from src.sources.github",
            "import src.GitHub": "import src.main",
        }
        
        logger.info("Import updates needed for:")
        for pattern in files_to_update:
            for file_path in self.root_dir.glob(str(pattern).replace(str(self.root_dir) + "/", "")):
                if file_path.is_file() and file_path.suffix == ".py":
                    logger.info(f"  - {file_path}")
        
        logger.info("Import mapping guide:")
        for old_import, new_import in import_mappings.items():
            logger.info(f"  {old_import} -> {new_import}")
    
    def _create_example_config(self):
        """Create example configuration for multi-source setup."""
        config_content = """# Multi-Source Configuration Example
# Copy to config/config.yaml and customize

# Source-specific configurations
source_configs:
  github:
    github_tokens:
      - "ghp_your_token_here"
    filter:
      min_stars: 10
      exclude_templates: true
      exclude_archived: true
  
  gitlab:
    gitlab_token: "glpat_your_token_here"
    gitlab_instances:
      - "gitlab.com"
    filter:
      min_stars: 5
  
  sourceforge:
    filter:
      exclude_patterns:
        - "abandoned"
        - "deprecated"

# Processing configuration
processing:
  async_enabled: true
  max_concurrent: 10
  timeout: 30

# Output configuration
output:
  include_summary: true
  include_metadata: true
  format: "csv"

# Logging configuration
logging:
  level: "INFO"
  file_logging: true
  console_logging: true
  log_file: "logs/winget_tool.log"
"""
        
        config_file = self.root_dir / "config" / "config.multi-source.example.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Created example config: {config_file}")
    
    def _update_documentation(self):
        """Update documentation for the new structure."""
        migration_doc = """# Migration Guide: Multi-Source Architecture

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
"""
        
        migration_file = self.root_dir / "docs" / "MIGRATION_GUIDE.md"
        migration_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(migration_file, 'w') as f:
            f.write(migration_doc)
        
        logger.info(f"Created migration guide: {migration_file}")


def main():
    """Run migration when executed as script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate to multi-source architecture")
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup')
    parser.add_argument('--root-dir', help='Root directory (default: current)')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    root_dir = Path(args.root_dir) if args.root_dir else Path.cwd()
    migrator = MigrationHelper(root_dir)
    
    success = migrator.run_migration(create_backup=not args.no_backup)
    
    if success:
        print("\n✓ Migration completed successfully!")
        print("Next steps:")
        print("1. Review the migration guide: docs/MIGRATION_GUIDE.md")
        print("2. Set up configuration: config/config.yaml")
        print("3. Test the new structure: python src/main.py --status")
        return 0
    else:
        print("\n✗ Migration failed. Check logs for details.")
        return 1


if __name__ == "__main__":
    exit(main())
