# Spec 701 Detailed Implementation Guide

**Status:** Implementation Ready
**Created:** 2026-03-27
**Scope:** Complete technical specification for building the dashboard
**Audience:** Developers implementing Phases 1-4

---

## Table of Contents

1. [Complete Module Structure](#1-complete-module-structure)
2. [Data Schemas & Type Definitions](#2-data-schemas--type-definitions)
3. [API Contracts](#3-api-contracts)
4. [Configuration Sources & Flow](#4-configuration-sources--flow)
5. [Dependency Injection & Decoupling](#5-dependency-injection--decoupling)
6. [Module Responsibilities](#6-module-responsibilities)
7. [Testing Strategy Per Module](#7-testing-strategy-per-module)
8. [Build & Deployment](#8-build--deployment)
9. [Documentation Standards](#9-documentation-standards)

---

## 1. Complete Module Structure

### 1.1 Backend Directory Layout

```
src/dashboard/
├── __init__.py                          # Package init
├── main.py                              # FastAPI app factory + startup
├── manifest_loader.py                   # Config loading + resolution
├── docker_handler.py                    # Docker socket integration
├── action_runner.py                     # Action execution dispatcher
├── prometheus_client.py                 # Prometheus HTTP client (for testing)
│
├── routers/
│   ├── __init__.py
│   ├── manifests.py                    # GET /api/v1/manifests*
│   ├── components.py                   # POST /api/v1/components/{id}/actions/{action_id}
│   ├── config.py                       # GET /api/v1/config/diff, POST /api/v1/config/reload
│   ├── logs.py                         # GET /api/v1/logs/{id} (SSE)
│   ├── models.py                       # GET /api/v1/models/catalog
│   └── health.py                       # GET /healthz
│
├── models/
│   ├── __init__.py
│   ├── manifest.py                     # Pydantic models for manifest schema
│   ├── action.py                       # Action type definitions
│   ├── prometheus.py                   # Prometheus query/response models
│   └── errors.py                       # Custom exception classes
│
├── services/
│   ├── __init__.py
│   ├── gateway_config.py               # Read stack.yaml + models.yaml
│   ├── action_executor.py              # Coordinate action execution
│   └── logger.py                       # Centralized logging (for SSE logs endpoint)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # Pytest fixtures
│   ├── test_manifest_loader.py         # Manifest loading + resolution
│   ├── test_manifest_api.py            # API endpoint tests
│   ├── test_action_runner.py           # Action execution tests
│   ├── test_docker_handler.py          # Docker socket tests (mock)
│   ├── test_independence.py            # Verify component independence
│   └── fixtures/
│       ├── mock_manifests.py           # Mock manifest data
│       └── mock_prometheus.py          # Mock Prometheus responses
│
├── Dockerfile                           # Multi-stage build
├── requirements-dashboard.txt           # Python dependencies
└── static/                              # Built Vue SPA (gitignored)
    └── index.html                       # Entry point
```

### 1.2 Frontend Directory Layout

```
src/dashboard/ui/
├── src/
│   ├── main.ts                         # Vue app entry point
│   ├── App.vue                         # Root component
│   ├── env.d.ts                        # TypeScript env declarations
│   │
│   ├── components/
│   │   ├── Dashboard.vue               # Main dashboard grid
│   │   ├── ComponentCard.vue           # Generic card (manifest-driven)
│   │   ├── ModelPanel.vue              # Loaded models display
│   │   ├── LogDrawer.vue               # SSE log viewer
│   │   └── cards/
│   │       └── VllmCard.vue            # (Optional) custom card override
│   │
│   ├── stores/
│   │   └── metricsStore.ts             # Pinia store (polling + state)
│   │
│   ├── services/
│   │   ├── apiClient.ts                # FastAPI HTTP client
│   │   ├── prometheusClient.ts         # Prometheus HTTP client
│   │   └── eventSource.ts              # SSE connection manager
│   │
│   ├── types/
│   │   ├── manifest.ts                 # TypeScript manifest schema
│   │   ├── action.ts                   # Action type definitions
│   │   ├── prometheus.ts               # Prometheus query/response types
│   │   └── index.ts                    # Re-exports
│   │
│   ├── utils/
│   │   ├── formatting.ts               # Format metric values (bytes, %, etc)
│   │   ├── timing.ts                   # Relative time display ("5m ago")
│   │   └── colors.ts                   # Status color mapping
│   │
│   └── styles/
│       ├── globals.css                 # Tailwind + global styles
│       └── components.css              # Component-specific styles
│
├── index.html                          # HTML entry point
├── package.json                        # Node dependencies
├── vite.config.ts                      # Vite build config
├── tailwind.config.js                  # Tailwind config
├── tsconfig.json                       # TypeScript config
└── vitest.config.ts                    # Test config
```

---

## 2. Data Schemas & Type Definitions

### 2.1 Manifest Schema (Pydantic + TypeScript)

**File:** `src/dashboard/models/manifest.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

class HealthProbeConfig(BaseModel):
    """Health check configuration."""
    endpoint: str = Field(..., description="Health check endpoint path")
    method: Literal["GET", "HEAD"] = "GET"
    expect_status: int = 200
    timeout_s: int = 3
    status_field: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "endpoint": "/health",
                "method": "GET",
                "expect_status": 200,
                "timeout_s": 3
            }
        }

class MetricConfig(BaseModel):
    """Metric definition for hwexp adapter + Prometheus."""
    id: str = Field(..., description="Unique metric ID within component")
    endpoint: str = Field(..., description="HTTP endpoint to query")
    source_format: Literal["json", "prometheus"] = "json"
    extract: Optional[str] = None  # jq expression for JSON
    metric_name: Optional[str] = None  # For Prometheus format
    prometheus_name: str = Field(..., description="Relabeled metric name in gateway_ namespace")
    unit: str = Field(..., description="Unit: count, bytes, ratio, tokens_per_second, etc")
    poll_interval_s: int = 15
    labels: Optional[List[str]] = None
    type: Literal["gauge", "counter", "histogram", "info", "derived"] = "gauge"
    formula: Optional[str] = None  # For derived metrics (PromQL)

    @validator("prometheus_name")
    def validate_prometheus_name(cls, v):
        assert v.startswith("gateway_"), "Metric must be prefixed with 'gateway_'"
        return v

class ActionConfig(BaseModel):
    """Action definition (button/command)."""
    id: str = Field(..., description="Unique action ID within component")
    label: str = Field(..., description="Button label shown to user")
    type: Literal["docker_restart", "http_post", "process_signal", "config_reload", "shell"]
    container: Optional[str] = None  # For docker_restart
    endpoint: Optional[str] = None  # For http_post
    body: Optional[Dict[str, Any]] = None  # For http_post
    signal: Optional[str] = None  # For process_signal (SIGHUP, SIGTERM)
    command: Optional[str] = None  # For shell (function name in process_manager.py)
    confirm: bool = False
    confirm_message: Optional[str] = None

class CardConfig(BaseModel):
    """UI card display configuration."""
    port: Optional[int] = None  # Shown in badge
    extra_fields: List[Dict[str, str]] = Field(default_factory=list)
    links: List[Dict[str, str]] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "port": 4000,
                "extra_fields": [
                    {"label": "Active Model", "metric": "active_model"},
                    {"label": "In-Flight Requests", "metric": "in_flight_requests"}
                ],
                "links": [
                    {"label": "API Docs", "path": "/ui/"},
                    {"label": "Health", "path": "/health"}
                ]
            }
        }

class ConnectionConfig(BaseModel):
    """How to reach this component."""
    host: str = Field(..., description="Service hostname, supports ${VAR:-default}")
    port: int = Field(..., description="Service port, supports ${VAR:-default}")
    auth: Optional[Dict[str, str]] = None
    timeout_s: int = 5

    class Config:
        json_schema_extra = {
            "example": {
                "host": "${LITELLM_HOST:-127.0.0.1}",
                "port": "${LITELLM_PORT:-4000}"
            }
        }

class ComponentManifest(BaseModel):
    """Complete component manifest."""
    id: str = Field(..., description="Component ID (machine identifier)")
    display_name: str = Field(..., description="Human-readable name")
    icon: str = Field(..., description="Icon key (cpu, server, brain, etc)")
    enabled: bool = True

    health: HealthProbeConfig
    metrics: List[MetricConfig] = Field(default_factory=list)
    actions: List[ActionConfig] = Field(default_factory=list)
    connection: ConnectionConfig
    card: CardConfig = Field(default_factory=CardConfig)

    class Config:
        json_schema_extra = {
            "title": "Component Manifest Schema",
            "description": "Complete specification for monitoring + controlling a component"
        }
```

**File:** `src/dashboard/ui/src/types/manifest.ts`

```typescript
export type HealthProbeMethod = 'GET' | 'HEAD'
export type MetricSourceFormat = 'json' | 'prometheus'
export type MetricUnit = 'count' | 'bytes' | 'ratio' | 'tokens_per_second' | 'seconds' | 'percent'
export type MetricType = 'gauge' | 'counter' | 'histogram' | 'info' | 'derived'
export type ActionType = 'docker_restart' | 'http_post' | 'process_signal' | 'config_reload' | 'shell'

export interface HealthProbeConfig {
  endpoint: string
  method: HealthProbeMethod
  expect_status: number
  timeout_s: number
  status_field?: string
  headers?: Record<string, string>
}

export interface MetricConfig {
  id: string
  endpoint: string
  source_format: MetricSourceFormat
  extract?: string
  metric_name?: string
  prometheus_name: string
  unit: MetricUnit
  poll_interval_s: number
  labels?: string[]
  type: MetricType
  formula?: string
}

export interface ActionConfig {
  id: string
  label: string
  type: ActionType
  container?: string
  endpoint?: string
  body?: Record<string, any>
  signal?: string
  command?: string
  confirm: boolean
  confirm_message?: string
}

export interface CardConfig {
  port?: number
  extra_fields: Array<{ label: string; metric: string }>
  links: Array<{ label: string; path: string }>
}

export interface ConnectionConfig {
  host: string
  port: number | string
  auth?: Record<string, string>
  timeout_s: number
}

export interface ComponentManifest {
  id: string
  display_name: string
  icon: string
  enabled: boolean
  health: HealthProbeConfig
  metrics: MetricConfig[]
  actions: ActionConfig[]
  connection: ConnectionConfig
  card: CardConfig
}
```

### 2.2 Prometheus Query/Response Schema

**File:** `src/dashboard/models/prometheus.py`

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal

class PrometheusLabel(BaseModel):
    """Label for a metric time series."""
    __root__: Dict[str, str]

class PrometheusValue(BaseModel):
    """Single scalar value with timestamp."""
    timestamp: int
    value: str

class PrometheusInstantVector(BaseModel):
    """Result from /api/v1/query (instant vector)."""
    metric: Dict[str, str]
    value: List[Any]  # [timestamp, value_string]

class PrometheusRangeVector(BaseModel):
    """Result from /api/v1/query_range."""
    metric: Dict[str, str]
    values: List[List[Any]]  # [[timestamp, value_string], ...]

class PrometheusQueryResult(BaseModel):
    """Query result (instant or range)."""
    resultType: Literal["matrix", "vector", "scalar", "string"]
    result: List[Dict[str, Any]]

class PrometheusResponse(BaseModel):
    """Standard Prometheus API response."""
    status: Literal["success", "error"]
    data: Optional[PrometheusQueryResult] = None
    error: Optional[str] = None
    errorType: Optional[str] = None

    def is_success(self) -> bool:
        return self.status == "success"

class MetricSnapshot(BaseModel):
    """Snapshot of a single metric value for dashboard display."""
    metric_name: str  # e.g., "gateway_component_up"
    labels: Dict[str, str]  # e.g., {"component": "litellm"}
    value: float  # Parsed numeric value
    timestamp: int
    unit: str  # For formatting display
```

**File:** `src/dashboard/ui/src/types/prometheus.ts`

```typescript
export interface PrometheusLabel {
  [key: string]: string
}

export interface PrometheusValue {
  timestamp: number
  value: string | number
}

export interface PrometheusInstantResult {
  metric: PrometheusLabel
  value: [number, string]
}

export interface PrometheusRangeResult {
  metric: PrometheusLabel
  values: Array<[number, string]>
}

export type PrometheusResult = PrometheusInstantResult | PrometheusRangeResult

export interface PrometheusResponse<T> {
  status: 'success' | 'error'
  data?: T
  error?: string
  errorType?: string
}

export interface MetricSnapshot {
  metric_name: string
  labels: Record<string, string>
  value: number
  timestamp: number
  unit: string
}
```

### 2.3 API Request/Response Models

**File:** `src/dashboard/models/api.py`

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ActionExecutionRequest(BaseModel):
    """Execute an action on a component."""
    component_id: str
    action_id: str
    # Optional parameters (for future extensibility)
    params: Optional[Dict[str, Any]] = None

class ActionExecutionResponse(BaseModel):
    """Response from action execution."""
    success: bool
    message: str
    execution_id: str
    started_at: datetime
    # Async actions may not be complete
    completed: bool = False
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ConfigDiffResponse(BaseModel):
    """Show what would change if config is regenerated."""
    changed_files: List[str]
    diffs: Dict[str, str]  # filename -> unified diff

class ManifestsResponse(BaseModel):
    """List of all enabled component manifests."""
    components: List[ComponentManifest]
    timestamp: datetime

class ModelsCatalogResponse(BaseModel):
    """Models available in the system."""
    llama_cpp_models: List[str]
    vllm_models: List[str]
    timestamp: datetime

class HealthCheckResponse(BaseModel):
    """Dashboard health status."""
    status: Literal["healthy", "degraded", "unhealthy"]
    dashboard_service: str = "ok"
    prometheus_connection: str
    components_up: int
    components_down: int
    last_metric_update: Optional[datetime] = None
```

---

## 3. API Contracts

### 3.1 Manifest Endpoints

**GET /api/v1/manifests**
- Authentication: Optional (if not in readonly mode)
- Response: `ManifestsResponse`
- Example:
```json
{
  "components": [
    {
      "id": "litellm",
      "display_name": "LiteLLM Gateway",
      "icon": "gateway",
      "enabled": true,
      "health": { ... },
      "metrics": [ ... ],
      "actions": [ ... ],
      "connection": { ... },
      "card": { ... }
    }
  ],
  "timestamp": "2026-03-27T10:30:00Z"
}
```

**GET /api/v1/manifests/{id}**
- Response: Single `ComponentManifest`

### 3.2 Action Endpoints

**POST /api/v1/components/{id}/actions/{action_id}**
- Authentication: Required (Bearer token)
- Body: `ActionExecutionRequest`
- Response: `ActionExecutionResponse`
- Example:
```json
POST /api/v1/components/litellm/actions/restart
Content-Type: application/json
Authorization: Bearer abc123...

{
  "component_id": "litellm",
  "action_id": "restart"
}

Response:
{
  "success": true,
  "message": "Restart command sent to audia-litellm container",
  "execution_id": "exec-20260327-abc123",
  "started_at": "2026-03-27T10:30:45Z",
  "completed": false
}
```

### 3.3 Config Endpoints

**GET /api/v1/config/diff**
- Authentication: Optional
- Response: `ConfigDiffResponse`

**POST /api/v1/config/reload**
- Authentication: Required
- Response: `ActionExecutionResponse`

### 3.4 Logs Endpoint (SSE)

**GET /api/v1/logs/{id}**
- Authentication: Required
- Response: Server-Sent Events stream
- Example:
```
data: {"timestamp": "2026-03-27T10:30:45Z", "level": "INFO", "message": "Starting..."}

data: {"timestamp": "2026-03-27T10:30:46Z", "level": "INFO", "message": "Ready"}

:keep-alive
```

### 3.5 Models Endpoint

**GET /api/v1/models/catalog**
- Authentication: Optional
- Response: `ModelsCatalogResponse`

---

## 4. Configuration Sources & Flow

### 4.1 Environment Variable Export

**File:** `src/dashboard/manifest_loader.py` → `export_stack_env_vars()`

```python
def export_stack_env_vars(root: Path) -> None:
    """Export stack config as environment variables for manifest resolution."""
    stack = load_stack_config(root)

    # From network.services.*
    os.environ.setdefault("LITELLM_HOST", stack.services.litellm.host)
    os.environ.setdefault("LITELLM_PORT", str(stack.services.litellm.port))

    os.environ.setdefault("LLAMASWAP_HOST", stack.services.llamaswap.host)
    os.environ.setdefault("LLAMASWAP_PORT", str(stack.services.llamaswap.port))

    os.environ.setdefault("VLLM_HOST", stack.services.vllm.host)
    os.environ.setdefault("VLLM_PORT", str(stack.services.vllm.port))

    # From llama-swap specific config
    os.environ.setdefault("LLAMASWAP_START_PORT", "41000")
    os.environ.setdefault("LLAMASWAP_END_PORT", "41099")
```

### 4.2 Manifest Loading

**File:** `src/dashboard/manifest_loader.py` → `load_manifests()`

```python
class ManifestLoader:
    """Load and merge project + local manifests with env var resolution."""

    def __init__(self, root: Path):
        self.root = root
        self.project_dir = root / "config" / "monitoring"
        self.local_dir = root / "config" / "local" / "monitoring"

    def load_manifests(self) -> Dict[str, ComponentManifest]:
        """Load all enabled manifests."""
        # 1. Export stack config as env vars
        export_stack_env_vars(self.root)

        # 2. Load project manifests
        project_manifests = self._load_dir(self.project_dir)

        # 3. Load local overrides
        local_manifests = self._load_dir(self.local_dir)

        # 4. Merge (local overrides project)
        merged = self._merge_manifests(project_manifests, local_manifests)

        # 5. Resolve ${VAR:-default} in each manifest
        resolved = {
            id: self._resolve_env_vars(manifest)
            for id, manifest in merged.items()
        }

        # 6. Filter enabled manifests
        return {id: m for id, m in resolved.items() if m.enabled}

    def _resolve_env_vars(self, manifest: ComponentManifest) -> ComponentManifest:
        """Replace ${VAR:-default} with actual values from environment."""
        # Resolve connection.host and connection.port
        host = self._resolve_string(manifest.connection.host)
        port = int(self._resolve_string(str(manifest.connection.port)))

        manifest.connection.host = host
        manifest.connection.port = port

        return manifest

    def _resolve_string(self, value: str) -> str:
        """Resolve ${VAR:-default} pattern."""
        import re
        pattern = r'\$\{([A-Z_]+)(?::-([^}]*))?\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2)
            return os.environ.get(var_name, default or '')

        return re.sub(pattern, replace, value)
```

---

## 5. Dependency Injection & Decoupling

### 5.1 FastAPI Dependency Pattern

**File:** `src/dashboard/main.py`

```python
from fastapi import FastAPI, Depends
from typing import Annotated

# Dependency functions (Dependency Injection)
async def get_manifest_loader() -> ManifestLoader:
    return ManifestLoader(GATEWAY_ROOT)

async def get_manifests(loader: Annotated[ManifestLoader, Depends(get_manifest_loader)]):
    return loader.load_manifests()

async def get_docker_handler() -> DockerActionHandler:
    return DockerActionHandler()

# In routers
@router.post("/components/{id}/actions/{action_id}")
async def execute_action(
    id: str,
    action_id: str,
    handler: Annotated[DockerActionHandler, Depends(get_docker_handler)],
    manifests: Annotated[Dict, Depends(get_manifests)]
):
    manifest = manifests[id]
    action = next((a for a in manifest.actions if a.id == action_id), None)
    if not action:
        raise HTTPException(404, "Action not found")

    executor = ActionRunner(handler)
    return await executor.execute(manifest, action)
```

### 5.2 Vue Store (Pinia) for Decoupling

**File:** `src/dashboard/ui/src/stores/metricsStore.ts`

```typescript
import { defineStore } from 'pinia'

// All components depend on ONE store, not directly on API
export const useMetricsStore = defineStore('metrics', {
  state: () => ({
    metrics: new Map<string, number>(),
    labels: new Map<string, Record<string, string>>(),
    lastUpdate: 0,
    isLoading: false,
    error: null as string | null,
  }),

  getters: {
    getValue: (state) => (metric: string) => {
      return state.metrics.get(metric)
    },

    getComponentStatus: (state) => (componentId: string) => {
      const upValue = state.metrics.get(`gateway_component_up{component="${componentId}"}`)
      return upValue === 1 ? 'up' : 'down'
    },
  },

  actions: {
    async pollMetrics() {
      this.isLoading = true
      try {
        const queries = [
          'gateway_component_up',
          'gateway_llamacpp_prompt_tokens_total{model_name="active"}',
          // ... all metrics
        ]

        const results = await prometheusClient.queryBatch(queries)
        results.forEach(r => {
          const key = `${r.metric}${JSON.stringify(r.labels)}`
          this.metrics.set(key, parseFloat(r.value))
          this.labels.set(key, r.labels)
        })

        this.lastUpdate = Date.now()
        this.error = null
      } catch (e) {
        this.error = e.message
      } finally {
        this.isLoading = false
      }
    }
  }
})

// ComponentCard doesn't care HOW data is fetched, just reads from store
```

---

## 6. Module Responsibilities

### 6.1 Manifest Loader (manifest_loader.py)

**Responsibilities:**
- Load YAML from `config/monitoring/` and `config/local/monitoring/`
- Merge project + local manifests
- Resolve `${VAR:-default}` using exported environment variables
- Validate against Pydantic schema
- Return clean, ready-to-use manifests

**Does NOT:**
- Make HTTP requests
- Talk to Prometheus
- Execute actions
- Cache results (always fresh from disk)

**Testing:**
- Test manifest loading from YAML
- Test merge logic (local overrides project)
- Test env var resolution
- Test validation errors
- Test missing files gracefully

### 6.2 Docker Handler (docker_handler.py)

**Responsibilities:**
- Connect to Docker socket (`/var/run/docker.sock`)
- Execute container restart commands
- Return success/failure + details

**Does NOT:**
- Make HTTP requests to components
- Modify any config files
- Start new containers
- Handle error recovery

**Testing:**
- Mock docker.Client
- Test restart with real container names
- Test error cases (container not found, socket unavailable)
- Test socket permission errors

### 6.3 Action Runner (action_runner.py)

**Responsibilities:**
- Dispatch action execution to appropriate handler
- Coordinate docker_restart, http_post, config_reload, shell
- Return execution status + results

**Does NOT:**
- Know implementation details of each action type
- Modify components directly

**Testing:**
- Test each action type dispatcher
- Test error handling + rollback
- Test concurrent action execution

### 6.4 Prometheus Client (prometheus_client.py)

**Responsibilities:**
- Query Prometheus HTTP API `/api/v1/query`
- Batch multiple queries into single call
- Parse responses into typed models
- Handle connection errors gracefully

**Does NOT:**
- Write to Prometheus
- Store state
- Start Prometheus

**Testing:**
- Mock HTTP responses
- Test query parsing
- Test error handling

### 6.5 Vue Prometheus Client (prometheusClient.ts)

**Responsibilities:**
- Query `/dashboard/prometheus/api/v1/query`
- Parse responses into MetricSnapshot[]
- Handle network errors

**Does NOT:**
- Store state (that's Pinia store job)
- Format metric values (utils do that)

### 6.6 Pinia Store (metricsStore.ts)

**Responsibilities:**
- Hold metric state
- Expose getters for components
- Poll Prometheus on timer
- Auto-update all components

**Does NOT:**
- Know component details
- Format values for display
- Know about actions

---

## 7. Testing Strategy Per Module

### 7.1 Unit Tests

**manifest_loader.py**
```python
def test_load_manifests_from_yaml():
    """Load manifests from YAML files."""
    loader = ManifestLoader(TEST_ROOT)
    manifests = loader.load_manifests()
    assert "litellm" in manifests
    assert manifests["litellm"].display_name == "LiteLLM Gateway"

def test_env_var_resolution():
    """${VAR:-default} resolves correctly."""
    os.environ["TEST_PORT"] = "1234"
    loader = ManifestLoader(TEST_ROOT)
    manifest = loader.load_manifests()["test_component"]
    assert manifest.connection.port == 1234

def test_no_hardcoded_ports():
    """Verify no hardcoded port numbers in dashboard code."""
    # Grep src/dashboard for numeric ports
    results = grep_code(r':\s*\d{4,5}', 'src/dashboard')
    # All matches should be in defaults: ${VAR:-DEFAULT}
    assert all(is_env_var_default(r) for r in results)

def test_components_independent():
    """Dashboard doesn't require components to run."""
    # Verify dashboard starts without components
    dashboard.start(mock_prometheus=True)
    assert dashboard.is_healthy()
    # Verify no component configs were modified
    assert not any_file_modified("config/project/")
```

### 7.2 Integration Tests

**test_manifest_api.py**
```python
async def test_get_manifests_endpoint():
    """GET /api/v1/manifests returns loaded manifests."""
    client = TestClient(app)
    response = client.get("/api/v1/manifests")
    assert response.status_code == 200
    data = response.json()
    assert len(data["components"]) > 0
    assert "litellm" in {c["id"] for c in data["components"]}

async def test_action_execution():
    """POST /api/v1/components/{id}/actions/{action_id} works."""
    client = TestClient(app)
    # Mock docker handler
    response = client.post(
        "/api/v1/components/litellm/actions/restart",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] == True
```

### 7.3 E2E Tests

**test_independence.py**
```python
def test_components_work_standalone():
    """Components function without dashboard service."""
    docker_compose_up("audia-litellm", "audia-llama-cpp")

    assert litellm_health_check()
    assert llamaswap_health_check()
    assert dashboard_not_running()

def test_dashboard_read_only():
    """Dashboard doesn't modify component configs."""
    before = read_file("config/local/litellm.yaml")

    dashboard.start()

    after = read_file("config/local/litellm.yaml")
    assert before == after
```

---

## 8. Build & Deployment

### 8.1 Python Backend Build

**Dockerfile**
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements-dashboard.txt .
RUN pip install -r requirements-dashboard.txt --target /build/deps

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /build/deps /app/deps
ENV PYTHONPATH=/app/deps:$PYTHONPATH

COPY src/dashboard/ ./src/dashboard/
COPY config/monitoring/ ./config/monitoring/
COPY config/local/monitoring/ ./config/local/monitoring/

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:4100/healthz')"

CMD ["uvicorn", "src.dashboard.main:app", "--host", "0.0.0.0", "--port", "4100"]
```

**requirements-dashboard.txt**
```
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.0.0
python-multipart==0.0.6
pyyaml==6.0
requests==2.31.0
docker==7.0.0
```

### 8.2 Vue Frontend Build

**vite.config.ts**
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../static',  // Output to src/dashboard/static/
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'pinia'],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:4100',
      '/dashboard/prometheus': 'http://localhost:9090',
    },
  },
})
```

**package.json**
```json
{
  "name": "audia-dashboard-ui",
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "vue-tsc": "^1.8.0",
    "@vue/test-utils": "^2.4.0",
    "vitest": "^1.0.0",
    "tailwindcss": "^3.3.0"
  }
}
```

---

## 9. Documentation Standards

### 9.1 Code Documentation

**File:** `src/dashboard/manifest_loader.py`

```python
"""
Manifest Loader Module

Responsible for loading and resolving component manifests from YAML files.
Manifests define how each component (LiteLLM, llama-swap, vLLM) is monitored
and controlled by the dashboard.

Configuration Resolution:
  1. Load stack.base.yaml (authoritative service definitions)
  2. Export network settings as environment variables
  3. Load config/monitoring/*.yaml (project manifests)
  4. Load config/local/monitoring/*.yaml (local overrides)
  5. Merge: local overrides project
  6. Resolve ${VAR:-default} patterns using exported env vars
  7. Validate against Pydantic schema
  8. Return enabled manifests

Key Principle:
  - Do NOT modify component configs (read-only)
  - Do NOT hardcode ports/hosts (use environment variables)
  - Do NOT duplicate config from stack.yaml

Example:
  loader = ManifestLoader(Path("/app"))
  manifests = loader.load_manifests()
  litellm = manifests["litellm"]
  await healthcheck(litellm.connection.host, litellm.connection.port)
"""
```

### 9.2 API Documentation

**FastAPI Automatically generates OpenAPI docs at `/api/docs`**

All endpoints documented with:
- Summary
- Description
- Parameter types + examples
- Response schema
- Error codes

```python
@router.post(
    "/components/{component_id}/actions/{action_id}",
    response_model=ActionExecutionResponse,
    tags=["Actions"],
    summary="Execute component action",
    description="""Execute an action on a monitored component (restart, reload config, etc).

Action types:
- docker_restart: Restart the container
- http_post: POST to component endpoint
- config_reload: Regenerate configs and restart services
- shell: Run a function from process_manager.py
- process_signal: Send a signal to a process

Requires DASHBOARD_API_KEY authorization."""
)
async def execute_action(...):
    ...
```

### 9.3 TypeScript Documentation

```typescript
/**
 * Prometheus query client for fetching metrics from /dashboard/prometheus/api/v1/query
 *
 * Usage:
 *   const client = new PrometheusClient(baseURL)
 *   const results = await client.query("gateway_component_up")
 *   results.forEach(r => console.log(r.metric, r.value))
 */
export class PrometheusClient {
  /**
   * Query Prometheus with a PromQL expression
   * @param query PromQL expression (e.g., "gateway_component_up{component=\"litellm\"}")
   * @returns Array of metric results with parsed numeric values
   * @throws PrometheusError if query fails
   */
  async query(query: string): Promise<MetricSnapshot[]> {
    ...
  }
}
```

### 9.4 Configuration Documentation

**File:** `config/monitoring/litellm.yaml`

```yaml
# LiteLLM Gateway Component Manifest
#
# This manifest tells the dashboard HOW to:
# 1. Check if LiteLLM is healthy (health probe)
# 2. Scrape metrics from LiteLLM (metrics extraction)
# 3. Control LiteLLM (restart, reload config)
# 4. Display LiteLLM status (card layout)
#
# What this file DOES NOT define:
# - Service host/port (defined in config/project/stack.base.yaml, exported as env vars)
# - Docker image (defined in docker/compose/docker-compose.yml)
# - Model definitions (defined in LiteLLM config)
#
# Configuration Sources:
#   Host/Port:  ${LITELLM_HOST:-127.0.0.1}  ← from stack.yaml export
#   Container:  audia-litellm               ← from docker/compose/docker-compose.yml
#   API Key:    ${LITELLM_MASTER_KEY}       ← from .env
#
# Do NOT hardcode or duplicate these values.
```

---

## Final Notes

This implementation guide ensures:

✅ **Complete Decoupling:** Dashboard independent of components
✅ **No Config Duplication:** Single source of truth
✅ **Modularity:** Clear responsibility boundaries
✅ **Testability:** Easy to mock and unit test
✅ **Maintainability:** Clear documentation + patterns
✅ **Extensibility:** New components = one manifest file

All code should follow these principles during Phase 1-4 implementation and code review.
