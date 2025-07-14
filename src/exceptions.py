"""Custom exceptions for the WinGet Manifest Generator Tool."""

from typing import Optional, Any, Dict


class WinGetAutomationError(Exception):
    """Base exception for all WinGet automation tool errors."""

    def __init__(self, message: str, details: Optional[Any] = None):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error details or context
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message


class GitHubAPIError(WinGetAutomationError):
    """Exception raised when GitHub API operations fail."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        rate_limit_exceeded: bool = False,
    ):
        """Initialize GitHub API error.

        Args:
            message: Error message
            status_code: HTTP status code from the API
            response_text: Response body text
            rate_limit_exceeded: Whether the error is due to rate limiting
        """
        super().__init__(
            message,
            {
                "status_code": status_code,
                "response_text": response_text,
                "rate_limit_exceeded": rate_limit_exceeded,
            },
        )
        self.status_code = status_code
        self.response_text = response_text
        self.rate_limit_exceeded = rate_limit_exceeded


class TokenManagerError(WinGetAutomationError):
    """Exception raised when token management operations fail."""

    def __init__(self, message: str, available_tokens: int = 0):
        """Initialize token manager error.

        Args:
            message: Error message
            available_tokens: Number of available tokens
        """
        super().__init__(message, {"available_tokens": available_tokens})
        self.available_tokens = available_tokens


class PackageProcessingError(WinGetAutomationError):
    """Exception raised when package processing fails."""

    def __init__(
        self,
        message: str,
        package_id: Optional[str] = None,
        file_path: Optional[str] = None,
    ):
        """Initialize package processing error.

        Args:
            message: Error message
            package_id: Package identifier that caused the error
            file_path: File path related to the error
        """
        super().__init__(message, {"package_id": package_id, "file_path": file_path})
        self.package_id = package_id
        self.file_path = file_path


class ManifestParsingError(PackageProcessingError):
    """Exception raised when manifest file parsing fails."""

    def __init__(self, message: str, file_path: str, line_number: Optional[int] = None):
        """Initialize manifest parsing error.

        Args:
            message: Error message
            file_path: Path to the manifest file
            line_number: Line number where the error occurred
        """
        super().__init__(message, file_path=file_path)
        self.line_number = line_number
        if line_number:
            self.details["line_number"] = line_number


class VersionAnalysisError(WinGetAutomationError):
    """Exception raised when version analysis fails."""

    def __init__(
        self,
        message: str,
        package_id: Optional[str] = None,
        current_version: Optional[str] = None,
        latest_version: Optional[str] = None,
    ):
        """Initialize version analysis error.

        Args:
            message: Error message
            package_id: Package identifier
            current_version: Current version in WinGet
            latest_version: Latest version found
        """
        super().__init__(
            message,
            {
                "package_id": package_id,
                "current_version": current_version,
                "latest_version": latest_version,
            },
        )
        self.package_id = package_id
        self.current_version = current_version
        self.latest_version = latest_version


class ConfigurationError(WinGetAutomationError):
    """Exception raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
    ):
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_file: Configuration file path
        """
        super().__init__(
            message, {"config_key": config_key, "config_file": config_file}
        )
        self.config_key = config_key
        self.config_file = config_file


class DataValidationError(WinGetAutomationError):
    """Exception raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        expected_type: Optional[type] = None,
    ):
        """Initialize data validation error.

        Args:
            message: Error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            expected_type: Expected type for the field
        """
        super().__init__(
            message,
            {
                "field_name": field_name,
                "field_value": field_value,
                "expected_type": expected_type.__name__ if expected_type else None,
            },
        )
        self.field_name = field_name
        self.field_value = field_value
        self.expected_type = expected_type


class FileOperationError(WinGetAutomationError):
    """Exception raised when file operations fail."""

    def __init__(self, message: str, file_path: str, operation: str):
        """Initialize file operation error.

        Args:
            message: Error message
            file_path: Path to the file
            operation: Type of operation that failed (read, write, delete, etc.)
        """
        super().__init__(message, {"file_path": file_path, "operation": operation})
        self.file_path = file_path
        self.operation = operation


class NetworkError(WinGetAutomationError):
    """Exception raised when network operations fail."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
    ):
        """Initialize network error.

        Args:
            message: Error message
            url: URL that caused the error
            timeout: Timeout value used
            retry_count: Number of retries attempted
        """
        super().__init__(
            message, {"url": url, "timeout": timeout, "retry_count": retry_count}
        )
        self.url = url
        self.timeout = timeout
        self.retry_count = retry_count


class MonitoringError(WinGetAutomationError):
    """Base exception for monitoring and observability errors."""

    def __init__(self, message: str, component: str = None, details: Dict[str, Any] = None):
        super().__init__(message, details)
        self.component = component

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.component:
            return f"[{self.component}] {base_msg}"
        return base_msg


class MetricsCollectionError(MonitoringError):
    """Exception raised when metrics collection fails."""

    def __init__(self, message: str, metric_name: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "MetricsCollector", details)
        self.metric_name = metric_name


class HealthCheckError(MonitoringError):
    """Exception raised when health checks fail."""

    def __init__(self, message: str, check_name: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "HealthChecker", details)
        self.check_name = check_name


class ProgressTrackingError(MonitoringError):
    """Exception raised when progress tracking fails."""

    def __init__(self, message: str, tracker_name: str = None, step_name: str = None, 
                 details: Dict[str, Any] = None):
        super().__init__(message, "ProgressTracker", details)
        self.tracker_name = tracker_name
        self.step_name = step_name


class StructuredLoggingError(MonitoringError):
    """Exception raised when structured logging fails."""

    def __init__(self, message: str, logger_name: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "StructuredLogger", details)
        self.logger_name = logger_name
