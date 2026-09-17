#!/usr/bin/env bash
# CBM BASIC snippets for .bas and .m65 (language name "CBM BASIC").
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/snippets"
DEST="${HOME}/.config/zed/snippets"
mkdir -p "$DEST"
cp "$SRC/cbm basic.json" "$DEST/cbm basic.json"
cp "$SRC/cbm basic.json" "$DEST/plaintext.json"
# Language-agnostic: works even if the buffer is still Unknown
cp "$SRC/cbm basic.json" "$DEST/snippets.json"
echo "CBM BASIC snippets → $DEST (cbm basic.json + snippets.json)"
echo "Type wht then Tab (completion: {wht})."
