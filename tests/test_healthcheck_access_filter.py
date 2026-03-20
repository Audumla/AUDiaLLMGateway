import logging

from src.launcher.log_filters import HealthcheckAccessFilter


def _record(path: str, status_code: int, method: str = "GET") -> logging.LogRecord:
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %s',
        args=("127.0.0.1:12345", method, path, "1.1", status_code),
        exc_info=None,
    )
    return record


def test_hides_successful_liveliness_probe() -> None:
    assert HealthcheckAccessFilter().filter(_record("/health/liveliness", 200)) is False


def test_keeps_failed_liveliness_probe() -> None:
    assert HealthcheckAccessFilter().filter(_record("/health/liveliness", 503)) is True


def test_keeps_non_health_request() -> None:
    assert HealthcheckAccessFilter().filter(_record("/v1/models", 200)) is True
