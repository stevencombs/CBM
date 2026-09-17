#!/usr/bin/env bash
# CBM BASIC snippets for .bas and .m65 (language name "CBM BASIC").
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/snippets"
DEST="${HOME}/.config/zed/snippets"
mkdir -p "$DEST"
cp "$SRC/cbm basic.json" "$DEST/cbm basic.json"
cp "$SRC/cbm basic.json" "$DEST/plaintext.json"
echo "CBM BASIC snippets → $DEST/cbm basic.json"
echo "Type wht / clr / red then Tab in a CBM BASIC buffer."
