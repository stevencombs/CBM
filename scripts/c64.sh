#!/usr/bin/env bash
# C64 BASIC 2.0: check / run / push / push-run
# Load $0801. Uses Homebrew VICE petcat, not MEGA65 petcat.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
C64="$ROOT/C64"
PETCAT="${PETCAT:-/opt/homebrew/bin/petcat}"
C1541="${C1541:-/opt/homebrew/bin/c1541}"
X64="${X64:-/opt/homebrew/bin/x64sc}"
SDCARD="${CBM_PUSH_C64:-$C64/sdcard}"
LOAD_HEX="${CBM_C64_LOAD:-0801}"
BREW_PREFIX="$(cd "$(dirname "$PETCAT")/.." && pwd)"

usage() {
  echo "usage: $(basename "$0") check|run|push|push-run [listing.bas]" >&2
  exit 2
}

gtk_env() {
  export GSETTINGS_SCHEMA_DIR="${GSETTINGS_SCHEMA_DIR:-$BREW_PREFIX/share/glib-2.0/schemas}"
  export XDG_DATA_DIRS="${XDG_DATA_DIRS:-$BREW_PREFIX/share:/usr/local/share:/usr/share}"
  export GDK_BACKEND="${GDK_BACKEND:-quartz}"
}

program_dir() {
  local f="${1:-}"
  if [[ -z "$f" || "$f" == *"\$ZED_FILE"* ]]; then
    echo "Open a .bas listing in src/ first." >&2
    exit 1
  fi
  [[ "$f" == /* ]] || f="$PWD/$f"
  local d
  d="$(cd "$(dirname "$f")" && pwd)"
  if [[ "$(basename "$d")" == "src" ]]; then
    dirname "$d"
    return
  fi
  echo "Expected a file in <program>/src/*.bas (got $f)" >&2
  exit 1
}

cbm_name() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9' | cut -c1-16
}

tokenize() {
  local dir="$1"
  local name
  name="$(basename "$dir")"
  local src="$dir/src/${name}.bas"
  if [[ ! -f "$src" ]]; then
    src="$(ls "$dir"/src/*.bas 2>/dev/null | head -1 || true)"
  fi
  if [[ -z "$src" || ! -f "$src" ]]; then
    echo "No .bas in $dir/src" >&2
    exit 1
  fi
  mkdir -p "$dir/export"
  local prg="$dir/export/${name}.prg"
  echo "petcat -w2 -l $LOAD_HEX  ($src)" >&2
  "$PETCAT" -w2 -l "$LOAD_HEX" -f -o "$prg" -- "$src"
  echo "PRG $prg  load \$$LOAD_HEX  $(wc -c < "$prg" | tr -d ' ') bytes" >&2
  echo "$prg"
}

make_d64() {
  local dir="$1"
  local name
  name="$(basename "$dir")"
  local prg="$dir/export/${name}.prg"
  local d64="$dir/export/${name}.d64"
  local disk
  disk="$(cbm_name "$name")"
  local id
  id="$(echo "$disk" | cut -c1-2 | tr '[:lower:]' '[:upper:]')"
  [[ -n "$id" ]] || id="C6"
  echo "c1541 format $disk,$id" >&2
  "$C1541" -format "$disk,$id" d64 "$d64" -attach "$d64" -write "$prg" "$disk" >/dev/null
  echo "D64 $d64" >&2
}

cmd="${1:-}"
file="${2:-}"
[[ -n "$cmd" ]] || usage

dir="$(program_dir "$file")"
name="$(basename "$dir")"

case "$cmd" in
  check)
    tokenize "$dir" >/dev/null
    make_d64 "$dir"
    echo "Check OK. Review the listing; Push is your key, not Grok's."
    ;;
  run)
    prg="$(tokenize "$dir")"
    gtk_env
    echo "Starting x64sc (NTSC). Close the window when finished."
    pkill -x x64sc 2>/dev/null || true
    sleep 0.2
    exec "$X64" -ntsc \
      -autostartprgmode 1 -autostart-warp +drive8truedrive \
      -autostart "$prg"
    ;;
  push|push-run)
    tokenize "$dir" >/dev/null
    make_d64 "$dir"
    mkdir -p "$SDCARD"
    cp "$dir/export/${name}.prg" "$SDCARD/"
    cp "$dir/export/${name}.d64" "$SDCARD/"
    disk="$(cbm_name "$name")"
    echo "Pushed to $SDCARD"
    echo "  ${name}.prg"
    echo "  ${name}.d64"
    echo
    echo "On the C64 (SD2IEC / Pi1541) or C64 Ultimate USB/SD:"
    echo "  LOAD\"$disk\",8"
    echo "  RUN"
    if [[ "$cmd" == "push-run" ]]; then
      echo
      echo "Push+run cannot press RUN on a breadbin or via USB copy."
      echo "The files are on the card; you type RUN (or pick the PRG in the Ultimate File Browser)."
      echo "To watch it execute here, use: C64: Run in VICE"
    fi
    ;;
  *)
    usage
    ;;
esac
