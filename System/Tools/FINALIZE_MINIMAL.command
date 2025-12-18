#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

touch .gitignore
grep -q "^\.y/$" .gitignore || echo ".y/" >> .gitignore
grep -q "^\.DS_Store$" .gitignore || { echo ""; echo "# macOS"; echo ".DS_Store"; } >> .gitignore
grep -q "^\*\.bak-\*$" .gitignore || { echo ""; echo "# Backups"; echo "*.bak-*"; } >> .gitignore

[ -f "IPRO/tenants.yaml" ]  && ln -sf "IPRO/tenants.yaml"  "tenants.yaml"
[ -f "IPRO/payments.yaml" ] && ln -sf "IPRO/payments.yaml" "payments.yaml"

cat > AUTOMATE_ALL.command <<'C1'
#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
[ -f "IPRO/tenants.yaml" ]  && ln -sf "IPRO/tenants.yaml"  "tenants.yaml"
[ -f "IPRO/payments.yaml" ] && ln -sf "IPRO/payments.yaml" "payments.yaml"
command -v y >/dev/null 2>&1 && y gen || true
command -v y >/dev/null 2>&1 && y report || true
echo
echo "Fertig. Report: .y/report.txt"
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
C1
chmod +x AUTOMATE_ALL.command

cat > START_IPRO.command <<'C2'
#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
chmod +x "IPRO/start_dashboard.command" 2>/dev/null || true
open "IPRO/start_dashboard.command"
C2
chmod +x START_IPRO.command

cat > START_TACHELES.command <<'C3'
#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
chmod +x "Am Tacheles/start_dashboard.command" 2>/dev/null || true
open "Am Tacheles/start_dashboard.command"
C3
chmod +x START_TACHELES.command

cat > STOP_ALL.command <<'C4'
#!/bin/bash
set -euo pipefail
pkill -f "dashboard_server.py" >/dev/null 2>&1 || true
pkill -f "launcher_server.py"  >/dev/null 2>&1 || true
echo "Stop-All: fertig."
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
C4
chmod +x STOP_ALL.command

mkdir -p .y
rm -f .y/report.txt .y/tasks.md .DS_Store 2>/dev/null || true

echo "OK. Maus-only aktiv:"
echo " - AUTOMATE_ALL.command"
echo " - START_IPRO.command"
echo " - START_TACHELES.command"
echo " - STOP_ALL.command"
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
