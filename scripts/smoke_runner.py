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

  # Test a specific model:
  python scripts/smoke_runner.py --model local/qwen4b_vision
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Ensure Unicode output works on Windows consoles regardless of system codepage.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from src.launcher.config_loader import load_stack_config, write_generated_configs
from src.launcher.health import http_probe
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

def run_stage5_routing(root: Path, stack, model_names: list[str]) -> bool:
    stage_header(5, "Routing test (inference)")

    # Route through nginx when enabled, direct to LiteLLM otherwise
    if stack.nginx.enabled:
        base_url = f"http://{stack.nginx.host}:{stack.nginx.port}"
        route_note = f"via nginx :{stack.nginx.port}"
    else:
        base_url = f"http://{stack.litellm.host}:{stack.litellm.port}"
        route_note = f"direct :{stack.litellm.port}"

    print(f"  [{INFO}] endpoint: {base_url}  ({route_note})")
    api_key = os.environ.get(stack.litellm.master_key_env, "sk-local-dev")
    prompt = "Reply with one short sentence confirming this request was handled."
    all_ok = True

    for model_name in model_names:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 48,
        }
        req = urllib.request.Request(
            f"{base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            choices = body.get("choices", [])
            content = choices[0]["message"]["content"][:60] if choices else ""
            step(model_name, True, repr(content))
        except Exception as exc:
            step(model_name, False, str(exc))
            all_ok = False

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
        help="Model stable-name(s) to test in stage 5 (default: local/qwen4b_vision)",
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
    model_names = args.models or ["local/qwen4b_vision"]
    ok = run_stage5_routing(root, stack, model_names)
    results["stage5_routing"] = ok

    if not args.no_stop:
        stop_all(root, stack)

    _summarise(results)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
