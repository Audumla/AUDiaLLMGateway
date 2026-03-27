"""Manifests router for dashboard API.

Endpoints for retrieving component layout and display metadata.

Endpoints:
- GET /api/v1/manifests - List all enabled components with display metadata
- GET /api/v1/manifests/{component_id} - Get component manifest for rendering
"""

import logging
from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.monitoring.models import ComponentManifest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/manifests", tags=["manifests"])


def get_manifests(app=Depends(lambda: None)) -> dict[str, ComponentManifest]:
    """Dependency: get loaded manifests."""
    raise NotImplementedError("Should be overridden by app")


@router.get("")
async def list_manifests(
    manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
):
    """List all enabled components with display metadata.

    Returns component manifests for Vue SPA card rendering, including:
    - Display name, icon, card configuration
    - Available actions
    - Quick links to component UIs
    """
    components = []

    for component_id, manifest in manifests.items():
        if not manifest.enabled:
            continue

        # Build actions list with essential fields for UI
        actions = []
        if manifest.actions:
            for action in manifest.actions:
                action_data = {
                    "id": action.id,
                    "label": action.label,
                    "type": action.type,
                    "confirm": action.confirm,
                }
                if action.confirm_message:
                    action_data["confirm_message"] = action.confirm_message
                actions.append(action_data)

        # Build card configuration for display
        card_data = {
            "port": manifest.card.port or manifest.connection.port,
            "extra_fields": manifest.card.extra_fields or [],
            "links": manifest.card.links or [],
        }

        component_data = {
            "id": component_id,
            "display_name": manifest.display_name,
            "icon": manifest.icon,
            "card": card_data,
            "actions": actions,
        }
        components.append(component_data)

    return {
        "components": components,
        "count": len(components),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{component_id}")
async def get_manifest(
    component_id: str,
    manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
):
    """Get complete manifest for a specific component.

    Returns full component specification including all metadata for detailed
    rendering, configuration, and action execution.
    """
    if component_id not in manifests:
        raise HTTPException(status_code=404, detail="Component not found")

    manifest = manifests[component_id]

    # Build actions list with all fields for detail view
    actions = []
    if manifest.actions:
        for action in manifest.actions:
            action_data = {
                "id": action.id,
                "label": action.label,
                "type": action.type,
                "confirm": action.confirm,
            }
            if action.confirm_message:
                action_data["confirm_message"] = action.confirm_message
            if action.container:
                action_data["container"] = action.container
            if action.endpoint:
                action_data["endpoint"] = action.endpoint
            if action.body:
                action_data["body"] = action.body
            if action.signal:
                action_data["signal"] = action.signal
            if action.command:
                action_data["command"] = action.command
            actions.append(action_data)

    # Build metrics list
    metrics = []
    if manifest.metrics:
        for metric in manifest.metrics:
            metric_data = {
                "id": metric.id,
                "endpoint": metric.endpoint,
                "source_format": metric.source_format,
                "metric_name": metric.metric_name,
                "extract": metric.extract,
                "prometheus_name": metric.prometheus_name,
                "unit": metric.unit,
                "poll_interval_s": metric.poll_interval_s,
                "labels": metric.labels or [],
                "type": metric.type,
                "formula": metric.formula,
            }
            metrics.append(metric_data)

    # Build health probe config
    health_data = {
        "endpoint": manifest.health.endpoint,
        "method": manifest.health.method,
        "expect_status": manifest.health.expect_status,
        "timeout_s": manifest.health.timeout_s,
    }
    if manifest.health.status_field:
        health_data["status_field"] = manifest.health.status_field
    if manifest.health.headers:
        health_data["headers"] = manifest.health.headers

    # Build connection config
    connection_data = {
        "host": manifest.connection.host,
        "port": manifest.connection.port,
        "timeout_s": manifest.connection.timeout_s,
    }
    if manifest.connection.auth:
        connection_data["auth"] = manifest.connection.auth

    # Build card configuration
    card_data = {
        "port": manifest.card.port or manifest.connection.port,
        "extra_fields": manifest.card.extra_fields or [],
        "links": manifest.card.links or [],
    }

    return {
        "id": component_id,
        "display_name": manifest.display_name,
        "icon": manifest.icon,
        "enabled": manifest.enabled,
        "health": health_data,
        "connection": connection_data,
        "metrics": metrics,
        "actions": actions,
        "card": card_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
