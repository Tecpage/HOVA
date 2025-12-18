#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8010}"

cd "$ROOT"

if [ ! -f "$ROOT/Tacheles.yaml" ]; then
  echo "FEHLER: Tacheles.yaml nicht gefunden: $ROOT/Tacheles.yaml"
  exit 2
fi

# Stop old server by PID if present
PID_FILE="$ROOT/.server.pid"
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" 2>/dev/null || true
    sleep 0.2
  fi
  rm -f "$PID_FILE" || true
fi

# Free port if needed
PIDS_BY_PORT="$(lsof -ti tcp:${PORT} 2>/dev/null || true)"
if [ -n "$PIDS_BY_PORT" ]; then
  kill ${PIDS_BY_PORT} 2>/dev/null || true
  sleep 0.2
fi

# Ensure python deps (quiet)
python3 -m pip install --user pyyaml openpyxl >/dev/null 2>&1 || true

# Start server detached (so Terminal can close without prompting)
nohup python3 "$ROOT/dashboard_server.py" "$PORT" "$ROOT" >/dev/null 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
sleep 0.4

STAMP="$(date +%s)"
URL="http://127.0.0.1:${PORT}/dashboard/?v=${STAMP}"

# Open in Chrome as a NEW TAB (non-destructive)
set +e
osascript <<OSA >/dev/null 2>&1
set targetURL to "${URL}"
tell application "Google Chrome"
  activate
  if (count of windows) = 0 then
    make new window
    set URL of active tab of front window to targetURL
  else
    tell front window
      make new tab at end of tabs with properties {URL:targetURL}
      set active tab index to (count of tabs)
    end tell
  end if
end tell
OSA
if [ $? -ne 0 ]; then
  open "$URL" >/dev/null 2>&1 || true
fi
set -e

echo "=== Läuft (PID $NEW_PID) auf $URL ==="
exit 0
