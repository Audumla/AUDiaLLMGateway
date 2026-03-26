# Spec 701 Implementation Plan — LLM Gateway Dashboard

**Status:** Implementation Ready
**Created:** 2026-03-26
**Related:** [spec-701-gateway-dashboard.md](./spec-701-gateway-dashboard.md)
**Dependencies:** AUDiotMonitor spec-801 (hwexp manifest adapter)

---

## Readiness Assessment

**Status Summary as of 2026-03-26:**

| Component | Status | Blocker? | Notes |
| --- | --- | --- | --- |
| Manifest schema | ✅ Defined | No | `litellm.yaml`, `llamaswap.yaml` exist; vLLM needs review |
| AUDiotMonitor hwexp | ⏳ Not started | **YES** | spec-801 must be complete before Phase 2 |
| FastAPI backend | 🔄 Scaffolding only | No | Routes defined, no implementation |
| Vue3 frontend | 🔄 Design only | No | Component structure designed, not coded |
| Prometheus integration | ⚠️ Partial | No | hwexp adapter needed (blocks SPA) |
| llama.cpp metrics | ✅ Enabled | No | `metrics: true` added by Gemini fix |
| vLLM metrics | ⚠️ Needs verification | No | Check if vLLM profiles have metrics enabled |
| Docker service | ⏳ Not defined | No | Needs docker-compose.yml update |

**Critical path to Phase 1 completion:**

1. Verify vLLM has `metrics: true` (check models.override.yaml)
2. Validate all manifest YAML files
3. Create manifest_loader.py + FastAPI scaffolding (3-4 days)

**Critical path to Phase 2 (SPA launch):**

1. AUDiotMonitor hwexp adapter complete (blocks everything)
2. Prometheus metrics flowing into TSDB
3. Vue3 component + Prometheus client complete

---

## Overview

This document provides the detailed implementation plan for spec-701, including:
1. Complete metric schemas for each component
2. Step-by-step implementation phases
3. Code structure and file locations
4. Testing strategy
5. Migration path from existing configs

---

## Table of Contents

