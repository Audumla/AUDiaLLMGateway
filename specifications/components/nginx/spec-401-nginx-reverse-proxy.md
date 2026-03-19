# Spec 401: nginx Reverse Proxy

## Scope

nginx is an optional component that exposes one front-door host for the full LiteLLM API and the full raw `llama-swap` API.

## Expectations

- `/v1/*` routes to LiteLLM as the primary OpenAI-compatible root
- `/litellm/*` exposes the full LiteLLM surface
- `/llamaswap/*` exposes the full `llama-swap` surface
- `/ui/` and `/litellm-asset-prefix/*` must stay fully proxied so the LiteLLM admin UI loads without broken asset paths
- `/health`, `/llamaswap-health`, and when enabled `/vllm-health` must remain reachable through nginx
- nginx remains optional and user-selectable during install
- nginx runtime config is generated from the central network config and written under `config/generated/nginx/nginx.conf`
