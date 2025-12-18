#!/bin/bash
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_FILE="$SRC_DIR/hammerspoon/y_launcher.lua"

DST_DIR="$HOME/.hammerspoon"
DST_FILE="$DST_DIR/y_launcher.lua"
INIT_FILE="$DST_DIR/init.lua"

if [ ! -f "$SRC_FILE" ]; then
  echo "FEHLER: Quelle nicht gefunden: $SRC_FILE"
  exit 2
fi

mkdir -p "$DST_DIR"
cp "$SRC_FILE" "$DST_FILE"

echo "OK: Kopiert -> $DST_FILE"

if [ ! -f "$INIT_FILE" ]; then
  echo 'require("y_launcher")' > "$INIT_FILE"
  echo "OK: init.lua erstellt -> $INIT_FILE"
else
  if ! grep -q 'require("y_launcher")' "$INIT_FILE"; then
    {
      echo ""
      echo "-- Y Launcher"
      echo 'require("y_launcher")'
    } >> "$INIT_FILE"
    echo "OK: init.lua ergänzt (require y_launcher)"
  else
    echo "OK: init.lua enthält y_launcher bereits"
  fi
fi

echo ""
echo "Nächster Schritt: Hammerspoon → Reload Config"
echo "(oder: Menüleisten-Icon → Reload Config)"

open -a Hammerspoon >/dev/null 2>&1 || true
