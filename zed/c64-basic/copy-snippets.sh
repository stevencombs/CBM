#!/usr/bin/env bash
# Copy C64 PETSCII snippets into Zed's user snippet dir.
# Does not overwrite mega65-zed plaintext.json or VIC-20 snippets.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/snippets"
DEST="${HOME}/.config/zed/snippets"
mkdir -p "$DEST"
cp "$SRC/c64 basic.json" "$DEST/c64 basic.json"
echo "C64 snippets → $DEST"
echo "In a C64 .bas buffer, type red / orng / lblu and Tab (or { then complete)."
