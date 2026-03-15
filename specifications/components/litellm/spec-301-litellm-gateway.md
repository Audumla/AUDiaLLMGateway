# Spec 301: LiteLLM Gateway

## Scope

LiteLLM exposes stable external aliases in front of `llama-swap`.

## Config Structure

- project and local alias settings merge from stack config layers
- generated gateway config is written to `config/generated/litellm.config.yaml`

## Expectations

- aliases remain stable for clients
- gateway points to the local `llama-swap` endpoint
- generated config may include metadata describing upstream `llama-swap` model IDs

