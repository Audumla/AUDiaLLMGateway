"""API request/response models."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime
from .manifest import ComponentManifest


class ActionExecutionRequest(BaseModel):
    """Execute an action on a component."""
    component_id: str = Field(..., description="Component ID")
    action_id: str = Field(..., description="Action ID within component")
    params: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional action parameters"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "component_id": "litellm",
                "action_id": "restart",
                "params": {}
            }
        }
    )


class ActionExecutionResponse(BaseModel):
    """Response from action execution."""
    success: bool = Field(..., description="Whether action started successfully")
    message: str = Field(..., description="Human-readable message")
    execution_id: str = Field(..., description="Unique execution ID for tracking")
    started_at: datetime = Field(..., description="When action started")
    completed: bool = Field(
        default=False,
        description="Whether action is complete (async actions may not be)"
    )
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Action result (if completed)"
    )
    error: Optional[str] = Field(None, description="Error message (if failed)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Restart command sent to audia-litellm container",
                "execution_id": "exec-20260327-abc123",
                "started_at": "2026-03-27T10:30:45Z",
                "completed": False,
                "result": None,
                "error": None
            }
        }
    )


class ConfigDiffResponse(BaseModel):
    """Show what would change if config is regenerated."""
    changed_files: List[str] = Field(
        ...,
        description="List of files that would change"
    )
    diffs: Dict[str, str] = Field(
        ...,
        description="Unified diffs (filename -> diff content)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "changed_files": [
                    "config/monitoring/litellm.yaml",
                    "config/monitoring/llamaswap.yaml"
                ],
                "diffs": {
                    "config/monitoring/litellm.yaml": "--- a/config/monitoring/litellm.yaml\n+++ b/config/monitoring/litellm.yaml\n..."
                }
            }
        }
    )


class ManifestsResponse(BaseModel):
    """List of all enabled component manifests."""
    components: List[ComponentManifest] = Field(
        ...,
        description="All enabled components"
    )
    timestamp: datetime = Field(
        ...,
        description="When manifests were loaded"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "components": [],
                "timestamp": "2026-03-27T10:30:45Z"
            }
        }
    )


class ModelsCatalogResponse(BaseModel):
    """Models available in the system."""
    llama_cpp_models: List[str] = Field(
        default_factory=list,
        description="Models loaded via llama.cpp"
    )
    vllm_models: List[str] = Field(
        default_factory=list,
        description="Models loaded via vLLM"
    )
    timestamp: datetime = Field(
        ...,
        description="When catalog was queried"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "llama_cpp_models": [
                    "qwen3.5-27b-(96k-Q6)",
                    "qwen3.5-122b"
                ],
                "vllm_models": [
                    "Qwen2.5-0.5B-Instruct"
                ],
                "timestamp": "2026-03-27T10:30:45Z"
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """Health check response for dashboard itself."""
    status: str = Field(..., description="'healthy' or 'unhealthy'")
    timestamp: datetime = Field(..., description="Check timestamp")
    components: Dict[str, bool] = Field(
        ...,
        description="Component ID -> health status"
    )
    errors: Optional[Dict[str, str]] = Field(
        None,
        description="Component ID -> error message (if unhealthy)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2026-03-27T10:30:45Z",
                "components": {
                    "litellm": True,
                    "llamaswap": True,
                    "vllm": False
                },
                "errors": {
                    "vllm": "Connection refused"
                }
            }
        }
    )
