# Spec 201: llama-swap Integration

## Scope

`llama-swap` is the local backend router and generated backend runtime. The shared model catalog is the canonical source for model and preset semantics.

## Config Structure

- project backend substrate in `config/project/llama-swap.base.yaml`
- machine-local extensions or overrides in `config/local/llama-swap.override.yaml`
- generated effective runtime config in `config/generated/llama-swap/llama-swap.generated.yaml`

## Expectations

- native `llama-server` launch arguments remain explicit in generated output
- local overrides may replace backend macros or add machine-specific substrate details
- generated config must reflect merged project and local layers
- project model entries, load groups, and preset macro bodies must be generated from the shared model catalog rather than defined directly in the `llama-swap` project substrate
