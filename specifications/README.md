# Specifications

Design documents for AUDiaLLMGateway. Each spec describes one architectural
concern at the mid or component level.

Legend: **Implemented** | *Draft / in progress* | Planned

---

## Foundation

| Spec | Status | Description |
| ---- | ------ | ----------- |
| [spec-001](spec-001-local-llm-gateway-mid-level.md) | **Implemented** | Mid-level architecture — component topology, deployment models, config system |
| [spec-002](spec-002-model-catalog-and-config-lifecycle.md) | *Draft* | Model catalog schema, config generation lifecycle, auto-reload |
| `foundation/spec-010-release-install-model.md` | Planned | Release archive install and update model |

---

## Components

| Spec | Status | Description |
| ---- | ------ | ----------- |
| `components/installer/spec-101-release-installer.md` | Planned | GitHub release installer and component management |
| `components/llama-cpp/spec-151-llama-cpp-runtime.md` | Planned | llama.cpp runtime profiles and sidecar management |
| `components/llama-swap/spec-201-llama-swap-integration.md` | Planned | llama-swap config generation and model routing |
| `components/litellm/spec-301-litellm-gateway.md` | Planned | LiteLLM gateway config and alias mapping |
| `components/nginx/spec-401-nginx-reverse-proxy.md` | Planned | nginx config generation and route layout |
| `components/vllm/spec-251-vllm-runtime.md` | **Implemented** | vLLM backend integration |
| `components/mcp/spec-501-mcp-scaffolding.md` | Planned | MCP client and server scaffolding |

---

## Dashboard & Monitoring

| Spec | Status | Description |
| ---- | ------ | ----------- |
| `components/dashboard/spec-701-gateway-dashboard.md` | *Draft* | Gateway dashboard & control panel — component status, model management, operational controls, AUDiotMonitor integration |

---

## Platform Variants

| Spec | Status | Description |
| ---- | ------ | ----------- |
| `platforms/windows/spec-601-windows-install-and-runtime.md` | Planned | Windows-specific install and PowerShell entrypoint |
| `platforms/linux/spec-611-linux-install-and-runtime.md` | Planned | Linux-specific install, Docker, and systemd |
| `platforms/macos/spec-621-macos-install-and-runtime.md` | Planned | macOS-specific install and Metal backend |

---

## Reading order

For a new contributor:

1. [README.md](../README.md) — project overview and quick start
2. [docs/architecture.md](../docs/architecture.md) — system design
3. [spec-001](spec-001-local-llm-gateway-mid-level.md) — component topology and deployment models
4. [spec-002](spec-002-model-catalog-and-config-lifecycle.md) — model catalog and config lifecycle (draft)
5. [docs/runbook.md](../docs/runbook.md) — operations reference
