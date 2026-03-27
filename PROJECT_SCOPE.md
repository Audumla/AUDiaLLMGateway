# Project Scope: AUDia LLM Gateway Dashboard

**Status:** Data Provider + Control Panel (Phase 3 Part 2)

## What This Project IS

A **lightweight data provider and control interface** for the LLM gateway:

1. **Component Status Provider**
   - Exposes component metadata (display name, icon, health config)
   - Lists available actions (restart, reload)
   - Tracks action execution state

2. **Log Provider**
   - Exposes application logs via REST API
   - Real-time log streaming via Server-Sent Events (SSE)
   - Supports filtering (level, component, source)

3. **Control Interface**
   - Trigger component actions (docker restart, shell commands, etc.)
   - Poll action execution status
   - Execute via ActionRunner + Docker socket

4. **Manifest Discovery**
   - Provides component layout metadata for UIs
   - Card configuration with quick links
   - Metric definitions and health probe specs

## What This Project IS NOT

This project does **NOT** include:
- ❌ **Metrics Collection** - No Prometheus integration
- ❌ **Health Checking** - No active health probes (config only)
- ❌ **Alerting** - No alert rules or thresholds
- ❌ **Dashboarding** - No Grafana integration
- ❌ **Monitoring System** - No metrics aggregation or time-series storage
- ❌ **Configuration Reload** - Operations only, no config management

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ LLM Gateway Components                                      │
│ ├─ LiteLLM (port 4000)                                      │
│ ├─ vLLM (port 8000)                                         │
│ └─ Other services                                           │
└──────────────────┬──────────────────────────────────────────┘
                   │ (Docker socket / REST calls)
                   │
        ┌──────────▼─────────┐
        │ This Dashboard     │
        │ Data Provider      │
        ├───────────────────┤
        │ ✓ Component info  │
        │ ✓ Action control  │
        │ ✓ Logs            │
        │ ✓ Manifests       │
        └──────────┬────────┘
                   │ (HTTP REST / SSE)
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
 Vue UI      External       Monitoring
(local UI)   Tools          Project
                         (Prometheus)
                         (Grafana)
                         (Alerting)
```

## Endpoints Provided

### Components (Action Control)
```
GET  /api/v1/components              List all components
GET  /api/v1/components/{id}         Component details
POST /api/v1/components/{id}/actions/{action_id}  Execute action
GET  /api/v1/components/{id}/actions/{action_id}/status/{execution_id}  Poll status
```

### Manifests (Metadata Discovery)
```
GET  /api/v1/manifests               List enabled components with display config
GET  /api/v1/manifests/{id}          Component manifest with full metadata
```

### Logs (Event Stream)
```
GET  /api/v1/logs                    Query logs with filters
GET  /api/v1/logs/stream             Real-time SSE stream
```

### Health (Liveness Check)
```
GET  /healthz                        Dashboard liveness
```

## External Responsibilities

### Monitoring Project (Separate)
- **Prometheus:** Metrics collection, time-series storage
- **Grafana:** Dashboards, visualization
- **Alerting:** Rules, notifications (PagerDuty, Slack, etc.)
- **Health Checks:** Active probes to component endpoints
- **Metrics:** Query, aggregate, correlate

### External Tools
- **Git/Version Control:** Configuration management
- **CI/CD:** Deployment automation
- **Container Registry:** Image management

## Technology Stack

**This Project:**
- FastAPI (REST API framework)
- Pydantic (Data validation)
- Python asyncio (Async operations)
- Docker socket (Container control)
- YAML (Component manifests)

**NOT in This Project:**
- Prometheus client/server
- Grafana
- Time-series database
- Alert manager

## Design Principles

1. **Minimal Scope** - Data provider only, no monitoring
2. **Read Most Data** - Logs and status are read-heavy
3. **Write Light Actions** - Only action execution is write (rare)
4. **External Integration** - Works with monitoring stack, doesn't replace it
5. **Stateless** - Logs in circular buffer (no persistence), state in containers

## What's NOT Implemented

- Config reload endpoint (deferred - operations only)
- Persistent log storage (in-memory circular buffer)
- Authentication/authorization (Phase 3 Part 3 - optional)
- Frontend UI (separate Vue project)
- Metrics export format (external monitoring handles this)

---

**Version:** Phase 3 Part 2 Complete
**Last Updated:** 2026-03-27
