#!/bin/bash
set -euo pipefail

# =========================
# IPRO – Dashboard Starter (self-healing + self-checking)
# - startet/prüft Build + lokalen Server
# - entfernt einen evtl. von uns angelegten Symlink Y/tenants.yaml (niemals echte Dateien löschen)
# - öffnet optional Chrome im App-Mode (ohne Adress-/Lesezeichenleiste)
# =========================

PORT="${1:-8000}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
DASH="$ROOT/dashboard"
DATA="$DASH/data"
PY="${PYTHON:-python3}"

LOG_DIR="$HOME/Library/Logs/IPRO"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/ipro_${PORT}.log"
BUILD_LOG="$LOG_DIR/ipro_build_${PORT}.log"

ts(){ date +"%Y-%m-%d %H:%M:%S"; }

echo "=== IPRO Dashboard Start (Self-Healing) ===" >"$LOG_FILE"
echo "$(ts) ROOT=$ROOT" >>"$LOG_FILE"
echo "$(ts) PORT=$PORT" >>"$LOG_FILE"

# 0) Pflichtdateien
TENANTS_YAML="$ROOT/tenants.yaml"
BUILD_PY="$ROOT/build_dashboard.py"

if [ ! -f "$TENANTS_YAML" ]; then
  echo "$(ts) ERROR: tenants.yaml fehlt: $TENANTS_YAML" >>"$LOG_FILE"
  osascript -e 'display alert "IPRO" message "tenants.yaml fehlt im IPRO-Ordner.\n\nBitte prüfe: IPRO/tenants.yaml" as critical buttons {"OK"}' >/dev/null 2>&1 || true
  exit 1
fi

if [ ! -f "$BUILD_PY" ]; then
  echo "$(ts) ERROR: build_dashboard.py fehlt: $BUILD_PY" >>"$LOG_FILE"
  osascript -e 'display alert "IPRO" message "build_dashboard.py fehlt im IPRO-Ordner.\n\nBitte prüfe den IPRO Projektordner." as critical buttons {"OK"}' >/dev/null 2>&1 || true
  exit 1
fi

# 1) Niemals tenants.yaml im Y-Root liegen lassen (nur Symlink entfernen!)
Y_ROOT="$(cd "$ROOT/.." && pwd)"
if [ -L "$Y_ROOT/tenants.yaml" ]; then
  echo "$(ts) FIX: Entferne Symlink $Y_ROOT/tenants.yaml" >>"$LOG_FILE"
  rm -f "$Y_ROOT/tenants.yaml" || true
fi
if [ -f "$Y_ROOT/tenants.yaml" ] && [ ! -L "$Y_ROOT/tenants.yaml" ]; then
  echo "$(ts) WARN: $Y_ROOT/tenants.yaml existiert als echte Datei – wird NICHT angerührt." >>"$LOG_FILE"
fi

