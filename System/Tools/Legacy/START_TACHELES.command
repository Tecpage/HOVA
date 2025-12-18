#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
chmod +x "Am Tacheles/start_dashboard.command" 2>/dev/null || true
open "Am Tacheles/start_dashboard.command"
