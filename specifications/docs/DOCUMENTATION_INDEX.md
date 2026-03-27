# AUDiaLLMGateway Documentation Index

Complete guide to all project documentation, organized by use case and reader type.

---

## Quick Start by Use Case

### I want to set up the system quickly
1. **Start here:** [README.md](../../README.md) — Overview and Quick Start sections
2. **Docker setup:** [docker.md](docker.md) — All deployment profiles
3. **Windows auto-start:** [SETUP_AUTOSTART.md](SETUP_AUTOSTART.md) — One-command auto-start (5 min)

### I want to understand what's supported
1. **Features overview:** [SUPPORTED_FEATURES.md](SUPPORTED_FEATURES.md) — All 6 backends, versions, capabilities
2. **Backend reference:** [BACKEND_VERSIONS.md](BACKEND_VERSIONS.md) — Complete version matrix and compatibility
3. **Performance details:** [PREBUILT_BINARIES_STRATEGY.md](PREBUILT_BINARIES_STRATEGY.md) — Boot times and caching

### I want to deploy to production
1. **Docker deployment:** [docker.md](docker.md) — Production profiles and configurations
2. **Architecture:** [architecture.md](architecture.md) — System design and topology
3. **Reverse proxy:** [reverse-proxy.md](reverse-proxy.md) — nginx configuration
4. **Config management:** [docker-field-notes.md](docker-field-notes.md) — Deployment notes

### I'm having issues
1. **Troubleshooting:** [troubleshooting.md](troubleshooting.md) — Common problems and solutions
2. **Diagnostics:** [SERVER_DIAGNOSTICS.md](SERVER_DIAGNOSTICS.md) — Server health and boot diagnostics
3. **Build investigation:** [FAILING_BUILDS_INVESTIGATION.md](FAILING_BUILDS_INVESTIGATION.md) — Root causes and fixes

### I want to test the system
1. **Manual testing:** [MANUAL_TESTING_INSTRUCTIONS.md](MANUAL_TESTING_INSTRUCTIONS.md) — Step-by-step testing procedures
2. **Testing framework:** [TEST_AUTOSTART.md](TEST_AUTOSTART.md) — 4-phase validation approach
3. **Docker auto-start:** [DOCKER_AUTOSTART.md](DOCKER_AUTOSTART.md) — Testing Docker-specific behavior

---

## Documentation by Category

### Core Documentation

| Document | Purpose | Best For |
| -------- | ------- | -------- |
| [README.md](../../README.md) | Project overview and quick start paths | First-time users, decision makers |
| [SUPPORTED_FEATURES.md](SUPPORTED_FEATURES.md) | Complete feature inventory (2000+ lines) | Understanding capabilities, version info |
| [CHANGELOG.md](CHANGELOG.md) | All changes and improvements | Version history, what's new |

### Backend & Infrastructure

| Document | Purpose | Best For |
| -------- | ------- | -------- |
| [PREBUILT_BINARIES_STRATEGY.md](PREBUILT_BINARIES_STRATEGY.md) | Prebuilt binary distribution, smart caching (500+ lines) | Performance optimization, understanding boot times |
| [BACKEND_VERSIONS.md](BACKEND_VERSIONS.md) | Complete backend version reference (300+ lines) | Compatibility checks, version selection |
| [FAILING_BUILDS_INVESTIGATION.md](FAILING_BUILDS_INVESTIGATION.md) | Root cause analysis of build failures (400+ lines) | Understanding why certain builds failed, alternative solutions |

### Deployment & Setup

| Document | Purpose | Best For |
| -------- | ------- | -------- |
| [docker.md](docker.md) | Docker deployment profiles and setup | Docker users, production deployments |
| [docker-field-notes.md](docker-field-notes.md) | Validated versions, first-install issues | Troubleshooting Docker deployments |
| [runbook.md](runbook.md) | Native install, operations, management | Non-Docker installations, native deployments |
| [SETUP_AUTOSTART.md](SETUP_AUTOSTART.md) | Windows Task Scheduler auto-start (150+ lines) | Windows users wanting auto-boot behavior |
| [DOCKER_AUTOSTART.md](DOCKER_AUTOSTART.md) | Docker auto-start configuration (400+ lines) | Docker-based auto-start setups |