- [1. Metric Schemas](#1-metric-schemas)
  - [1.1 LiteLLM Gateway Metrics](#11-litellm-gateway-metrics)
  - [1.2 llama-swap + llama.cpp Metrics](#12-llama-swap--llamacpp-metrics)
  - [1.3 vLLM Metrics](#13-vllm-metrics)
- [2. Implementation Phases](#2-implementation-phases)
  - [Phase 1: Manifest Loader + FastAPI Scaffolding](#phase-1-manifest-loader--fastapi-scaffolding)
  - [Phase 2: hwexp Adapter Implementation](#phase-2-hwexp-adapter-implementation)
  - [Phase 3: Vue SPA Frontend](#phase-3-vue-spa-frontend)
  - [Phase 4: Control Plane Actions](#phase-4-control-plane-actions)
  - [Phase 5: Grafana Dashboard](#phase-5-grafana-dashboard)
- [3. File Structure](#3-file-structure)
- [4. Configuration Migration](#4-configuration-migration)
- [5. Testing Strategy](#5-testing-strategy)
- [6. Rollout Plan](#6-rollout-plan)

---

## 1. Metric Schemas

### 1.1 LiteLLM Gateway Metrics

**Service:** `audia-litellm`
**Port:** `${LITELLM_PORT:-4000}`
**Metrics Endpoint:** `http://${LITELLM_HOST}:${LITELLM_PORT}/metrics`

#### Proxy-Level Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_component_up` | gauge | `component` | Component health status (1=up, 0=down) | 10s |
| `gateway_litellm_proxy_total_requests` | counter | `model, key, team, user, endpoint` | Total requests through proxy | 15s |
| `gateway_litellm_proxy_failed_requests` | counter | `model, key, team` | Failed requests (4xx/5xx) | 15s |
| `gateway_litellm_request_total_latency` | histogram | `model, key, team` | End-to-end request latency (seconds) | 15s |
| `gateway_litellm_llm_api_latency` | histogram | `model, deployment` | LLM API call latency (seconds) | 15s |
| `gateway_litellm_time_to_first_token` | histogram | `model, deployment` | Time to first token (streaming only) | 15s |
| `gateway_litellm_total_tokens` | counter | `model, key, team, user` | Total tokens (input + output) | 15s |
| `gateway_litellm_input_tokens` | counter | `model, key, team, user` | Input/prompt tokens | 15s |
| `gateway_litellm_output_tokens` | counter | `model, key, team, user` | Output/completion tokens | 15s |
| `gateway_litellm_spend` | counter | `model, key, team, user` | Total spend in USD | 30s |

#### Deployment Health Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_litellm_deployment_state` | gauge | `deployment, model` | Deployment state (0=healthy, 1=partial, 2=outage) | 30s |
| `gateway_litellm_deployment_success` | counter | `deployment, model` | Successful LLM API responses | 15s |
| `gateway_litellm_deployment_failure` | counter | `deployment, model` | Failed LLM API responses | 15s |
| `gateway_litellm_remaining_requests` | gauge | `deployment, provider` | Remaining requests (rate limit) | 10s |
| `gateway_litellm_remaining_tokens` | gauge | `deployment, provider` | Remaining tokens (rate limit) | 10s |

#### Budget & Rate Limit Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_litellm_api_key_max_budget` | gauge | `key` | Max budget for API key (USD) | 30s |
| `gateway_litellm_remaining_api_key_budget` | gauge | `key` | Remaining budget for API key (USD) | 30s |
| `gateway_litellm_team_max_budget` | gauge | `team` | Max budget for team (USD) | 30s |
| `gateway_litellm_remaining_team_budget` | gauge | `team` | Remaining budget for team (USD) | 30s |

#### System Health Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_litellm_in_flight_requests` | gauge | - | Current in-flight requests | 5s |
| `gateway_litellm_redis_latency` | histogram | `operation` | Redis operation latency (seconds) | 15s |
| `gateway_litellm_redis_fails` | counter | - | Failed Redis operations | 15s |

#### Fallback Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_litellm_deployment_cooled_down` | counter | `deployment` | Times deployment cooled down | 15s |
| `gateway_litellm_successful_fallbacks` | counter | `primary_model, fallback_model` | Successful fallback requests | 15s |
| `gateway_litellm_failed_fallbacks` | counter | `primary_model, fallback_model` | Failed fallback requests | 15s |

---

### 1.2 llama-swap + llama.cpp Metrics

**Service:** `audia-llama`
**Router Port:** `${LLAMA_SWAP_PORT:-41080}`
**Backend Port Range:** `${LLAMA_SWAP_START_PORT:-41000}` to `${LLAMA_SWAP_END_PORT:-41099}`
**Metrics Endpoints:**
- Router: `http://${LLAMA_SWAP_HOST}:${LLAMA_SWAP_PORT}/v1/models` (JSON)
- Backends: `http://${HOST}:${BACKEND_PORT}/metrics` (Prometheus, per-model)

#### Optimization Strategy: Single-Query Model State

**Problem:** Polling individual llama.cpp backend `/metrics` endpoints wastes CPU and network:
- Each backend scrape is read-heavy (KV cache, memory state extraction)
- Idle models shouldn't consume inference resources for monitoring
- Scales poorly with 10+ loaded models

**Solution:** Query the service manager for model state; skip individual backend polling entirely:

```
┌────────────────────────────────────────────────────────────┐
│ Single Query Approach: Router + Service Manager             │
├────────────────────────────────────────────────────────────┤
│ llamaswap /v1/models (JSON):                              │
│   - All loaded models + request counts                     │
│   - Returns per-model: requests_processing, last_used      │
│   - Poll: 15s (single HTTP request)                        │
│                                                             │
│ vLLM (single model per instance):                          │
│   - Query /metrics to find currently loaded model          │
│   - Query /v1/models to confirm                            │
│   - Poll: 10s (single HTTP request)                        │
│                                                             │
│ LiteLLM:                                                    │
│   - Query /metrics for proxy stats                         │
│   - Poll: 10s (always active as gateway)                   │
└────────────────────────────────────────────────────────────┘
```

**Why NOT scrape individual backends:**

The llamaswap `/v1/models` endpoint already returns:
- `requests_processing` per model (current load)
- `last_used_timestamp` per model (activity)
- Implicitly: if model in list = loaded, if not in list = unloaded

This is sufficient for:
- Knowing which models are active (requests_processing > 0)
- Alerting on queue depth (requests_deferred)
- Tracking model lifetime (first_loaded, last_used)
- Dashboard cards (loaded models count)

**What we lose:** Per-model token throughput and KV cache ratio during active inference. **Trade-off: Worth it** — those metrics are only useful during active requests anyway.

**Benefits:**
- 95% reduction in HTTP requests (from ~120/min to ~6/min)
- Zero CPU overhead on inference servers
- Simpler implementation (no dynamic discovery)
- Scales to 100+ loaded models without degradation

**New Request Budget:**

```
llama-swap:  /v1/models @ 15s = 4 req/min
vLLM:        /metrics @ 10s = 6 req/min
LiteLLM:     /metrics @ 10s = 6 req/min
─────────────────────────────────
TOTAL:                          16 req/min (vs. 142 with per-backend polling)
```

#### llama-swap Router Metrics (Always Polled)

Tier 1: All data extracted from `/v1/models` endpoint (single HTTP call every 15s):

| Metric Name | Type | Labels | Source | Description |
|-------------|------|--------|--------|-------------|
| `gateway_component_up` | gauge | `component=llamaswap` | `/health` | Router health (1=up, 0=down) |
| `gateway_llamaswap_models_loaded` | gauge | - | `/v1/models` → count | Number of models currently loaded |
| `gateway_llamaswap_active_model` | info | `model_name` | `/v1/models` → first loaded | Currently selected/active model |
| `gateway_llamaswap_model_requests_processing{model_name}` | gauge | `model_name` | `/v1/models` per-model | Requests being processed per model |
| `gateway_llamaswap_model_requests_deferred{model_name}` | gauge | `model_name` | `/v1/models` per-model | Requests in queue per model |
| `gateway_llamaswap_model_last_used_timestamp{model_name}` | gauge | `model_name` | `/v1/models` per-model | Last activity timestamp per model |

#### llama.cpp Backend Metrics (Active Models Only)

Tier 2: For each model where `requests_processing > 0`, scrape `/metrics` at 10s interval:

**Per-Model Metrics:**

| Metric Name | Type | Labels | Source | Description |
|-------------|------|--------|--------|-------------|
| `gateway_llamacpp_prompt_tokens_total{model_name="..."}` | counter | `model_name` | `/metrics` on backend port | Total prompt tokens processed |
| `gateway_llamacpp_tokens_predicted_total{model_name="..."}` | counter | `model_name` | `/metrics` on backend port | Total generation tokens processed |
| `gateway_llamacpp_prompt_tokens_per_second{model_name="..."}` | gauge | `model_name` | `/metrics` on backend port | Prompt throughput (tokens/s) |
| `gateway_llamacpp_predicted_tokens_per_second{model_name="..."}` | gauge | `model_name` | `/metrics` on backend port | Generation throughput (tokens/s) |
| `gateway_llamacpp_kv_cache_usage_ratio{model_name="..."}` | gauge | `model_name` | `/metrics` on backend port | KV cache usage (0.0-1.0) |
| `gateway_llamacpp_kv_cache_tokens{model_name="..."}` | gauge | `model_name` | `/metrics` on backend port | Number of tokens in KV cache |
| `gateway_llamacpp_request_latency_seconds{model_name="..."}` | histogram | `model_name` | `/metrics` on backend port | Request latency distribution |

**Aggregate Metrics (Sum of all active models):**

| Metric Name | Type | Labels | Computation | Description |
|-------------|------|--------|-------------|-------------|
| `gateway_llamacpp_prompt_tokens_total{model_name="active"}` | counter | `model_name="active"` | `sum(all per-model)` | Total prompt tokens across all active models |
| `gateway_llamacpp_tokens_predicted_total{model_name="active"}` | counter | `model_name="active"` | `sum(all per-model)` | Total generation tokens across all active models |
| `gateway_llamacpp_prompt_tokens_per_second{model_name="active"}` | gauge | `model_name="active"` | `sum(all per-model)` | Aggregate prompt throughput |
| `gateway_llamacpp_predicted_tokens_per_second{model_name="active"}` | gauge | `model_name="active"` | `sum(all per-model)` | Aggregate generation throughput |
| `gateway_llamacpp_kv_cache_usage_ratio{model_name="active"}` | gauge | `model_name="active"` | `avg(all per-model)` | Average KV cache ratio across active models |

**Example Prometheus output:**

```promql
# 3 models total (2 active, 1 idle)
gateway_llamacpp_prompt_tokens_total{model_name="qwen27b"} 12500
gateway_llamacpp_prompt_tokens_total{model_name="llama70b"} 8300
gateway_llamacpp_prompt_tokens_total{model_name="active"} 20800   ← sum

gateway_llamacpp_kv_cache_usage_ratio{model_name="qwen27b"} 0.85
gateway_llamacpp_kv_cache_usage_ratio{model_name="llama70b"} 0.62
gateway_llamacpp_kv_cache_usage_ratio{model_name="active"} 0.735  ← avg
```

**Dashboard Query Examples:**

```promql
# Current aggregate throughput
gateway_llamacpp_predicted_tokens_per_second{model_name="active"}

# Per-model breakdown
gateway_llamacpp_prompt_tokens_total{model_name!="active"}

# All active models combined
sum(gateway_llamacpp_prompt_tokens_total)
```

**Activation logic (hwexp adapter):**

```python
def should_scrape_backend(model):
    """Only scrape detailed metrics if model is actively processing."""
    return model['requests_processing'] > 0

async def emit_metrics(active_models):
    """Emit per-model + aggregate metrics."""
    for model in active_models:
        emit(f"gateway_llamacpp_prompt_tokens_total{{model_name='{model.name}'}}",
             model.prompt_tokens)

    # Emit "active" aggregate
    total_prompt = sum(m.prompt_tokens for m in active_models)
    emit("gateway_llamacpp_prompt_tokens_total{model_name='active'}", total_prompt)
```

**Benefits:**
- Zero overhead when models idle (only router query)
- Full detailed metrics during active inference (when they matter)
- Per-model metrics for detailed analysis
- Aggregate "active" metrics for dashboard gauges (single query for total throughput)
- No complex derived metrics or PromQL expressions needed
- Idiomatic Prometheus: queries like `sum()` work naturally

---

### 1.3 vLLM Metrics

**Service:** `audia-vllm`
**External Port:** `${VLLM_PORT:-41090}`
**Internal Port:** `${VLLM_SERVICE_PORT:-8000}`
**Metrics Endpoint:** `http://${VLLM_HOST}:${VLLM_SERVICE_PORT}/metrics`

#### vLLM Metrics (Per-Instance + Aggregate)

vLLM serves a single model per instance. Query `/metrics` endpoint at fixed 10s interval.

**Supports both single instance and distributed cluster deployments:**

**Per-Instance Metrics:**

| Metric Name | Type | Labels | Source | Description |
|-------------|------|--------|--------|-------------|
| `gateway_component_up{component="vllm"}` | gauge | `component=vllm` | `/metrics` | vLLM health (1=up, 0=down) |
| `gateway_vllm_num_requests_running{model_name="..."}` | gauge | `model_name` | `/metrics` → `vllm:num_requests_running` | Requests being processed on this instance |
| `gateway_vllm_num_requests_waiting{model_name="..."}` | gauge | `model_name` | `/metrics` → `vllm:num_requests_waiting` | Requests in queue on this instance |
| `gateway_vllm_gpu_cache_usage_perc{model_name="..."}` | gauge | `model_name` | `/metrics` → `vllm:gpu_cache_usage_perc` | GPU KV cache usage (0-100%) |
| `gateway_vllm_gpu_memory_usage_bytes{model_name="..."}` | gauge | `model_name` | `/metrics` → `vllm:gpu_memory_usage_bytes` | GPU memory in use on this instance |
| `gateway_vllm_num_preemptions_total{model_name="..."}` | counter | `model_name` | `/metrics` → `vllm:num_preemptions_total` | Total request preemptions on this instance |

**Aggregate Metrics (Sum across all vLLM instances):**

| Metric Name | Type | Labels | Computation | Description |
|-------------|------|--------|-------------|-------------|
| `gateway_vllm_num_requests_running{model_name="active"}` | gauge | `model_name="active"` | `sum(all instances)` | Total requests across all vLLM instances |
| `gateway_vllm_num_requests_waiting{model_name="active"}` | gauge | `model_name="active"` | `sum(all instances)` | Total queued requests across all instances |
| `gateway_vllm_gpu_cache_usage_perc{model_name="active"}` | gauge | `model_name="active"` | `avg(all instances)` | Average KV cache usage across instances |
| `gateway_vllm_gpu_memory_usage_bytes{model_name="active"}` | gauge | `model_name="active"` | `sum(all instances)` | Total GPU memory across all instances |

**Example Prometheus output (3 vLLM instances):**

```promql
# Per-instance metrics
gateway_vllm_num_requests_running{model_name="qwen72b"} 5
gateway_vllm_num_requests_running{model_name="llama70b"} 3
gateway_vllm_num_requests_running{model_name="mistral7b"} 0

# Aggregate across all instances
gateway_vllm_num_requests_running{model_name="active"} 8

# GPU memory: sum of all instances
gateway_vllm_gpu_memory_usage_bytes{model_name="qwen72b"} 45000000000
gateway_vllm_gpu_memory_usage_bytes{model_name="llama70b"} 42000000000
gateway_vllm_gpu_memory_usage_bytes{model_name="mistral7b"} 0
gateway_vllm_gpu_memory_usage_bytes{model_name="active"} 87000000000  ← sum
```

**Poll interval:** Fixed 10s (always, whether active or idle). Single HTTP call to `/metrics` per instance.

**Rationale:** vLLM instances are always running and serving their model. No benefit to adaptive polling — always need to know current request count and memory usage.

**Single instance vs. cluster:**
- **Single vLLM instance:** Model label identifies the single model, "active" == that model's metrics
- **Multiple instances (cluster):** Each instance identified by its model name, "active" aggregates across all

**Dashboard queries:**

```promql
# Total requests across all vLLM instances
gateway_vllm_num_requests_running{model_name="active"}

# Per-instance breakdown
gateway_vllm_num_requests_running{model_name!="active"}

# Total GPU memory in use
gateway_vllm_gpu_memory_usage_bytes{model_name="active"}
```

---

## 1.4 Hybrid Polling Strategy & Request Budget

### Request Budget (Two-Tier: Always + Active)

**Scenario A: All models idle (no active inference)**

```
llama-swap router:    /v1/models @ 15s = 4 req/min
vLLM:                 /metrics @ 10s   = 6 req/min
LiteLLM:              /metrics @ 10s   = 6 req/min
llama.cpp backends:   (none)             0 req/min
────────────────────────────────────────
TOTAL:                                  = 16 req/min ✅
```

**Scenario B: 2 models actively processing (out of 10 loaded)**

```
llama-swap router:        /v1/models @ 15s    = 4 req/min
vLLM:                     /metrics @ 10s      = 6 req/min
LiteLLM:                  /metrics @ 10s      = 6 req/min
llama.cpp active (2x):    /metrics @ 10s each = 12 req/min
────────────────────────────────────────
TOTAL:                                       = 28 req/min ✅
```

**Scenario C: Full capacity (10 models processing, typical load test)**

```
llama-swap router:        /v1/models @ 15s    = 4 req/min
vLLM:                     /metrics @ 10s      = 6 req/min
LiteLLM:                  /metrics @ 10s      = 6 req/min
llama.cpp active (10x):   /metrics @ 10s each = 60 req/min
────────────────────────────────────────
TOTAL:                                       = 76 req/min ✅
```

**Comparison with old approaches:**

```
Naive polling (all backends fixed 10s):     ~120 req/min ❌ (wasteful)
Adaptive polling (60s for idle):             ~50 req/min (complex logic)
Hybrid tier (active-only scrape):            16-76 req/min ✅ (dynamic, simple)
```

### CPU Impact Analysis

**Idle scenario (~16 req/min):**
- Router query: ~10ms CPU
- Service `/metrics` reads: ~30ms CPU
- **Total: ~2.4s CPU/hour** (negligible)

**Active scenario (2 models, ~28 req/min):**
- Router + service queries: ~40ms CPU
- 2 backend scrapes: ~100ms CPU (50ms each)
- **Total: ~8.4s CPU/hour** (still <2% overhead)

**Peak scenario (10 models, ~76 req/min):**
- All queries: ~550ms CPU per minute
- **Total: ~33s CPU/hour** (acceptable during load test)

### Prometheus Storage Impact

Metrics are dynamic: only metrics from active models are emitted.

- Idle state: ~20 metrics emitted
- Active state (2 models): ~35 metrics emitted
- Peak state (10 models): ~80 metrics emitted

**Storage estimate (15 days retention):**
- Idle (constant): 20 × 50KB × 15 = 15MB
- Active spikes (temporary): minimal extra (compressed time-series)
- **Total: ~20MB negligible**

---

## 2. Implementation Phases

### Phase 0: Readiness & Prerequisites

**Duration:** 1 day
**Goal:** Verify all preconditions before development begins

#### Tasks

- [ ] **0.1** Verify vLLM metrics flag
  - Check `config/local/models.override.yaml` for all vLLM profiles
  - Confirm `backend.vllm.metrics: true` exists (or add it)
  - Reference: same as llama.cpp `metrics: true` added by Gemini

- [ ] **0.2** Validate manifest files
  - `config/monitoring/{litellm,llamaswap,vllm}.yaml` must parse without errors
  - Run: `python -c "import yaml; yaml.safe_load(open('config/monitoring/litellm.yaml'))"`
  - Check all `${VAR:-default}` references match stack config keys

- [ ] **0.3** Verify Prometheus access
  - AUDiotMonitor stack running and accessible
  - Can curl `http://prometheus:9090/api/v1/query?query=up`
  - Document host/port for `/dashboard/prometheus/` proxy

- [ ] **0.4** Create issue tracking
  - Create GitHub issues for each Phase 1-4 task (helps with PRs)
  - Tag with `spec-701` label

#### Success Criteria

- All manifests validate
- vLLM metrics flag confirmed/added
- Prometheus endpoint accessible
- AUDiotMonitor spec-801 status known (blocking dependency)

---

### Phase 1: Manifest Loader + FastAPI Scaffolding

**Duration:** 3-4 days
**Goal:** Load manifests, export env vars, serve via FastAPI

#### Tasks

- [ ] **1.1** Create `src/dashboard/manifest_loader.py`
  - Load manifests from `config/monitoring/` and `config/local/monitoring/`
  - Merge logic (shallow merge, lists by `id`)
  - Environment variable resolution (`${VAR:-default}`)
  - Export stack config as env vars (section 5.2.1)

- [ ] **1.2** Create `src/dashboard/main.py`
  - FastAPI app initialization
  - Load manifests at startup
  - Health endpoint: `GET /healthz`

- [ ] **1.3** Create `src/dashboard/routers/manifests.py`
  - `GET /api/v1/manifests` - All manifests (card + actions only)
  - `GET /api/v1/manifests/{id}` - Single manifest

- [ ] **1.4** Create `src/dashboard/routers/models.py`
  - `GET /api/v1/models/catalog` - Load from `config/local/models.override.yaml`

- [ ] **1.5** Create `src/dashboard/routers/config.py`
  - `GET /api/v1/config/diff` - Show config changes without applying
  - `POST /api/v1/config/reload` - Regenerate configs

- [ ] **1.6** Create `src/dashboard/types.py`
  - Pydantic models for manifest schema
  - TypeScript type generation script

- [ ] **1.7** Update `config_loader.py`
  - Add `export_stack_env_vars()` function
  - Ensure network settings exported before manifest load

- [ ] **1.8** Add tests
  - `tests/test_manifest_loader.py` - Merge logic, env var resolution
  - `tests/test_manifest_api.py` - API endpoint tests

#### Files Created

```
src/dashboard/
  __init__.py
  main.py
  manifest_loader.py
  types.py
  routers/
    __init__.py
    manifests.py
    models.py
    config.py
```

#### Deliverable

FastAPI service running on port 4100, serving manifest metadata and model catalog.

#### Success Criteria

- [ ] FastAPI starts without errors: `uvicorn src.dashboard.main:app --port 4100`
- [ ] `GET /api/v1/manifests` returns valid JSON with all 3 components
- [ ] `GET /api/v1/manifests/llamaswap` returns component card layout + actions
- [ ] `GET /api/v1/models/catalog` returns vLLM + llama.cpp models
- [ ] `GET /api/v1/config/diff` shows diffs without applying
- [ ] All env vars resolve correctly (no `${UNKNOWN_VAR}` in output)
- [ ] Tests pass: `pytest tests/test_manifest_loader.py tests/test_manifest_api.py -v`

---

### Phase 2: hwexp Adapter Implementation

**Duration:** 5-7 days
**Goal:** Poll components, emit Prometheus metrics

#### Tasks

- [ ] **2.1** Create hwexp manifest adapter in AUDiotMonitor project
  - `AUDiotMonitor/src/hwexp/adapters/gateway_manifest/`
  - Load same manifests from `config/monitoring/`
  - Parse `health` and `metrics` sections

- [ ] **2.2** Implement health polling
  - HTTP probe to `connection.host:connection.port + health.endpoint`
  - Emit `gateway_component_up` for each component
  - Poll interval from manifest (default 10s)

- [ ] **2.3** Implement JSON metrics extraction
  - Query endpoint (e.g., `/v1/models`)
  - Apply `extract` jq expression
  - Emit as Prometheus gauge/info metric

- [ ] **2.4** Implement Prometheus text scraping
  - Parse Prometheus text format from `/metrics`
  - Extract metric by name
  - Relabel with `gateway_` prefix

- [ ] **2.5** Implement dynamic llama.cpp discovery
  - Query llama-swap `/v1/models`
  - Extract model→port mapping
  - Scrape each backend's `/metrics`
  - Add `model_name` label to all metrics

- [ ] **2.6** Implement derived metrics
  - Support `type: derived` in manifests
  - Evaluate PromQL-like formulas
  - Emit computed metrics

- [ ] **2.7** Create Prometheus mappings
  - `AUDiotMonitor/config/gateway/mappings.yaml`
  - Map raw metric names to `gateway_*` namespace
  - Define label transformations

- [ ] **2.8** Add tests
  - Mock component servers
  - Verify metric emission
  - Test dynamic discovery

#### Files Created (in AUDiotMonitor project)

```
AUDiotMonitor/
  src/hwexp/adapters/gateway_manifest/
    __init__.py
    adapter.py
    health_poller.py
    metrics_extractor.py
    llama_cpp_discovery.py
  config/gateway/
    mappings.yaml
```

#### Deliverable

hwexp adapter emitting all metrics from section 1 to Prometheus.

#### Success Criteria

- [ ] hwexp adapter code merged into AUDiotMonitor
- [ ] Prometheus scrape targets include gateway components
- [ ] `gateway_component_up{component="litellm"}` exists in Prometheus
- [ ] `gateway_component_up{component="llamaswap"}` exists in Prometheus
- [ ] `gateway_llamaswap_models_loaded` returns a gauge value
- [ ] `gateway_litellm_proxy_total_requests` increments with API traffic
- [ ] Dynamic llama.cpp discovery working: `/metrics` scraped from backend instances
- [ ] Derived metrics (`gateway_llamaswap_requests_rate_5m`) computed correctly
- [ ] All metrics prefixed with `gateway_` (no collision with other exporters)
- [ ] No scrape errors in Prometheus logs for 24 hours

**Blocking note:** Phase 3 (Vue SPA) cannot proceed until Phase 2 is complete and Prometheus is populated.

---

### Phase 3: Vue SPA Frontend

**Duration:** 5-7 days
**Goal:** Control panel UI reading from Prometheus

#### Tasks

- [ ] **3.1** Scaffold Vue 3 + Vite + Tailwind project
  - `src/dashboard/ui/`
  - Configure Vite build to output to `src/dashboard/static/`

- [ ] **3.2** Create TypeScript types
  - `src/dashboard/ui/src/manifest.ts` - Manifest schema types
  - `src/dashboard/ui/src/prometheus.ts` - Prometheus API types

- [ ] **3.3** Create Prometheus client
  - `src/dashboard/ui/src/prometheus.ts`
  - Typed queries to `/dashboard/prometheus/api/v1/query`
  - Batch queries for efficiency

- [ ] **3.4** Create `ComponentCard.vue`
  - Generic card rendered from manifest
  - Poll Prometheus for state every 15s
  - Display health, metrics, links
  - Action buttons (read-only in Phase 3)

- [ ] **3.5** Create `ModelPanel.vue`
  - Show loaded models from Prometheus
  - Model metadata from FastAPI `/models/catalog`

- [ ] **3.6** Create `Dashboard.vue` (main view)
  - Grid of `ComponentCard` instances
  - `ModelPanel` below
  - Grafana link in header

- [ ] **3.7** Create nginx config generator
  - Update `config_loader.py` to emit nginx blocks
  - `/dashboard/` → static files
  - `/dashboard/api/` → FastAPI
  - `/dashboard/prometheus/` → Prometheus proxy

- [ ] **3.8** Add tests
  - Component unit tests
  - Prometheus client mocks
  - E2E test with mock data

#### Files Created

```
src/dashboard/ui/
  src/
    App.vue
    main.ts
    components/
      Dashboard.vue
      ComponentCard.vue
      ModelPanel.vue
      LogDrawer.vue
    prometheus.ts
    manifest.ts
    cards.ts
  package.json
  vite.config.ts
  tailwind.config.js
  index.html
```

#### Deliverable

SPA served at `/dashboard/` showing live component health and model state.

#### Success Criteria

- [ ] Vue3 SPA compiles without errors: `npm run build`
- [ ] Dashboard loads at `http://localhost:8080/dashboard/`
- [ ] ComponentCard renders for all 3 components
- [ ] Prometheus queries return data: `query(gateway_component_up)`
- [ ] Health status indicators show correct state (green/red)
- [ ] Metric values display correctly from Prometheus
- [ ] Prometheus proxy works: `curl http://localhost:8080/dashboard/prometheus/api/v1/query?query=up`
- [ ] ModelPanel shows loaded models
- [ ] Links to component APIs/UIs work
- [ ] Layout responsive on mobile/tablet (Tailwind)
- [ ] No console errors or warnings
- [ ] Tests pass: `npm test`

---

### Phase 4: Control Plane Actions

**Duration:** 4-5 days
**Goal:** Enable action execution via FastAPI

#### Tasks

- [ ] **4.1** Create `src/dashboard/action_runner.py`
  - `docker_restart` - `docker compose restart <container>`
  - `http_post` - POST to component endpoint
  - `process_signal` - Signal to PID file
  - `config_reload` - Regenerate + restart
  - `shell` - Run named command

- [ ] **4.2** Create `src/dashboard/routers/components.py`
  - `POST /api/v1/components/{id}/actions/{action_id}`
  - Validate action exists in manifest
  - Execute via `action_runner.py`
  - Return execution status

- [ ] **4.3** Create `src/dashboard/routers/logs.py`
  - `GET /api/v1/logs/{id}` - SSE stream
  - Tail last 200 lines + live updates
  - Read from component log files

- [ ] **4.4** Update `ComponentCard.vue`
  - Add action buttons (gated by `DASHBOARD_AUTH_READONLY`)
  - Confirmation dialogs from manifest
  - Show execution status

- [ ] **4.5** Create `LogDrawer.vue`
  - Slide-out log viewer
  - SSE connection to FastAPI
  - Auto-scroll, pause, search

- [ ] **4.6** Add authorization
  - Bearer token from `DASHBOARD_API_KEY`
  - Read-only mode from `DASHBOARD_AUTH_READONLY`
  - Token validation middleware

- [ ] **4.7** Add tests
  - Action execution mocks
  - SSE stream tests
  - Authorization tests

#### Files Created

```
src/dashboard/
  action_runner.py
  routers/
    components.py
    logs.py
```

#### Deliverable

Full operational control panel with restart, reload, and log viewing.

#### Success Criteria

- [ ] `POST /api/v1/components/llamaswap/actions/restart` executes docker restart
- [ ] Action buttons render in ComponentCard (if not read-only)
- [ ] Confirmation dialogs show before destructive actions
- [ ] LogDrawer opens/closes correctly
- [ ] Log SSE stream works: curl `-N` to `/api/v1/logs/litellm`
- [ ] Bearer token validation works on protected endpoints
- [ ] Read-only mode hides action buttons when `DASHBOARD_AUTH_READONLY=true`
- [ ] Config reload shows diff before applying
- [ ] After action execution, Prometheus is re-queried and state updates
- [ ] No actions execute without correct auth token
- [ ] Tests pass: action mocks, SSE, auth validation

---

### Phase 5: Grafana Dashboard

**Duration:** 3-4 days
**Goal:** Observability dashboards in Grafana

#### Tasks

- [ ] **5.1** Create Grafana dashboard JSON
  - `AUDiotMonitor/grafana/dashboards/llm-gateway.json`
  - Import via AUDiotMonitor provisioning

- [ ] **5.2** Component Health Row
  - `gateway_component_up` status panel
  - Health history timeline
  - Alert annotations

- [ ] **5.3** LiteLLM Row
  - Request rate (5m average)
  - Latency histogram
  - Token throughput
  - Deployment state panel
  - Error rate by model

- [ ] **5.4** llama-swap Row
  - Models loaded gauge
  - KV cache usage
  - Token generation speed
  - Request queue depth

- [ ] **5.5** vLLM Row
  - GPU cache usage
  - GPU memory usage
  - Request latency
  - Preemption rate

- [ ] **5.6** Correlation Panel
  - GPU temperature vs inference latency
  - Request rate vs KV cache usage
  - Error spikes with deployment state

- [ ] **5.7** Alerts
  - Component down (>1m)
  - Error rate >5% (5m)
  - KV cache >90%
  - GPU memory >95%

- [ ] **5.8** Documentation
  - Dashboard usage guide
  - Alert runbooks
  - Metric glossary

#### Deliverable

Grafana dashboard with full observability.

#### Success Criteria

- [ ] Grafana dashboard JSON created and validates
- [ ] All rows render without errors
- [ ] `gateway_component_up` shows current status for all 3 components
- [ ] Request rate graphs show data from `gateway_litellm_proxy_total_requests`
- [ ] Latency histograms display percentile bucketing
- [ ] KV cache usage graph shows ratio 0.0-1.0
- [ ] GPU memory graph shows bytes in human-readable format (GB)
- [ ] Correlation panel shows temporal alignment of metrics
- [ ] Alerts fire when component down >1m
- [ ] Alert annotations appear on dashboards
- [ ] Dashboard imports via AUDiotMonitor provisioning
- [ ] Runbooks linked from alerts
- [ ] Metric glossary complete (all 80+ metrics documented)

**Note:** This phase is optional for MVP. Phases 0-3 provide a working control panel.

---

## 3. File Structure

### Complete Project Structure After Implementation

```
AUDiaLLMGateway/
  config/
    monitoring/                    # ← New directory
      litellm.yaml                 # LiteLLM manifest
      llamaswap.yaml               # llama-swap manifest
      vllm.yaml                    # vLLM manifest

    local/
      monitoring/                  # ← New directory (git-ignored)
        (user overrides here)

    generated/
      nginx/
        dashboard/                 # ← Built SPA output
          index.html
          assets/

  src/
    launcher/
      config_loader.py             # Updated: export_stack_env_vars()

    dashboard/                     # ← New directory
      __init__.py
      main.py                      # FastAPI app
      manifest_loader.py           # Load + merge manifests
      action_runner.py             # Execute actions
      types.py                     # Pydantic models

      routers/
        __init__.py
        manifests.py               # GET /manifests
        models.py                  # GET /models/catalog
        config.py                  # POST /config/reload
        components.py              # POST /actions/{action_id}
        logs.py                    # GET /logs/{id} (SSE)

      ui/                          # Vue 3 SPA source
        src/
          App.vue
          main.ts
          components/
            Dashboard.vue
            ComponentCard.vue
            ModelPanel.vue
            LogDrawer.vue
          prometheus.ts
          manifest.ts
          cards.ts
        package.json
        vite.config.ts
        dist/                      # Built output → config/generated/nginx/dashboard/

      static/                      # Built SPA (generated by build)
      Dockerfile

  tests/
    test_manifest_loader.py
    test_manifest_api.py
    test_action_runner.py
    test_dashboard_spa.py
```

---

## 4. Configuration Migration

### 4.1 Environment Variables

Add to `.env`:

```bash
# Dashboard API
DASHBOARD_API_KEY=your-secure-key-here
DASHBOARD_AUTH_READONLY=true

# Port configuration (if overriding defaults)
LITELLM_PORT=4000
LLAMA_SWAP_PORT=41080
LLAMA_SWAP_START_PORT=41000
LLAMA_SWAP_END_PORT=41099
VLLM_PORT=41090
VLLM_SERVICE_PORT=8000
```

### 4.2 llama-swap Model Configuration

Update `config/local/llama-swap.override.yaml` to enable metrics:

```yaml
# Add --metrics flag to each model
models:
  qwen3.5-27b:
    cmd: |
      llama-server-rocm \
        --model /app/models/gguf/qwen3.5-27b-q4_k_m.gguf \
        --port 41001 \
        --metrics  # ← Required for Prometheus scraping
```

### 4.3 Docker Compose

Add to `docker-compose.yml`:

```yaml
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

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Manifest Loader:**
```python
def test_manifest_merge():
    project = load_manifest("config/monitoring/llamaswap.yaml")
    local = load_manifest("config/local/monitoring/llamaswap.yaml")
    merged = merge_manifests(project, local)
    assert merged["connection"]["port"] == local["connection"]["port"]
```

**Environment Variable Resolution:**
```python
def test_env_var_resolution(monkeypatch):
    monkeypatch.setenv("LLAMA_SWAP_PORT", "42000")
    manifest = load_manifest("config/monitoring/llamaswap.yaml")
    assert manifest["connection"]["port"] == 42000
```

### 5.2 Integration Tests

**Mock Component Servers:**
```python
@pytest.fixture
def mock_llamaswap():
    server = MockServer(port=41080)
    server.register("/health", {"status": "healthy"})
    server.register("/v1/models", {"data": [{"id": "qwen3.5-27b"}]})
    yield server
    server.stop()
```

**hwexp Adapter:**
```python
def test_health_polling(mock_llamaswap):
    adapter = GatewayManifestAdapter()
    metrics = adapter.poll_health("llamaswap")
    assert metrics["gateway_component_up"] == 1
```

### 5.3 E2E Tests

**Full Stack:**
```python
def test_dashboard_loads(browser):
    browser.get("/dashboard/")
    assert "LiteLLM Gateway" in browser.page_source
    assert "llama-swap" in browser.page_source
```

**Action Execution:**
```python
def test_restart_action(browser, docker_client):
    browser.click("button[data-action='restart']")
    browser.click("button[data-confirm='true']")
    wait_for_container_restart("audia-litellm")
```

---

## 6. Rollout Plan

### Week 1: Foundation
- Days 1-2: Manifest loader + FastAPI scaffolding (Phase 1)
- Days 3-5: hwexp adapter core (Phase 2, partial)

### Week 2: Metrics + UI
- Days 1-3: hwexp adapter completion (Phase 2)
- Days 4-5: Vue SPA scaffolding (Phase 3, partial)

### Week 3: Frontend + Actions
- Days 1-3: Vue SPA completion (Phase 3)
- Days 4-5: Control plane actions (Phase 4, partial)

### Week 4: Polish + Grafana
- Days 1-2: Action completion + logs (Phase 4)
- Days 3-5: Grafana dashboard (Phase 5)

### Rollback Plan

If issues arise:
1. Disable dashboard profile: `docker compose --profile dashboard stop`
2. Revert manifest files from git
3. Restart gateway: `docker compose restart audia-litellm`

No changes to core gateway functionality until Phase 4 (actions). Phases 1-3 are read-only.

---

## Appendix A: Manifest Schema Reference

### Complete Schema

```yaml
# Identity (required)
id: string                    # Machine identifier
display_name: string          # Human-readable name
icon: string                  # Icon key for UI
enabled: boolean              # false = not polled

# Health probe (required)
health:
  endpoint: string            # Health check path
  method: GET | HEAD          # HTTP method
  expect_status: integer      # Expected status code
  timeout_s: integer          # Timeout in seconds
  headers:                    # Optional headers
    Authorization: string
  status_field: string        # jq path to status in JSON response

# Metrics (optional)
metrics:
  - id: string                # Metric identifier
    endpoint: string          # Metrics endpoint path
    source_format: json | prometheus | text
    extract: string           # jq expression (for JSON)
    metric_name: string       # Prometheus metric name to extract
    prometheus_name: string   # Output metric name
    unit: string              # Unit (count, seconds, bytes, etc.)
    poll_interval_s: integer  # Polling interval
    labels: [string]          # Label names
    type: derived             # Optional: derived metric
    formula: string           # PromQL formula (for derived)

# Actions (optional)
actions:
  - id: string                # Action identifier
    label: string             # Button label
    type: docker_restart | http_post | process_signal | config_reload | shell
    container: string         # For docker_restart
    endpoint: string          # For http_post
    body: object              # For http_post
    signal: string            # For process_signal
    command: string           # For shell
    confirm: boolean          # Show confirmation dialog
    confirm_message: string   # Confirmation message

# Card display (optional)
card:
  port: string                # Port to display (can be ${VAR})
  extra_fields:
    - label: string
      metric: string          # References metrics[].id
      aggregation: string     # Optional: rate_5m, avg_5m
      format: string          # Optional: percent, "{value:.1f}"
  links:
    - label: string
      path: string            # URL path

# Connection (required)
connection:
  host: string                # Can be ${VAR:-default}
  port: integer               # Can be ${VAR:-default}
  auth:
    type: none | bearer | basic
    token_env: string         # For bearer auth
```

---

## Appendix B: Prometheus Metric Naming Convention

All metrics follow this pattern:

```
gateway_<component>_<metric_name>[_<unit>]
```

Examples:
- `gateway_litellm_proxy_total_requests` (counter)
- `gateway_llamacpp_kv_cache_usage_ratio` (gauge)
- `gateway_vllm_time_to_first_token_seconds` (histogram)

**Units:**
- `count` - Dimensionless count
- `seconds` - Time duration
- `bytes` - Memory/data size
- `ratio` - 0.0 to 1.0 ratio
- `percent` - 0 to 100 percentage
- `usd` - Currency

**Labels:**
- Always include `component` label
- Include `model_name` or `model` for model-specific metrics
- Include `deployment` for LiteLLM deployment-specific metrics
