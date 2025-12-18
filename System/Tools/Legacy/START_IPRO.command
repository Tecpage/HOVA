#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
chmod +x "IPRO/start_dashboard.command" 2>/dev/null || true
open "IPRO/start_dashboard.command"