### Architecture & Configuration

| Document | Purpose | Best For |
| -------- | ------- | -------- |
| [architecture.md](architecture.md) | System design, runtime topology, config layers | Understanding system structure |
| [reverse-proxy.md](reverse-proxy.md) | nginx configuration and routing | Reverse proxy setup and customization |
| [README.md](../../README.md) — "Config layering" section | Project/local/generated config model | Config management and overrides |

### Testing & Validation

| Document | Purpose | Best For |
| -------- | ------- | -------- |
| [MANUAL_TESTING_INSTRUCTIONS.md](MANUAL_TESTING_INSTRUCTIONS.md) | 4-phase testing procedures (200+ lines) | Manual QA, validation testing |
| [TEST_AUTOSTART.md](TEST_AUTOSTART.md) | Comprehensive testing framework (400+ lines) | Full system validation, boot testing |
| [SETUP_AUTOSTART.md](SETUP_AUTOSTART.md) — Testing section | Auto-start verification steps | Validating auto-start setup |

### Diagnostics & Monitoring

| Document | Purpose | Best For |
| -------- | ------- | -------- |
| [SERVER_DIAGNOSTICS.md](SERVER_DIAGNOSTICS.md) | Server health report and diagnostics (300+ lines) | Checking system status, troubleshooting |
| [troubleshooting.md](troubleshooting.md) | Common issues and solutions | Problem solving |
| [FAILING_BUILDS_INVESTIGATION.md](FAILING_BUILDS_INVESTIGATION.md) | Build failures and solutions | Understanding build issues |

### Agent & Provider Instructions

| Document | Purpose | Best For |
| -------- | ------- | -------- |
| [CLAUDE.md](CLAUDE.md) | Claude AI agent instructions | Claude Code integration |
| [AGENT.md](AGENT.md) | Agent framework instructions | Agent-based automation |
| [AGENTS.md](AGENTS.md) | Multi-agent coordination | Distributed agent setups |
| [GEMINI.md](GEMINI.md) | Gemini-specific instructions | Gemini AI integration |

### Specifications (Detailed Design)

Technical specifications in `specifications/` directory:

| Spec | Purpose | Scope |
| ---- | ------- | ----- |
| [spec-001](specifications/spec-001-local-llm-gateway-mid-level.md) | High-level gateway design | Overall architecture |
| [spec-010](specifications/foundation/spec-010-release-install-model.md) | Release and installation model | Installer design |
| [spec-101](specifications/components/installer/spec-101-release-installer.md) | Release installer specification | Component installer |
| [spec-151](specifications/components/llama-cpp/spec-151-llama-cpp-runtime.md) | llama.cpp runtime spec | Inference backend |
| [spec-152](specifications/components/llama-cpp/spec-152-llama-cpp-profile-matrix.md) | Backend profile matrix | Platform/backend combinations |
| [spec-201](specifications/components/llama-swap/spec-201-llama-swap-integration.md) | Model router integration | Model management |
| [spec-251](specifications/components/vllm/spec-251-vllm-runtime.md) | Optional vLLM backend | High-throughput inference |
| [spec-301](specifications/components/litellm/spec-301-litellm-gateway.md) | LiteLLM gateway component | API gateway |
| [spec-401](specifications/components/nginx/spec-401-nginx-reverse-proxy.md) | nginx reverse proxy | Front-door routing |
| [spec-501](specifications/components/mcp/spec-501-mcp-scaffolding.md) | MCP client scaffolding | Tool integration |
| [spec-601](specifications/platforms/windows/spec-601-windows-install-and-runtime.md) | Windows platform specs | Windows deployment |
| [spec-611](specifications/platforms/linux/spec-611-linux-install-and-runtime.md) | Linux platform specs | Linux deployment |
| [spec-621](specifications/platforms/macos/spec-621-macos-install-and-runtime.md) | macOS platform specs | macOS deployment |

