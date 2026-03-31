# Benchmark Lifecycle Scripts

These scripts are the execution layer for the benchmark workspace.

They are intentionally small and composable so benchmark runs can be repeated in
the same order without relying on ad hoc shell history.

Scripts:

- `preflight.sh` - validate the environment before a backend starts
- `kill_backend.sh` - stop a backend container or process cleanly
- `reset_rocm_state.sh` - restart the gateway container to clear dirty ROCm state
- `wait_ready.sh` - poll a health endpoint and stop early if the backend exits
- `collect_metrics.sh` - emit a compact JSON summary for a completed run

Windows-native companions:

- `preflight.ps1`
- `kill_backend.ps1`
- `reset_rocm_state.ps1`
- `wait_ready.ps1`
- `collect_metrics.ps1`
- `Invoke-BenchmarkRun.ps1` - one-command wrapper that chains preflight, stop, reset, start, wait, and optional metrics capture
