# Spec 152: llama.cpp Profile Matrix

## Scope

Define the greenfield `llama.cpp` install-profile matrix used by the release installer.

## Requirements

- `llama.cpp` selection must be profile-based rather than a flat backend field
- each profile must declare:
  - `platform`
  - `support_tier`
  - `backend`
  - `version`
  - `asset_match_tokens`
  - optional `sidecar_files`
- the config must declare a default profile for each first-tier platform
- selecting `auto` must resolve to the configured default profile for the current platform
- selecting a profile for the wrong platform must fail with a clear error

## Current Profile Matrix

- Windows:
  - `windows-vulkan`
  - `windows-hip`
  - `windows-cpu`
- Linux:
  - `linux-vulkan`
  - `linux-rocm`
  - `linux-cuda`
  - `linux-cpu`
- macOS:
  - `macos-metal`
  - `macos-cpu`

## Testability

- unit tests must verify default profile resolution
- unit tests must verify platform mismatch rejection
- repo fixture tests must verify the profile matrix is present in project config
