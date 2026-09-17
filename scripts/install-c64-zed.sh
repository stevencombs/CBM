#!/usr/bin/env bash
# One-time C64 Zed setup on this Mac.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXT="$ROOT/zed/c64-basic"

echo "==> snippets"
"$EXT/copy-snippets.sh"

echo "==> Source Code Pro"
if ! fc-list 2>/dev/null | grep -qi "Source Code Pro"; then
  echo "    Font not found. Install with:  brew install --cask font-source-code-pro"
else
  echo "    found"
fi

echo
echo "In Zed:"
echo "  1. zed: extensions  →  Install Dev Extension"
echo "     pick:  $EXT"
echo "  2. File → Open Folder → $ROOT/C64"
echo "     (or run:  $ROOT/scripts/retro c64 )"
echo "  3. Theme should be C64 Blue (navy listing, green Grok chrome)."
echo "  4. Open hello/src/hello.bas — type red / orng / clr then Tab."
echo "  5. Command palette → task: spawn → C64: Check listing"
echo
echo "Push copies PRG/D64 to $ROOT/C64/sdcard (you press that task, not Grok)."
echo "Grok is the bottom terminal: task: spawn → Grok Build. Leave Zed Agent chat closed."
