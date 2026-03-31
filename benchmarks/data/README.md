# Benchmark Data

Use this tree for machine-readable benchmark outputs, captured runs, and
compatibility matrices.

Recommended layout:

- `backend-benchmarks/` for per-run JSON and CSV exports
- `notes/` for short machine-readable annotations
- `snapshots/` for hardware state captures tied to a benchmark session

The gateway repo currently keeps the authoritative historical outputs in:

- `specifications/data/backend-benchmarks/`

Future benchmark runs should land in this directory structure instead of the
gateway spec tree.

