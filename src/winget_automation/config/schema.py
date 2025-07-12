"""Configuration validation schemas for WinGetManifestAutomationTool."""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import re


@dataclass
class ValidationRule:
    """Base class for validation rules."""
    
    required: bool = True
    description: str = ""
    
    def validate(self, value: Any) -> bool:
        """Validate a value according to this rule."""
        # Allow None values when not required
        if value is None and not self.required:
            return True
        raise NotImplementedError


@dataclass
class StringValidation(ValidationRule):
    """String validation rule."""
    
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    
    def validate(self, value: Any) -> bool:
        """Validate string value."""
        # Allow None values when not required
        if value is None and not self.required:
            return True
            
        if not isinstance(value, str):
            return False
            
        if self.min_length is not None and len(value) < self.min_length:
            return False
            
        if self.max_length is not None and len(value) > self.max_length:
            return False
            
        if self.pattern is not None and not re.match(self.pattern, value):
            return False
            
        if self.allowed_values is not None and value not in self.allowed_values:
            return False
            
        return True


@dataclass
class IntegerValidation(ValidationRule):
    """Integer validation rule."""
    
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    
    def validate(self, value: Any) -> bool:
        """Validate integer value."""
        # Allow None values when not required
        if value is None and not self.required:
            return True
            
        if not isinstance(value, int):
            return False
            
        if self.min_value is not None and value < self.min_value:
            return False
            
        if self.max_value is not None and value > self.max_value:
            return False
            
        return True


@dataclass
class FloatValidation(ValidationRule):
    """Float validation rule."""
    
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def validate(self, value: Any) -> bool:
        """Validate float value."""
        # Allow None values when not required
        if value is None and not self.required:
            return True
            
        if not isinstance(value, (int, float)):
            return False
            
        if self.min_value is not None and value < self.min_value:
            return False
            
        if self.max_value is not None and value > self.max_value:
            return False
            
        return True


@dataclass
class BooleanValidation(ValidationRule):
    """Boolean validation rule."""
    
    def validate(self, value: Any) -> bool:
        """Validate boolean value."""
        # Allow None values when not required
        if value is None and not self.required:
            return True
            
        return isinstance(value, bool)


@dataclass
class ListValidation(ValidationRule):
    """List validation rule."""
    
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    item_validation: Optional[ValidationRule] = None
    
    def validate(self, value: Any) -> bool:
        """Validate list value."""
        # Allow None values when not required
        if value is None and not self.required:
            return True
            
        if not isinstance(value, list):
            return False
            
        if self.min_items is not None and len(value) < self.min_items:
            return False
            
        if self.max_items is not None and len(value) > self.max_items:
            return False
            
        if self.item_validation is not None:
            for item in value:
                if not self.item_validation.validate(item):
                    return False
                    
        return True


@dataclass
class DictValidation(ValidationRule):
    """Dictionary validation rule."""
    
    schema: Dict[str, ValidationRule] = field(default_factory=dict)
    allow_extra_keys: bool = True
    
    def validate(self, value: Any) -> bool:
        """Validate dictionary value."""
        # Allow None values when not required
        if value is None and not self.required:
            return True
            
        if not isinstance(value, dict):
            return False
            
        # Check required fields
        for key, rule in self.schema.items():
            if rule.required and key not in value:
                return False
                
        # Validate existing fields
        for key, val in value.items():
            if key in self.schema:
                if not self.schema[key].validate(val):
                    return False
            elif not self.allow_extra_keys:
                return False
                
        return True


