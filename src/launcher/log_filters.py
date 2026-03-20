from __future__ import annotations

import logging
from typing import Any


class HealthcheckAccessFilter(logging.Filter):
    """Suppress only successful liveliness probe access logs.

    Uvicorn access log records expose their request metadata via ``record.args`` as:
    ``(client_addr, method, path, http_version, status_code)``.
    Keep all non-health traffic and all non-200 health responses visible.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args: Any = getattr(record, "args", ())
        if not isinstance(args, tuple) or len(args) < 5:
            return True

        method = str(args[1])
        path = str(args[2])
        status_code = str(args[4])

        if method == "GET" and path.startswith("/health/liveliness") and status_code == "200":
            return False
        return True
