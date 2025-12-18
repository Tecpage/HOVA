#!/bin/bash
set -euo pipefail
pkill -f "dashboard_server.py" >/dev/null 2>&1 || true
pkill -f "launcher_server.py"  >/dev/null 2>&1 || true
echo "Stop-All: fertig."
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
