#!/usr/bin/env bash
# Copy VIC-20 PETSCII snippets into Zed's user snippet dir.
# Does not overwrite mega65-zed plaintext.json.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/snippets"
DEST="${HOME}/.config/zed/snippets"
mkdir -p "$DEST"
cp "$SRC/cbm basic.json" "$DEST/cbm basic.json"
cp "$SRC/vic-20 basic.json" "$DEST/vic-20 basic.json"
echo "CBM BASIC snippets (VIC-20 set) → $DEST"
echo "In a .bas buffer, type red / clr / cyn and Tab (or { then complete)."
