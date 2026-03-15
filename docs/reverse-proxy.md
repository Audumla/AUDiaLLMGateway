# Reverse Proxy

This repo includes an optional nginx config at `config/nginx/nginx.conf`.

## Purpose

Expose one front-door host while keeping:

- LiteLLM as the main OpenAI-compatible API
- the full raw `llama-swap` API available for monitoring and diagnostics

## Route layout

Assuming nginx listens on `http://127.0.0.1:8080`:

- `http://127.0.0.1:8080/v1/...`
  - forwarded to LiteLLM
- `http://127.0.0.1:8080/litellm/...`
  - forwarded to LiteLLM with the prefix stripped
- `http://127.0.0.1:8080/llamaswap/...`
  - forwarded to `llama-swap` with the prefix stripped

## Examples

- LiteLLM models:
  - `/v1/models`
- LiteLLM health:
  - `/litellm/health`
  - `/health`
- llama-swap health:
  - `/llamaswap/health`
  - `/llamaswap-health`
- llama-swap logs:
  - `/llamaswap/logs`
  - `/llamaswap/logs/stream`
  - `/llamaswap/logs/stream/proxy`
  - `/llamaswap/logs/stream/upstream`
- llama-swap running model:
  - `/llamaswap/running`
- llama-swap upstream details:
  - `/llamaswap/upstream/<model_id>`

## Notes

- `/v1/*` is intentionally reserved for LiteLLM.
- `llama-swap` also exposes OpenAI-compatible `/v1/*`, but this config does not put those at the root because they would collide with LiteLLM.
- For streaming endpoints, nginx buffering is disabled.

## Running nginx on Windows

1. Install nginx for Windows.
2. Copy or reference `config/nginx/nginx.conf`.
3. Start nginx with that config file.

Example:

```powershell
nginx -p H:\development\projects\AUDia\AUDiaLLMGateway\config\nginx -c nginx.conf
```

Adjust paths as needed for your nginx installation layout.

