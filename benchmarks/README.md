# AUDia Backend Benchmarks

This tree is the separate home for backend build, compatibility, and performance
work.

The intent is to keep benchmark investigation isolated from the main gateway
implementation so the results can later be promoted into their own project
without dragging the gateway codebase along with them.

## Scope

- Backend build/run recipes
- Compatibility notes by GPU and backend family
- Performance results and reproducible run logs
- Known failure modes and remediation steps
- Optimization roadmap and decision matrix
- Lifecycle scripts for repeatable backend start/stop/reset/wait/collect flow
- Windows-native PowerShell companions for local validation and orchestration
- One-command PowerShell wrapper for repeatable benchmark runs

## Current migration state

The long-form benchmark history is still being migrated from the gateway
specification docs.

Canonical reference docs during the transition:

- [Performance history](../specifications/docs/llm-backend-performance.md)
- [Backend build catalog](../specifications/docs/llm-backend-builds.md)
- [Backend version reference](../specifications/docs/BACKEND_VERSIONS.md)
- [Backend source catalog](docs/backend-catalog.md)
- [Engine version catalog](docs/engine-version-catalog.md)
- [Optimization roadmap](docs/optimization-roadmap.md)
- [Latest run notes](docs/latest-run-notes.md)
- [Benchmark profiles](data/backend-benchmarks/benchmark-profiles.yaml)
- [Backend catalog data](data/backend-benchmarks/backend-catalog.yaml)
- [Engine version catalog data](data/backend-benchmarks/engine-version-catalog.yaml)
- [Optimization matrix](data/backend-benchmarks/optimization-matrix.yaml)
- [Compatibility matrix](data/backend-benchmarks/compatibility-matrix.yaml)

New benchmark work should be added under this tree rather than into the main
gateway docs.
