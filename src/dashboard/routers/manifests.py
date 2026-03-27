"""Manifests endpoints.

GET /api/v1/manifests        - List all enabled manifests
GET /api/v1/manifests/{id}   - Get specific manifest
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from ..models import ComponentManifest, ManifestsResponse

router = APIRouter(prefix="/api/v1", tags=["manifests"])


def get_manifests() -> dict[str, ComponentManifest]:
    """Dependency: get manifests from app state."""
    # TODO: implement dependency injection from main.py
    return {}


@router.get("/manifests", response_model=ManifestsResponse)
async def list_manifests(
    manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
):
    """Get all enabled component manifests."""
    from datetime import datetime
    return ManifestsResponse(
        components=list(manifests.values()),
        timestamp=datetime.utcnow(),
    )


@router.get("/manifests/{component_id}", response_model=ComponentManifest)
async def get_manifest(
    component_id: str,
    manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
):
    """Get manifest for a specific component."""
    if component_id not in manifests:
        raise HTTPException(
            status_code=404,
            detail=f"Component '{component_id}' not found"
        )
    return manifests[component_id]
