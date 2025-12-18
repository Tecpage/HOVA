#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Commit nur auf Branch (Sicherheit)
BR="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BR" = "main" ] || [ "$BR" = "master" ]; then echo "Refuse: nicht auf $BR"; exit 1; fi

git add -A
git commit -m "chore: maus-only automation scripts + symlinks + cleanup"

echo "Commit fertig. Repo sollte jetzt clean sein."
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
