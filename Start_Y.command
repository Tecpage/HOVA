#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER_DIR="$ROOT/System/Launcher"

if [ ! -d "$LAUNCHER_DIR" ]; then
  echo "FEHLER: Launcher nicht gefunden: $LAUNCHER_DIR"
  exit 2
fi

chmod +x "$LAUNCHER_DIR/start_launcher.command" 2>/dev/null || true
"$LAUNCHER_DIR/start_launcher.command" 8090
