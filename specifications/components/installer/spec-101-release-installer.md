# Spec 101: Release Installer

## Scope

The installer is responsible for:

- discovering a GitHub release
- downloading a source archive
- unpacking it into a temporary workspace
- syncing managed files into the target install directory
- preserving protected local paths
- installing required and selected components
- validating config layering
- recording install state

## Inputs

- GitHub owner/repo
- release version or `latest`
- install directory
- selected optional components

## Outputs

- populated install directory
- installed dependencies
- `state/install-state.json`

## Protected Paths

- `config/local/`
- `state/`
- `.venv/`
- `.runtime/`
- `.agent_runner/`

