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

#### Optimization Strategy: Adaptive Polling

**Problem:** Polling all model backends every 10-15s is wasteful when:
- Many models are loaded but idle (no active requests)
- Models may sit unused for hours
- Each scrape adds CPU overhead to inference

**Solution:** Two-tier adaptive polling:

```
┌─────────────────────────────────────────────────────────┐
│ Tier 1: Router Health (ALL models, lightweight)         │
│ Poll interval: 15s                                       │
│ Endpoint: /v1/models (single request)                   │
│ Returns: List of loaded models + basic stats            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Tier 2: Detailed Metrics (ACTIVE models only)           │
│ Poll interval: 5s for active, 60s for idle              │
│ Endpoint: /metrics (per backend)                        │
│ Triggered when: requests_processing > 0 OR              │
│                 last_used within 5 minutes              │
└─────────────────────────────────────────────────────────┘
```

**Activity Detection:**
- llama-swap `/v1/models` returns `requests_processing` per model
- Only scrape `/metrics` from backends with `requests_processing > 0`
- Idle models polled every 60s for health check only
- Active models (recent traffic) polled every 5s for full metrics

**Benefits:**
- 90% reduction in scrapes when models are idle
- CPU cycles preserved for inference
- Still captures full metrics during active use

#### Router-Level Metrics (llama-swap) - Tier 1

| Metric Name | Type | Labels | Source | Poll Interval |
|-------------|------|--------|--------|---------------|
| `gateway_component_up` | gauge | `component` | `/health` | 10s |
| `gateway_llamaswap_models_loaded` | gauge | - | `/v1/models` → `.data \| length` | 15s |
| `gateway_llamaswap_models_available` | gauge | - | `/v1/models` → `.data \| length` | 15s |
| `gateway_llamaswap_active_model` | info | `model_name` | `/v1/models` → `.data[0].id` | 15s |
| `gateway_llamaswap_health_status` | gauge | - | `/health` → `.status` | 10s |
| `gateway_llamaswap_model_requests_processing` | gauge | `model_name` | `/v1/models` → per-model | 15s |
| `gateway_llamaswap_model_last_used_timestamp` | gauge | `model_name` | `/v1/models` → per-model | 15s |

#### Backend Metrics (llama.cpp per-model) - Tier 2

**Discovery:** hwexp adapter queries `/v1/models` on llama-swap every 15s.
For each model with `requests_processing > 0` OR `last_used > now - 5min`:
  → Scrape `/metrics` from backend at 5s interval

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_llamacpp_prompt_tokens_total` | counter | `model_name` | Total prompt tokens processed | 5s (active) / 60s (idle) |
| `gateway_llamacpp_tokens_predicted_total` | counter | `model_name` | Total generation tokens processed | 5s (active) / 60s (idle) |
| `gateway_llamacpp_prompt_tokens_per_second` | gauge | `model_name` | Prompt throughput (tokens/s) | 5s (active) / 60s (idle) |
| `gateway_llamacpp_predicted_tokens_per_second` | gauge | `model_name` | Generation throughput (tokens/s) | 5s (active) / 60s (idle) |
| `gateway_llamacpp_kv_cache_usage_ratio` | gauge | `model_name` | KV cache usage (0.0-1.0) | 5s (active) / 60s (idle) |
| `gateway_llamacpp_kv_cache_tokens` | gauge | `model_name` | Number of tokens in KV cache | 5s (active) / 60s (idle) |
| `gateway_llamacpp_requests_processing` | gauge | `model_name` | Requests currently processing | 5s (active) / 60s (idle) |
| `gateway_llamacpp_requests_deferred` | gauge | `model_name` | Requests waiting in queue | 5s (active) / 60s (idle) |

**Idle Model Detection:**
```python
# hwexp adapter logic (sketch)
def should_scrape_backend(model_info):
    if model_info['requests_processing'] > 0:
        return True  # Actively processing
    if model_info['last_used_timestamp'] > (now - 300):  # 5 minutes
        return True  # Recently used
    return False  # Idle - skip detailed scrape
