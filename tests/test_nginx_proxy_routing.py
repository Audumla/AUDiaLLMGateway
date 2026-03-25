"""Regression tests for nginx reverse-proxy routing.

These tests verify that the generated nginx config routes every path that the
llama-swap UI JavaScript calls to the correct upstream.  This is a recurring
regression: the llamaswap UI uses absolute root paths (/logs, /api/events, …)
regardless of the base URL it is served from, so explicit nginx locations are
required to forward them to llamaswap_upstream.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.launcher.config_loader import build_nginx_config, load_stack_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def nginx_cfg() -> str:
    stack = load_stack_config(ROOT)
    return build_nginx_config(stack)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _has_location(cfg: str, location_pattern: str, upstream: str) -> bool:
    """Return True if cfg contains a location block for *location_pattern* that
    proxies to *upstream* (string match on the proxy_pass line)."""
    # Match "location <pattern> {" followed by a proxy_pass line within ~10 lines
    block_re = re.compile(
        r"location\s+" + re.escape(location_pattern) + r"\s*\{[^}]*proxy_pass\s+[^\n;]*" + re.escape(upstream),
        re.DOTALL,
    )
    return bool(block_re.search(cfg))


# ---------------------------------------------------------------------------
# llamaswap UI: HTML/asset routes (under /llamaswap/ prefix)
# ---------------------------------------------------------------------------

def test_llamaswap_ui_redirect(nginx_cfg: str) -> None:
    """Bare /llamaswap redirects to the UI page."""
    assert "location = /llamaswap" in nginx_cfg
    assert "return 301 /llamaswap/ui/" in nginx_cfg


def test_llamaswap_ui_asset_proxy(nginx_cfg: str) -> None:
    """/llamaswap/ui/ proxies to llamaswap_upstream."""
    assert "location /llamaswap/ui/" in nginx_cfg
    assert "proxy_pass http://llamaswap_upstream" in nginx_cfg


def test_llamaswap_ui_sub_filter_rewrites_asset_paths(nginx_cfg: str) -> None:
    """Asset hrefs/srcs inside the UI HTML are rewritten to /llamaswap/ui/."""
    assert 'sub_filter \'href="/ui/\' \'href="/llamaswap/ui/\'' in nginx_cfg
    assert 'sub_filter \'src="/ui/\' \'src="/llamaswap/ui/\'' in nginx_cfg


# ---------------------------------------------------------------------------
# llamaswap API routes called with absolute paths from the UI JavaScript
#
# The llamaswap UI JS bundle uses root-level paths regardless of the URL the
# page is served from.  Each path below MUST be proxied to llamaswap_upstream
# or the UI will 404 / hang.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,upstream_fragment", [
    # Exact single-path locations
    ("= /activity", "llamaswap_upstream"),
    ("= /logs",     "llamaswap_upstream"),
    ("= /models",   "llamaswap_upstream"),
    # Prefix locations covering template-literal API calls
    ("/api/",       "llamaswap_upstream"),
    ("/upstream/",  "llamaswap_upstream"),
    ("/dev/",       "llamaswap_upstream"),
])
def test_llamaswap_api_route_proxied_to_llamaswap(
    nginx_cfg: str,
    path: str,
    upstream_fragment: str,
) -> None:
    """Verify each llamaswap API path is forwarded to llamaswap_upstream.

    Regression: these paths were previously unhandled and returned 404 when
    the UI was accessed via the /llamaswap/ proxy prefix.
    """
    assert _has_location(nginx_cfg, path, upstream_fragment), (
        f"nginx config is missing a proxy_pass to {upstream_fragment!r} "
        f"under 'location {path}'"
    )


def test_llamaswap_api_paths_not_routed_to_litellm(nginx_cfg: str) -> None:
    """None of the llamaswap-specific API paths should fall through to litellm."""
    # Build a rough set of location→upstream pairs and make sure /activity,
    # /logs, /models, /api/, /upstream/, /dev/ don't map to litellm_upstream.
    litellm_blocks_re = re.compile(
        r"location\s+(= /activity|= /logs|= /models|/api/|/upstream/|/dev/)\s*\{[^}]*proxy_pass[^;]*litellm_upstream",
        re.DOTALL,
    )
    assert not litellm_blocks_re.search(nginx_cfg), (
        "A llamaswap API path is mistakenly routing to litellm_upstream"
    )


# ---------------------------------------------------------------------------
# LiteLLM / gateway routes
# ---------------------------------------------------------------------------

def test_v1_routes_to_litellm(nginx_cfg: str) -> None:
    assert _has_location(nginx_cfg, "/v1/", "litellm_upstream")


def test_health_routes_to_litellm(nginx_cfg: str) -> None:
    assert _has_location(nginx_cfg, "/health", "litellm_upstream")


def test_litellm_ui_routes_to_litellm(nginx_cfg: str) -> None:
    assert _has_location(nginx_cfg, "/ui/", "litellm_upstream")


# ---------------------------------------------------------------------------
# Consistency: all expected upstreams declared
# ---------------------------------------------------------------------------

def test_upstreams_declared(nginx_cfg: str) -> None:
    assert "upstream litellm_upstream" in nginx_cfg
    assert "upstream llamaswap_upstream" in nginx_cfg
