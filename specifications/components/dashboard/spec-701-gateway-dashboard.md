# Spec 701 — LLM Gateway Dashboard & Control Panel

**Status:** Draft
**Covers:** Gateway-wide status dashboard, component monitoring, model management, operational controls
**Related specs:** spec-001 (architecture), spec-401 (nginx), spec-201 (llama-swap), spec-301 (litellm), spec-251 (vllm)

---

## 1. Goals

| Goal | Detail |
|------|--------|
| Single-pane visibility | See all gateway components and their live health at a glance |
| Model awareness | Show which models are currently loaded in llama-swap and vLLM, with memory/GPU context |
| Operational control | Trigger component reloads, config regeneration, model load/unload without SSH |
| Manifest-driven plugins | Adding a new component to monitor requires only a YAML manifest — no Go, Python, or Vue code |
| AUDiot integration | Time-series metrics flow into Prometheus → Grafana via the existing AUDiotMonitor stack |
| Served via existing nginx | Hosted at `/dashboard/` behind the gateway's nginx on port 8080 |

---

## 2. Architecture Overview

```
  ┌─────────────────────────────────────────────────────┐
  │  AUDiotMonitor                                       │
  │                                                      │
  │  hwexp manifest adapter                              │
  │    └─> polls health + metrics from manifests         │
  │          └─> Prometheus (:9090)                      │
  │                ├─> Grafana (:3000)  ← PRIMARY DISPLAY│
  │                └─> Control Panel UI (reads state)    │
  └─────────────────────────────────────────────────────┘
                             │ Prometheus HTTP API
  ┌────────────────────────────────────────────────┐
  │  AUDiaLLMGateway nginx :8080                   │
  │                                                │
  │  /dashboard/          ← Control Panel SPA      │
  │  /dashboard/api/      ← FastAPI :4100          │
  │  /dashboard/prometheus/ ← proxied to Prometheus│
  │  /llamaswap/ui/       ← llama-swap UI          │
  │  /ui/                 ← LiteLLM UI             │
  │  /v1/                 ← LiteLLM API            │
  └────────────────────────────────────────────────┘

  Component manifests (shared by both projects)
    config/monitoring/*.yaml
```

### Strict layer responsibilities

| Layer | Reads | Writes | Tool |
| --- | --- | --- | --- |
| **Data emission** | component endpoints | Prometheus TSDB | hwexp manifest adapter |
| **Display / dashboards** | Prometheus | — | Grafana |
| **Control plane API** | manifests (actions only) | component restart/reload APIs | FastAPI |
| **Control panel UI** | Prometheus HTTP API (for state) | FastAPI (for actions) | Vue3 SPA |

**Prometheus is the single source of truth for all component state.**
The FastAPI service does not poll components and does not duplicate hwexp's work.
The Vue SPA reads current state (health, active model, metric values) from Prometheus,
and calls FastAPI only when the user triggers an action.

### What each layer owns

**Grafana** is the primary dashboard. It displays all time-series data, component
health history, model state, GPU correlation, and alerting. Users who need to
observe the system use Grafana.

**Control panel** (`/dashboard/`) is the operational interface for users who need
to act on the system — restart a component, swap a model, reload config. It shows
just enough current state (sourced from Prometheus) to make those actions
contextually meaningful, then hands off to FastAPI for execution.

**The two are independent.** The control panel does not require Grafana; Grafana
does not require the control panel. Both require Prometheus (via AUDiotMonitor).

---

## 3. Dashboard Framework Selection

### 3.1 Frontend: Vue 3 + Vite + Tailwind CSS

**Rationale:**
- Component-based: each gateway component maps to a Vue component card
- No build-time server dependency; output is static HTML/JS/CSS nginx can serve directly
- Tailwind enables dense, information-rich layouts without a heavyweight component library
- Generic `ComponentCard` renders any manifest without per-component Vue code

**Rejected alternatives:**
- **Grafana only** — no write/action support; cannot trigger reloads or model swaps
- **React** — larger ecosystem overhead for an internal tool of this size
- **HTMX + Jinja2** — simpler but less composable; adding new cards requires template changes
- **Homepage / Dashy** — preconfigured homelab dashboards; insufficient control-plane hooks
- **Appsmith / Retool** — overweight for a self-hosted component; external dependency

### 3.2 Backend: FastAPI (Python)

**Rationale:**
- Same language as `config_loader.py`, `process_manager.py`, `health.py` — shared imports
- Auto-generates OpenAPI docs; the Vue frontend can use typed client stubs
- `process_manager.py` functions callable directly (no subprocess shelling)
- Async support for SSE (Server-Sent Events) push for live status updates
- Manifest files loaded at startup; new components registered without code changes

