# Spec 002: Model Catalog and Configuration Lifecycle

## Spec Level

Mid-level

## Status

Draft

## Project Name

AUDiaLLMGateway

## Purpose

Define the target model catalog schema, deployment routing model, config generation
lifecycle, and auto-reload behaviour that replace the current manual
`generate + restart` workflow.

This spec extends the phase 1 foundation (spec-001) without breaking the existing
config layer. It is the authoritative design guide for the next build-out phase.

## Goals

1. Maintain a single backend-agnostic model catalog as the only place a model is
   defined — no duplicating model semantics into per-backend files.
2. Allow each model to declare one or more deployment targets
   (`llama_swap`, `vllm`, `unsloth`, future backends) with backend-specific
   parameters isolated to those declarations.
3. Support model load groups that are backend-agnostic in definition but translate
   to native group semantics for each installed backend.
4. Auto-detect changes to any source config layer and regenerate only the affected
   generated files without manual intervention.
5. Restart only the components whose generated config actually changed, leaving
   unaffected components running.
6. Enable `llama-swap` live config monitoring (`--watch`) so model-level changes
   are picked up without a process restart.
7. Default all components to enabled; let users narrow the selection during the
   bootstrap install rather than requiring opt-in for each component.
8. Make port and host bindings trivially editable in a single override file with
   changes auto-detected and propagated.
9. Keep the config system understandable — no hidden magic, full audit trail in
   generated files and change logs.

## Non-Goals

1. No GUI config editor in this phase.
2. No automatic model file download triggered by config change (download remains
   a deliberate user action).
3. No cloud-aware routing or multi-host orchestration.
4. No breaking changes to the existing `models.base.yaml` schema — extensions only.

---

## Model Catalog Schema

### Existing structure (preserved)

The current `models.base.yaml` schema is the foundation and is not replaced:

- `frameworks` — framework capability declarations (`llama_cpp`, `vllm`)
- `presets.contexts` — named context sizes (`32k`, `64k`, `96k`, `256k`)
- `presets.gpu_profiles` — named GPU placement configs (device, split mode, layers)
- `presets.runtime_profiles` — named inference behaviour configs (jinja, nothink, coder,
  vision, batch, cache settings)
- `model_profiles` — per-model definitions with `defaults`, `artifacts`, `deployments`
- `exposures` — stable LiteLLM gateway alias → model_profile + deployment bindings
- `load_groups` — activity-oriented model residency groups

### Extensions required by this spec

#### 1. Deployment targets per model profile

Each entry in `model_profiles[*].deployments` must support multiple named
deployment blocks, one per backend type the model can run on. The `framework`
field identifies which backend runtime handles it; the `transport` field identifies
the proxy layer above it.

```yaml
model_profiles:
  my_model:
    deployments:
      llamacpp_vulkan:
        framework: llama_cpp
        transport: llama-swap
        llama_swap_model: my-model-id
        backend_model_name: my-model-id
        # backend-specific overrides (optional — falls back to model defaults)
        context_preset: 64k
        gpu_preset: gpu1
        runtime_presets: [jinja, nothink]

      llamacpp_cpu:
        framework: llama_cpp
        transport: llama-swap
        llama_swap_model: my-model-id-cpu
        backend_model_name: my-model-id-cpu
        gpu_preset: ~          # no GPU for CPU deployment

      vllm_primary:
        framework: vllm
        transport: direct      # vllm speaks directly to LiteLLM, no llama-swap
        gpu_memory_utilization: 0.85
        max_model_len: 32768
        dtype: bfloat16

      unsloth_primary:
        framework: unsloth
        transport: direct
        load_in_4bit: true
        max_seq_length: 32768
```

The config generator emits a deployment into a backend's generated config only if:

- the deployment's `framework` is installed (present in `install-state.json`)
- the deployment's `transport` layer is installed and enabled

A model with both `llamacpp_vulkan` and `vllm_primary` deployments will appear in
both the `llama-swap` generated config and the vllm-facing LiteLLM section when
both backends are installed.

#### 2. Deployment-agnostic load groups

`load_groups` are defined independently of any backend. The generator translates
group semantics into the native mechanism of each installed transport:

