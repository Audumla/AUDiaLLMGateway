# Dashboard API Reference

Complete API specification for the AUDia LLM Gateway Dashboard control panel. This document shows all data structures and response examples for Vue frontend integration.

---

## Components Endpoints

### GET `/api/v1/components`

List all monitored gateway components with their current status and available actions.

**Response:**
```json
{
  "components": [
    {
      "id": "litellm",
      "display_name": "LiteLLM Gateway",
      "icon": "gateway",
      "enabled": true,
      "health": {
        "endpoint": "/health",
        "expect_status": 200,
        "timeout_s": 5
      },
      "connection": {
        "host": "localhost",
        "port": 4000,
        "timeout_s": 5
      },
      "actions": [
        {
          "id": "reload",
          "label": "Reload Configuration",
          "type": "shell",
          "confirm": true
        },
        {
          "id": "restart",
          "label": "Restart Service",
          "type": "docker_restart",
          "confirm": true
        }
      ]
    },
    {
      "id": "prometheus",
      "display_name": "Prometheus",
      "icon": "server",
      "enabled": true,
      "health": {
        "endpoint": "/-/healthy",
        "expect_status": 200,
        "timeout_s": 5
      },
      "connection": {
        "host": "localhost",
        "port": 9090,
        "timeout_s": 5
      },
      "actions": [
        {
          "id": "restart",
          "label": "Restart Prometheus",
          "type": "docker_restart",
          "confirm": true
        }
      ]
    }
  ],
  "count": 2,
  "timestamp": "2026-03-27T01:46:04.894511+00:00"
}
```

**Use in Vue:**
- Display component cards for each item in `components`
- Show health/connection info in component details
- List available actions as buttons under each component

---

### GET `/api/v1/components/{component_id}`

Get detailed configuration for a specific component.

**URL Parameters:**
- `component_id` (string, required) - Component ID (e.g., "litellm")

**Response:**
```json
{
  "id": "litellm",
  "display_name": "LiteLLM Gateway",
  "icon": "gateway",
  "enabled": true,
  "health": {
    "endpoint": "/health",
    "expect_status": 200,
    "timeout_s": 5
  },
  "connection": {
    "host": "localhost",
    "port": 4000,
    "timeout_s": 5
  },
  "actions": [
    {
      "id": "reload",
      "label": "Reload Configuration",
      "type": "shell",
      "confirm": true,
      "container": null,
      "command": "systemctl reload litellm"
    },
    {
      "id": "restart",
      "label": "Restart Service",
      "type": "docker_restart",
      "confirm": true,
      "container": "litellm",
      "command": null
    }
  ],
  "timestamp": "2026-03-27T01:46:07.841698+00:00"
}
```

**Error Responses:**
- `404 Not Found` - Component not found

---

### POST `/api/v1/components/{component_id}/actions/{action_id}`

Trigger an action on a component. Returns execution tracking info.

**URL Parameters:**
- `component_id` (string, required) - Component ID
- `action_id` (string, required) - Action ID

**Query Parameters:**
- `request_id` (string, optional) - Request tracking ID for logging

**Response (Successful Execution):**
```json
{
  "execution_id": "exec-123",
  "component_id": "litellm",
  "action_id": "restart",
  "state": "completed",
  "started_at": "2026-03-27T01:46:10.659737+00:00",
  "completed_at": "2026-03-27T01:46:10.659737+00:00",
  "duration_seconds": 2.5,
  "success": true,
  "message": "Container restarted successfully",
  "error": null,
  "result": {
    "success": true,
    "action_id": "restart",
    "component_id": "litellm",
    "execution_id": "exec-123",
    "started_at": "2026-03-27T01:46:10.659737+00:00",
    "completed_at": "2026-03-27T01:46:10.659737+00:00",
    "message": "Container restarted successfully",
    "error": null,
    "result": null
  }
}
```

**Response (Shell Command with Output):**
```json
{
  "execution_id": "exec-456",
  "component_id": "litellm",
  "action_id": "reload",
  "state": "completed",
  "started_at": "2026-03-27T01:46:13.603882+00:00",
  "completed_at": "2026-03-27T01:46:13.603882+00:00",
  "duration_seconds": 1.2,
  "success": true,
  "message": "Configuration reloaded",
  "error": null,
  "result": {
    "success": true,
    "action_id": "reload",
    "component_id": "litellm",
    "execution_id": "exec-456",
    "started_at": "2026-03-27T01:46:13.603882+00:00",
    "completed_at": "2026-03-27T01:46:13.603882+00:00",
    "message": "Configuration reloaded",
    "error": null,
    "result": {
      "returncode": 0,
      "stdout": "Reloading configuration...\nConfiguration loaded from /etc/litellm/config.yaml\n",
      "stderr": ""
    }
  }
}
```

**Response (Failed Execution):**
```json
{
  "execution_id": "exec-789",
  "component_id": "litellm",
  "action_id": "restart",
  "state": "failed",
  "started_at": "2026-03-27T01:46:20.950381+00:00",
  "completed_at": "2026-03-27T01:46:20.950381+00:00",
  "duration_seconds": 0.5,
  "success": false,
  "message": "",
  "error": "Container not found",
  "result": {
    "success": false,
    "action_id": "restart",
    "component_id": "litellm",
    "execution_id": "exec-789",
    "started_at": "2026-03-27T01:46:20.950381+00:00",
    "completed_at": "2026-03-27T01:46:20.950381+00:00",
    "message": "",
    "error": "Container not found",
    "result": null
  }
}
```