```

#### Derived/Aggregated Metrics

| Metric Name | Type | Labels | Formula | Poll Interval |
|-------------|------|--------|---------|---------------|
| `gateway_llamaswap_requests_rate_5m` | gauge | - | `sum(rate(gateway_llamacpp_prompt_tokens_total[5m]))` | 15s |
| `gateway_llamaswap_avg_kv_cache_usage` | gauge | - | `avg(gateway_llamacpp_kv_cache_usage_ratio)` | 15s |

---

### 1.3 vLLM Metrics

**Service:** `audia-vllm`
**External Port:** `${VLLM_PORT:-41090}`
**Internal Port:** `${VLLM_SERVICE_PORT:-8000}`
**Metrics Endpoint:** `http://${VLLM_HOST}:${VLLM_SERVICE_PORT}/metrics`

#### Optimization Strategy: Activity-Based Polling

vLLM serves a single model at a time (per instance). Polling strategy:

- **Active** (`num_requests_running > 0`): Poll every 5s
- **Idle** (`num_requests_running == 0`): Poll every 30s

**Implementation:**
```python
# hwexp adapter checks num_requests_running first
def get_vllm_poll_interval(metrics):
    if metrics.get('vllm:num_requests_running', 0) > 0:
        return 5  # Active - high resolution
    return 30     # Idle - reduced overhead
```

#### Request Processing Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_component_up` | gauge | `component` | Component health status (1=up, 0=down) | 10s |
| `gateway_vllm_num_requests_running` | gauge | `model_name` | Requests currently executing | 5s (active) / 30s (idle) |
| `gateway_vllm_num_requests_waiting` | gauge | `model_name` | Requests in queue | 5s (active) / 30s (idle) |
| `gateway_vllm_time_to_first_token_seconds` | histogram | `model_name` | Time to first token | 5s (active) / 30s (idle) |
| `gateway_vllm_time_per_output_token_seconds` | histogram | `model_name` | Time per output token | 5s (active) / 30s (idle) |
| `gateway_vllm_e2e_request_latency_seconds` | histogram | `model_name` | End-to-end request latency | 5s (active) / 30s (idle) |

#### Token Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_vllm_request_prompt_tokens` | histogram | `model_name` | Prompt tokens per request | 5s (active) / 30s (idle) |
| `gateway_vllm_request_generation_tokens` | histogram | `model_name` | Generation tokens per request | 5s (active) / 30s (idle) |
| `gateway_vllm_num_tokens_total` | counter | `model_name` | Total tokens processed | 5s (active) / 30s (idle) |

#### KV Cache & Memory Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_vllm_gpu_cache_usage_perc` | gauge | `model_name` | GPU KV cache usage percentage | 10s (active) / 60s (idle) |
| `gateway_vllm_cpu_cache_usage_perc` | gauge | `model_name` | CPU KV cache usage percentage | 10s (active) / 60s (idle) |
| `gateway_vllm_gpu_memory_usage_bytes` | gauge | `model_name` | GPU memory usage in bytes | 10s (active) / 60s (idle) |

#### Scheduler & Engine Metrics

| Metric Name | Type | Labels | Description | Poll Interval |
|-------------|------|--------|-------------|---------------|
| `gateway_vllm_num_preemptions_total` | counter | `model_name` | Total request preemptions | 5s (active) / 30s (idle) |
| `gateway_vllm_avg_num_batched_tokens` | gauge | `model_name` | Average batched tokens | 5s (active) / 30s (idle) |
| `gateway_vllm_avg_num_running_tokens` | gauge | `model_name` | Average running tokens | 5s (active) / 30s (idle) |
| `gateway_vllm_iteration_steps_total` | counter | `model_name` | Total iteration steps | 5s (active) / 30s (idle) |

#### Derived Metrics

| Metric Name | Type | Labels | Formula | Poll Interval |
|-------------|------|--------|---------|---------------|
| `gateway_vllm_gpu_memory_usage_gb` | gauge | `model_name` | `gateway_vllm_gpu_memory_usage_bytes / 1073741824` | 10s (active) / 60s (idle) |
| `gateway_vllm_tokens_rate_5m` | gauge | `model_name` | `rate(gateway_vllm_num_tokens_total[5m])` | 15s |

