#!/usr/bin/env bash
# MEGA65 BASIC65: check / run / push / push-run / push-xemu
# Tokenize with VICE petcat -w65 ($2001). Network: ~/m65tools/etherload.
# Emulator: /Applications/xmega65.app
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
M65TOOLS="${M65TOOLS:-$HOME/m65tools}"
export PATH="$M65TOOLS:$HOME/.local/bin:/opt/homebrew/bin:$PATH"
PETCAT="${PETCAT:-/opt/homebrew/bin/petcat}"
XMEGA65_APP="${XMEGA65_APP:-/Applications/xmega65.app}"
LOAD_HEX="${CBM_MEGA65_LOAD:-2001}"

find_m65tool() {
  local name="$1"
  local c
  for c in "$M65TOOLS/$name" "$M65TOOLS/${name}.osx" "$(command -v "$name" 2>/dev/null || true)"; do
    if [[ -n "$c" && -x "$c" ]]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

usage() {
  echo "usage: $(basename "$0") check|run|push|push-run|push-xemu [listing.m65]" >&2
  exit 2
}

program_dir() {
  local f="${1:-}"
  if [[ -z "$f" || "$f" == *"\$ZED_FILE"* ]]; then
    echo "Open a .m65 listing in src/ first." >&2
    exit 1
  fi
  [[ "$f" == /* ]] || f="$PWD/$f"
  local d
  d="$(cd "$(dirname "$f")" && pwd)"
  if [[ "$(basename "$d")" == "src" ]]; then
    dirname "$d"
    return
  fi
  echo "$d"
}

tokenize() {
  local dir="$1"
  local name
  name="$(basename "$dir")"
  local src="$dir/src/${name}.m65"
  if [[ ! -f "$src" ]]; then
    src="$(ls "$dir"/src/*.m65 2>/dev/null | head -1 || true)"
  fi
  if [[ -z "$src" || ! -f "$src" ]]; then
    echo "No .m65 in $dir/src" >&2
    exit 1
  fi
  mkdir -p "$dir/export"
  local prg="$dir/export/${name}.prg"
  echo "petcat -w65  ($src) → $prg" >&2
  "$PETCAT" -w65 -f -o "$prg" -- "$src"
  echo "PRG $prg  load \$$LOAD_HEX  $(wc -c < "$prg" | tr -d ' ') bytes" >&2
  echo "$prg"
}

cmd="${1:-}"
file="${2:-}"
[[ -n "$cmd" ]] || usage

dir="$(program_dir "$file")"

case "$cmd" in
  check)
    tokenize "$dir" >/dev/null
    echo "Check OK. Review the listing; Push is your key, not Grok's."
    ;;
  run|push-xemu)
    prg="$(tokenize "$dir")"
    xbin="$XMEGA65_APP/Contents/MacOS/xmega65"
    if [[ ! -x "$xbin" ]]; then
      echo "xmega65 not found at $xbin" >&2
      exit 1
    fi
    echo "Pushing $prg into XEMU (-besure -prg)"
    pkill -x xmega65 2>/dev/null || true
    sleep 0.3
    # App bundle is x86_64; Rosetta is required on Apple Silicon.
    arch -x86_64 "$xbin" -besure -prg "$prg" \
      >/tmp/cbm-xmega65.log 2>&1 &
    echo "XEMU started (log /tmp/cbm-xmega65.log)"
    ;;
  push)
    prg="$(tokenize "$dir")"
    etherload="$(find_m65tool etherload || true)"
    if [[ -z "$etherload" ]]; then
      echo "etherload not found in $M65TOOLS" >&2
      exit 1
    fi
    echo "Network push via $etherload (load, do not RUN)"
    "$etherload" "$prg"
    echo "On the MEGA65 you should be at READY. Type RUN if you want it to go."
    ;;
  push-run)
    prg="$(tokenize "$dir")"
    etherload="$(find_m65tool etherload || true)"
    if [[ -z "$etherload" ]]; then
      echo "etherload not found in $M65TOOLS" >&2
      exit 1
    fi
    echo "Network push+run via $etherload -r"
    "$etherload" -r "$prg"
    ;;
  *)
    usage
    ;;
esac