class ConfigSchema:
    """Configuration schema definition."""
    
    def __init__(self):
        """Initialize the configuration schema."""
        self.schema = self._build_schema()
    
    def _build_schema(self) -> DictValidation:
        """Build the complete configuration schema."""
        return DictValidation(
            schema={
                "environment": StringValidation(
                    required=True,
                    allowed_values=["development", "staging", "production"],
                    description="Environment type (development/staging/production)"
                ),
                "debug": BooleanValidation(
                    required=False,
                    description="Enable debug mode"
                ),
                "logging": DictValidation(
                    required=True,
                    schema={
                        "level": StringValidation(
                            required=True,
                            allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            description="Logging level"
                        ),
                        "format": StringValidation(
                            required=False,
                            description="Log message format"
                        ),
                        "file": StringValidation(
                            required=False,
                            description="Log file path"
                        ),
                        "max_size": IntegerValidation(
                            required=False,
                            min_value=1,
                            description="Maximum log file size in MB"
                        ),
                        "backup_count": IntegerValidation(
                            required=False,
                            min_value=0,
                            description="Number of backup log files to keep"
                        )
                    },
                    description="Logging configuration"
                ),
                "github": DictValidation(
                    required=True,
                    schema={
                        "tokens": ListValidation(
                            required=False,
                            min_items=0,
                            item_validation=StringValidation(min_length=1),
                            description="List of GitHub API tokens"
                        ),
                        "api_url": StringValidation(
                            required=False,
                            pattern=r"^https?://.*",
                            description="GitHub API URL"
                        ),
                        "per_page": IntegerValidation(
                            required=False,
                            min_value=1,
                            max_value=100,
                            description="Items per page for API requests"
                        ),
                        "retry_attempts": IntegerValidation(
                            required=False,
                            min_value=0,
                            max_value=10,
                            description="Number of retry attempts for failed requests"
                        ),
                        "retry_delay": FloatValidation(
                            required=False,
                            min_value=0.1,
                            max_value=60.0,
                            description="Delay between retry attempts in seconds"
                        ),
                        "rate_limit_buffer": IntegerValidation(
                            required=False,
                            min_value=0,
                            max_value=1000,
                            description="Buffer for rate limit (requests to keep in reserve)"
                        )
                    },
                    description="GitHub API configuration"
                ),
                "package_processing": DictValidation(
                    required=True,
                    schema={
                        "winget_repo_path": StringValidation(
                            required=True,
                            description="Path to the WinGet packages repository"
                        ),
                        "output_directory": StringValidation(
                            required=True,
                            description="Directory for output files"
                        ),
                        "file_patterns": ListValidation(
                            required=False,
                            item_validation=StringValidation(),
                            description="File patterns to process"
                        ),
                        "max_workers": IntegerValidation(
                            required=False,
                            min_value=1,
                            max_value=32,
                            description="Maximum number of worker threads"
                        ),
                        "batch_size": IntegerValidation(
                            required=False,
                            min_value=1,
                            max_value=10000,
                            description="Batch size for processing"
                        ),
                        "timeout": IntegerValidation(
                            required=False,
                            min_value=1,
                            max_value=3600,
                            description="Processing timeout in seconds"
                        )
                    },
                    description="Package processing configuration"
                ),
                "filtering": DictValidation(
                    required=False,
                    schema={
                        "blocked_packages": ListValidation(
                            required=False,
                            item_validation=StringValidation(),
                            description="List of packages to exclude from processing"
                        ),
                        "allowed_architectures": ListValidation(
                            required=False,
                            item_validation=StringValidation(),
                            description="List of allowed architectures"
                        ),
                        "allowed_extensions": ListValidation(
                            required=False,
                            item_validation=StringValidation(),
                            description="List of allowed file extensions"
                        ),
                        "min_download_count": IntegerValidation(
                            required=False,
                            min_value=0,
                            description="Minimum download count for packages"
                        ),
                        "max_package_age_days": IntegerValidation(
                            required=False,
                            min_value=0,
                            description="Maximum package age in days"
                        )
                    },
                    description="Package filtering configuration"
                ),
                "output": DictValidation(
                    required=False,
                    schema={
                        "formats": ListValidation(
                            required=False,
                            item_validation=StringValidation(allowed_values=["csv", "json", "xml", "parquet"]),
                            description="Output formats to generate"
                        ),
                        "compression": StringValidation(
                            required=False,
                            allowed_values=["none", "gzip", "bz2", "xz"],
                            description="Output compression format"
                        ),
                        "include_metadata": BooleanValidation(
                            required=False,
                            description="Include metadata in output files"
                        ),
                        "timestamp_format": StringValidation(
                            required=False,
                            description="Timestamp format for output files"
                        )
                    },
                    description="Output configuration"
                ),
                "performance": DictValidation(
                    required=True,
                    schema={
                        "cache_enabled": BooleanValidation(
                            required=False,
                            description="Enable caching"
                        ),
                        "cache_ttl": IntegerValidation(
                            required=False,
                            min_value=60,
                            max_value=86400,
                            description="Cache TTL in seconds"
                        ),
                        "memory_limit_mb": IntegerValidation(
                            required=False,
                            min_value=128,
                            max_value=32768,
                            description="Memory limit in MB"
                        ),
                        "enable_profiling": BooleanValidation(
                            required=False,
                            description="Enable performance profiling"
                        )
                    },
                    description="Performance configuration"
                ),
                "monitoring": DictValidation(
                    required=False,
                    schema={
                        "metrics_enabled": BooleanValidation(
                            required=False,
                            description="Enable metrics collection"
                        ),
                        "max_timer_history": IntegerValidation(
                            required=False,
                            min_value=100,
                            max_value=10000,
                            description="Maximum timer history entries"
                        ),
                        "max_metric_history": IntegerValidation(
                            required=False,
                            min_value=1000,
                            max_value=100000,
                            description="Maximum metric history entries"
                        ),
                        "health_check_interval": IntegerValidation(
                            required=False,
                            min_value=30,
                            max_value=3600,
                            description="Health check interval in seconds"
                        ),
                        "export_metrics_interval": IntegerValidation(
                            required=False,
                            min_value=60,
                            max_value=86400,
                            description="Metrics export interval in seconds"
                        ),
                        "progress": DictValidation(
                            required=False,
                            schema={
                                "console_output": BooleanValidation(
                                    required=False,
                                    description="Enable console progress output"
                                ),
                                "log_updates": BooleanValidation(
                                    required=False,
                                    description="Enable progress log updates"
                                ),
                                "update_interval": FloatValidation(
                                    required=False,
                                    min_value=0.1,
                                    max_value=10.0,
                                    description="Progress update interval in seconds"
                                )
                            },
                            description="Progress tracking configuration"
                        )
                    },
                    description="Monitoring and observability configuration"
                ),
                "service": DictValidation(
                    required=False,
                    schema={
                        "name": StringValidation(
                            required=False,
                            description="Service name for logging"
                        ),
                        "version": StringValidation(
                            required=False,
                            description="Service version for logging"
                        )
                    },
                    description="Service information"
                )
            },
            allow_extra_keys=False,
            description="Main configuration schema"
        )
    
    def validate(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate configuration against schema.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            if not self.schema.validate(config):
                errors.append("Configuration validation failed")
                # Add detailed error checking
                errors.extend(self._get_detailed_errors(config, self.schema.schema, ""))
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _get_detailed_errors(self, config: Dict[str, Any], schema: Dict[str, ValidationRule], path: str) -> List[str]:
        """Get detailed validation errors.
        
        Args:
            config: Configuration to validate
            schema: Schema rules
            path: Current path in the configuration
            
        Returns:
            List of detailed error messages
        """
        errors = []
        
        # Check required fields
        for key, rule in schema.items():
            current_path = f"{path}.{key}" if path else key
            
            if rule.required and key not in config:
                errors.append(f"Required field '{current_path}' is missing")
                continue
            
            if key in config:
                value = config[key]
                if not rule.validate(value):
                    errors.append(f"Invalid value for '{current_path}': {value}")
                    
                    # Add specific error details for dict validation
                    if isinstance(rule, DictValidation) and isinstance(value, dict):
                        errors.extend(self._get_detailed_errors(value, rule.schema, current_path))
        
        return errors