---

## 1.4 Polling Optimization Summary

### Comparative Load Analysis

#### Without Optimization (Naive Approach)

```
llama-swap with 10 loaded models:
  - Router: 1 request every 15s = 4/min
  - Backends: 10 requests every 10s = 60/min
  - Total: 64 requests/min

vLLM:
  - 1 request every 10s = 6/min

LiteLLM:
  - 1 request every 10s = 6/min

TOTAL: ~76 requests/min (all polling at fixed intervals)
```

#### With Adaptive Polling (Optimized)

```
Scenario A: All models idle (no traffic)
llama-swap with 10 loaded models:
  - Router: 1 request every 15s = 4/min
  - Backends: 10 requests every 60s = 10/min (idle polling)
  - Total: 14 requests/min

vLLM (idle):
  - 1 request every 30s = 2/min

LiteLLM:
  - 1 request every 10s = 6/min (always active as gateway)

TOTAL: ~22 requests/min (71% reduction)

─────────────────────────────────────────────────────────

Scenario B: 2 active models, 8 idle
llama-swap with 10 loaded models:
  - Router: 1 request every 15s = 4/min
  - Active backends (2): 2 requests every 5s = 24/min
  - Idle backends (8): 8 requests every 60s = 8/min
  - Total: 36 requests/min

vLLM (active):
  - 1 request every 5s = 12/min

LiteLLM:
  - 1 request every 10s = 6/min

TOTAL: ~54 requests/min (29% reduction, but better resolution on active models)

─────────────────────────────────────────────────────────

Scenario C: All models active (heavy traffic)
llama-swap with 10 loaded models:
  - Router: 1 request every 15s = 4/min
  - Backends: 10 requests every 5s = 120/min
  - Total: 124 requests/min

vLLM (active):
  - 1 request every 5s = 12/min

LiteLLM:
  - 1 request every 10s = 6/min

TOTAL: ~142 requests/min (higher resolution for debugging)
```

### Implementation Guidelines

**1. Two-Tier Polling (llama-swap):**
```python
class LlamaSwapAdapter:
    def __init__(self):
        self.model_states = {}  # Track activity per model

    async def poll(self):
        # Tier 1: Query router (always)
        models = await self.query_router()

        # Tier 2: Scrape backends (active only)
        for model in models:
            if self.is_active(model):
                await self.scrape_backend(model, interval=5)
            else:
                await self.scrape_backend(model, interval=60)

    def is_active(self, model):
        return (model['requests_processing'] > 0 or
                time.now() - model['last_used'] < 300)
```

**2. Dynamic Interval Adjustment (vLLM):**
```python
class VLLMAdapter:
    async def poll(self):
        metrics = await self.scrape_metrics()

        # Adjust next poll interval based on activity
        if metrics['vllm:num_requests_running'] > 0:
            self.next_poll = 5   # High resolution
        else:
            self.next_poll = 30  # Reduced overhead
```

**3. LiteLLM (Always Active):**
```python
# LiteLLM is the gateway - always process requests
# No optimization needed, fixed 10s interval
class LiteLLMAdapter:
    INTERVAL = 10  # Always poll at fixed interval
```

### CPU Impact Analysis

**llama.cpp backend scrape cost:**
- Idle model: ~50ms CPU time per scrape (KV cache, memory read)
- Active model: ~100ms CPU time per scrape (adds request state)
- At 10s interval: 600 scrapes/hour = 60s CPU/hour per model
- At 60s interval (idle): 60 scrapes/hour = 6s CPU/hour per model

**Savings with adaptive polling:**
- 10 idle models: 540s CPU/hour saved (9 minutes of inference time)
- Significant for GPU-constrained environments

### Memory Impact

Metrics scraping is read-only, no memory overhead. Prometheus stores:
- Active metrics: Last 15 days (configurable)
- Resolution: 15s (default scrape interval)
- Storage: ~100KB per metric per day (compressed)

**Total storage estimate (all metrics):**
- 80 metrics × 100KB × 15 days = ~120MB (negligible)

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
