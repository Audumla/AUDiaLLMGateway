"""Logs router for dashboard API.

Endpoints for retrieving logs and real-time event streaming.

Endpoints:
- GET /api/v1/logs - Query logs with filtering
- GET /api/v1/logs/stream - Real-time SSE event stream
"""

import logging
from typing import Annotated, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.dashboard.services.logger import DashboardLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


def get_logger(app=Depends(lambda: None)) -> DashboardLogger:
    """Dependency: get dashboard logger instance."""
    raise NotImplementedError("Should be overridden by app")


@router.get("")
async def get_logs(
    log_service: Annotated[DashboardLogger, Depends(get_logger)],
    level: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
    component: Optional[str] = Query(None, description="Filter by component"),
    source: Optional[str] = Query(None, description="Filter by source module"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get logs with optional filtering.

    Supports filtering by level, component, and source.
    Returns paginated results with total count.
    """
    try:
        # Convert LogLevel string if provided
        from src.dashboard.services.logger import LogLevel
        log_level = LogLevel(level) if level else None

        # Get logs with filters
        logs = log_service.get_logs(
            level=log_level,
            component_id=component,
            source=source,
            limit=limit + offset,  # Get enough to skip offset
        )

        # Apply offset pagination
        paginated_logs = logs[offset : offset + limit]

        # Convert to dicts
        log_dicts = [log.to_dict() for log in paginated_logs]

        return {
            "logs": log_dicts,
            "total": len(logs),
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def stream_logs(
    log_service: Annotated[DashboardLogger, Depends(get_logger)],
    level: Optional[str] = Query(None, description="Filter by log level"),
    component: Optional[str] = Query(None, description="Filter by component"),
    source: Optional[str] = Query(None, description="Filter by source module"),
):
    """Stream logs in real-time via Server-Sent Events (SSE).

    Sends new log entries as they occur.
    Client should use EventSource API to consume.
    """

    async def event_generator():
        """Generate SSE events for incoming logs."""
        # Create an async queue to receive log events
        import asyncio
        from queue import Queue
        from src.dashboard.services.logger import LogLevel

        log_queue: Queue = Queue()
        log_level = LogLevel(level) if level else None

        def on_log(log_entry):
            """Callback when a new log is created."""
            # Apply filters
            if log_level and log_entry.level != log_level:
                return
            if component and log_entry.component_id != component:
                return
            if source and log_entry.source != source:
                return

            log_queue.put(log_entry)

        # Register callback
        log_service.add_callback(on_log)

        try:
            # Send initial data event
            yield f"data: {{'type': 'connected', 'timestamp': '{datetime.now(timezone.utc).isoformat()}'}}\n\n"

            # Stream logs
            while True:
                try:
                    # Check queue with timeout
                    log_entry = log_queue.get(timeout=30)  # 30s timeout before ping
                    log_dict = log_entry.to_dict()
                    yield f"data: {log_dict}\n\n"
                except Exception:
                    # Timeout - send keep-alive ping
                    yield f": ping at {datetime.now(timezone.utc).isoformat()}\n\n"
        except GeneratorExit:
            pass
        except Exception as e:
            logger.error(f"Error in log streaming: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stats")
async def get_log_stats(
    log_service: Annotated[DashboardLogger, Depends(get_logger)]
):
    """Get log statistics and breakdown.

    Returns statistics by level, component, and overall metrics.
    """
    try:
        stats = log_service.get_statistics()

        return {
            "by_level": stats.get("by_level", {}),
            "by_component": stats.get("by_component", {}),
            "by_source": stats.get("by_source", {}),
            "total_logs": stats.get("total_logs", 0),
            "error_count": stats.get("error_count", 0),
            "warning_count": stats.get("warning_count", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting log statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
