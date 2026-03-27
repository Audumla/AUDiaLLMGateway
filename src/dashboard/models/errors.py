"""Custom exception classes for dashboard."""


class DashboardException(Exception):
    """Base exception for dashboard errors."""
    pass


class ManifestLoadError(DashboardException):
    """Error loading or parsing manifests."""
    pass


class ComponentNotFoundError(DashboardException):
    """Component manifest not found."""
    pass


class ActionExecutionError(DashboardException):
    """Error executing action."""
    pass


class PrometheusClientError(DashboardException):
    """Error querying Prometheus."""
    pass


class ConnectionError(DashboardException):
    """Error connecting to component."""
    pass