### 3.3 Metrics: Prometheus + Grafana (via AUDiotMonitor)

The AUDiotMonitor hwexp stack already scrapes hardware metrics. The generic manifest
adapter means gateway health flows into the same Prometheus instance, enabling
correlated dashboards (GPU temperature next to inference latency). Adding a new
component to Grafana only requires a new manifest file.

---

## 4. Manifest-Driven Plugin System

### 4.1 Design Principle

Every component (existing or future) is described by a single YAML manifest file.
Each layer reads only the sections it owns:

| Layer | Manifest sections consumed | Does NOT read |
| --- | --- | --- |
| **hwexp** (Go) | `health`, `metrics[]`, `connection` | `actions`, `card` |
| **FastAPI** (Python) | `actions[]`, `connection`, `id` | `health`, `metrics`, `card` |
| **Vue SPA** | `card`, `actions[]` (for button labels/confirm text) | all polling concerns |

`health` and `metrics` are exclusively a data-emission concern (hwexp → Prometheus).
`actions` are exclusively a control concern (FastAPI execution, Vue rendering).
`card` is exclusively a display concern (Vue layout hints).

Adding Ollama, Open WebUI, or any future service requires **only a new manifest file**.
No Go code, no Python code, no Vue code.

### 4.2 Manifest Schema

Location: `config/monitoring/<id>.yaml`
User overrides: `config/local/monitoring/<id>.yaml` (merged on top, same keys)

**Dynamic Port Discovery:** All connection settings use environment variable references
that resolve from the authoritative stack configuration (`stack.base.yaml` and
`stack.override.yaml`). Ports are NOT duplicated in manifests.

```yaml
# ── Identity ────────────────────────────────────────────────────────────────
id: llamaswap               # machine identifier; used in API paths and metric labels
display_name: llama-swap    # shown in the UI
icon: server                # icon key (maps to icon set in the SPA)
enabled: true               # false = shown as "disabled", not polled

# ── Connection (resolved from stack config via environment variables) ────────
connection:
  host: ${LLAMA_SWAP_HOST:-127.0.0.1}    # Resolved from network.services.llama_swap.host
  port: ${LLAMA_SWAP_PORT:-41080}        # Resolved from network.services.llama_swap.port
  auth:
    type: none

# ── Health probe ─────────────────────────────────────────────────────────────
health:
  endpoint: /health         # GET this path on the component's host:port
  method: GET               # GET | HEAD
  expect_status: 200        # HTTP status that means "healthy"
  timeout_s: 3
  # Optional: extract a field from the JSON response body to surface as status detail
  status_field: ".status"   # jq-style path; value shown as sub-status string
```

### 4.2.1 Environment Variable Resolution

Manifest loader resolves `${VAR_NAME:-default}` syntax at runtime:

| Component | Host Variable | Port Variable | Source in `stack.base.yaml` |
|-----------|---------------|---------------|----------------------------|
| LiteLLM | `LITELLM_HOST` | `LITELLM_PORT` | `network.services.litellm.host/port` |
| llama-swap | `LLAMA_SWAP_HOST` | `LLAMA_SWAP_PORT` | `network.services.llama_swap.host/port` |
| vLLM | `VLLM_HOST` | `VLLM_PORT` | `network.services.vllm.host/port` |

**Default values** in manifests are fallbacks only. In production, the manifest
loader exports these from the stack config before passing to hwexp/FastAPI.

# ── Metrics (polled and emitted as RawMeasurements for Prometheus) ───────────
metrics:
  - id: models_loaded
    endpoint: /v1/models
    extract: ".data | length"          # jq expression applied to JSON response body
    prometheus_name: gateway_llamaswap_models_loaded
    unit: count
    poll_interval_s: 15

  - id: active_model
    endpoint: /v1/models
    extract: '.data[0].id // "none"'
    prometheus_name: gateway_llamaswap_active_model
    unit: label                        # label-type: emitted as info metric, not gauge
    poll_interval_s: 15

  - id: vram_used_bytes
    endpoint: /metrics                 # prometheus text format endpoint (if available)
    extract: "llama_kv_cache_usage_ratio"  # metric name to pull from prom text
    prometheus_name: gateway_llamaswap_vram_ratio
    unit: ratio
    poll_interval_s: 30
    source_format: prometheus          # json (default) | prometheus

