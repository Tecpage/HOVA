#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== Projekt Y: Vollautomatik =="

echo "1) Symlinks (Root → IPRO)"
[ -f "IPRO/tenants.yaml" ]  && ln -sf "IPRO/tenants.yaml"  "tenants.yaml"
[ -f "IPRO/payments.yaml" ] && ln -sf "IPRO/payments.yaml" "payments.yaml"

echo "2) .y/ aus Git ausschließen"
touch .gitignore
grep -q '^\.y/$' .gitignore || echo ".y/" >> .gitignore

echo "3) Generator laufen lassen (y gen)"
command -v y >/dev/null 2>&1 && y gen || true

echo "4) Report erzeugen"
command -v y >/dev/null 2>&1 && y report || true

echo
echo "== Fertig =="
echo "Report: .y/report.txt"
echo "Browser kann jetzt genutzt werden."
echo
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