| Group field | llama-swap translation | Future native llama.cpp groups |
|---|---|---|
| `persistent: true` | llama-swap `group` with model listed | TBD — native resident list |
| `persistent: false` | llama-swap group with swap-on-demand | TBD |
| `exclusive: true` | only one member runs at a time | TBD |
| `swap: true` | unload non-active group members on switch | TBD |

When llama.cpp gains native group/persistence support, the generator can emit that
natively without changing the catalog definition.

#### 3. Backend selector in exposures

Each `exposures` entry must name which deployment the gateway alias routes to:

```yaml
exposures:
  - stable_name: local/my_model
    model_profile: my_model
    deployment: llamacpp_vulkan   # which deployment block to route through
    mode: chat
```

If the named deployment is not installed, the exposure is omitted from the
generated LiteLLM config and a warning is recorded.

#### 4. Component-enabled flags per deployment

A deployment block may be disabled without removing it from the catalog:

```yaml
deployments:
  vllm_primary:
    framework: vllm
    enabled: false   # skipped by generator even if vllm is installed
```

#### 5. Framework registry in stack config

`stack.base.yaml` gains a `frameworks` section mapping framework names to install
state keys and health endpoints, so the generator knows how to resolve each
deployment's framework:

```yaml
frameworks:
  llama_cpp:
    state_key: llama_cpp
    transport: llama-swap
  vllm:
    state_key: vllm
    transport: direct
    base_url_template: "http://{host}:{port}/v1"
  unsloth:
    state_key: unsloth
    transport: direct
    base_url_template: "http://{host}:{port}/v1"
```

---

## Config Generation Lifecycle

### Source layers (read-only inputs)

```
config/project/stack.base.yaml          project defaults
config/project/models.base.yaml         project model catalog
config/project/llama-swap.base.yaml     llama-swap substrate defaults
config/project/mcp.base.yaml            MCP scaffold

config/local/stack.override.yaml        machine overrides (ports, hosts, flags)
config/local/models.override.yaml       machine model additions or overrides
config/local/llama-swap.override.yaml   machine llama-swap substrate overrides

state/install-state.json               installed components and binary paths
```

### Generated outputs (derived, never hand-edited)

```
config/generated/llama-swap/llama-swap.generated.yaml
config/generated/litellm/litellm.config.yaml
config/generated/mcp/litellm.mcp.client.json
config/generated/nginx/nginx.conf
config/generated/systemd/audia-gateway.service
```

### Generation rules

1. Every generated file records a hash of its source inputs in a header comment.
2. The generator compares the new output against the existing file before writing.
   If the content is identical the file is not touched (mtime preserved).
3. The generator is idempotent — running it twice with no source changes produces
   no file modifications.
4. Deployments whose framework is not installed are silently skipped. A summary of
   skipped deployments is written to `state/generate-report.json`.

---

## Auto-Detection and Selective Reload

### Watcher

A lightweight config watcher runs as part of the orchestrator process or as a
standalone daemon thread. It polls the mtime of every source config file at a
configurable interval (default: 5 seconds).

Source files monitored:

- all files under `config/project/`
- all files under `config/local/`
- `state/install-state.json`

When any mtime changes:

1. Run the full generation pass.
2. Compare each generated file against its pre-generation snapshot (content hash).
3. For each file that changed, identify the owning component and apply the
   appropriate reload action.

### Reload actions per component

| Generated file | Reload action |
|---|---|
| `llama-swap.generated.yaml` | No restart — llama-swap `--watch` picks up the file automatically |
| `litellm.config.yaml` | Graceful restart of litellm process only |
| `nginx.conf` | `nginx -s reload` (no full restart) |
| Port or host change in any config | Restart the affected component (port change requires socket rebind) |
| `audia-gateway.service` | Write only; user must run `systemctl daemon-reload` (service unit changes are not auto-applied) |

### Port change detection

After generation, the watcher compares the effective network bindings from the
merged stack config against the previously recorded bindings in
`state/runtime-bindings.json`. If any binding changed, the watcher restarts the
component that owns that binding.

