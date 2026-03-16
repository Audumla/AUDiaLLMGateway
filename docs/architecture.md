# Architecture

## Runtime topology

Client or tool
-> optional nginx
-> LiteLLM
-> llama-swap
-> local llama-server profiles from an installed llama.cpp runtime

Optional MCP path later:

Client or tool
-> LiteLLM MCP endpoint
-> configured MCP servers

## Config topology

Project layer:

- shipped in GitHub releases
- updated by release installer
- safe to replace during updates

Local layer:

- machine-owned
- never overwritten by release update
- used for paths, local model additions, site-specific overrides, and optional component choices

Generated layer:

- derived from project plus local config
- safe to regenerate at any time

## Installer topology

Bootstrap script
-> GitHub release archive
-> unpack bundle
-> sync managed files
-> preserve local files
-> install required and selected components
-> validate layered config
-> write install state

## State tracking

`state/install-state.json` is the installer-facing source for:

- installed version
- selected components
- install locations
- installed llama.cpp version/backend metadata
- validation warnings
- last successful update time

## Executable resolution

`load_stack_config()` resolves executable paths at config-load time using a
three-tier priority chain:

1. **YAML config** — an absolute path in `stack.override.yaml` wins outright.
2. **install-state.json** — `component_results.<name>.path` written by the
   component installer (`ensure_nginx`, `ensure_llama_swap`, etc.).  This is
   the primary mechanism for tools installed outside the venv (e.g. nginx via
   winget/apt, llama-swap via GitHub release).
3. **Fallback** — `shutil.which()` / bare name passed to the OS.

The Windows registry is intentionally **not** consulted.  Installers write the
resolved absolute path to `install-state.json` immediately after installing, so
the path is available in any subsequent process regardless of how the shell
environment was inherited.

Components that write to `install-state.json`:

- `ensure_llama_swap` → `component_results.llama_swap.path`
- `ensure_nginx`      → `component_results.nginx.path`
- `ensure_llama_cpp`  → `component_results.llama_cpp.executable_path`
- `ensure_models`     → `component_results.models.model_dir` + per-model paths
