#!/usr/bin/env bash
# Install VICE + 64tass, the Python MCP venv, the Grok skill symlink, and print
# (or apply) the Grok MCP stanza. Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_SRC="$ROOT/grok/skills/cbm"
SKILL_DST="${GROK_HOME:-$HOME/.grok}/skills/cbm"

echo "==> CBM root: $ROOT"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required: https://brew.sh" >&2
  exit 1
fi

echo "==> brew install vice tass64"
brew install vice tass64

echo "==> python venv for MCP"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m venv "$ROOT/mcp/vice/.venv"
"$ROOT/mcp/vice/.venv/bin/pip" install --upgrade pip
"$ROOT/mcp/vice/.venv/bin/pip" install -r "$ROOT/mcp/vice/requirements.txt"

echo "==> Grok skill symlink"
mkdir -p "$(dirname "$SKILL_DST")"
ln -sfn "$SKILL_SRC" "$SKILL_DST"
echo "    $SKILL_DST -> $SKILL_SRC"

if command -v grok >/dev/null 2>&1; then
  echo "==> grok mcp add vice"
  grok mcp add vice \
    -e "PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
    -e "HOME=$HOME" \
    -e "CBM_ROOT=$ROOT" \
    -e "GSETTINGS_SCHEMA_DIR=/opt/homebrew/share/glib-2.0/schemas" \
    -e "XDG_DATA_DIRS=/opt/homebrew/share:/usr/local/share:/usr/share" \
    -e "GDK_BACKEND=quartz" \
    -- "$ROOT/mcp/vice/.venv/bin/python" "$ROOT/mcp/vice/server.py" || true
  echo "Reload MCP in Grok: /mcps then r, or start a new session."
else
  echo "==> grok CLI not on PATH. Append this to ~/.grok/config.toml:"
  sed -e "s|__CBM_ROOT__|$ROOT|g" -e "s|__HOME__|$HOME|g" \
    "$ROOT/grok/config.snippet.toml"
fi

echo "==> done"
echo "VICE: $(command -v x64sc) / $(command -v xvic)"
echo "petcat: $(command -v petcat)"
echo "64tass: $(command -v 64tass)"