# 2) Alte Server/Build-Prozesse stoppen (nur IPRO-Port)
PIDFILE="$DATA/server.pid"
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [[ "${OLD_PID:-}" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "$(ts) STOP: PIDFILE-Prozess $OLD_PID beenden" >>"$LOG_FILE"
    kill "$OLD_PID" 2>/dev/null || true
    sleep 0.2
    kill -9 "$OLD_PID" 2>/dev/null || true
  fi
  rm -f "$PIDFILE" 2>/dev/null || true
fi

# falls Port blockiert ist: kill (nur diesen Port)
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -ti tcp:"$PORT" 2>/dev/null || true)"
  if [ -n "${PIDS:-}" ]; then
    echo "$(ts) STOP: Port $PORT belegt → kill: ${PIDS}" >>"$LOG_FILE"
    for p in $PIDS; do
      kill "$p" 2>/dev/null || true
    done
    sleep 0.2
  fi
fi

mkdir -p "$DATA" >/dev/null 2>&1 || true

# 3) Self-Check: braucht es einen Build?
NEED_BUILD=0
REQ_FILES=(
  "$DASH/index.html"
  "$DASH/app.js"
  "$DATA/index.json"
  "$DATA/tenants_indexation.json"
  "$DATA/payments_rent_roll.json"
)
for f in "${REQ_FILES[@]}"; do
  if [ ! -s "$f" ]; then
    NEED_BUILD=1
  fi
done

# wenn YAML neuer als JSON -> rebuild
if [ "$NEED_BUILD" -eq 0 ] && [ -s "$DATA/tenants_indexation.json" ]; then
  if [ "$TENANTS_YAML" -nt "$DATA/tenants_indexation.json" ]; then
    NEED_BUILD=1
  fi
fi

# 4) Build (nur wenn nötig)
if [ "$NEED_BUILD" -eq 1 ]; then
  echo "$(ts) BUILD: start build_dashboard.py" >>"$LOG_FILE"
  echo "=== BUILD $(ts) ===" >"$BUILD_LOG"
  set +e
  "$PY" "$BUILD_PY" >>"$BUILD_LOG" 2>&1
  RC=$?
  set -e
  if [ "$RC" -ne 0 ]; then
    echo "$(ts) BUILD_FAIL (rc=$RC) → siehe $BUILD_LOG" >>"$LOG_FILE"
    # wir versuchen trotzdem ggf. mit alten Artefakten zu starten
  else
    echo "$(ts) BUILD_OK" >>"$LOG_FILE"
  fi
else
  echo "$(ts) BUILD: übersprungen (Artefakte vorhanden)" >>"$LOG_FILE"
fi

# 5) Final Verify (mindestens 1 Tenant muss im JSON sein)
if [ ! -s "$DATA/tenants_indexation.json" ]; then
  echo "$(ts) ERROR: tenants_indexation.json fehlt/leer: $DATA/tenants_indexation.json" >>"$LOG_FILE"
  osascript -e "display alert \"IPRO\" message \"Build/Verify fehlgeschlagen.\n\ntenants_indexation.json fehlt/leer.\n\nLog: $BUILD_LOG\" as critical buttons {\"OK\"}" >/dev/null 2>&1 || true
  exit 1
fi

# tenant count aus JSON prüfen
TENANTS_IN_JSON="$("$PY" - <<'PY'
import json, sys, pathlib
p=pathlib.Path(sys.argv[1])
try:
    data=json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("0"); raise SystemExit
if isinstance(data, dict):
    # mögliche keys: "rows", "items", "tenants"
    for k in ("rows","items","tenants","data"):
        if k in data and isinstance(data[k], list):
            print(len(data[k])); raise SystemExit
    print(len(data))
elif isinstance(data, list):
    print(len(data))
else:
    print("0")
PY
"$DATA/tenants_indexation.json")" || TENANTS_IN_JSON="0"

echo "$(ts) VERIFY: tenants_in_json=$TENANTS_IN_JSON" >>"$LOG_FILE"
if [ "${TENANTS_IN_JSON:-0}" -lt 1 ]; then
  osascript -e "display alert \"IPRO\" message \"IPRO Dashboard hat keine Mieter-Daten geladen (JSON leer).\n\nBitte prüfe tenants.yaml im IPRO Ordner.\n\nLog: $BUILD_LOG\" as critical buttons {\"OK\"}" >/dev/null 2>&1 || true
  exit 1
fi

# 6) Server starten
echo "$(ts) SERVER: start python http.server" >>"$LOG_FILE"
cd "$ROOT"

# Wichtig: --directory ist in Python >=3.7 verfügbar
nohup "$PY" -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT" >>"$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" >"$PIDFILE"

# 7) Wait until ready (ansonsten: Alert)
READY=0
for i in $(seq 1 60); do
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS "http://127.0.0.1:${PORT}/dashboard/" >/dev/null 2>&1; then
      READY=1
      break
    fi
  else
    # fallback: nc
    if command -v nc >/dev/null 2>&1; then
      if nc -z 127.0.0.1 "$PORT" >/dev/null 2>&1; then
        READY=1
        break
      fi
    fi
  fi
  sleep 0.1
done

if [ "$READY" -ne 1 ]; then
  echo "$(ts) ERROR: Server nicht erreichbar auf 127.0.0.1:$PORT" >>"$LOG_FILE"
  osascript -e "display alert \"IPRO\" message \"IPRO Server startet nicht oder ist nicht erreichbar.\n\nPort: $PORT\nLog: $LOG_FILE\" as critical buttons {\"OK\"}" >/dev/null 2>&1 || true
  exit 1
fi

echo "$(ts) OK: Server erreichbar." >>"$LOG_FILE"

# 8) Browser öffnen (nur wenn nicht durch Dock-App bereits geöffnet)
if [ "${Y_NO_OPEN:-0}" != "1" ]; then
  URL="http://127.0.0.1:${PORT}/dashboard/?v=$(date +%s)"
  echo "$(ts) OPEN: $URL" >>"$LOG_FILE"
  open -na "Google Chrome" --args --app="$URL" --new-window >/dev/null 2>&1 || open "$URL" >/dev/null 2>&1 || true
fi

exit 0
