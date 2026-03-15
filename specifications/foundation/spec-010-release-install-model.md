# Spec 010: Release Install Model

## Intent

Define how AUDiaLLMGateway is installed and updated on target machines without Git operations.

## Requirements

- installation must work from a GitHub release archive
- update must pull a newer release archive and apply managed changes in place
- local config and state must not be overwritten
- required dependencies must be installed automatically where supported
- optional components must be selectable
- install state must track version, components, and paths

## Layering

- `config/project/` is release-managed
- `config/local/` is machine-owned
- `config/generated/` is derived
- `state/install-state.json` tracks installation status

## Conflict Handling

- updates must validate project and local config compatibility
- validation should warn on type conflicts and invalid layered structures
- warnings should be recorded in install state