# ── Actions (rendered as buttons in the control panel) ───────────────────────
actions:
  - id: restart
    label: Restart
    type: docker_restart               # docker_restart | http_post | process_signal | config_reload
    container: audia-llama             # for docker_restart
    confirm: false

  - id: reload_config
    label: Reload Config
    type: config_reload                # runs config_loader generate-configs then restarts
    confirm: true
    confirm_message: "Reload llama-swap config and restart?"

  - id: unload_model
    label: Unload Model
    type: http_post
    endpoint: /v1/unload
    body: {}
    confirm: false

# ── Card display ─────────────────────────────────────────────────────────────
card:
  port: 41080                          # shown as port badge
  extra_fields:                        # additional rows shown below standard health/uptime
    - label: Active Model
      metric: active_model             # references metrics[].id above
    - label: Models Available
      metric: models_loaded
  links:                               # quick-link buttons on the card
    - label: UI
      path: /llamaswap/ui/
    - label: API
      path: /llamaswap/v1/models

# ── Connection (how hwexp and FastAPI reach this component) ──────────────────
connection:
  host: ${LLAMA_SWAP_HOST:-127.0.0.1}   # overridden in Docker by service hostname
  port: ${LLAMA_SWAP_PORT:-41080}
  auth:
    type: none                         # none | bearer | basic
    # token_env: LLAMASWAP_TOKEN       # env var holding the bearer token (if bearer)
```

### 4.2.2 Dynamic llama.cpp Port Discovery

llama-swap starts llama.cpp instances on dynamic ports. The manifest does NOT
hardcode these ports. Instead, the hwexp adapter:

1. **Queries llama-swap** at `${LLAMA_SWAP_HOST}:${LLAMA_SWAP_PORT}/v1/models`
2. **Extracts port mapping** from the response (each model reports its backend port)
3. **Scrapes `/metrics`** from each discovered llama.cpp instance
4. **Labels metrics** with `model_name` for aggregation

```yaml
# In llamaswap.yaml - port range from stack config, not hardcoded
llama_cpp_backends:
  port_range:
    start: ${LLAMA_SWAP_START_PORT:-41000}   # From llama-swap.base.yaml startPort
    end: ${LLAMA_SWAP_END_PORT:-41099}       # startPort + 99
```

**Authoritative source:** `config/project/llama-swap.base.yaml` defines `startPort`.
The manifest references it via environment variable, set by the manifest loader.

### 4.3 Built-in Action Types

| `type` | What it does | Required fields |
| --- | --- | --- |
| `docker_restart` | `docker compose restart <container>` | `container` |
| `http_post` | POST to `connection.host:port/<endpoint>` | `endpoint`, `body` |
| `process_signal` | Send SIGHUP/SIGTERM to PID from `.runtime/services/<id>.pid` | `signal` |
| `config_reload` | Run `config_loader.py generate-configs`, restart affected containers | — |
| `shell` | Run a named command from `process_manager.py` | `command` |

### 4.4 Bundled Manifests

Shipped in `config/monitoring/`:

```
config/monitoring/
  litellm.yaml
  llamaswap.yaml
  vllm.yaml          ← enabled: false by default
```

User additions go in `config/local/monitoring/`:
```
config/local/monitoring/
  ollama.yaml        ← user adds Ollama; no project files modified
  open_webui.yaml
```

### 4.5 Manifest Merge Rules

Local overrides are shallow-merged on top of project manifests at load time:

- Scalar fields: local value wins
- `metrics[]` and `actions[]`: merged by `id`; local entry replaces matching project entry
- `card.extra_fields` and `card.links`: local list appended after project list
- `enabled: false` in local always wins (safety gate)

### 4.6 Example: Adding Ollama Without Any Code Changes

Create `config/local/monitoring/ollama.yaml`:

```yaml
id: ollama
display_name: Ollama
icon: brain
enabled: true

health:
  endpoint: /api/version
  expect_status: 200

metrics:
  - id: models_loaded
    endpoint: /api/tags
    extract: ".models | length"
    prometheus_name: gateway_ollama_models_loaded
    unit: count
    poll_interval_s: 30

actions:
  - id: restart
    label: Restart
    type: docker_restart
    container: ollama
    confirm: false

card:
  port: ${OLLAMA_PORT:-11434}
  extra_fields:
    - label: Models Available
      metric: models_loaded
  links:
    - label: API
      path: /api/tags

connection:
  host: ${OLLAMA_HOST:-127.0.0.1}
  port: ${OLLAMA_PORT:-11434}
