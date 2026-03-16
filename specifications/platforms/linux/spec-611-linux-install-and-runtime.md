# Spec 611: Linux Install and Runtime

## Scope

Linux is a first-tier platform. The installer handles all mainstream package manager
families automatically. No distro-specific configuration is required from the user
beyond having Python 3.11+ available before running the bootstrap script.

---

## Supported Distributions

| Distro | Version | Python | Package manager | Status |
| --- | --- | --- | --- | --- |
| Ubuntu | 22.04 LTS | 3.10 (system) | apt-get | ✅ Tested (Docker) |
| Ubuntu | 24.04 LTS | 3.12 (system) | apt-get | Expected pass |
| Debian | 12 (Bookworm) | 3.12 (python:3.12-slim-bookworm image) | apt-get | ✅ Tested (Docker) |
| Fedora | 40 | 3.12 (system) | dnf | ✅ Tested (Docker) |
| Fedora | 41 | 3.13 | dnf | ❌ SIGSEGV in litellm native ext — use Fedora 40 |
| Rocky Linux | 9 | 3.11 (AppStream) | dnf + EPEL | ✅ Tested (Docker) |
| AlmaLinux | 9 | 3.11 (AppStream) | dnf + EPEL | Expected pass (same as Rocky) |
| RHEL | 9 | 3.11 (AppStream) | dnf + EPEL | Expected pass |
| openSUSE Tumbleweed | rolling | 3.12 | zypper | ✅ Tested (Docker) |
| openSUSE Leap | 15.6 | 3.12 | zypper | ✅ Tested (Docker) |
| Arch Linux | rolling | 3.12+ | pacman | Supported (untested) |

> **Minimum Python version:** 3.11. The installer rejects older versions.
> Python version is not detected by distro — it is detected by running `python3 --version`.

---

## Python Version Notes

| Distro family | How to get Python 3.11+ |
| --- | --- |
| Ubuntu 22.04 | `python3` is 3.10 — accepted; 3.11 available via `apt install python3.11` |
| Ubuntu 24.04+ | `python3` is 3.12 — no action needed |
| Debian 12 | System `python3` is 3.11 but has a bytecode issue with litellm; use `python:3.12-slim-bookworm` Docker base or install Python 3.12 manually |
| Fedora 40 | `python3` is 3.12 — no action needed |
| Fedora 41+ | `python3` is 3.13 — **not supported** (SIGSEGV in litellm); use Fedora 40 or install `python3.12` |
| Rocky / Alma / RHEL 9 | Default is 3.9; install `python3.11` from AppStream: `dnf install python3.11` |
| openSUSE Tumbleweed | `sudo zypper install python312` |
| openSUSE Leap 15.6 | `sudo zypper install python312` (built-in repo) |
| Arch Linux | `python3` is latest stable — no action needed |

If the system Python is below 3.11, pass the correct interpreter explicitly:

```bash
PYTHON_BIN=python3.11 curl -fsSL <url> | bash
```

---

## Package Manager Support

The installer (`ensure_nginx`) detects and uses the first available package manager:

| Package manager | Distros | nginx install command |
| --- | --- | --- |
| `apt-get` | Ubuntu, Debian, Mint, Pop!_OS | `sudo apt-get update && sudo apt-get install -y nginx` |
| `zypper` | openSUSE Tumbleweed, Leap, SLES | `sudo zypper --non-interactive install nginx` |
| `dnf` | Fedora, Rocky, Alma, RHEL 8/9 | `sudo dnf install -y nginx` |
| `yum` | CentOS 7, older RHEL | `sudo yum install -y nginx` |
| `pacman` | Arch, Manjaro | `sudo pacman -Sy --noconfirm nginx` |

> nginx must be accessible to `sudo`. The installer finds it at `/usr/sbin/nginx`,
> `/usr/bin/nginx`, or `/usr/local/bin/nginx` regardless of the current `$PATH`.

---

## llama.cpp Linux Profiles

The asset tokens map to ggml-org's release naming (`ubuntu-*` prefixed, works on all glibc-based Linux):

| Profile | Asset tokens | Use case |
| --- | --- | --- |
| `linux-cpu` | `ubuntu-x64` | Default — any CPU, no GPU required |
| `linux-vulkan` | `ubuntu-vulkan-x64` | AMD/Intel GPU via Vulkan |
| `linux-rocm` | `ubuntu-rocm`, `x64` | AMD GPU via ROCm |
| `linux-cuda` | `ubuntu-cuda`, `x64` | NVIDIA GPU via CUDA |

The default profile is `linux-cpu`. Override via `config/local/stack.override.yaml`:

```yaml
component_settings:
  llama_cpp:
    selected_profile: linux-vulkan
```

These binaries are glibc-linked ELFs. They run on any Linux distro with a compatible
glibc version (≥ 2.31 for current ggml-org releases). No per-distro profiles are needed.

---

## Bootstrap

```bash
# Standard install (latest release)
curl -fsSL https://raw.githubusercontent.com/ExampleOrg/AUDiaLLMGateway/main/bootstrap/AUDiaLLMGateway-install-release.sh | bash

# Specify a version
VERSION=v1.2.0 curl -fsSL ... | bash

# Specify install directory
INSTALL_DIR=/opt/AUDiaLLMGateway curl -fsSL ... | bash

# Specify Python interpreter (if system python3 is too old)
PYTHON_BIN=python3.11 curl -fsSL ... | bash
```

---

## Runtime Operations

All operations use the `process_manager.py` CLI via the installed wrapper:

```bash
AUDiaLLMGateway.sh start-all     # start llama-swap + LiteLLM + nginx (if enabled)
AUDiaLLMGateway.sh stop-all      # stop all services
AUDiaLLMGateway.sh status        # show running service PIDs
AUDiaLLMGateway.sh start-nginx   # start nginx separately
AUDiaLLMGateway.sh stop-nginx
```

Services run as detached background processes (not systemd units). Logs are written to
`.runtime/logs/<service>.log` under the install directory.

---

## Docker Smoke Test Images

Each image exercises the full installer on a clean distro container (no model inference):

| Dockerfile | Target | Build command |
| --- | --- | --- |
| `Dockerfile.ubuntu` | Ubuntu 22.04 | `docker build -f test-work/docker-install-smoke/Dockerfile.ubuntu -t audia-smoke-ubuntu .` |
| `Dockerfile.debian` | Debian 12 | `docker build -f test-work/docker-install-smoke/Dockerfile.debian -t audia-smoke-debian .` |
| `Dockerfile.fedora` | Fedora 40 | `docker build -f test-work/docker-install-smoke/Dockerfile.fedora -t audia-smoke-fedora .` |
| `Dockerfile.rocky` | Rocky Linux 9 | `docker build -f test-work/docker-install-smoke/Dockerfile.rocky -t audia-smoke-rocky .` |
| `Dockerfile` | openSUSE Leap 15.6 | `docker build -f test-work/docker-install-smoke/Dockerfile -t audia-smoke-leap .` |
| `Dockerfile.tumbleweed` | openSUSE Tumbleweed | `docker build -f test-work/docker-install-smoke/Dockerfile.tumbleweed -t audia-smoke-tumbleweed .` |

Run any image:

```bash
docker run --rm audia-smoke-<distro>
```
