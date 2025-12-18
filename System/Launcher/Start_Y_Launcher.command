#!/bin/bash
set -euo pipefail
ROOT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Y/System/Launcher"
cd "$ROOT"
chmod +x "./start_launcher.command" 2>/dev/null || true
./start_launcher.command 8090
