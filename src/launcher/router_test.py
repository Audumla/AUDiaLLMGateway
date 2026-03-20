from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from .config_loader import load_published_models, load_stack_config


def invoke_chat_completion(base_url: str, api_key: str, model_name: str, prompt: str) -> dict[str, Any]:
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 96,
    }
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_response(model_name: str, response: dict[str, Any]) -> None:
    choices = response.get("choices", [])
    if not choices:
        raise ValueError(f"{model_name} returned no choices")
    message = choices[0].get("message", {})
    if "content" not in message:
        raise ValueError(f"{model_name} response did not include message content")


def run_tests(root: str | Path, all_models: bool, model_names: list[str], prompt: str) -> list[dict[str, Any]]:
    stack = load_stack_config(root)
    base_url = f"http://{stack.litellm.host}:{stack.litellm.port}"
    api_key = os.environ.get(stack.litellm.master_key_env, "sk-local-dev")

    selected = [model.label for model in load_published_models(root)] if all_models else model_names
    results = []
    for model_name in selected:
        response = invoke_chat_completion(base_url, api_key, model_name, prompt)
        validate_response(model_name, response)
        results.append({"model": model_name, "id": response.get("id"), "object": response.get("object")})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Send routing tests through the LiteLLM gateway.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--model", action="append", default=[], help="Model label to test")
    parser.add_argument("--all-models", action="store_true", help="Test every configured model")
    parser.add_argument(
        "--prompt",
        default="Reply with one short sentence confirming which profile handled this request.",
        help="Prompt used for the routing check",
    )
    args = parser.parse_args()

    if not args.all_models and not args.model:
        parser.error("Use --all-models or provide at least one --model value.")

    results = run_tests(args.root, args.all_models, args.model, args.prompt)
    print(json.dumps({"ok": True, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
