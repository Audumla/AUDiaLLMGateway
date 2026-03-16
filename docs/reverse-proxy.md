# Reverse Proxy

This repo includes an optional generated nginx config at `config/generated/nginx/nginx.conf`.

That file is generated from the central `network` settings in `config/project/stack.base.yaml`.

## Purpose

Expose one front-door host while keeping:

- LiteLLM fully proxied through nginx
- `llama-swap` fully proxied through nginx
- LiteLLM as the main OpenAI-compatible root API

## Route layout

Assuming nginx listens on `http://127.0.0.1:8080`:

- `http://127.0.0.1:8080/v1/...`
  - forwarded to LiteLLM
- `http://127.0.0.1:8080/litellm/...`
  - full LiteLLM API with the prefix stripped
- `http://127.0.0.1:8080/llamaswap/...`
  - full `llama-swap` API with the prefix stripped

## Examples

- LiteLLM models:
  - `/v1/models`
- LiteLLM examples:
  - `/v1/models`
  - `/litellm/health`
  - `/litellm/routes`
  - `/litellm/model/info`
  - `/health`
- llama-swap health:
  - `/llamaswap/health`
  - `/llamaswap-health`
- llama-swap examples:
  - `/llamaswap/v1/models`
  - `/llamaswap/logs`
  - `/llamaswap/logs/stream`
  - `/llamaswap/logs/stream/proxy`
  - `/llamaswap/logs/stream/upstream`
  - `/llamaswap/running`
  - `/llamaswap/upstream/<model_id>`

## Notes

- `/v1/*` is intentionally reserved for LiteLLM.
- Both products are fully proxied via their own namespaces: `/litellm/*` and `/llamaswap/*`.
- `llama-swap` also exposes OpenAI-compatible `/v1/*`, but this config intentionally keeps that under `/llamaswap/v1/*` so it does not collide with LiteLLM at the root.
- Buffering is disabled on the namespaced proxy routes so streaming responses continue to pass through cleanly.

## Installation and startup

nginx is installed and started through the stack management system, not manually.

**Install** (run once, or after updates):

```powershell
python -m src.installer.release_installer install
```

This calls `ensure_nginx()`, installs nginx via the platform package manager
(winget on Windows, zypper/apt on Linux), and records the resolved executable
path in `state/install-state.json` under `component_results.nginx.path`.

**Start/stop** via the process manager:

```powershell
python -m src.launcher.process_manager --root . start-nginx
python -m src.launcher.process_manager --root . stop-nginx
python -m src.launcher.process_manager --root . start-all   # starts llama-swap + gateway + nginx
python -m src.launcher.process_manager --root . stop-all
```

The process manager reads `state/install-state.json` at startup to resolve the
nginx executable path — no shell reload or registry access required.

**nginx config** is generated from the central `network` section:

```powershell
python -m src.launcher.process_manager --root . generate-configs
```

nginx is started with `-p <workspace>` so all relative paths in the generated
config resolve against the workspace root, and `-e <path>` to set the error log
before nginx reads the config file.
