from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .config_loader import load_stack_config


def http_probe(url: str, headers: dict[str, str] | None = None, timeout: float = 5.0) -> tuple[bool, int | None, str]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(256).decode("utf-8", errors="replace")
            return True, response.getcode(), body
    except urllib.error.HTTPError as exc:
        body = exc.read(256).decode("utf-8", errors="replace")
        return False, exc.code, body
    except urllib.error.URLError as exc:
        return False, None, str(exc.reason)
    except OSError as exc:
        return False, None, str(exc)


def wait_for_any(urls: list[str], headers: dict[str, str] | None = None, timeout: float = 120.0, interval: float = 2.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for url in urls:
            ok, _, _ = http_probe(url, headers=headers)
            if ok:
                return url
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for readiness: {urls}")


def check_stack_health(root: str | Path) -> dict[str, Any]:
    stack = load_stack_config(root)
    results: dict[str, Any] = {"llama_swap": {}, "gateway": {}}

    llama_swap_urls = [f"http://{stack.llama_swap.host}:{stack.llama_swap.port}{path}" for path in stack.llama_swap.health_paths]
    llama_swap_checks = []
    llama_swap_ok = False
    for url in llama_swap_urls:
        ok, status_code, detail = http_probe(url)
        llama_swap_checks.append({"url": url, "ok": ok, "status_code": status_code, "detail": detail})
        llama_swap_ok = llama_swap_ok or ok
    results["llama_swap"] = {"ok": llama_swap_ok, "checks": llama_swap_checks}

    gateway_headers: dict[str, str] = {}
    if stack.litellm.master_key_env in os.environ:
        gateway_headers["Authorization"] = f"Bearer {os.environ[stack.litellm.master_key_env]}"

    gateway_urls = [f"http://{stack.litellm.host}:{stack.litellm.port}{path}" for path in stack.litellm.health_paths]
    gateway_checks = []
    gateway_ok = False
    for url in gateway_urls:
        ok, status_code, detail = http_probe(url, headers=gateway_headers)
        gateway_checks.append({"url": url, "ok": ok, "status_code": status_code, "detail": detail})
        gateway_ok = gateway_ok or ok

    results["gateway"] = {"ok": gateway_ok, "checks": gateway_checks}
    results["all_ok"] = gateway_ok and llama_swap_ok
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check llama-swap and LiteLLM health.")
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()

    results = check_stack_health(args.root)
    print(json.dumps(results, indent=2))
    return 0 if results["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