---

## Documentation Statistics

**Total documentation:** 2,000+ lines across 15+ guides

**By category:**
- Backend & Performance: ~1,300 lines (SUPPORTED_FEATURES, PREBUILT_BINARIES_STRATEGY, BACKEND_VERSIONS)
- Setup & Testing: ~650 lines (SETUP_AUTOSTART, MANUAL_TESTING_INSTRUCTIONS, TEST_AUTOSTART, DOCKER_AUTOSTART)
- Diagnostics: ~600 lines (SERVER_DIAGNOSTICS, FAILING_BUILDS_INVESTIGATION)
- Core Documentation: ~450 lines (README, CHANGELOG)

---

## Features Documented

✅ **6 inference backends** (CPU, CUDA, ROCm, Vulkan, ROCm GFX1100, ROCm GFX1030)
✅ **Smart caching** — 45-90 second boot time with version-based invalidation
✅ **Windows auto-start** — Task Scheduler integration with auto-retry
✅ **Health checks** — Automated service monitoring
✅ **Prebuilt binaries** — ggml-org release distribution
✅ **Version management** — Build number versioning (b8508, b8153, etc.)
✅ **Complete testing framework** — 4-phase validation approach
✅ **Configuration layering** — Project/local/generated with override support
✅ **Docker profiles** — Universal, NVIDIA, AMD Vulkan/ROCm
✅ **Reverse proxy** — nginx with auto-generated routing

---

## How to Use This Index

**If you're:** → **Start with:**
- Setting up the system → [README.md](../../README.md)
- Checking supported features → [SUPPORTED_FEATURES.md](SUPPORTED_FEATURES.md)
- Deploying to Docker → [docker.md](docker.md)
- Setting up auto-start → [SETUP_AUTOSTART.md](SETUP_AUTOSTART.md)
- Testing the system → [MANUAL_TESTING_INSTRUCTIONS.md](MANUAL_TESTING_INSTRUCTIONS.md)
- Troubleshooting issues → [troubleshooting.md](troubleshooting.md)
- Understanding architecture → [architecture.md](architecture.md)
- Looking for backend details → [PREBUILT_BINARIES_STRATEGY.md](PREBUILT_BINARIES_STRATEGY.md)
- Checking versions → [BACKEND_VERSIONS.md](BACKEND_VERSIONS.md)

---

## Version Information

| Component | Version | Reference |
| --------- | ------- | --------- |
| llama.cpp | latest (default: b8508) | [SUPPORTED_FEATURES.md](SUPPORTED_FEATURES.md#version-support) |
| Minimum for Qwen 3.5 | b8153 | [BACKEND_VERSIONS.md](BACKEND_VERSIONS.md) |
| Docker Compose | Compatible | [docker.md](docker.md) |
| Python | 3.10+ | [README.md](../../README.md) |

---

## Related Repositories

- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) — Inference engine
- [ExampleOrg/llama-swap](https://github.com/example/llama-swap) — Model router
- [BerriAI/litellm](https://github.com/BerriAI/litellm) — API gateway
- [vllm-project/vllm](https://github.com/vllm-project/vllm) — Optional backend

---

## Document Maintenance

All documentation updated as of 2026-03-25:
- ✅ SUPPORTED_FEATURES.md — Feature inventory complete
- ✅ PREBUILT_BINARIES_STRATEGY.md — Smart caching documented
- ✅ BACKEND_VERSIONS.md — Version matrix current
- ✅ SETUP_AUTOSTART.md — Windows setup guide complete
- ✅ MANUAL_TESTING_INSTRUCTIONS.md — Testing procedures documented
- ✅ TEST_AUTOSTART.md — 4-phase framework documented
- ✅ README.md — References updated
- ✅ CHANGELOG.md — All changes recorded



