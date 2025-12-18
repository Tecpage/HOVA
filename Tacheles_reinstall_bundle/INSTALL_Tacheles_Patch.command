#!/bin/bash
set -euo pipefail

Y="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Y"

# find Tacheles root: contains Tacheles.yaml
TROOT=""
if [ -f "$Y/Tacheles/Tacheles.yaml" ]; then
  TROOT="$Y/Tacheles"
elif [ -f "$Y/Am Tacheles/Tacheles.yaml" ]; then
  TROOT="$Y/Am Tacheles"
else
  # fallback: first match under Y
  CAND="$(find "$Y" -maxdepth 6 -type f -name "Tacheles.yaml" -print -quit 2>/dev/null || true)"
  if [ -n "${CAND}" ]; then
    TROOT="$(dirname "$CAND")"
  fi
fi

if [ -z "${TROOT}" ] || [ ! -f "$TROOT/Tacheles.yaml" ]; then
  echo "FEHLER: Tacheles.yaml nicht gefunden unter:"
  echo " - $Y/Tacheles/Tacheles.yaml"
  echo " - $Y/Am Tacheles/Tacheles.yaml"
  echo "Bitte prüfe den Ordnernamen und lege Tacheles.yaml dort ab."
  exit 2
fi

echo "OK: Tacheles-Ordner gefunden:"
echo " -> $TROOT"

TS="$(date '+%Y%m%d_%H%M%S')"

backup_one(){
  local f="$1"
  if [ -f "$f" ]; then
    cp -p "$f" "$f.bak.$TS"
    echo "Backup: $f.bak.$TS"
  fi
}

mkdir -p "$TROOT/dashboard"

backup_one "$TROOT/dashboard/index.html"
backup_one "$TROOT/dashboard/styles.css"
backup_one "$TROOT/dashboard/app.js"
backup_one "$TROOT/dashboard_server.py"

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -p "$SRC_DIR/dashboard/index.html" "$TROOT/dashboard/index.html"
cp -p "$SRC_DIR/dashboard/styles.css" "$TROOT/dashboard/styles.css"
cp -p "$SRC_DIR/dashboard/app.js" "$TROOT/dashboard/app.js"
cp -p "$SRC_DIR/dashboard_server.py" "$TROOT/dashboard_server.py"

echo "OK: Patch installiert (nur Code/Frontend)."

export TROOT
python3 - <<'PY'
import os, yaml
troot = os.environ.get("TROOT","")
p = os.path.join(troot, "Tacheles.yaml")
with open(p, "r", encoding="utf-8") as f:
    doc = yaml.safe_load(f) or {}
defs = doc.get("defects") if isinstance(doc.get("defects"), list) else []
print("Defects in Tacheles.yaml:", len(defs))
PY

echo ""
echo "Nächster Schritt:"
echo "1) Tacheles neu starten (start_dashboard.command) ODER via Launcher."
echo "2) Öffnen: http://127.0.0.1:8010/dashboard/"
