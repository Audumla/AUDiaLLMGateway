"""Centralized logging service for dashboard.

Provides centralized log management with:
- Log entry storage with timestamps and metadata
- Log filtering and retrieval
- Log level classification
- Component-specific logging
- Log cleanup and rotation

Designed for Server-Sent Events (SSE) streaming to frontend.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Callable, Deque
from collections import deque

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Log level classification."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Single log entry."""

    level: LogLevel
    message: str
    component_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "dashboard"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "message": self.message,
            "component_id": self.component_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metadata": self.metadata,
        }


class LoggingError(Exception):
    """Base exception for logging errors."""

    pass


class DashboardLogger:
    """Centralized logging service for dashboard.

    Features:
    - Circular buffer for log storage (configurable size)
    - Log filtering by level, component, source
    - Log retrieval with time-based filtering
    - Callback support for real-time log notifications
    - Thread-safe log storage
    """

    def __init__(self, max_entries: int = 1000):
        """Initialize logger service.

        Args:
            max_entries: Maximum number of log entries to store
        """
        self.max_entries = max_entries
        self.logs: Deque[LogEntry] = deque(maxlen=max_entries)
        self.callbacks: list[Callable[[LogEntry], None]] = []

    def log(
        self,
        level: LogLevel,
        message: str,
        component_id: Optional[str] = None,
        source: str = "dashboard",
        metadata: Optional[dict[str, Any]] = None,
    ) -> LogEntry:
        """Log a message.

        Args:
            level: Log level
            message: Log message
            component_id: Optional component identifier
            source: Log source identifier
            metadata: Optional metadata dict

        Returns:
            LogEntry that was created
        """
        entry = LogEntry(
            level=level,
            message=message,
            component_id=component_id,
            source=source,
            metadata=metadata or {},
        )

        self.logs.append(entry)
        logger.debug(f"Logged {level.value}: {message}")

        # Notify callbacks
        self._notify_callbacks(entry)

        return entry

    def debug(
        self,
        message: str,
        component_id: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Log at DEBUG level."""
        return self.log(LogLevel.DEBUG, message, component_id=component_id, **kwargs)

    def info(
        self,
        message: str,
        component_id: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Log at INFO level."""
        return self.log(LogLevel.INFO, message, component_id=component_id, **kwargs)

    def warning(
        self,
        message: str,
        component_id: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Log at WARNING level."""
        return self.log(LogLevel.WARNING, message, component_id=component_id, **kwargs)

    def error(
        self,
        message: str,
        component_id: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Log at ERROR level."""
        return self.log(LogLevel.ERROR, message, component_id=component_id, **kwargs)

    def critical(
        self,
        message: str,
        component_id: Optional[str] = None,
        **kwargs
    ) -> LogEntry:
        """Log at CRITICAL level."""
        return self.log(LogLevel.CRITICAL, message, component_id=component_id, **kwargs)

    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        component_id: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> list[LogEntry]:
        """Get logs with optional filtering.

        Args:
            level: Filter by log level
            component_id: Filter by component
            source: Filter by source
            limit: Maximum number of entries to return
            since: Only return entries after this timestamp

        Returns:
            List of LogEntry matching criteria
        """
        filtered = []

        for entry in reversed(list(self.logs)):  # Most recent first
            if level and entry.level != level:
                continue
            if component_id and entry.component_id != component_id:
                continue
            if source and entry.source != source:
                continue
            if since and entry.timestamp <= since:
                continue

            filtered.append(entry)

            if len(filtered) >= limit:
                break

        return list(reversed(filtered))  # Return in chronological order

    def get_component_logs(
        self,
        component_id: str,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Get logs for a specific component.

        Args:
            component_id: Component identifier
            limit: Maximum number of entries to return

        Returns:
            List of LogEntry for component
        """
        return self.get_logs(component_id=component_id, limit=limit)

    def get_recent_logs(
        self,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Get most recent logs.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of most recent LogEntry
        """
        return self.get_logs(limit=limit)

    def get_error_logs(
        self,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Get error and critical logs.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of error/critical LogEntry
        """
        error_logs = []

        for entry in reversed(list(self.logs)):
            if entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
                error_logs.append(entry)

            if len(error_logs) >= limit:
                break

        return list(reversed(error_logs))

    def add_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """Add callback for new log entries.

        Callback will be called with LogEntry whenever a new entry is logged.

        Args:
            callback: Callable that accepts LogEntry
        """
        self.callbacks.append(callback)
        callback_name = getattr(callback, "__name__", str(callback))
        logger.debug(f"Added log callback: {callback_name}")

    def remove_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """Remove log callback.

        Args:
            callback: Callback to remove
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            callback_name = getattr(callback, "__name__", str(callback))
            logger.debug(f"Removed log callback: {callback_name}")

    def clear_logs(self) -> int:
        """Clear all logs.

        Returns:
            Number of entries cleared
        """
        count = len(self.logs)
        self.logs.clear()
        logger.info(f"Cleared {count} log entries")
        return count

    def get_statistics(self) -> dict[str, Any]:
        """Get logging statistics.

        Returns:
            Dictionary with log statistics
        """
        total = len(self.logs)
        by_level = {}
        by_component = {}

        for entry in self.logs:
            by_level[entry.level.value] = by_level.get(entry.level.value, 0) + 1
            if entry.component_id:
                by_component[entry.component_id] = (
                    by_component.get(entry.component_id, 0) + 1
                )

        return {
            "total_entries": total,
            "capacity": self.max_entries,
            "by_level": by_level,
            "by_component": by_component,
            "callbacks": len(self.callbacks),
        }

    def _notify_callbacks(self, entry: LogEntry) -> None:
        """Notify all callbacks of new log entry.

        Args:
            entry: LogEntry that was created
        """
        for callback in self.callbacks:
            try:
                callback(entry)
            except Exception as e:
                logger.error(f"Error in log callback: {e}")


def create_dashboard_logger(max_entries: int = 1000) -> DashboardLogger:
    """Factory function to create dashboard logger.

    Args:
        max_entries: Maximum number of entries to store

    Returns:
        DashboardLogger instance
    """
    return DashboardLogger(max_entries=max_entries)
