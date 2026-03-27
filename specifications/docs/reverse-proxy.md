# Reverse Proxy

This repo includes an optional generated nginx config at `config/generated/nginx/nginx.conf`.

That file is generated from the central `network` settings in `config/project/stack.base.yaml`.

## Purpose

Expose one front-door host while keeping:

- LiteLLM fully proxied through nginx
- `llama-swap` fully proxied through nginx
- LiteLLM as the main OpenAI-compatible root API

## Route layout

Assuming nginx listens on `http://127.0.0.1:8080` and the default base URL
`/audia/llmgateway` is enabled:

- `http://127.0.0.1:8080/audia/llmgateway/v1/...`
  - forwarded to LiteLLM
- `http://127.0.0.1:8080/audia/llmgateway/litellm/...`
  - full LiteLLM API with the prefix stripped
- `http://127.0.0.1:8080/audia/llmgateway/llamaswap/...`
  - full `llama-swap` API with the prefix stripped

The root routes (`/v1/*`, `/litellm/*`, `/llamaswap/*`) remain available for
backward compatibility.

## Examples

- LiteLLM models:
  - `/audia/llmgateway/v1/models`
- LiteLLM examples:
  - `/audia/llmgateway/v1/models`
  - `/audia/llmgateway/litellm/health`
  - `/audia/llmgateway/litellm/routes`
  - `/audia/llmgateway/litellm/model/info`
  - `/audia/llmgateway/health`
- llama-swap health:
  - `/audia/llmgateway/llamaswap/health`
  - `/audia/llmgateway/llamaswap-health`
- llama-swap examples:
  - `/audia/llmgateway/llamaswap/v1/models`
  - `/audia/llmgateway/llamaswap/logs`
  - `/audia/llmgateway/llamaswap/logs/stream`
  - `/audia/llmgateway/llamaswap/logs/stream/proxy`
  - `/audia/llmgateway/llamaswap/logs/stream/upstream`
  - `/audia/llmgateway/llamaswap/running`
  - `/audia/llmgateway/llamaswap/upstream/<model_id>`

## Notes

- `/v1/*` is intentionally reserved for LiteLLM.
- Both products are fully proxied via their own namespaces: `/litellm/*` and `/llamaswap/*`.
- `llama-swap` also exposes OpenAI-compatible `/v1/*`, but this config intentionally keeps that under `/llamaswap/v1/*` so it does not collide with LiteLLM at the root.
- Buffering is disabled on the namespaced proxy routes so streaming responses continue to pass through cleanly.
- The base URL path is configured by `network.base_path` in `stack.base.yaml`
  (default `/audia/llmgateway`). Set it to `""` to disable base-path routing.

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
