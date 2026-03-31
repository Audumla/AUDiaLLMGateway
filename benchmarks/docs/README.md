# Benchmark Docs

This directory is the documentation entry point for backend testing work.

Use this area for:

- repeatable benchmark procedures
- backend compatibility matrices
- build recipes and troubleshooting notes
- per-run result summaries
- optimization roadmap and phase tracking
- latest run notes
- backend source and release catalog
- engine version catalog
- compatibility matrix
- benchmark profile catalog for model/config swap-ins

Current live results and historical notes are still available in the gateway
specification docs during the migration:

- [llm-backend-performance.md](../../specifications/docs/llm-backend-performance.md)
- [llm-backend-builds.md](../../specifications/docs/llm-backend-builds.md)
- [optimization-roadmap.md](optimization-roadmap.md)
- [latest-run-notes.md](latest-run-notes.md)
- [backend-catalog.md](backend-catalog.md)
- [engine-version-catalog.md](engine-version-catalog.md)
- [compatibility-matrix.yaml](../data/backend-benchmarks/compatibility-matrix.yaml)
- [benchmark-profiles.yaml](../data/backend-benchmarks/benchmark-profiles.yaml)
- [backend-catalog.yaml](../data/backend-benchmarks/backend-catalog.yaml)
- [engine-version-catalog.yaml](../data/backend-benchmarks/engine-version-catalog.yaml)

The benchmark workspace is intentionally separate from the gateway runtime
docs, even though it currently informs which backends should be built into the
gateway.
