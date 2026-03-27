"""Components router for dashboard API.

Endpoints for querying component status and triggering actions.

Endpoints:
- GET /api/v1/components - List all components with status
- GET /api/v1/components/{component_id} - Get component details
- POST /api/v1/components/{component_id}/actions/{action_id} - Execute action
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone

from src.monitoring.manifest_loader import ManifestLoader
from src.monitoring.models import ComponentManifest
from src.monitoring.action_runner import ActionRunner
from src.monitoring.services.action_executor import ActionExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/components", tags=["components"])


def get_manifest_loader(app=Depends(lambda: None)) -> ManifestLoader:
    """Dependency: get manifest loader."""
    raise NotImplementedError("Should be overridden by app")


def get_manifests(app=Depends(lambda: None)) -> dict[str, ComponentManifest]:
    """Dependency: get loaded manifests."""
    raise NotImplementedError("Should be overridden by app")


def get_action_executor(app=Depends(lambda: None)) -> ActionExecutor:
    """Dependency: get action executor."""
    raise NotImplementedError("Should be overridden by app")


@router.get("")
async def list_components(
    manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
):
    """List all components with their status.

    Returns component manifest data including available actions.
    """
    components = []

    for component_id, manifest in manifests.items():
        component_data = {
            "id": component_id,
            "display_name": manifest.display_name,
            "icon": manifest.icon,
            "enabled": manifest.enabled,
            "health": {
                "endpoint": manifest.health.endpoint,
                "expect_status": manifest.health.expect_status,
                "timeout_s": manifest.health.timeout_s,
            },
            "connection": {
                "host": manifest.connection.host,
                "port": manifest.connection.port,
                "timeout_s": manifest.connection.timeout_s,
            },
            "actions": [
                {
                    "id": action.id,
                    "label": action.label,
                    "type": action.type,
                    "confirm": action.confirm,
                }
                for action in manifest.actions
            ] if manifest.actions else [],
        }
        components.append(component_data)

    return {
        "components": components,
        "count": len(components),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{component_id}")
async def get_component(
    component_id: str,
    manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
):
    """Get detailed information about a specific component."""
    if component_id not in manifests:
        raise HTTPException(status_code=404, detail="Component not found")

    manifest = manifests[component_id]

    return {
        "id": component_id,
        "display_name": manifest.display_name,
        "icon": manifest.icon,
        "enabled": manifest.enabled,
        "health": {
            "endpoint": manifest.health.endpoint,
            "expect_status": manifest.health.expect_status,
            "timeout_s": manifest.health.timeout_s,
        },
        "connection": {
            "host": manifest.connection.host,
            "port": manifest.connection.port,
            "timeout_s": manifest.connection.timeout_s,
        },
        "actions": [
            {
                "id": action.id,
                "label": action.label,
                "type": action.type,
                "confirm": action.confirm,
                "container": action.container,
                "command": action.command,
            }
            for action in manifest.actions
        ] if manifest.actions else [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{component_id}/actions/{action_id}")
async def execute_component_action(
    component_id: str,
    action_id: str,
    manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)],
    executor: Annotated[ActionExecutor, Depends(get_action_executor)],
    request_id: Optional[str] = Query(None),
):
    """Execute an action on a component.

    Args:
        component_id: Component identifier
        action_id: Action identifier
        request_id: Optional request tracking ID

    Returns:
        Execution status and result
    """
    # Validate component exists
    if component_id not in manifests:
        raise HTTPException(status_code=404, detail="Component not found")

    manifest = manifests[component_id]

    # Validate action exists
    action_config = None
    if manifest.actions:
        for action in manifest.actions:
            if action.id == action_id:
                action_config = action
                break

    if not action_config:
        raise HTTPException(status_code=404, detail="Action not found")

    # Execute action
    try:
        metadata = {
            "request_id": request_id,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }
        history = executor.execute(component_id, action_config, metadata=metadata)

        return {
            "execution_id": history.execution_id,
            "component_id": component_id,
            "action_id": action_id,
            "state": history.state.value,
            "started_at": history.started_at.isoformat(),
            "completed_at": history.completed_at.isoformat() if history.completed_at else None,
            "duration_seconds": history.duration_seconds,
            "success": history.result.success if history.result else None,
            "message": history.result.message if history.result else None,
            "error": history.error,
            "result": history.result.to_dict() if history.result else None,
        }
    except Exception as e:
        logger.error(f"Error executing action {action_id} on {component_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{component_id}/actions/{action_id}/status/{execution_id}")
async def get_action_status(
    component_id: str,
    action_id: str,
    execution_id: str,
    executor: Annotated[ActionExecutor, Depends(get_action_executor)],
):
    """Get execution status of a triggered action.

    Useful for polling or checking async action results.
    """
    status = executor.get_execution_status(execution_id)

    if not status:
        raise HTTPException(status_code=404, detail="Execution not found")

    return status