`state/runtime-bindings.json` is written by the generator on each pass and records
the resolved host/port for each component.

### llama-swap `--watch` mode

llama-swap is always launched with `--watch` enabled. This allows the watcher to
push model-level config changes (new model added, context size changed, GPU preset
updated) to a running llama-swap process without a restart. The watcher does not
restart llama-swap unless a substrate-level change occurs (executable path,
bind address, port, or healthCheckTimeout).

---

## Component Selection

### Default state

All components default to enabled. The current `default_enabled: false` entries
in `stack.base.yaml` are changed to `default_enabled: true` for all components
except those that require manual setup steps that cannot be automated
(e.g., `vllm` on Windows where it is genuinely unsupported).

```yaml
components:
  python_runtime:       required: true,  default_enabled: true
  gateway_python_deps:  required: true,  default_enabled: true
  llama_cpp:            required: true,  default_enabled: true
  llama_swap:           required: true,  default_enabled: true
  nginx:                required: false, default_enabled: true
  vllm:                 required: false, default_enabled: true   # Linux/macOS only
  unsloth:              required: false, default_enabled: true   # Linux/macOS only
  models:               required: false, default_enabled: true
```

Platform-aware defaults: the installer suppresses components that cannot function
on the current platform (e.g., vllm and unsloth on Windows) regardless of the
`default_enabled` value. The user is not asked about unsupported components.

### Interactive selection during bootstrap

The bootstrap install script presents a component menu before downloading anything.
The selection is persisted to `config/local/components.yaml` (protected from
updates).

```
AUDia LLM Gateway — component selection
  [x] python_runtime        required
  [x] gateway_python_deps   required
  [x] llama_cpp             on
      Backends:
        [x] cpu
        [x] vulkan
        [x] rocm
        [ ] cuda              (not available on this platform)
  [x] llama_swap            on
  [x] nginx                 on
  [x] vllm                  on
  [x] models                on

Space: toggle   Enter: confirm   Q: quit
```

### Persistent component selection file

`config/local/components.yaml` records the user's choices and is the authoritative
source for component selection on all subsequent `install components` and `update`
operations:

```yaml
selected_components:
  llama_cpp:
    enabled: true
    profiles:
      - linux-cpu
      - linux-vulkan
      - linux-rocm
  llama_swap:
    enabled: true
  nginx:
    enabled: true
  vllm:
    enabled: false
  unsloth:
    enabled: false
  models:
    enabled: true
```

On update, the installer merges the project's new `default_enabled` values against
the recorded selection: newly added components that were not present in the previous
selection are installed if `default_enabled: true` and recorded in
`components.yaml`.

---

## Port and Host Management

### Single point of configuration

All network port bindings remain in `config/project/stack.base.yaml` under
`network`. Machine-specific overrides go in `config/local/stack.override.yaml`.
No port or host literal appears in any other project file.

Backend service hosts (`litellm`, `llama_swap`, `backend_bind_host`) are
**pinned to `127.0.0.1`** in `stack.base.yaml`. These services are only
reachable via the nginx reverse proxy and must not be exposed directly on the
network. `public_host` (used for nginx landing page links and any externally
advertised URLs) is **not** hardcoded — `config_loader.py` auto-detects the
machine's outbound IPv4 address at config-load time. If the machine has exactly
one non-loopback IPv4 interface the detected address is used; otherwise
`127.0.0.1` is used as a safe fallback. `public_host` can be pinned explicitly
in `config/local/stack.override.yaml`.

### Seeded override file

`config/local/` is seeded with commented template files on first run. Both paths
create the same three files if absent:

| File | Seeded by |
| ---- | --------- |
| `config/local/stack.override.yaml` | `postinstall.sh` (native) · `gateway-entrypoint.sh` (Docker) |
| `config/local/models.override.yaml` | `postinstall.sh` (native) · `gateway-entrypoint.sh` (Docker) |
| `config/local/env` | `postinstall.sh` (native) · `gateway-entrypoint.sh` (Docker) |

Port settings are commented out with project defaults shown as reference. Host
values are omitted from the seed because they are auto-detected; users only need
to add them if overriding the detected address. Files are only written if absent —
user edits are never overwritten.

