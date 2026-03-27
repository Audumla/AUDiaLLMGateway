"""FastAPI application factory for the gateway dashboard.

The dashboard is observational-only and manifest-driven. Components are discovered
via YAML files with zero modifications required to monitored services.
"""

import logging
from pathlib import Path
from typing import Annotated
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .manifest_loader import ManifestLoader
from .models import ComponentManifest
from .models.errors import ManifestLoadError

# Configure logging
logger = logging.getLogger(__name__)


def get_manifest_loader(app: FastAPI = Depends(lambda: None)) -> ManifestLoader:
    """Dependency injection: get manifest loader from app state."""
    # This will be injected by the app via app.dependency_overrides
    raise NotImplementedError("This should be overridden by the app")


def get_manifests(app: FastAPI = Depends(lambda: None)) -> dict[str, ComponentManifest]:
    """Dependency injection: get loaded manifests from app state."""
    # This will be injected by the app via app.dependency_overrides
    raise NotImplementedError("This should be overridden by the app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    try:
        loader = app.state.manifest_loader
        app.state.manifests = loader.load_manifests()
        logger.info(f"Loaded {len(app.state.manifests)} component manifests")
    except ManifestLoadError as e:
        logger.error(f"Failed to load manifests at startup: {e}")
        raise

    yield

    # Shutdown
    logger.info("Dashboard shutting down")


def create_app(root: Path = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        root: Project root directory. If None, uses current working directory.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="AUDia LLM Gateway Dashboard",
        version="0.1.0",
        description="Observational dashboard for LLM gateway components",
        lifespan=lifespan,
    )

    # Initialize app state
    app.state.manifest_loader = ManifestLoader(root)
    app.state.manifests = {}

    # Set up dependency injection overrides
    def get_manifest_loader_impl() -> ManifestLoader:
        return app.state.manifest_loader

    def get_manifests_impl() -> dict[str, ComponentManifest]:
        return app.state.manifests

    app.dependency_overrides[get_manifest_loader] = get_manifest_loader_impl
    app.dependency_overrides[get_manifests] = get_manifests_impl

    # CORS middleware (for UI served from different origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict to localhost + configured origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/healthz")
    async def health():
        """Simple health check."""
        return {
            "status": "healthy",
            "version": "0.1.0",
        }

    # Manifests endpoint (for debugging)
    @app.get("/api/v1/manifests")
    async def get_all_manifests(
        manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
    ):
        """Get all enabled component manifests."""
        return {
            "components": list(manifests.values()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Component-specific manifest
    @app.get("/api/v1/manifests/{component_id}")
    async def get_component_manifest(
        component_id: str,
        manifests: Annotated[dict[str, ComponentManifest], Depends(get_manifests)]
    ):
        """Get manifest for a specific component."""
        if component_id not in manifests:
            raise HTTPException(status_code=404, detail="Component not found")
        return manifests[component_id]

    # TODO: Import and register routers
    # from .routers import manifests, components, config, logs, models, health
    # app.include_router(manifests.router)
    # app.include_router(components.router)
    # app.include_router(config.router)
    # app.include_router(logs.router)
    # app.include_router(models.router)
    # app.include_router(health.router)

    # Mount static files (built Vue SPA)
    # static_dir = Path(__file__).parent / "static"
    # if static_dir.exists():
    #     app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8080)
