# Spec 501: MCP Scaffolding

## Scope

MCP support is scaffolded separately from core gateway runtime config.

## Config Structure

- project defaults in `config/project/mcp.base.yaml`
- local overrides in `config/local/mcp.override.yaml`
- generated client-facing config in `config/generated/litellm.mcp.client.json`

## Expectations

- MCP config updates must not break core gateway operation
- MCP remains version-sensitive and should be validated against the installed LiteLLM build

