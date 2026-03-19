#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


def _load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class Handler(BaseHTTPRequestHandler):
    config: dict = {}

    def log_message(self, format: str, *args) -> None:
        return

    def _write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        startup = self.config.get("startup", {})
        model = startup.get("model", "mock-vllm-model")
        if self.path == "/health":
            self._write_json({"status": "ok", "model": model})
            return
        if self.path == "/v1/models":
            self._write_json({"object": "list", "data": [{"id": model, "object": "model"}]})
            return
        self._write_json({"path": self.path, "model": model})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            request = json.loads(body.decode("utf-8"))
        except Exception:
            request = {}
        startup = self.config.get("startup", {})
        model = request.get("model") or startup.get("model", "mock-vllm-model")
        self._write_json(
            {
                "id": "mock-vllm-001",
                "object": "chat.completion",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": f"Mock vLLM response from {model}"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 6, "total_tokens": 11},
            }
        )


def main() -> int:
    config = _load_config(sys.argv[1])
    Handler.config = config
    port = int(config.get("service", {}).get("port", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Mock vLLM listening on http://0.0.0.0:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