```

Restart the dashboard service. Ollama appears as a component card with its metric
polled and exposed to Prometheus. No other files change.

---

## 5. Control Plane API — New Service (`src/dashboard/`)

The FastAPI service is a **write-only control plane**. It does not poll components,
does not maintain health state, and does not duplicate any data that hwexp already
emits to Prometheus. Its only job is to execute actions defined in manifests.

### 5.1 Directory Layout

```
src/dashboard/
  main.py                    ← FastAPI app; loads manifests at startup
  manifest_loader.py         ← reads + merges config/monitoring/ + config/local/monitoring/
  routers/
    components.py            ← POST /api/v1/components/{id}/actions/{action_id}
    config.py                ← POST /api/v1/config/reload, GET /api/v1/config/diff
    logs.py                  ← GET  /api/v1/logs/{id}  (SSE stream)
    manifests.py             ← GET  /api/v1/manifests  (card layout + action metadata for SPA)
  action_runner.py           ← dispatches action types (docker_restart, http_post, etc.)
  services/
    gateway_config.py        ← reads config layers (models catalog, stack config)
  ui/                        ← Vue3 SPA source
    src/
      components/
        ComponentCard.vue    ← generic card; state from Prometheus, actions from FastAPI
        ModelPanel.vue
        LogDrawer.vue
      prometheus.ts          ← typed Prometheus HTTP API client
      manifest.ts            ← TypeScript types matching manifest schema
      cards.ts               ← (optional) custom card overrides by component id
    package.json
    vite.config.ts
  static/                    ← built SPA output (generated by npm run build)
  Dockerfile
```

`health_poller.py` does not exist. There is no `/status` endpoint. State comes
from Prometheus.

### 5.2 FastAPI Startup

```python
# main.py (sketch)
from manifest_loader import load_manifests

app = FastAPI()
manifests = load_manifests(
    project_dir="config/monitoring",
    local_dir="config/local/monitoring",
)

# Only action-related routers. No health polling, no status aggregation.
app.include_router(components_router(manifests))   # POST actions
app.include_router(manifests_router(manifests))    # GET layout metadata for SPA
app.include_router(config_router())
app.include_router(logs_router(manifests))
```

### 5.2.1 Environment Variable Export

The `manifest_loader.py` exports environment variables from the stack configuration
before loading manifests:

```python
# manifest_loader.py (sketch)
import os
from pathlib import Path
from ..launcher.config_loader import load_stack_config

def export_stack_env_vars(root: Path) -> None:
    """Export network settings from stack config as environment variables."""
    stack = load_stack_config(root)

    # Export network settings for manifest ${VAR} resolution
    os.environ.setdefault("LITELLM_HOST", stack.litellm.host)
    os.environ.setdefault("LITELLM_PORT", str(stack.litellm.port))

    os.environ.setdefault("LLAMA_SWAP_HOST", stack.llama_swap.host)
    os.environ.setdefault("LLAMA_SWAP_PORT", str(stack.llama_swap.port))

    os.environ.setdefault("VLLM_HOST", stack.vllm.host)
    os.environ.setdefault("VLLM_PORT", str(stack.vllm.port))

    # llama.cpp backend port range from llama-swap config
    os.environ.setdefault("LLAMA_SWAP_START_PORT", "41000")  # from llama-swap.base.yaml
    os.environ.setdefault("LLAMA_SWAP_END_PORT", "41099")
```

This ensures manifests reference the **authoritative port configuration** from
`stack.base.yaml` and `stack.override.yaml` without duplication.

### 5.3 API Endpoints

All endpoints prefixed `/dashboard/api/v1/`.

#### Manifests (layout metadata for the SPA)

The SPA calls this once at startup to know which components exist, what cards to
render, and what action buttons to show. State values (health, metrics) come from
Prometheus — not from this endpoint.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/manifests` | All enabled manifests: `id`, `display_name`, `icon`, `card`, `actions[]` |
| `GET` | `/manifests/{id}` | Single component manifest (card layout + actions only) |

#### Actions

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/components/{id}/actions/{action_id}` | Execute a manifest-defined action |

`{id}` and `{action_id}` are dynamic — resolved from loaded manifests at startup.

#### Config

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/config/reload` | Re-runs `config_loader.py generate-configs`, restarts affected services |
| `GET` | `/config/diff` | Shows what generated configs would change without applying |

#### Logs

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/logs/{id}` | SSE: last 200 lines + live tail of component log |

Log streaming is kept here (not in Prometheus) because logs are not metrics — they
are operational output that Prometheus does not store.

#### Models catalog

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/models/catalog` | Model catalog from `config/local/models.override.yaml` |

This is a config file read, not a component poll. The list of *loaded* models is
read by the SPA directly from Prometheus (`gateway_model_loaded` metric).

### 5.4 Authorization

Bearer token from `.env` `DASHBOARD_API_KEY`. Vue SPA reads it from
`/dashboard/config.json` served by nginx (not bundled in SPA).

All write endpoints (`POST`) require the token. `GET /manifests` and
`GET /models/catalog` are open (no secrets, no state).