### Auto-propagation

When the watcher detects a port or host change in the merged stack config:

1. It regenerates all affected generated configs.
2. It restarts the component whose binding changed.
3. It records the new bindings in `state/runtime-bindings.json`.

Downstream components that depend on the changed binding (e.g., LiteLLM upstream
URL pointing at llama-swap) are also regenerated and reloaded.

---

## nginx Reverse Proxy

### Architecture

nginx is the only externally-facing service. litellm and llama-swap bind to
`127.0.0.1` and are not directly reachable from the network. All public traffic
enters through nginx on port 8080 (default).

### Routes

| nginx path | Upstream | Notes |
| --- | --- | --- |
| `/` | static `config/generated/nginx/index.html` | Landing page with links to all endpoints |
| `/v1/` | litellm | OpenAI-compatible API |
| `/litellm/` | litellm | Full litellm API under prefix |
| `/ui/` | litellm | LiteLLM admin UI — `proxy_redirect` rewrites absolute redirect to public host |
| `/health` | litellm `/health` | |
| `/llamaswap/` | llama-swap | Path prefix stripped; `proxy_redirect` rewrites upstream Location headers to `/llamaswap/` prefix so redirect chains stay inside the proxy |
| `/llamaswap-health` | llama-swap `/health` | |

The `server_name` directive is set to `_` (catch-all) so any `Host` header is
accepted. The listen directive binds to all interfaces on the configured port.

### Authentication

LiteLLM is configured with `general_settings.no_auth: true` so all endpoints
are accessible without a bearer token through the nginx proxy. The
`LITELLM_MASTER_KEY` env var is still set in `config/local/env` for internal
admin operations but is not enforced on incoming requests.

### Landing page

`config/generated/nginx/index.html` is regenerated on each `generate-configs`
run. All links use `network.public_host` (auto-detected LAN IP) so they resolve
correctly from a remote browser. The page lists every proxied endpoint with its
description and type.

---

## llama-swap Monitoring

llama-swap is launched with:

```
--watch           monitor the config file and reload models on change
--log-level info  structured log output
```

The `--watch` flag is unconditional — it is always included in the generated
launch command regardless of platform or override settings. Local overrides may
add extra llama-swap args but may not remove `--watch`.

The watcher therefore never needs to restart llama-swap for model-level changes.
It restarts llama-swap only for substrate-level changes: executable path, bind
address, port, or top-level llama-swap settings like `healthCheckTimeout`.

---

## Implementation Mapping

The following components require changes or creation:

### Changes to existing components

- `src/launcher/config_loader.py`
  - Generator becomes deployment-aware: reads `install-state.json` to determine
    which frameworks are present and skips deployments for absent frameworks
  - Writes `state/generate-report.json` summarising skipped deployments
  - Records content hashes in `state/generate-hashes.json` for change detection
  - Records resolved network bindings in `state/runtime-bindings.json`
  - Adds `--watch` flag to llama-swap launch args in generated systemd/process config

- `src/installer/release_installer.py`
  - Reads `config/local/components.yaml` for component selection
  - Writes selection back to `config/local/components.yaml` after install
  - Interactive component selection menu in bootstrap path (non-interactive fallback
    uses `default_enabled` values)

- `config/project/stack.base.yaml`
  - All `default_enabled` values set to `true` except platform-unsupported components
  - Add `frameworks` registry section

- `scripts/postinstall.sh`
  - Generates and seeds `config/local/stack.override.yaml` with commented defaults
  - Generates and seeds `config/local/components.yaml` with platform-aware defaults

### New components

- `src/launcher/watcher.py`
  - Polls source config mtimes at configurable interval (default 5s)
  - Triggers generation pass on any change
  - Diffs generated outputs against pre-generation hashes
  - Applies per-component reload action for each changed output
  - Detects port/host binding changes and restarts affected components

- `src/launcher/reload.py`
  - Per-component reload action implementations
  - `reload_litellm(root)` — graceful restart of the litellm process
  - `reload_nginx(root)` — `nginx -s reload`
  - `reload_llama_swap(root)` — full restart (substrate-level change only)
  - `restart_component(root, name)` — generic stop + start for other components

