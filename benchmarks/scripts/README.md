# Benchmark Scripts

This folder is reserved for helper scripts that keep benchmark work repeatable.

Planned helpers should be small and purpose-built:

- result summarizers
- matrix checks
- report generators
- threshold comparisons

The scripts should operate on the benchmark workspace, not on the main gateway
runtime code.

When a run needs to switch between the shared compare model and the real
Qwen3.5-27B dual-XTX target, use the named profiles in
`../data/backend-benchmarks/benchmark-profiles.yaml` as the source of truth
for model, topology, and backend-specific settings.