**Error Responses:**
- `404 Not Found` - Component or action not found
- `500 Internal Server Error` - Execution error (check `error` field in response)

**Use in Vue:**
- Show confirmation dialog if `action.confirm` is true
- Submit POST and track execution via `execution_id`
- Poll status endpoint for async operations
- Display result message and any errors to user
- Show command output (stdout/stderr) if available

---

### GET `/api/v1/components/{component_id}/actions/{action_id}/status/{execution_id}`

Poll the status of a previously triggered action.

**URL Parameters:**
- `component_id` (string, required)
- `action_id` (string, required)
- `execution_id` (string, required) - From action execution response

**Response:**
```json
{
  "execution_id": "exec-123",
  "action_id": "restart",
  "component_id": "litellm",
  "state": "completed",
  "started_at": "2026-03-27T01:46:10.659737+00:00",
  "completed_at": "2026-03-27T01:46:10.659737+00:00",
  "duration_seconds": 2.5,
  "success": true,
  "error": null
}
```

**State Values:**
- `pending` - Action queued but not started
- `running` - Action currently executing
- `completed` - Action finished successfully
- `failed` - Action failed (check `error` field)
- `cancelled` - Action was cancelled

**Use in Vue:**
- Poll this endpoint periodically after triggering an action
- Show loading indicator while state is `pending` or `running`
- Display result when state is `completed` or `failed`
- Stop polling once final state reached

---

## Action Types Reference

**docker_restart** - Restart a Docker container
- Fields: `container` (required)
- Example: `{"id": "restart", "type": "docker_restart", "container": "litellm"}`

**shell** - Execute a shell command
- Fields: `command` (required)
- Response includes `stdout`, `stderr`, `returncode`
- Example: `{"id": "reload", "type": "shell", "command": "systemctl reload litellm"}`

**http_post** - POST to component endpoint (Phase 3 Part 2)
- Fields: `endpoint`, `body` (optional)

**process_signal** - Send signal to process (Phase 3 Part 2)
- Fields: `signal` (required)

**config_reload** - Shell macro config reload (Phase 3 Part 2)
- Fields: `command` (required)

---

## Component Icons

Used in `icon` field of ComponentManifest. Frontend can map to Tabler Icons, FontAwesome, or custom SVGs:

- `gateway` - Network gateway icon
- `server` - Server/container icon
- `cpu` - CPU/processing icon
- `brain` - AI/LLM icon
- `storage` - Database/storage icon
- `monitor` - Monitoring/dashboard icon

---

## Integration Examples

### Vue Composition Example

```typescript
// Fetch all components
const response = await fetch('/api/v1/components')
const { components, timestamp } = await response.json()

// Render component cards
components.forEach(component => {
  // Display component.display_name with component.icon
  // List buttons for each action in component.actions
  // Show connection info: component.connection.host:component.connection.port
})

// Execute action
const actionResponse = await fetch(
  `/api/v1/components/${componentId}/actions/${actionId}?request_id=${uuid()}`,
  { method: 'POST' }
)
const execution = await actionResponse.json()

// Poll status
const interval = setInterval(async () => {
  const statusResponse = await fetch(
    `/api/v1/components/${componentId}/actions/${actionId}/status/${execution.execution_id}`
  )
  const status = await statusResponse.json()

  if (['completed', 'failed'].includes(status.state)) {
    clearInterval(interval)
    // Update UI with final result
  }
}, 1000)
```

---

## Data Type Definitions

### Component Manifest
```typescript
interface ComponentManifest {
  id: string
  display_name: string
  icon: string
  enabled: boolean
  health: HealthProbeConfig
  connection: ConnectionConfig
  actions: ActionConfig[]
}
```

### Health Probe Config
```typescript
interface HealthProbeConfig {
  endpoint: string
  expect_status: number
  timeout_s: number
}
```

### Connection Config
```typescript
interface ConnectionConfig {
  host: string
  port: number
  timeout_s: number
}
```

### Action Config
```typescript
interface ActionConfig {
  id: string
  label: string
  type: 'docker_restart' | 'shell' | 'http_post' | 'process_signal' | 'config_reload'
  confirm: boolean
  container?: string
  command?: string
  endpoint?: string
  signal?: string
}
```

### Execution Result
```typescript
interface ExecutionResult {
  execution_id: string
  component_id: string
  action_id: string
  state: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string (ISO 8601)
  completed_at?: string
  duration_seconds?: number
  success?: boolean
  message?: string
  error?: string
  result?: Record<string, any>
}
```

---

## Notes for Frontend

1. **Request Tracking** - Use `request_id` query param on action POST to correlate with backend logs
2. **Polling** - Don't poll too frequently; 1-2 second intervals recommended
3. **Timestamps** - All timestamps are ISO 8601 with UTC timezone
4. **Error Handling** - Always check `success` field and `error` message
5. **Confirmation** - Respect `confirm` field; show dialog before executing destructive actions
6. **State Display** - Map `state` values to UI states: loading, success, error
7. **Output Display** - Shell actions may have multi-line stdout/stderr; use `<pre>` or monospace font

