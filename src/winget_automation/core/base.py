"""Base classes and abstract interfaces for WinGet Manifest Generator Tool."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class BaseProcessor(ABC):
    """Base processor class providing common functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize base processor with configuration."""
        self.config = config or {}
        self._logger = None
    
    @property
    def logger(self):
        """Get logger instance."""
        if self._logger is None:
            from ..monitoring import get_logger
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """Process the given input."""
        pass
    
    def validate_config(self) -> bool:
        """Validate processor configuration."""
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default."""
        return self.config.get(key, default)
