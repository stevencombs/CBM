#!/usr/bin/env bash
# VIC-20 BASIC 2.0: check / run / push / push-run
# Unexpanded 3.5K default (load $1001). Uses Homebrew VICE petcat, not MEGA65 petcat.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VIC="$ROOT/VIC20"
PETCAT="${PETCAT:-/opt/homebrew/bin/petcat}"
C1541="${C1541:-/opt/homebrew/bin/c1541}"
XVIC="${XVIC:-/opt/homebrew/bin/xvic}"
SDCARD="${CBM_PUSH_VIC20:-$VIC/sdcard}"
LOAD_HEX="${CBM_VIC20_LOAD:-1001}"
MEMORY="${CBM_VIC20_MEMORY:-none}"
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
  [[ -n "$id" ]] || id="VC"
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
    echo "Starting xvic (NTSC, memory=$MEMORY). Close the window when finished."
    pkill -x xvic 2>/dev/null || true
    sleep 0.2
    exec "$XVIC" -ntsc -model vic20ntsc -memory "$MEMORY" \
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
    echo "On the VIC-20 (SD2IEC / Pi1541):"
    echo "  LOAD\"$disk\",8"
    echo "  RUN"
    if [[ "$cmd" == "push-run" ]]; then
      echo
      echo "Push+run cannot press RUN on a real VIC-20."
      echo "The files are on the card; you type RUN."
      echo "To watch it execute here, use: VIC-20: Run in VICE"
    fi
    ;;
  *)
    usage
    ;;
esac
