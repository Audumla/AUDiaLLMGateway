"""Smoke test runner for local LLM gateway workspaces.

Runs in stages so each layer is verified independently:
  Stage 0  (--install only): Download/resolve binaries via installer
  Stage 1: generate-configs
  Stage 2: llama-swap start + /health check
  Stage 3: gateway (LiteLLM) start + /health check
  Stage 4: nginx start + /health check  (auto-skipped when nginx.enabled=False)
  Stage 5: routing test through active proxy endpoint

Usage (from project root, with venv active):

  # Full e2e test with installer-driven binary download:
  python scripts/smoke_runner.py --root test-work/e2e-nginx-smoke --install

  # Use existing smoke workspace (binaries already installed):
  python scripts/smoke_runner.py --root test-work/component-layout-smoke

  # Stop after llama-swap health only:
  python scripts/smoke_runner.py --stage 2

  # Leave services running for manual investigation:
  python scripts/smoke_runner.py --no-stop

  # Test the default benchmark model:
  python scripts/smoke_runner.py --model local/qwen2b_validation_cpu
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import re
import shlex
import statistics
import sys
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Ensure Unicode output works on Windows consoles regardless of system codepage.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from src.launcher.config_loader import load_stack_config, write_generated_configs
from src.launcher.health import http_probe
from src.launcher.local_backend_validation import (
    detect_host_acceleration,
    native_smoke_model_for_acceleration,
    summarize_device_selection,
)
from src.launcher.process_manager import (
    ensure_runtime_dirs,
    is_pid_running,
    launch_detached,
    litellm_command,
    llama_swap_command,
    nginx_command,
    read_metadata,
    stop_service,
)


# ── ANSI labels ──────────────────────────────────────────────────────────────

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"
INFO = "\033[36mINFO\033[0m"


def _label(ok: bool) -> str:
    return PASS if ok else FAIL


def step(name: str, ok: bool | None = None, detail: str = "") -> None:
    if ok is None:
        label = SKIP
    else:
        label = _label(ok)
    suffix = f"  {detail}" if detail else ""
    print(f"  [{label}] {name}{suffix}")


def stage_header(n: int | str, title: str) -> None:
    print(f"\n=== Stage {n}: {title} ===")


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _wait_for_any(
    urls: list[str],
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
    interval: float = 3.0,
) -> tuple[bool, str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for url in urls:
            ok, _, _ = http_probe(url, headers=headers, timeout=5.0)
            if ok:
                return True, url
        time.sleep(interval)
    return False, ""


def _http_any_response(url: str, timeout: float = 5.0) -> bool:
    """Returns True if ANY HTTP response is received (even 5xx) — proxy is alive."""
    try:
        urllib.request.urlopen(
            urllib.request.Request(url, method="GET"),
            timeout=timeout,
        )
        return True
    except urllib.error.HTTPError:
        return True  # Got an HTTP error response — server is alive
    except Exception:
        return False


def _extract_message_content(body: dict[str, Any]) -> str:
    choices = body.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, list):
        parts = [str(item.get("text", "")).strip() for item in content if isinstance(item, dict)]
        return " ".join(part for part in parts if part).strip()
    if isinstance(content, str):
        return content.strip()
    reasoning_content = message.get("reasoning_content")
    if isinstance(reasoning_content, str):
        return reasoning_content.strip()
    return ""


def _total_memory_bytes() -> int | None:
    try:
        if os.name == "nt":
            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
                return int(status.ullTotalPhys)
            return None
        if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
            return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))
    except Exception:
        return None
    return None


def _published_model_details(root: Path, stack, model_label: str) -> dict[str, Any]:
    model_lookup = {model.label: model for model in stack.published_models}
    published = model_lookup.get(model_label)
    if published is None:
        return {"model_label": model_label}
    source_page = str(published.source_page_url or "").strip()
    source_repo = ""
    if "huggingface.co/" in source_page:
        source_repo = (
            source_page.split("huggingface.co/", 1)[1]
            .strip("/")
            .replace("/tree/main", "")
            .replace("/blob/main", "")
        )
    model_display_name = published.model_filename or published.backend_model_name or published.label
    if source_repo and published.model_filename:
        model_display_name = f"{source_repo} / {published.model_filename}"
    details: dict[str, Any] = {
        "model_label": published.label,
        "framework": published.framework,
        "transport": published.transport,
        "llama_swap_model": published.llama_swap_model,
        "backend_model_name": published.backend_model_name,
        "model_display_name": model_display_name,
        "source_repo": source_repo,
        "source_page_url": published.source_page_url,
        "model_filename": published.model_filename,
        "purpose": published.purpose,
        "revision": published.revision,
        "mode": published.mode,
        "load_groups": list(published.load_groups),
        "api_base": published.api_base,
    }
    generated_config_path = getattr(stack.llama_swap, "generated_config_path", "")
    if generated_config_path and published.llama_swap_model:
        generated_path = root / generated_config_path
        try:
            data = yaml.safe_load(generated_path.read_text(encoding="utf-8")) or {}
            model_entry = (data.get("models") or {}).get(published.llama_swap_model)
            if isinstance(model_entry, dict) and model_entry.get("cmd"):
                resolved_command = str(model_entry["cmd"])
                details["resolved_llama_swap_command"] = resolved_command
                device_selection = summarize_device_selection(resolved_command)
                if device_selection:
                    details["backend_device_selection"] = device_selection
        except Exception:
            pass
    return details


def _benchmark_context(*, root: Path, stack, detection, model_names: list[str]) -> dict[str, Any]:
    return {
        "host": {
            "platform": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "memory_bytes": _total_memory_bytes(),
            "gpu_name": detection.gpu_name,
            "host_acceleration": detection.host_acceleration,
            "container_acceleration": detection.container_acceleration,
            "reason": detection.reason,
            "supported_accelerations": list(detection.supported_accelerations),
        },
        "stack": {
            "root": str(root),
            "litellm": {
                "host": stack.litellm.host,
                "port": stack.litellm.port,
            },
            "llama_swap": {
                "host": stack.llama_swap.host,
                "port": stack.llama_swap.port,
                "generated_config_path": stack.llama_swap.generated_config_path,
            },
            "nginx": {
                "enabled": stack.nginx.enabled,
                "host": stack.nginx.host,
                "port": stack.nginx.port,
            },
        },
        "targets": [_published_model_details(root, stack, name) for name in model_names],
    }


def _stage5_model_names(models: list[str], host_acceleration: str) -> list[str]:
    return models or [native_smoke_model_for_acceleration(host_acceleration)]


def _chat_completion_request(
    *,
    base_url: str,
    model_name: str,
    prompt: str,
    max_tokens: int,
    api_key: str | None = None,
) -> dict[str, Any]:
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    elapsed_seconds = max(time.perf_counter() - started, 1e-9)
    usage = body.get("usage", {})
    choices = body.get("choices", [])
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    timings = body.get("timings", {})
    backend_tok_per_sec = None
    if isinstance(timings, dict):
        predicted_per_second = timings.get("predicted_per_second")
        if isinstance(predicted_per_second, (int, float)):
            backend_tok_per_sec = float(predicted_per_second)
    return {
        "body": body,
        "elapsed_seconds": elapsed_seconds,
        "completion_tokens": completion_tokens,
        "tok_per_sec": completion_tokens / elapsed_seconds if completion_tokens > 0 else 0.0,
        "finish_reason": choices[0].get("finish_reason") if choices else "",
        "model": str(body.get("model", "")),
        "content": _extract_message_content(body),
        "timings": timings,
        "backend_tok_per_sec": backend_tok_per_sec,
    }


def _preload_chat_completion_route(
    *,
    base_url: str,
    model_name: str,
    max_tokens: int,
    api_key: str | None = None,
) -> dict[str, Any]:
    return _chat_completion_request(
        base_url=base_url,
        model_name=model_name,
        prompt="Warm up and reply with one word.",
        max_tokens=min(max_tokens, 8),
        api_key=api_key,
    )


def _warm_chat_completion_route(
    *,
    base_url: str,
    model_name: str,
    max_tokens: int,
    api_key: str | None = None,
    ) -> dict[str, Any]:
    return _preload_chat_completion_route(
        base_url=base_url,
        model_name=model_name,
        max_tokens=max_tokens,
        api_key=api_key,
    )


def _benchmark_request_suite(
    default_prompt: str,
    default_max_tokens: int,
    suite_definition: Any | None = None,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    if isinstance(suite_definition, list):
        for index, item in enumerate(suite_definition, start=1):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or f"sample-{index}").strip() or f"sample-{index}"
            prompt = str(item.get("prompt") or default_prompt)
            max_tokens = int(item.get("max_tokens", default_max_tokens) or default_max_tokens)
            requests.append({"label": label, "prompt": prompt, "max_tokens": max_tokens})
    if not requests:
        requests.append({"label": "baseline", "prompt": default_prompt, "max_tokens": default_max_tokens})
    return requests


def _summarize_benchmark_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if isinstance(row.get("tok_per_sec"), (int, float))]
    summary: dict[str, Any] = {
        "sample_count": len(rows),
        "success_count": len(successful),
        "failure_count": len(rows) - len(successful),
    }
    if not successful:
        summary.update(
            {
                "client_avg_tok_per_sec": None,
                "backend_avg_tok_per_sec": None,
                "round_trip_avg_seconds": None,
                "client_min_tok_per_sec": None,
                "client_max_tok_per_sec": None,
                "backend_min_tok_per_sec": None,
                "backend_max_tok_per_sec": None,
            }
        )
        return summary

    client_values = [float(row["tok_per_sec"]) for row in successful]
    backend_values = [
        float(row.get("backend_tok_per_sec", 0.0) or 0.0)
        for row in successful
        if isinstance(row.get("backend_tok_per_sec"), (int, float))
    ]
    elapsed_values = [float(row["elapsed_seconds"]) for row in successful if isinstance(row.get("elapsed_seconds"), (int, float))]
    summary.update(
        {
            "client_avg_tok_per_sec": statistics.mean(client_values),
            "backend_avg_tok_per_sec": statistics.mean(backend_values) if backend_values else None,
            "round_trip_avg_seconds": statistics.mean(elapsed_values) if elapsed_values else None,
            "client_min_tok_per_sec": min(client_values),
            "client_max_tok_per_sec": max(client_values),
            "backend_min_tok_per_sec": min(backend_values) if backend_values else None,
            "backend_max_tok_per_sec": max(backend_values) if backend_values else None,
        }
    )
    return summary


def _render_macro_text(template: str, macros: dict[str, str]) -> str:
    pattern = re.compile(r"\$\{([^}]+)\}")
    rendered = template
    for _ in range(10):
        updated = pattern.sub(lambda match: str(macros.get(match.group(1), match.group(0))), rendered)
        if updated == rendered:
            return updated
        rendered = updated
    return rendered


def _resolve_direct_llama_server_command(root: Path, stack, model_label: str, *, port: int) -> list[str] | None:
    generated_path = root / stack.llama_swap.generated_config_path
    if not generated_path.exists():
        return None
    generated = yaml.safe_load(generated_path.read_text(encoding="utf-8")) or {}
    model_lookup = {model.label: model for model in stack.published_models}
    published = model_lookup.get(model_label)
    if published is None or published.transport != "llama-swap" or not published.llama_swap_model:
        return None
    model_entry = (generated.get("models") or {}).get(published.llama_swap_model)
    if not isinstance(model_entry, dict) or not model_entry.get("cmd"):
        return None
    macros = {str(key): str(value) for key, value in (generated.get("macros") or {}).items()}
    macros["PORT"] = str(port)
    rendered = _render_macro_text(str(model_entry["cmd"]), macros)
    return shlex.split(rendered, posix=os.name != "nt")


def _benchmark_direct_llama_server(
    root: Path,
    stack,
    *,
    model_label: str,
    prompt: str,
    max_tokens: int,
    benchmark_requests: list[dict[str, Any]] | None = None,
    port: int = 41990,
) -> dict[str, Any] | None:
    from src.launcher.process_manager import launch_detached, stop_service

    command = _resolve_direct_llama_server_command(root, stack, model_label, port=port)
    if not command:
        return None

    service_name = "direct-llama-server"
    # Benchmark the raw server in isolation so we do not measure contention from
    # gateway/llama-swap still holding the same model/backend on the GPU.
    stop_service(root, "gateway")
    stop_service(root, "llama-swap")
    stop_service(root, service_name)
    base_url = f"http://127.0.0.1:{port}"
    preload_result: dict[str, Any] | None = None
    preload_error: str | None = None
    try:
        launch_detached(root, service_name, command)
        ok, _ = _wait_for_any([f"{base_url}/health"], timeout=180.0, interval=1.0)
        if not ok:
            return {
                "route": "direct-llama-server",
                "benchmark_mode": "preload+timed",
                "base_url": base_url,
                "preload": preload_result,
                "preload_error": preload_error,
                "error": "health check failed",
            }

        try:
            preload_result = _preload_chat_completion_route(
                base_url=base_url,
                model_name=model_label,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            preload_error = str(exc)
        request_suite = benchmark_requests or _benchmark_request_suite(prompt, max_tokens)
        sample_rows: list[dict[str, Any]] = []
        all_ok = True
        for index, request in enumerate(request_suite, start=1):
            try:
                result = _chat_completion_request(
                    base_url=base_url,
                    model_name=model_label,
                    prompt=str(request.get("prompt", prompt)),
                    max_tokens=int(request.get("max_tokens", max_tokens) or max_tokens),
                )
                sample_rows.append(
                    {
                        "sample_index": index,
                        "sample_label": str(request.get("label", f"sample-{index}")),
                        "sample_count": len(request_suite),
                        "prompt": str(request.get("prompt", prompt)),
                        "max_tokens": int(request.get("max_tokens", max_tokens) or max_tokens),
                        "model": model_label,
                        "route": "direct-llama-server",
                        "benchmark_mode": "timed",
                        "base_url": base_url,
                        "elapsed_seconds": result["elapsed_seconds"],
                        "completion_tokens": result["completion_tokens"],
                        "tok_per_sec": result["tok_per_sec"],
                        "backend_tok_per_sec": result.get("backend_tok_per_sec"),
                        "finish_reason": result["finish_reason"],
                        "timings": result.get("timings", {}),
                        "preload": preload_result,
                        "preload_error": preload_error,
                    }
                )
            except Exception as exc:
                all_ok = False
                sample_rows.append(
                    {
                        "sample_index": index,
                        "sample_label": str(request.get("label", f"sample-{index}")),
                        "sample_count": len(request_suite),
                        "prompt": str(request.get("prompt", prompt)),
                        "max_tokens": int(request.get("max_tokens", max_tokens) or max_tokens),
                        "model": model_label,
                        "route": "direct-llama-server",
                        "benchmark_mode": "timed",
                        "base_url": base_url,
                        "error": str(exc),
                        "preload": preload_result,
                        "preload_error": preload_error,
                    }
                )
        return {
            "route": "direct-llama-server",
            "benchmark_mode": "preload+timed",
            "base_url": base_url,
            "preload": preload_result,
            "preload_error": preload_error,
            "results": sample_rows,
            "summary": _summarize_benchmark_rows(sample_rows),
            "resolved_command": command,
            "status": "passed" if all_ok else "failed",
        }
    except Exception as exc:
        return {
            "route": "direct-llama-server",
            "benchmark_mode": "preload+timed",
            "base_url": base_url,
            "preload": preload_result,
            "preload_error": preload_error,
            "error": str(exc),
        }
    finally:
        stop_service(root, service_name)


# ── Stage 0: install ──────────────────────────────────────────────────────────

def run_stage0_install(root: Path, model_names: list[str] | None = None) -> bool:
    stage_header(0, "Install components (fresh binary download)")
    import shutil
    from src.installer.release_installer import ensure_llama_cpp, ensure_llama_swap, ensure_models, ensure_nginx

    # Sync project base configs from the main project root so this workspace
    # always has the latest catalog, stack settings, etc.  This mirrors what
    # the production installer would do when deploying a release bundle.
    project_config_src = _PROJECT_ROOT / "config" / "project"
    project_config_dst = root / "config" / "project"
    if root != _PROJECT_ROOT and project_config_src.is_dir():
        project_config_dst.mkdir(parents=True, exist_ok=True)
        for src_file in project_config_src.glob("*.yaml"):
            dst_file = project_config_dst / src_file.name
            shutil.copy2(src_file, dst_file)
        step("synced config/project", True, str(project_config_dst.relative_to(root)))

    # Download llama.cpp from GitHub into workspace/tools/llama.cpp/
    try:
        result = ensure_llama_cpp(root)
        exe = result.get("executable_path", "")
        step("llama.cpp", True, f"v{result.get('version', '?')} ->...{exe[-50:]}")
        llama_cpp_result = result
    except Exception as exc:
        step("llama.cpp download", False, str(exc))
        return False

    # Resolve llama-swap (LLAMA_SWAP_EXE env ->PATH ->GitHub download ->winget)
    try:
        result = ensure_llama_swap(root)
        swap_path = result.get("path", "")
        if swap_path:
            os.environ.setdefault("LLAMA_SWAP_EXE", swap_path)
        step("llama-swap", True, f"{result.get('mode', '?')} ->{swap_path or 'unresolved'}")
        llama_swap_result = result
    except Exception as exc:
        step("llama-swap resolve", False, str(exc))
        return False

    # Resolve nginx (PATH ->winget/brew/apt/zypper/dnf)
    nginx_result: dict = {}
    try:
        result = ensure_nginx(root)
        step("nginx", True, f"{result.get('mode', '?')} ->{result.get('path', 'unresolved')}")
        nginx_result = result
    except Exception as exc:
        step("nginx resolve", False, str(exc))
        # nginx failure is non-fatal during install — stack still works without reverse proxy
        step("nginx", None, "continuing without nginx (configure manually if needed)")

    # Download model files into workspace/models/
    models_result: dict = {}
    try:
        result = ensure_models(root, model_names)
        downloaded = result.get("models", {})
        model_dir = result.get("model_dir", "")
        for sname, info in downloaded.items():
            step(f"model {sname}", True, info.get("model_path", "")[-60:])
        step("models root", True, model_dir[-60:])
        models_result = result
    except Exception as exc:
        step("models download", False, str(exc))
        # Model download failure is non-fatal at install time — inference will fail later
        step("models", None, "model files unavailable; stage 5 (routing) will fail")

    # Persist to install-state.json so generate-configs picks up binary and model paths
    state: dict = {
        "product": "AUDiaLLMGateway",
        "version": "local-test",
        "install_root": str(root),
        "component_results": {
            "llama_cpp": llama_cpp_result,
            "llama_swap": llama_swap_result,
        },
    }
    if nginx_result:
        state["component_results"]["nginx"] = nginx_result
    if models_result:
        state["component_results"]["models"] = models_result

    state_path = root / "state" / "install-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    step("saved install-state.json", True, str(state_path.relative_to(root)))
    return True


# ── Stage 1: generate configs ─────────────────────────────────────────────────

def run_stage1(root: Path) -> bool:
    stage_header(1, "Generate configs")
    try:
        written = write_generated_configs(root)
        for name, path in written.items():
            step(f"wrote {name}", True, str(path.relative_to(root)))
        return True
    except Exception as exc:
        step("generate-configs", False, str(exc))
        return False


# ── Stage 2: llama-swap ───────────────────────────────────────────────────────

def run_stage2(root: Path, stack) -> bool:
    stage_header(2, "llama-swap start + health")
    existing = read_metadata(root, "llama-swap")
    if existing and is_pid_running(int(existing.get("pid", 0))):
        step("llama-swap already running", True, f"pid={existing['pid']}")
    else:
        cmd = llama_swap_command(root, stack.llama_swap)
        step("command", True, " ".join(cmd[:3]) + " ...")
        pid = launch_detached(root, "llama-swap", cmd)
        step("launched", True, f"pid={pid}")

    urls = [
        f"http://{stack.llama_swap.host}:{stack.llama_swap.port}{path}"
        for path in stack.llama_swap.health_paths
    ]
    ok, url = _wait_for_any(urls, timeout=60.0)
    step(f"health ({url or urls[0]})", ok)
    return ok


# ── Stage 3: gateway (LiteLLM) ────────────────────────────────────────────────

def run_stage3(root: Path, stack) -> bool:
    stage_header(3, "Gateway (LiteLLM) start + health")
    existing = read_metadata(root, "gateway")
    if existing and is_pid_running(int(existing.get("pid", 0))):
        step("gateway already running", True, f"pid={existing['pid']}")
    else:
        env = os.environ.copy()
        env.pop("DEBUG", None)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        cmd = litellm_command(root, stack.litellm)
        step("command", True, " ".join(cmd[:2]) + " ...")
        pid = launch_detached(root, "gateway", cmd, env=env)
        step("launched", True, f"pid={pid}")

    headers: dict[str, str] = {}
    if stack.litellm.master_key_env in os.environ:
        headers["Authorization"] = f"Bearer {os.environ[stack.litellm.master_key_env]}"

    urls = [
        f"http://{stack.litellm.host}:{stack.litellm.port}{path}"
        for path in stack.litellm.health_paths
    ]
    ok, url = _wait_for_any(urls, headers=headers, timeout=90.0)
    step(f"health ({url or urls[0]})", ok)
    return ok


# ── Stage 4: nginx ────────────────────────────────────────────────────────────

def run_stage4_nginx(root: Path, stack) -> bool:
    if not stack.nginx.enabled:
        stage_header(4, "nginx (skipped — not enabled in this workspace)")
        step("nginx", None, "set reverse_proxy.nginx.enabled: true to activate")
        return True  # not a failure — nginx is optional

    stage_header(4, "nginx start + health")
    ensure_runtime_dirs(root)
    existing = read_metadata(root, "nginx")
    if existing and is_pid_running(int(existing.get("pid", 0))):
        step("nginx already running", True, f"pid={existing['pid']}")
    else:
        cmd = nginx_command(root, stack.nginx)
        step("command", True, " ".join(cmd))
        pid = launch_detached(root, "nginx", cmd)
        step("launched", True, f"pid={pid}")

    # nginx is a reverse proxy — it may return 502 while upstreams are still warming.
    # Accept any HTTP response (including 5xx) as "nginx is alive".
    probe_url = f"http://{stack.nginx.host}:{stack.nginx.port}/health"
    alive = False
    deadline = time.time() + 20.0
    while time.time() < deadline:
        if _http_any_response(probe_url):
            alive = True
            break
        time.sleep(1.0)
    step(f"http probe ({probe_url})", alive)
    return alive


# ── Stage 5: routing test ─────────────────────────────────────────────────────

def run_stage5_routing(
    root: Path,
    stack,
    model_names: list[str],
    *,
    prompt: str,
    max_tokens: int,
    benchmark_requests: list[dict[str, Any]] | None = None,
    benchmark_output: Path | None = None,
    benchmark_context: dict[str, Any] | None = None,
) -> bool:
    stage_header(5, "Routing test (inference)")

    # Route through nginx when enabled, direct to LiteLLM otherwise
    if stack.nginx.enabled:
        base_url = f"http://{stack.nginx.host}:{stack.nginx.port}"
        route_note = "gateway"
        route_detail = f"via nginx :{stack.nginx.port}"
    else:
        base_url = f"http://{stack.litellm.host}:{stack.litellm.port}"
        route_note = "gateway"
        route_detail = f"direct :{stack.litellm.port}"

    print(f"  [{INFO}] endpoint: {base_url}  ({route_detail})")
    api_key = os.environ.get(stack.litellm.master_key_env, "sk-local-dev")
    all_ok = True
    benchmark_rows: list[dict[str, Any]] = []
    llama_swap_base_url = f"http://{stack.llama_swap.host}:{stack.llama_swap.port}"
    resolved_targets = [_published_model_details(root, stack, name) for name in model_names]
    request_suite = benchmark_requests or _benchmark_request_suite(prompt, max_tokens)

    model_lookup = {model.label: model for model in stack.published_models}
    for model_name in model_names:
        published = model_lookup.get(model_name)
        display_model_name = (
            published.model_filename
            if published and published.model_filename
            else (published.backend_model_name if published and published.backend_model_name else model_name)
        )
        observed_model_name = model_name
        preload_result: dict[str, Any] | None = None
        preload_error: str | None = None
        try:
            preload_result = _preload_chat_completion_route(
                base_url=base_url,
                model_name=model_name,
                max_tokens=max_tokens,
                api_key=api_key,
            )
            model_rows: list[dict[str, Any]] = []
            for index, request in enumerate(request_suite, start=1):
                sample_label = str(request.get("label", f"sample-{index}"))
                sample_prompt = str(request.get("prompt", prompt))
                sample_max_tokens = int(request.get("max_tokens", max_tokens) or max_tokens)
                try:
                    result = _chat_completion_request(
                        base_url=base_url,
                        model_name=model_name,
                        prompt=sample_prompt,
                        max_tokens=sample_max_tokens,
                        api_key=api_key,
                    )
                    model_rows.append(
                        {
                            "model": display_model_name,
                            "observed_model": result.get("model") or observed_model_name,
                            "sample_index": index,
                            "sample_label": sample_label,
                            "sample_count": len(request_suite),
                            "prompt": sample_prompt,
                            "max_tokens": sample_max_tokens,
                            "route": route_note,
                            "benchmark_mode": "timed",
                            "base_url": base_url,
                            "elapsed_seconds": result["elapsed_seconds"],
                            "completion_tokens": result["completion_tokens"],
                            "tok_per_sec": result["tok_per_sec"],
                            "backend_tok_per_sec": result.get("backend_tok_per_sec"),
                            "finish_reason": result["finish_reason"],
                            "timings": result.get("timings", {}),
                            "llama_swap_model": model_name,
                            "preload": preload_result,
                            "preload_error": preload_error,
                        }
                    )
                except Exception as exc:
                    all_ok = False
                    model_rows.append(
                        {
                            "model": display_model_name,
                            "observed_model": observed_model_name,
                            "sample_index": index,
                            "sample_label": sample_label,
                            "sample_count": len(request_suite),
                            "prompt": sample_prompt,
                            "max_tokens": sample_max_tokens,
                            "route": route_note,
                            "benchmark_mode": "timed",
                            "base_url": base_url,
                            "error": str(exc),
                            "llama_swap_model": model_name,
                            "preload": preload_result,
                            "preload_error": preload_error,
                        }
                    )
            summary = _summarize_benchmark_rows(model_rows)
            if summary.get("success_count", 0):
                detail_parts = [f"{summary.get('success_count')}/{summary.get('sample_count')} samples"]
                client_avg = summary.get("client_avg_tok_per_sec")
                backend_avg = summary.get("backend_avg_tok_per_sec")
                if isinstance(client_avg, (int, float)):
                    detail_parts.append(f"{float(client_avg):.2f} client T/s avg")
                if isinstance(backend_avg, (int, float)):
                    detail_parts.append(f"{float(backend_avg):.2f} backend T/s avg")
                detail_parts.append("preload ok" if not preload_error else f"preload failed: {preload_error}")
                step(model_name, True, "; ".join(detail_parts))
            else:
                step(model_name, False, "all timed samples failed")
            benchmark_rows.extend(model_rows)
        except Exception as exc:
            step(model_name, False, str(exc))
            all_ok = False
            benchmark_rows.append(
                {
                    "model": model_name,
                    "route": route_note,
                    "benchmark_mode": "preload+timed",
                    "base_url": base_url,
                    "preload": preload_result,
                    "preload_error": preload_error,
                    "error": str(exc),
                }
            )

        llama_swap_model_name = published.llama_swap_model if published and published.llama_swap_model else model_name
        preload_result = None
        preload_error = None
        try:
            preload_result = _preload_chat_completion_route(
                base_url=llama_swap_base_url,
                model_name=llama_swap_model_name,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            preload_error = str(exc)
        swap_rows: list[dict[str, Any]] = []
        for index, request in enumerate(request_suite, start=1):
            sample_label = str(request.get("label", f"sample-{index}"))
            sample_prompt = str(request.get("prompt", prompt))
            sample_max_tokens = int(request.get("max_tokens", max_tokens) or max_tokens)
            try:
                swap_result = _chat_completion_request(
                    base_url=llama_swap_base_url,
                    model_name=llama_swap_model_name,
                    prompt=sample_prompt,
                    max_tokens=sample_max_tokens,
                )
                swap_rows.append(
                    {
                        "model": display_model_name,
                        "observed_model": swap_result.get("model") or model_name,
                        "sample_index": index,
                        "sample_label": sample_label,
                        "sample_count": len(request_suite),
                        "prompt": sample_prompt,
                        "max_tokens": sample_max_tokens,
                        "route": "direct-llama-swap",
                        "benchmark_mode": "timed",
                        "base_url": llama_swap_base_url,
                        "elapsed_seconds": swap_result["elapsed_seconds"],
                        "completion_tokens": swap_result["completion_tokens"],
                        "tok_per_sec": swap_result["tok_per_sec"],
                        "backend_tok_per_sec": swap_result.get("backend_tok_per_sec"),
                        "finish_reason": swap_result["finish_reason"],
                        "timings": swap_result.get("timings", {}),
                        "llama_swap_model": llama_swap_model_name,
                        "preload": preload_result,
                        "preload_error": preload_error,
                    }
                )
            except Exception as exc:
                all_ok = False
                swap_rows.append(
                    {
                        "model": display_model_name,
                        "observed_model": model_name,
                        "sample_index": index,
                        "sample_label": sample_label,
                        "sample_count": len(request_suite),
                        "prompt": sample_prompt,
                        "max_tokens": sample_max_tokens,
                        "route": "direct-llama-swap",
                        "benchmark_mode": "timed",
                        "base_url": llama_swap_base_url,
                        "error": str(exc),
                        "llama_swap_model": llama_swap_model_name,
                        "preload": preload_result,
                        "preload_error": preload_error,
                    }
                )
        swap_summary = _summarize_benchmark_rows(swap_rows)
        if swap_summary.get("success_count", 0):
            preload_note = "preload ok" if not preload_error else f"preload failed: {preload_error}"
            backend_avg = swap_summary.get("backend_avg_tok_per_sec")
            detail_parts = [
                f"{swap_summary.get('success_count')}/{swap_summary.get('sample_count')} samples",
                f"{float(swap_summary['client_avg_tok_per_sec']):.2f} client T/s avg",
            ]
            if isinstance(backend_avg, (int, float)):
                detail_parts.append(f"{float(backend_avg):.2f} backend T/s avg")
            detail_parts.append(preload_note)
            step(
                f"{model_name} llama-swap",
                True,
                "; ".join(detail_parts),
            )
        else:
            step(f"{model_name} llama-swap", False, "all timed samples failed")
        benchmark_rows.extend(swap_rows)

        direct_row = _benchmark_direct_llama_server(
            root,
            stack,
            model_label=model_name,
            prompt=prompt,
            max_tokens=max_tokens,
            benchmark_requests=request_suite,
        )
        if direct_row is not None:
            if direct_row.get("error"):
                step(f"{model_name} direct", False, str(direct_row["error"]))
                all_ok = False
            else:
                summary = direct_row.get("summary", {})
                preload_note = "preload ok" if not direct_row.get("preload_error") else f"preload failed: {direct_row.get('preload_error')}"
                success_count = summary.get("success_count", 0)
                sample_count = summary.get("sample_count", 0)
                client_avg = summary.get("client_avg_tok_per_sec")
                backend_avg = summary.get("backend_avg_tok_per_sec")
                summary_parts = [f"{success_count}/{sample_count} samples"]
                if isinstance(client_avg, (int, float)):
                    summary_parts.append(f"{float(client_avg):.2f} client T/s avg")
                if isinstance(backend_avg, (int, float)):
                    summary_parts.append(f"{float(backend_avg):.2f} backend T/s avg")
                summary_parts.append(preload_note)
                direct_ok = direct_row.get("status") == "passed" and success_count == sample_count
                step(
                    f"{model_name} direct",
                    direct_ok,
                    "; ".join(summary_parts),
                )
                if not direct_ok:
                    all_ok = False
            benchmark_rows.extend(direct_row.get("results", []))

    if benchmark_output is not None:
        benchmark_context_payload: dict[str, Any] = dict(benchmark_context or {})
        if resolved_targets and "targets" not in benchmark_context_payload:
            benchmark_context_payload["targets"] = resolved_targets
        benchmark_output.parent.mkdir(parents=True, exist_ok=True)
        benchmark_output.write_text(
            json.dumps(
                {
                    "route": route_note,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "benchmark_suite": request_suite,
                    "benchmark_context": benchmark_context_payload,
                    "results": benchmark_rows,
                    "summary": _summarize_benchmark_rows(benchmark_rows),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return all_ok


# ── Stop helpers ──────────────────────────────────────────────────────────────

def stop_all(root: Path, stack) -> None:
    print("\n=== Stopping services ===")
    if stack.nginx.enabled:
        import subprocess
        from src.launcher.process_manager import nginx_stop_command
        subprocess.run(nginx_stop_command(root, stack.nginx), check=False, capture_output=True)
    for svc in ("nginx", "gateway", "llama-swap"):
        meta = read_metadata(root, svc)
        if meta is None:
            step(f"stop {svc}", None, "not started")
            continue
        stopped = stop_service(root, svc)
        step(f"stop {svc}", stopped)


# ── Summary ───────────────────────────────────────────────────────────────────

def _summarise(results: dict[str, bool]) -> None:
    print("\n=== Summary ===")
    for name, ok in results.items():
        step(name, ok)
    overall = all(results.values())
    print(f"\nResult: {'PASS' if overall else 'FAIL'}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test runner for the local LLM gateway stack.")
    parser.add_argument(
        "--root",
        default=str(_PROJECT_ROOT / "test-work" / "component-layout-smoke"),
        help="Workspace root (default: test-work/component-layout-smoke)",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Run Stage 0: download llama.cpp from GitHub and resolve other binaries",
    )
    parser.add_argument(
        "--stage",
        type=int,
        default=5,
        help="Run up to this stage (0-5, default 5)",
    )
    parser.add_argument(
        "--no-stop",
        action="store_true",
        help="Leave services running after the test",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        dest="models",
        help="Model stable-name(s) to test in stage 5 (default: the profile's native validation model)",
    )
    parser.add_argument(
        "--benchmark-output",
        default="",
        help="Optional JSON file path for stage-5 benchmark results",
    )
    parser.add_argument(
        "--benchmark-prompt",
        default="Reply with one short sentence confirming this request was handled.",
        help="Prompt used for stage-5 routing validation",
    )
    parser.add_argument(
        "--benchmark-max-tokens",
        type=int,
        default=48,
        help="max_tokens value used for stage-5 routing validation",
    )
    parser.add_argument(
        "--benchmark-context-json",
        default="",
        help="Optional JSON encoded benchmark context to embed in the output artifact",
    )
    parser.add_argument(
        "--benchmark-suite-json",
        default="",
        help="Optional JSON encoded benchmark request suite to use for stage-5 routing",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print(f"Workspace : {root}")

    results: dict[str, bool] = {}
    stack = None

    # ── Stage 0: install ──
    if args.install:
        install_model_names = args.models if args.models else None
        ok = run_stage0_install(root, model_names=install_model_names)
        results["stage0_install"] = ok
        if not ok:
            _summarise(results)
            return 1
        if args.stage == 0:
            _summarise(results)
            return 0

    # ── Stage 1: generate ──
    ok = run_stage1(root)
    results["stage1_generate"] = ok
    if not ok:
        _summarise(results)
        return 1
    if args.stage < 2:
        _summarise(results)
        return 0

    try:
        stack = load_stack_config(root)
    except Exception as exc:
        print(f"  [FAIL] load_stack_config: {exc}")
        return 1
    detection = detect_host_acceleration()

    # ── Stage 2: llama-swap ──
    ok = run_stage2(root, stack)
    results["stage2_llama_swap"] = ok
    if not ok or args.stage < 3:
        if not args.no_stop and stack:
            stop_all(root, stack)
        _summarise(results)
        return 0 if all(results.values()) else 1

    # ── Stage 3: gateway ──
    ok = run_stage3(root, stack)
    results["stage3_gateway"] = ok
    if not ok or args.stage < 4:
        if not args.no_stop:
            stop_all(root, stack)
        _summarise(results)
        return 0 if all(results.values()) else 1

    # ── Stage 4: nginx (auto-skipped when disabled) ──
    ok = run_stage4_nginx(root, stack)
    results["stage4_nginx"] = ok
    if not ok or args.stage < 5:
        if not args.no_stop:
            stop_all(root, stack)
        _summarise(results)
        return 0 if all(results.values()) else 1

    # ── Stage 5: routing ──
    model_names = _stage5_model_names(args.models, detection.host_acceleration)
    benchmark_output = Path(args.benchmark_output).resolve() if args.benchmark_output else None
    benchmark_context = None
    if args.benchmark_context_json:
        try:
            benchmark_context = json.loads(args.benchmark_context_json)
        except Exception:
            benchmark_context = {"raw": args.benchmark_context_json}
    benchmark_suite = None
    if args.benchmark_suite_json:
        try:
            benchmark_suite = json.loads(args.benchmark_suite_json)
        except Exception:
            benchmark_suite = {"raw": args.benchmark_suite_json}
    if benchmark_context is None:
        benchmark_context = _benchmark_context(root=root, stack=stack, detection=detection, model_names=model_names)
    ok = run_stage5_routing(
        root,
        stack,
        model_names,
        prompt=args.benchmark_prompt,
        max_tokens=args.benchmark_max_tokens,
        benchmark_requests=benchmark_suite if isinstance(benchmark_suite, list) else None,
        benchmark_output=benchmark_output,
        benchmark_context=benchmark_context,
    )
    results["stage5_routing"] = ok

    if not args.no_stop:
        stop_all(root, stack)

    _summarise(results)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
