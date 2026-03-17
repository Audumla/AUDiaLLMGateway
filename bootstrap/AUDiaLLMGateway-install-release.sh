#!/usr/bin/env bash
set -euo pipefail

OWNER="${OWNER:-ExampleOrg}"
REPO="${REPO:-AUDiaLLMGateway}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/AUDiaLLMGateway}"
VERSION="${VERSION:-latest}"

TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ "$VERSION" == "latest" ]]; then
  API_URL="https://api.github.com/repos/$OWNER/$REPO/releases/latest"
else
  API_URL="https://api.github.com/repos/$OWNER/$REPO/releases/tags/$VERSION"
fi

ARCHIVE_URL="$(curl -fsSL "$API_URL" | python3 -c 'import json,sys; print(json.load(sys.stdin)["tarball_url"])')"
ARCHIVE_PATH="$TMP_ROOT/release.tar.gz"
curl -fsSL "$ARCHIVE_URL" -o "$ARCHIVE_PATH"

EXTRACT_ROOT="$TMP_ROOT/bundle"
mkdir -p "$EXTRACT_ROOT"
tar -xzf "$ARCHIVE_PATH" -C "$EXTRACT_ROOT"
BUNDLE_DIR="$(find "$EXTRACT_ROOT" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

cd "$BUNDLE_DIR"

# Install Python dependencies in a venv (needed on modern systems with PEP 668)
VENV_DIR="$BUNDLE_DIR/.venv-bootstrap"
"$PYTHON_BIN" -m venv "$VENV_DIR" --system-site-packages
VENV_PYTHON="$VENV_DIR/bin/python"
"$VENV_PYTHON" -m pip install -q -r requirements.txt

# Run the installer with the venv Python
"$VENV_PYTHON" -m src.installer.release_installer install-bundle --bundle-root "$BUNDLE_DIR" --install-dir "$INSTALL_DIR" --version "$VERSION"
