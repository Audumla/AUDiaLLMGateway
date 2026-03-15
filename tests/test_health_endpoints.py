import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.launcher.health import http_probe, wait_for_any


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/health", "/ready"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def test_http_probe_and_wait_for_any() -> None:
    server = HTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        base = f"http://127.0.0.1:{server.server_port}"
        ok, status_code, _ = http_probe(f"{base}/health")
        assert ok is True
        assert status_code == 200
        assert wait_for_any([f"{base}/ready"], timeout=2.0, interval=0.1) == f"{base}/ready"
    finally:
        server.shutdown()
        thread.join()

