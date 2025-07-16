"""
Package Source Registry and Factory.

This module provides a registry and factory for managing different package sources,
enabling dynamic source creation and management.
"""

from typing import Dict, List, Type, Optional, Any
from .base import BasePackageSource, SourceType, PackageMetadata
import logging

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Registry for package source implementations."""
    
    def __init__(self):
        self._sources: Dict[SourceType, Type[BasePackageSource]] = {}
        self._instances: Dict[SourceType, BasePackageSource] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def register_source(self, source_type: SourceType, source_class: Type[BasePackageSource]):
        """Register a source implementation."""
        self._sources[source_type] = source_class
        self.logger.info(f"Registered source: {source_type.value}")
    
    def unregister_source(self, source_type: SourceType):
        """Unregister a source implementation."""
        if source_type in self._sources:
            del self._sources[source_type]
            if source_type in self._instances:
                del self._instances[source_type]
            self.logger.info(f"Unregistered source: {source_type.value}")
    
    def get_source_class(self, source_type: SourceType) -> Optional[Type[BasePackageSource]]:
        """Get the source class for a given type."""
        return self._sources.get(source_type)
    
    def get_source_instance(self, source_type: SourceType, config: Dict[str, Any] = None) -> Optional[BasePackageSource]:
        """Get or create a source instance."""
        if source_type not in self._sources:
            self.logger.error(f"Source not registered: {source_type.value}")
            return None
        
        # Return cached instance if available and no new config provided
        if source_type in self._instances and config is None:
            return self._instances[source_type]
        
        # Create new instance
        try:
            source_class = self._sources[source_type]
            instance = source_class(config or {})
            
            # Validate configuration
            if not instance.validate_config():
                self.logger.error(f"Invalid configuration for source: {source_type.value}")
                return None
            
            self._instances[source_type] = instance
            self.logger.debug(f"Created source instance: {source_type.value}")
            return instance
            
        except Exception as e:
            self.logger.error(f"Failed to create source instance {source_type.value}: {e}")
            return None
    
    def get_available_sources(self) -> List[SourceType]:
        """Get list of available source types."""
        return list(self._sources.keys())
    
    def is_source_available(self, source_type: SourceType) -> bool:
        """Check if a source type is available."""
        return source_type in self._sources


class SourceFactory:
    """Factory for creating and managing package sources."""
    
    def __init__(self, registry: SourceRegistry):
        self.registry = registry
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def create_source(self, source_type: SourceType, config: Dict[str, Any] = None) -> Optional[BasePackageSource]:
        """Create a source instance."""
        return self.registry.get_source_instance(source_type, config)
    
    def create_all_sources(self, configs: Dict[SourceType, Dict[str, Any]] = None) -> Dict[SourceType, BasePackageSource]:
        """Create instances for all available sources."""
        sources = {}
        configs = configs or {}
        
        for source_type in self.registry.get_available_sources():
            config = configs.get(source_type, {})
            source = self.registry.get_source_instance(source_type, config)
            if source:
                sources[source_type] = source
            else:
                self.logger.warning(f"Failed to create source: {source_type.value}")
        
        return sources
    
    def detect_source_from_url(self, url: str) -> Optional[SourceType]:
        """Detect the appropriate source type from a URL."""
        for source_type in self.registry.get_available_sources():
            source = self.registry.get_source_instance(source_type)
            if source and source.is_supported_url(url):
                return source_type
        
        return None
    
    def process_url_with_appropriate_source(self, url: str, configs: Dict[SourceType, Dict[str, Any]] = None) -> Optional[PackageMetadata]:
        """Process a URL with the appropriate source."""
        source_type = self.detect_source_from_url(url)
        if not source_type:
            self.logger.warning(f"No source found for URL: {url}")
            return None
        
        config = configs.get(source_type, {}) if configs else {}
        source = self.registry.get_source_instance(source_type, config)
        if not source:
            self.logger.error(f"Failed to create source {source_type.value} for URL: {url}")
            return None
        
        return source.extract_package_info(url)


# Global registry instance
_global_registry = SourceRegistry()


def get_registry() -> SourceRegistry:
    """Get the global source registry."""
    return _global_registry


def get_factory() -> SourceFactory:
    """Get a factory using the global registry."""
    return SourceFactory(_global_registry)


def register_source(source_type: SourceType, source_class: Type[BasePackageSource]):
    """Register a source with the global registry."""
    _global_registry.register_source(source_type, source_class)


def create_source(source_type: SourceType, config: Dict[str, Any] = None) -> Optional[BasePackageSource]:
    """Create a source using the global factory."""
    factory = get_factory()
    return factory.create_source(source_type, config)


def auto_detect_and_process(url: str, configs: Dict[SourceType, Dict[str, Any]] = None) -> Optional[PackageMetadata]:
    """Auto-detect source and process URL."""
    factory = get_factory()
    return factory.process_url_with_appropriate_source(url, configs)