---

## 6. Frontend — Vue 3 Control Panel SPA

The SPA is an **action panel**, not a monitoring dashboard. Grafana handles all
historical and time-series display. The SPA shows just enough current state to
make actions contextually useful, sourcing that state from Prometheus.

### 6.1 Build Output

```
config/generated/nginx/dashboard/   ← nginx serves at /dashboard/
```

### 6.2 Data Sources

The SPA talks to two backends:

| What | Source | How |
| --- | --- | --- |
| Component layout, action buttons | FastAPI `/manifests` | Fetched once at startup |
| Current health, metric values | Prometheus HTTP API | Queried on load + polled every 15 s |
| Log output | FastAPI `/logs/{id}` SSE | Opened on demand per component |
| Action execution | FastAPI `/components/{id}/actions/{action_id}` | POST on user interaction |

Prometheus is proxied through nginx at `/dashboard/prometheus/` to avoid CORS
issues (`proxy_pass http://prometheus:9090`).

Example Prometheus queries the SPA uses:

```
gateway_component_up{component="llamaswap"}
gateway_llamaswap_active_model         ← info metric; label value is the model name
gateway_llamaswap_models_loaded
gateway_model_vram_bytes
```

### 6.3 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  AUDia LLM Gateway Control Panel         [Grafana ↗]        │
├─────────────────────────────────────────────────────────────┤
│ COMPONENTS           (status from Prometheus)               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ LiteLLM  ●  │ │ llama-swap ● │ │  llama.cpp ● │  ...   │
│  │ :4000        │ │ active model │ │  :41008      │        │
│  │ [restart]    │ │ [restart]    │ │  [restart]   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
├─────────────────────────────────────────────────────────────┤
│ ACTIVE MODELS        (loaded state from Prometheus)         │
│  llama-swap: qwen3.5-27b  [VRAM: 18.2 GB]  [unload]       │
│  vLLM:       (disabled)                                     │
│  [load model ▾]                                             │
├─────────────────────────────────────────────────────────────┤
│ QUICK ACTIONS                                               │
│  [Reload All Configs]  [Restart Gateway]  [View Logs ▾]    │
└─────────────────────────────────────────────────────────────┘
```

A "Grafana ↗" link in the header navigates to the Grafana dashboard for full
monitoring and historical views. The control panel makes no attempt to replicate
those panels.

### 6.4 Generic ComponentCard

`ComponentCard.vue` is driven by two inputs: the manifest (from FastAPI `/manifests`,
fetched once) and the current metric snapshot (from Prometheus, polled):

```
props:
  manifest: ComponentManifest    ← card layout, action list, links
  metrics:  PrometheusSnapshot   ← current values keyed by metric id

renders:
  - display_name + icon (from manifest)
  - status dot (from gateway_component_up{component=id} in Prometheus)
  - extra_fields[] rows (label from manifest, value from metrics snapshot)
  - links[] buttons (from manifest card.links)
  - actions[] buttons (label/confirm from manifest; POST to FastAPI on click)
  - [Logs] toggle (opens LogDrawer → FastAPI SSE)
```

No component-specific Vue code for standard components.

### 6.5 Custom Card Overrides (Optional)

For components needing a richer layout beyond manifest card fields:

```ts
// cards.ts — only add entries for non-standard layouts
import VllmCard from './components/cards/VllmCard.vue'

