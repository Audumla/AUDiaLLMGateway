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
