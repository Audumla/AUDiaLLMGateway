# Backend Benchmark Results

Store per-run benchmark artifacts here once the benchmark workspace is fully
moved out of the gateway spec tree.

Suggested contents:

- `*.jsonl` run outputs
- `*.json` summarized result snapshots
- `benchmark-profiles.yaml` named model/config profiles for repeatable runs
- `backend-catalog.yaml` source/release catalog for maintained backend channels
- `engine-version-catalog.yaml` engine/version compatibility catalog
- `*.md` short analysis notes tied to a single session
- `*.txt` captured command output when it matters for reproducibility

This folder is intentionally separate from the gateway runtime docs so backend
investigation can evolve independently.