export const cardOverrides: Record<string, Component> = {
  vllm: VllmCard,
}
```

The renderer checks `cardOverrides[id]` first; falls back to generic `ComponentCard`.

### 6.6 Prometheus Polling

The SPA polls Prometheus every 15 s using the HTTP API:

```http
GET /dashboard/prometheus/api/v1/query?query=<expr>
```

Queries are batched into a single `query_range` call where possible. On action
execution (e.g., restart), the SPA immediately re-queries the relevant metrics
after a 3 s delay to reflect the new state.

---

## 7. Monitoring Integration (AUDiotMonitor)

The monitoring layer — hwexp adapter, Prometheus metrics, and Grafana dashboard —
is specified and implemented in the AUDiotMonitor project.

See **[AUDiotMonitor spec-801](../../../../AUDiot/AUDiotMonitor/specifications/spec-801-llmgateway-monitor-adapter.md)**
for:

- `gateway_manifest` hwexp adapter (replaces the bare `llamaswap` adapter)
- Manifest `health` and `metrics` section consumption
- Prometheus metric names and `mappings.yaml` rules
- Grafana `AUDia LLM Gateway` dashboard layout

### Dependency from this project

The manifests defined here (`config/monitoring/*.yaml`) are the input
consumed by the AUDiotMonitor adapter. The `health`, `metrics`, and `connection`
sections of each manifest must be kept valid for the adapter to function.

The control panel SPA (§6) queries Prometheus at `/dashboard/prometheus/` to read
current component state. This requires the AUDiotMonitor collector stack to be
running and scraping the gateway host.

---

## 8. nginx Routing Additions

Config generator adds these blocks when `dashboard.enabled: true` in `stack.override.yaml`:

```nginx
# Dashboard SPA
location /dashboard/ {
    alias  /etc/nginx/dashboard/;
    try_files $uri $uri/ /dashboard/index.html;
}

# Dashboard control-plane API
location /dashboard/api/ {
    proxy_pass http://127.0.0.1:4100;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_request_buffering off;
}

# Prometheus proxy — allows the SPA to query Prometheus without CORS issues.
# Read-only: only /api/v1/query* paths are forwarded.
location /dashboard/prometheus/api/v1/ {
    proxy_pass http://127.0.0.1:9090/api/v1/;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    # Strip write paths — deny anything that isn't a query
    limit_except GET { deny all; }
}
```

---

## 9. Docker Integration

### 9.1 New Service: `audia-dashboard`

```yaml
# docker-compose.yml addition
audia-dashboard:
  build:
    context: .
    dockerfile: src/dashboard/Dockerfile
  container_name: audia-dashboard
  profiles: [dashboard, full]
  ports:
    - "127.0.0.1:4100:4100"
  volumes:
    - ./config/monitoring:/app/config/monitoring:ro
    - ./config/local/monitoring:/app/config/local/monitoring:ro
    - ./config/local:/app/config/local:ro
    - ./config/generated:/app/config/generated:ro
    - /var/run/docker.sock:/var/run/docker.sock:ro
  environment:
    GATEWAY_ROOT: /app
    DASHBOARD_API_KEY: ${DASHBOARD_API_KEY:-changeme}
    DASHBOARD_AUTH_READONLY: ${DASHBOARD_AUTH_READONLY:-true}
  depends_on:
    - audia-litellm
    - audia-nginx
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:4100/healthz"]
    interval: 30s
    timeout: 5s
    retries: 3
```

### 9.2 Multi-Stage Dockerfile

```dockerfile
FROM node:20-alpine AS ui-builder
WORKDIR /ui
COPY src/dashboard/ui/package*.json ./
RUN npm ci
COPY src/dashboard/ui/ ./
RUN npm run build -- --outDir /dist

FROM python:3.12-slim
WORKDIR /app
COPY requirements-dashboard.txt .
RUN pip install -r requirements-dashboard.txt
COPY src/dashboard/ ./src/dashboard/
COPY src/launcher/ ./src/launcher/
COPY --from=ui-builder /dist ./src/dashboard/static/
CMD ["uvicorn", "src.dashboard.main:app", "--host", "0.0.0.0", "--port", "4100"]
```

---

## 10. Delivery Phases

### 10.0 Prerequisites & Readiness Checklist

**Critical blocking dependencies:**

- [ ] **AUDiotMonitor spec-801 complete** — hwexp manifest adapter must exist and scrape gateway metrics before Vue SPA can be built. Without it, Prometheus has no data to display.
- [ ] **vLLM metrics enabled** — Verify `config/local/models.override.yaml` has `metrics: true` in all vLLM deployment profiles (parallel to llama.cpp's `metrics: true`)
- [ ] **Manifest files validated** — `config/monitoring/{litellm,llamaswap,vllm}.yaml` exist and pass YAML validation
- [ ] **Prometheus access** — Verify AUDiotMonitor stack is running and accessible; dashboard will proxy `/dashboard/prometheus/` to it

**Environmental setup (do first):**
1. Verify all three component manifests are syntactically valid
2. Check vLLM deployment in models.override.yaml (add metrics flag if missing)
3. Confirm AUDiotMonitor hwexp adapter spec is finalized
4. Test manifest loader locally: `python -c "from src.dashboard.manifest_loader import load_manifests; m = load_manifests(); print(len(m))"`

Prerequisite: AUDiotMonitor spec-801 must be complete before Phase 1 below,
as the SPA depends on Prometheus being populated by the hwexp adapter.

### Phase 1 — Read-only control panel

- [ ] Write bundled manifests: `config/monitoring/{litellm,llamaswap,vllm}.yaml`
- [ ] Implement `src/dashboard/manifest_loader.py` (merge logic, type validation)
- [ ] Scaffold FastAPI service: `/manifests` GET endpoint, `/models/catalog` GET endpoint
- [ ] Scaffold Vue3 SPA: `ComponentCard` (reads Prometheus for state), `ModelPanel`, `prometheus.ts` client
- [ ] Update `config_loader.py` to emit nginx blocks for `/dashboard/` and `/dashboard/prometheus/`
- [ ] Update `docker-compose.yml` with `dashboard` profile
- [ ] Add `/dashboard/` link to nginx `index.html`

**Outcome:** Control panel at `/dashboard/` shows all manifest-defined components with
live health and model state sourced from Prometheus. Grafana link in header.
Adding a new component = drop a YAML file, restart dashboard service.

### Phase 2 — Control plane actions

- [ ] Implement `src/dashboard/action_runner.py` (docker_restart, http_post, config_reload, shell types)
- [ ] Add `POST /components/{id}/actions/{action_id}` endpoint
- [ ] Add action buttons to `ComponentCard` (gated by `DASHBOARD_AUTH_READONLY`)
- [ ] Add model load/unload actions via manifest
- [ ] Add `GET /logs/{id}` SSE endpoint + log drawer in UI
- [ ] Add config reload button + diff preview

**Outcome:** Full operational control panel. New action types added to `action_runner.py`
are immediately available to any manifest that references them.

### Phase 3 — Extended (future)

- [ ] OTEL export from LiteLLM → Prometheus (per-request latency histograms)
- [ ] Model benchmark results panel (links to test runner output)
- [ ] Token budget / cost tracking
- [ ] Multi-host support (manifest `connection.host` pointing at remote gateway instances)

---

## 10.1 Metric Naming Convention & Universal Status

All Prometheus metrics emitted by this gateway follow a strict naming convention:

```promql
gateway_<component>_<metric_name>{<labels>}
```

**Component identifiers:** `litellm`, `llamaswap`, `llamacpp`, `vllm`, `nginx` (if monitored)

**Universal health metric (all components):**

```promql
gateway_component_up{component="<id>"}  → 1 (healthy) | 0 (down)
```

This allows aggregation queries like:

```promql
count(gateway_component_up == 1)  # How many components are up?
gateway_component_up{component="llamaswap"}  # Is llama-swap healthy?
```

All component-specific metrics follow the pattern:

- **LiteLLM:** `gateway_litellm_proxy_total_requests`, `gateway_litellm_llm_api_latency`, etc.
- **llama-swap router:** `gateway_llamaswap_models_loaded`, `gateway_llamaswap_active_model`
- **llama.cpp backends:** `gateway_llamacpp_prompt_tokens_total{model_name="qwen27b"}` (per-model)
  - Plus aggregate: `gateway_llamacpp_prompt_tokens_total{model_name="active"}` (sum of active models)
- **vLLM:** `gateway_vllm_num_requests_running`, `gateway_vllm_gpu_memory_usage_bytes`, etc.

**Special label value: `model_name="active"`**

For multi-model systems (llama-swap), aggregate metrics are emitted with `model_name="active"`:
```promql
# Per-model metrics (emitted only when model is active)
gateway_llamacpp_prompt_tokens_total{model_name="qwen27b"} 12500
gateway_llamacpp_prompt_tokens_total{model_name="llama70b"} 8300

# Aggregate metric (sum of all active models)
gateway_llamacpp_prompt_tokens_total{model_name="active"} 20800
```

Dashboard queries become simple:
```promql
gateway_llamacpp_prompt_tokens_total{model_name="active"}  # Total active throughput
sum(gateway_llamacpp_prompt_tokens_total)                   # Also works (includes active label)
```

This namespace isolation makes it easy to:

1. Filter dashboard by component: `{__name__=~"gateway_llamaswap.*"}`
2. Query aggregate metrics: `{model_name="active"}`
3. Create Grafana alerts per component or per model
4. Extend monitoring to new components without naming conflicts

---

## 10.2 Component Metrics Summary

The dashboard monitors **three core components** (nginx and postgres excluded):

| Component | Service Name | Metrics Source | Key Metrics |
|-----------|--------------|---------------|-------------|
| **LiteLLM Gateway** | `audia-litellm` | Native `/metrics` (Prometheus) | Requests, latency, tokens, spend, deployment health, rate limits, fallbacks |
| **llama-swap + llama.cpp** | `audia-llama` | `/v1/models` (JSON) + per-instance `/metrics` | Models loaded, KV cache, token throughput, request queue |
| **vLLM** | `audia-vllm` | Native `/metrics` (Prometheus) | GPU usage, memory, request queue, latency, KV cache, preemptions |

### llama-swap + llama.cpp Unified Model

llama-swap is the router; llama.cpp provides inference. They are monitored as a single logical component:

1. **llama-swap router** (port 41080): Polled for `/v1/models` to discover active models
2. **llama.cpp instances** (ports 41000-41099): Each model runs on a dynamic port with its own `/metrics` endpoint
3. **hwexp adapter** aggregates both into unified `gateway_llamaswap_*` and `gateway_llamacpp_*` metrics

**Required Configuration:** llama.cpp must be started with `--metrics` flag. Add to each model in `config/local/llama-swap.override.yaml`:

```yaml
models:
  qwen3.5-27b:
    cmd: |
      llama-server-rocm \
        --model /app/models/gguf/qwen3.5-27b-q4_k_m.gguf \
        --port 41001 \
        --metrics  # ← Required for Prometheus scraping
```

### Metric Categories by Component

**LiteLLM (40+ metrics):**
- Request tracking: `litellm_proxy_total_requests_metric`, `litellm_proxy_failed_requests_metric`
- Latency: `litellm_request_total_latency_metric`, `litellm_llm_api_latency_metric`, `litellm_llm_api_time_to_first_token_metric`
- Tokens: `litellm_total_tokens_metric`, `litellm_input_tokens_metric`, `litellm_output_tokens_metric`
- Spend: `litellm_spend_metric`
- Deployment health: `litellm_deployment_state`, `litellm_deployment_success_responses`, `litellm_deployment_failure_responses`
- Rate limits: `litellm_remaining_requests_metric`, `litellm_remaining_tokens_metric`
- Budgets: `litellm_api_key_max_budget_metric`, `litellm_remaining_api_key_budget_metric`, `litellm_team_max_budget_metric`
- System: `litellm_in_flight_requests`, `litellm_redis_latency`, `litellm_redis_fails`
- Fallbacks: `litellm_deployment_cooled_down`, `litellm_deployment_successful_fallbacks`, `litellm_deployment_failed_fallbacks`

**llama-swap + llama.cpp (15+ metrics):**
- Router: `gateway_llamaswap_models_loaded`, `gateway_llamaswap_active_model`, `gateway_llamaswap_health_status`
- Tokens: `llamacpp:prompt_tokens_total`, `llamacpp:tokens_predicted_total`
- Throughput: `llamacpp:prompt_tokens_seconds`, `llamacpp:predicted_tokens_seconds`
- KV Cache: `llamacpp:kv_cache_usage_ratio`, `llamacpp:kv_cache_tokens`
- Requests: `llamacpp:requests_processing`, `llamacpp:requests_deferred`

**vLLM (20+ metrics):**
- Requests: `vllm:num_requests_running`, `vllm:num_requests_waiting`
- Latency: `vllm:time_to_first_token_seconds`, `vllm:time_per_output_token_seconds`, `vllm:e2e_request_latency_seconds`
- Tokens: `vllm:request_prompt_tokens`, `vllm:request_generation_tokens`
- KV Cache: `vllm:gpu_cache_usage_perc`, `vllm:cpu_cache_usage_perc`
- Memory: `vllm:gpu_memory_usage_bytes`
- Scheduler: `vllm:num_preemptions_total`, `vllm:avg_num_batched_tokens`, `vllm:avg_num_running_tokens`
- Engine: `vllm:iteration_steps_total`, `vllm:num_tokens_total`

---

## 10.3 vLLM Metrics Enablement

vLLM by default does not expose Prometheus metrics. The deployment must be started with metrics enabled.

**Check current state in `config/local/models.override.yaml`:**

```yaml
vllm_default:
  framework: vllm
  transport: direct
  profile: vllm_rocm_single_gpu1
  # ← Verify metrics flag exists and is true
```

If not present, add to all vLLM deployment profiles:

```yaml
  backend:
    vllm:
      metrics: true  # Required to expose /metrics endpoint
```

This is parallel to llama.cpp's `metrics: true` flag (already enabled by Gemini's fix in Phase 1 prerequisites).

---

## 11. Constraints & Non-Goals

| Constraint | Detail |
|------------|--------|
| No nginx/postgres monitoring | Out of scope; focus on LLM inference components only |
| No auth redesign | Uses `DASHBOARD_API_KEY`; full multi-user auth is out of scope |
| No model file management | Dashboard does not download, delete, or move model files |
| No config editing | Config remains YAML-file-based; dashboard triggers reload only |
| Project separation | All dashboard source under `src/dashboard/`; no AgentRunner path references |
| Read-only in Phase 1–2 | Control actions require Phase 3; earlier phases are safe for always-on use |
| Manifest schema versioning | Schema changes are additive; new fields must have defaults so old manifests stay valid |
| llama.cpp metrics opt-in | Requires `--metrics` flag in llama-swap model config; disabled by default |
