#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

touch .gitignore
grep -q "^\.y/$" .gitignore || echo ".y/" >> .gitignore
grep -q "^\.DS_Store$" .gitignore || { echo ""; echo "# macOS"; echo ".DS_Store"; } >> .gitignore
grep -q "^\*\.bak-\*$" .gitignore || { echo ""; echo "# Backups"; echo "*.bak-*"; } >> .gitignore

git rm -r --cached .y >/dev/null 2>&1 || true

if ! git diff --quiet || ! git diff --cached --quiet; then
  git add -A
  git commit -m "chore: ignore .y artifacts and clean working tree" || true
fi

echo "Git-Minimalismus: fertig."
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
