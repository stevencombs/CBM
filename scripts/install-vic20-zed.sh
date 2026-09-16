#!/usr/bin/env bash
# One-time VIC-20 Zed beta setup on this Mac.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXT="$ROOT/zed/vic20-basic"

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
echo "  2. File → Open Folder → $ROOT/VIC20"
echo "     (or run:  $ROOT/scripts/retro vic20 )"
echo "  3. Theme should be VIC-20 Cyan (cyan listing, green Grok chrome)."
echo "  4. Open hello/src/hello.bas — type red / clr then Tab."
echo "  5. Command palette → task: spawn → VIC-20: Check listing"
echo
echo "Push copies PRG/D64 to $ROOT/VIC20/sdcard (you press that task, not Grok)."
echo "Grok on the right: agent panel is already docked right in this workspace."