---

## Operational Flows

### First install (interactive)

1. Bootstrap script runs.
2. Component selection menu shown — all supported components pre-checked.
3. User adjusts selection, confirms.
4. `install stack` runs (venv, pip).
5. `install components` runs selected components.
6. `generate` runs — emits configs for installed components only.
7. `config/local/stack.override.yaml` seeded with commented port reference (hosts auto-detected; not seeded).
8. `config/local/components.yaml` written with user's selection.
9. Service registered and started.

### Config change (runtime)

1. User edits `config/local/stack.override.yaml` (e.g., changes litellm port).
2. Watcher detects mtime change within 5 seconds.
3. Full generation pass runs.
4. Watcher diffs outputs — `litellm.config.yaml` changed, `runtime-bindings.json`
   shows litellm port changed.
5. Litellm process restarted with new config.
6. llama-swap not touched (its config unchanged).

### Model change (runtime)

1. User edits `config/local/models.override.yaml` (e.g., adds a new model).
2. Watcher detects change.
3. `llama-swap.generated.yaml` regenerated with the new model entry.
4. llama-swap `--watch` picks up the new file and loads the new model definition.
5. LiteLLM config regenerated with the new exposure.
6. LiteLLM restarted to pick up the new model alias.

### Update

1. New release archive downloaded.
2. Managed paths replaced from archive.
3. `config/local/` preserved untouched.
4. `config/local/components.yaml` read for component selection.
5. New components added to selection if `default_enabled: true` and not previously
   seen.
6. `install components` runs for newly added or updated components.
7. `generate` runs — new catalog entries appear automatically.
8. Watcher detects generated file changes and reloads affected components.

---

## Acceptance Criteria

This spec is implemented when:

1. A model added to `config/local/models.override.yaml` appears in the running
   llama-swap and LiteLLM gateway within 10 seconds without a manual command.
2. A port change in `config/local/stack.override.yaml` causes only the affected
   component to restart; other components continue without interruption.
3. llama-swap is always launched with `--watch` and picks up model-level config
   changes without a process restart.
4. The bootstrap install menu is shown on first install and the selection is
   persisted to `config/local/components.yaml`.
5. A fresh package install (RPM or DEB) with no previous state runs the component
   menu (or accepts defaults non-interactively), downloads all selected binaries,
   generates all configs, and starts the service without manual steps.
6. A model with `vllm_primary` deployment appears in the LiteLLM config only when
   vllm is installed; it is absent and a warning is recorded when vllm is not
   installed.
7. `state/generate-report.json` accurately records which deployments were skipped
   and why after each generation pass.

---

## Known Gaps and Open Questions

1. **unsloth integration**: unsloth Studio's OpenAI-compatible server API is not
   yet fully characterised. The deployment block schema reserves `framework: unsloth`
   but the generator will not emit unsloth config until that API is confirmed.

2. **native llama.cpp group support**: llama.cpp group/persistence APIs are under
   development. The load_groups catalog definition is designed to be
   backend-agnostic; the generator will emit the native form when the API
   stabilises.

3. **watcher process model**: whether the watcher runs as a thread inside the
   orchestrator or as a separate lightweight process is an implementation choice.
   The watcher must not block the main start/stop command surface.

4. **interactive menu in package postinstall**: RPM/DEB postinstall runs
   non-interactively. The menu is only shown by the bootstrap script. Package
   installs use `default_enabled` values adjusted for the detected platform.
   Users adjust the selection post-install by editing `config/local/components.yaml`
   and running `install components`.

5. **watcher polling vs inotify**: Linux supports inotify for true event-driven
   file watching. The initial implementation may use polling for portability across
   Windows, Linux, and macOS. A later optimisation can use platform-native watchers
   through `watchdog` or equivalent.

---

## Next Specs

1. Spec 003: Config watcher implementation detail
2. Spec 004: Interactive component selection and `components.yaml` format
3. Spec 005: vLLM deployment integration
4. Spec 006: unsloth deployment integration
5. Spec 007: Native llama.cpp group support migration
