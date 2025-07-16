"""
Base filter implementation for package sources.

This module provides common filtering functionality that can be used
across different package sources.
"""

from typing import List, Set, Dict, Any
from ..base import PackageMetadata, BasePackageSource
import logging

logger = logging.getLogger(__name__)


class BasePackageFilter:
    """Base package filter with common filtering logic."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def filter_packages(self, packages: List[PackageMetadata]) -> List[PackageMetadata]:
        """Filter packages based on configured criteria."""
        filtered = []
        
        for package in packages:
            if self.should_include_package(package):
                filtered.append(package)
            else:
                self.logger.debug(f"Filtered out package: {package.identifier}")
        
        return filtered
    
    def should_include_package(self, package: PackageMetadata) -> bool:
        """Determine if a package should be included based on criteria."""
        # Basic validation
        if not package.identifier or not package.name:
            return False
        
        # Check minimum requirements
        if not self._has_valid_release(package):
            return False
        
        # Check against exclusion criteria
        if self._is_excluded(package):
            return False
        
        # Check against inclusion criteria
        if not self._meets_inclusion_criteria(package):
            return False
        
        return True
    
    def _has_valid_release(self, package: PackageMetadata) -> bool:
        """Check if package has a valid release."""
        if not package.latest_release:
            return False
        
        release = package.latest_release
        
        # Must have download URLs
        if not release.download_urls:
            return False
        
        # Skip draft releases unless configured otherwise
        if release.is_draft and not self.config.get('include_drafts', False):
            return False
        
        # Skip prereleases unless configured otherwise
        if release.is_prerelease and not self.config.get('include_prereleases', False):
            return False
        
        return True
    
    def _is_excluded(self, package: PackageMetadata) -> bool:
        """Check if package matches exclusion criteria."""
        exclusion_patterns = self.config.get('exclude_patterns', [])
        
        for pattern in exclusion_patterns:
            if pattern.lower() in package.name.lower():
                return True
            if pattern.lower() in package.identifier.lower():
                return True
        
        # Exclude packages without installer URLs
        if self.config.get('require_installer_urls', True):
            if package.installer_urls_count == 0:
                return True
        
        return False
    
    def _meets_inclusion_criteria(self, package: PackageMetadata) -> bool:
        """Check if package meets inclusion criteria."""
        inclusion_patterns = self.config.get('include_patterns', [])
        
        # If no inclusion patterns specified, include by default
        if not inclusion_patterns:
            return True
        
        for pattern in inclusion_patterns:
            if pattern.lower() in package.name.lower():
                return True
            if pattern.lower() in package.identifier.lower():
                return True
        
        return False
    
    def filter_by_source(self, packages: List[PackageMetadata], source_types: Set[str]) -> List[PackageMetadata]:
        """Filter packages by source type."""
        if not source_types:
            return packages
        
        return [pkg for pkg in packages if pkg.source_type.value in source_types]
    
    def filter_by_language(self, packages: List[PackageMetadata], languages: Set[str]) -> List[PackageMetadata]:
        """Filter packages by programming language."""
        if not languages:
            return packages
        
        filtered = []
        for package in packages:
            if package.repository and package.repository.language:
                if package.repository.language.lower() in {lang.lower() for lang in languages}:
                    filtered.append(package)
        
        return filtered
    
    def filter_by_stars(self, packages: List[PackageMetadata], min_stars: int = 0) -> List[PackageMetadata]:
        """Filter packages by minimum star count."""
        if min_stars <= 0:
            return packages
        
        return [pkg for pkg in packages 
                if pkg.repository and pkg.repository.stars >= min_stars]
    
    def filter_by_recent_activity(self, packages: List[PackageMetadata], max_days: int = 365) -> List[PackageMetadata]:
        """Filter packages by recent release activity."""
        # This would require date parsing and comparison
        # For now, return all packages
        return packages
    
    def deduplicate_packages(self, packages: List[PackageMetadata]) -> List[PackageMetadata]:
        """Remove duplicate packages based on identifier."""
        seen_identifiers = set()
        unique_packages = []
        
        for package in packages:
            if package.identifier not in seen_identifiers:
                seen_identifiers.add(package.identifier)
                unique_packages.append(package)
            else:
                self.logger.debug(f"Duplicate package filtered: {package.identifier}")
        
        return unique_packages
