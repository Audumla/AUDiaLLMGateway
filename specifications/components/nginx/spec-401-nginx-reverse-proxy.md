# Spec 401: nginx Reverse Proxy

## Scope

nginx is an optional component that exposes one front-door host for LiteLLM and raw `llama-swap` monitoring paths.

## Expectations

- `/v1/*` routes to LiteLLM
- namespaced `llama-swap` routes remain available for monitoring and logs
- nginx remains optional and user-selectable during install

