#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8090}"
PID_FILE="$ROOT/.launcher.pid"

# Stop previous launcher if running
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" 2>/dev/null || true
    sleep 0.2
  fi
  rm -f "$PID_FILE" || true
fi

# free port
PIDS_BY_PORT="$(lsof -ti tcp:${PORT} 2>/dev/null || true)"
if [ -n "$PIDS_BY_PORT" ]; then
  kill ${PIDS_BY_PORT} 2>/dev/null || true
  sleep 0.2
fi

# Ensure deps (no Tkinter needed)
python3 -m pip install --user pyyaml >/dev/null 2>&1 || true

python3 "$ROOT/launcher_server.py" "$PORT" "$ROOT" >/dev/null 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
sleep 0.3

URL="http://127.0.0.1:${PORT}/launcher/?v=$(date +%s)"

# Open Launcher in a NEW Chrome window (non-destructive)
set +e
osascript <<OSA >/dev/null 2>&1
set targetURL to "${URL}"

tell application "Google Chrome"
  activate
  make new window
  set URL of active tab of front window to targetURL
end tell
OSA
if [ $? -ne 0 ]; then
  open "$URL" >/dev/null 2>&1 || true
fi
set -e

# Optional: close the Terminal window that launched this script (best-effort)
# We do this AFTER this script exits to avoid the "running process" confirmation.
( sleep 0.4; osascript -e 'tell application "Terminal" to try' \
    -e 'if (count of windows) > 0 then close front window saving no' \
    -e 'end try' >/dev/null 2>&1 ) &

exit 0
