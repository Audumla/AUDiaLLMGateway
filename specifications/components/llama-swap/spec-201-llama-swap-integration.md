# Spec 201: llama-swap Integration

## Scope

`llama-swap` is the local backend router and the canonical model catalog source.

## Config Structure

- project baseline catalog in `config/project/llama-swap.base.yaml`
- machine-local extensions or overrides in `config/local/llama-swap.override.yaml`
- generated effective runtime config in `config/generated/llama-swap.generated.yaml`

## Expectations

- native `llama-server` launch arguments remain explicit
- local overrides may add models, macros, and groups
- generated config must reflect merged project and local layers

