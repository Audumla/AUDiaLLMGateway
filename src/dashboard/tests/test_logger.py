"""Tests for centralized logging service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from src.dashboard.services.logger import (
    DashboardLogger,
    LogEntry,
    LogLevel,
    LoggingError,
    create_dashboard_logger,
)


@pytest.fixture
def logger_service():
    """Create logger service for testing."""
    return DashboardLogger(max_entries=1000)


class TestDashboardLogger:
    """Test DashboardLogger class."""

    def test_initialization(self):
        """Test logger initialization."""
        logger = DashboardLogger(max_entries=500)

        assert logger.max_entries == 500
        assert len(logger.logs) == 0
        assert len(logger.callbacks) == 0

    def test_log_message(self, logger_service):
        """Test logging a message."""
        entry = logger_service.log(
            LogLevel.INFO,
            "Test message",
            component_id="test-comp",
        )

        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.component_id == "test-comp"
        assert entry.source == "dashboard"
        assert len(logger_service.logs) == 1

    def test_log_with_metadata(self, logger_service):
        """Test logging with metadata."""
        metadata = {"user": "test", "request_id": "123"}
        entry = logger_service.log(
            LogLevel.INFO,
            "Test message",
            metadata=metadata,
        )

        assert entry.metadata == metadata

    def test_log_debug(self, logger_service):
        """Test debug level logging."""
        entry = logger_service.debug("Debug message")

        assert entry.level == LogLevel.DEBUG
        assert entry.message == "Debug message"

    def test_log_info(self, logger_service):
        """Test info level logging."""
        entry = logger_service.info("Info message")

        assert entry.level == LogLevel.INFO
        assert entry.message == "Info message"

    def test_log_warning(self, logger_service):
        """Test warning level logging."""
        entry = logger_service.warning("Warning message")

        assert entry.level == LogLevel.WARNING
        assert entry.message == "Warning message"

    def test_log_error(self, logger_service):
        """Test error level logging."""
        entry = logger_service.error("Error message")

        assert entry.level == LogLevel.ERROR
        assert entry.message == "Error message"

    def test_log_critical(self, logger_service):
        """Test critical level logging."""
        entry = logger_service.critical("Critical message")

        assert entry.level == LogLevel.CRITICAL
        assert entry.message == "Critical message"

    def test_get_logs_all(self, logger_service):
        """Test retrieving all logs."""
        logger_service.info("Message 1")
        logger_service.warning("Message 2")
        logger_service.error("Message 3")

        logs = logger_service.get_logs(limit=100)

        assert len(logs) == 3
        assert logs[0].message == "Message 1"
        assert logs[2].message == "Message 3"

    def test_get_logs_filter_by_level(self, logger_service):
        """Test filtering logs by level."""
        logger_service.info("Info 1")
        logger_service.warning("Warning 1")
        logger_service.error("Error 1")
        logger_service.info("Info 2")

        logs = logger_service.get_logs(level=LogLevel.INFO)

        assert len(logs) == 2
        assert all(l.level == LogLevel.INFO for l in logs)

    def test_get_logs_filter_by_component(self, logger_service):
        """Test filtering logs by component."""
        logger_service.info("Message 1", component_id="comp1")
        logger_service.info("Message 2", component_id="comp2")
        logger_service.info("Message 3", component_id="comp1")

        logs = logger_service.get_logs(component_id="comp1")

        assert len(logs) == 2
        assert all(l.component_id == "comp1" for l in logs)

    def test_get_logs_filter_by_source(self, logger_service):
        """Test filtering logs by source."""
        logger_service.log(
            LogLevel.INFO,
            "Message 1",
            source="service-a",
        )
        logger_service.log(
            LogLevel.INFO,
            "Message 2",
            source="service-b",
        )

        logs = logger_service.get_logs(source="service-a")

        assert len(logs) == 1
        assert logs[0].source == "service-a"

    def test_get_logs_filter_by_time(self, logger_service):
        """Test filtering logs by timestamp."""
        logger_service.info("Message 1")
        since = datetime.now(timezone.utc)
        logger_service.info("Message 2")

        logs = logger_service.get_logs(since=since)

        assert len(logs) == 1
        assert logs[0].message == "Message 2"

    def test_get_logs_limit(self, logger_service):
        """Test log limit."""
        for i in range(10):
            logger_service.info(f"Message {i}")

        logs = logger_service.get_logs(limit=5)

        assert len(logs) == 5
        assert logs[0].message == "Message 5"
        assert logs[4].message == "Message 9"

    def test_get_component_logs(self, logger_service):
        """Test getting component-specific logs."""
        logger_service.info("Message 1", component_id="comp1")
        logger_service.info("Message 2", component_id="comp2")
        logger_service.info("Message 3", component_id="comp1")

        logs = logger_service.get_component_logs("comp1")

        assert len(logs) == 2
        assert all(l.component_id == "comp1" for l in logs)

    def test_get_recent_logs(self, logger_service):
        """Test getting recent logs."""
        for i in range(10):
            logger_service.info(f"Message {i}")

        logs = logger_service.get_recent_logs(limit=3)

        assert len(logs) == 3
        assert logs[0].message == "Message 7"
        assert logs[2].message == "Message 9"

    def test_get_error_logs(self, logger_service):
        """Test getting error and critical logs."""
        logger_service.info("Info message")
        logger_service.warning("Warning message")
        logger_service.error("Error message")
        logger_service.critical("Critical message")
        logger_service.info("Info message 2")

        logs = logger_service.get_error_logs()

        assert len(logs) == 2
        assert logs[0].level == LogLevel.ERROR
        assert logs[1].level == LogLevel.CRITICAL

    def test_add_callback(self, logger_service):
        """Test adding log callback."""
        callback = Mock()
        logger_service.add_callback(callback)

        logger_service.info("Test message")

        assert callback.called
        args, _ = callback.call_args
        assert isinstance(args[0], LogEntry)

    def test_multiple_callbacks(self, logger_service):
        """Test multiple callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        logger_service.add_callback(callback1)
        logger_service.add_callback(callback2)

        logger_service.info("Test message")

        assert callback1.called
        assert callback2.called

    def test_remove_callback(self, logger_service):
        """Test removing callback."""
        callback = Mock()
        logger_service.add_callback(callback)
        logger_service.remove_callback(callback)

        logger_service.info("Test message")

        assert not callback.called

    def test_callback_exception_handling(self, logger_service):
        """Test that callback exceptions don't break logging."""
        bad_callback = Mock(side_effect=Exception("Callback error"))
        good_callback = Mock()

        logger_service.add_callback(bad_callback)
        logger_service.add_callback(good_callback)

        # Should not raise
        logger_service.info("Test message")

        assert bad_callback.called
        assert good_callback.called

    def test_clear_logs(self, logger_service):
        """Test clearing logs."""
        for i in range(10):
            logger_service.info(f"Message {i}")

        count = logger_service.clear_logs()

        assert count == 10
        assert len(logger_service.logs) == 0

    def test_max_entries_enforcement(self):
        """Test that max entries limit is enforced."""
        logger = DashboardLogger(max_entries=5)

        for i in range(10):
            logger.info(f"Message {i}")

        assert len(logger.logs) == 5
        # Should contain the last 5 messages
        logs = list(logger.logs)
        assert logs[0].message == "Message 5"
        assert logs[4].message == "Message 9"

    def test_get_statistics(self, logger_service):
        """Test getting logger statistics."""
        logger_service.info("Message 1", component_id="comp1")
        logger_service.warning("Message 2", component_id="comp2")
        logger_service.error("Message 3", component_id="comp1")

        stats = logger_service.get_statistics()

        assert stats["total_entries"] == 3
        assert stats["capacity"] == 1000
        assert stats["by_level"]["INFO"] == 1
        assert stats["by_level"]["WARNING"] == 1
        assert stats["by_level"]["ERROR"] == 1
        assert stats["by_component"]["comp1"] == 2
        assert stats["by_component"]["comp2"] == 1

    def test_log_entry_to_dict(self):
        """Test LogEntry.to_dict()."""
        entry = LogEntry(
            level=LogLevel.INFO,
            message="Test",
            component_id="comp1",
            source="service",
            metadata={"key": "value"},
        )

        data = entry.to_dict()

        assert data["level"] == "INFO"
        assert data["message"] == "Test"
        assert data["component_id"] == "comp1"
        assert data["source"] == "service"
        assert data["metadata"] == {"key": "value"}
        assert "timestamp" in data

    def test_log_level_enum(self):
        """Test LogLevel enum."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_create_dashboard_logger(self):
        """Test factory function."""
        logger = create_dashboard_logger(max_entries=500)

        assert isinstance(logger, DashboardLogger)
        assert logger.max_entries == 500

    def test_create_dashboard_logger_default(self):
        """Test factory function with defaults."""
        logger = create_dashboard_logger()

        assert isinstance(logger, DashboardLogger)
        assert logger.max_entries == 1000

    def test_chronological_order(self, logger_service):
        """Test that logs are returned in chronological order."""
        logger_service.info("Message 1")
        logger_service.info("Message 2")
        logger_service.info("Message 3")

        logs = logger_service.get_logs()

        assert logs[0].message == "Message 1"
        assert logs[1].message == "Message 2"
        assert logs[2].message == "Message 3"

    def test_most_recent_first(self, logger_service):
        """Test that get_recent_logs returns most recent first."""
        logger_service.info("Message 1")
        logger_service.info("Message 2")
        logger_service.info("Message 3")

        logs = logger_service.get_recent_logs(limit=2)

        assert logs[0].message == "Message 2"
        assert logs[1].message == "Message 3"

    def test_log_with_custom_source(self, logger_service):
        """Test logging with custom source."""
        entry = logger_service.log(
            LogLevel.INFO,
            "Message",
            source="custom-source",
        )

        assert entry.source == "custom-source"

    def test_multiple_component_filters(self, logger_service):
        """Test filtering with multiple log conditions."""
        logger_service.info("Info 1", component_id="comp1")
        logger_service.warning("Warning 1", component_id="comp1")
        logger_service.error("Error 1", component_id="comp2")
        logger_service.info("Info 2", component_id="comp2")

        logs = logger_service.get_logs(
            level=LogLevel.INFO,
            component_id="comp1",
        )

        assert len(logs) == 1
        assert logs[0].message == "Info 1"
