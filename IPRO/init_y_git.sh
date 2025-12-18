#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
TARGET="IPRO/operating_costs.yaml"
GITIGNORE=".gitignore"

echo "[Y] Root: ${ROOT}"

# 1) Git init (falls nötig)
if [ ! -d ".git" ]; then
  echo "[Y] Kein .git gefunden → initialisiere Repository…"
  git init
else
  echo "[Y] Git Repo vorhanden."
fi

# 2) .gitignore (idempotent)
ensure_gitignore_block() {
  local marker_begin="# --- Project Y defaults (managed) BEGIN ---"
  local marker_end="# --- Project Y defaults (managed) END ---"

  if [ ! -f "${GITIGNORE}" ]; then
    echo "[Y] .gitignore fehlt → lege an."
    touch "${GITIGNORE}"
  fi

  if ! grep -qF "${marker_begin}" "${GITIGNORE}"; then
    echo "[Y] Ergänze Standard-.gitignore-Block."
    cat >> "${GITIGNORE}" <<'EOF'

# --- Project Y defaults (managed) BEGIN ---
# macOS / Finder
.DS_Store

# iCloud placeholders
*.icloud

# IPRO Dashboard generated artefacts (deterministic build outputs)
IPRO/dashboard/data/*.json
IPRO/dashboard/index.html
IPRO/dashboard/app.js
IPRO/dashboard/*.map
IPRO/dashboard/data/server.pid

# Logs
*.log
# --- Project Y defaults (managed) END ---
EOF
  else
    echo "[Y] .gitignore-Block bereits vorhanden (ok)."
  fi
}

ensure_gitignore_block

# 3) Sicherstellen, dass Ziel-Datei existiert
if [ ! -f "${TARGET}" ]; then
  echo "[Y] FEHLER: ${TARGET} nicht gefunden. Bitte Pfad prüfen."
  exit 2
fi

# 4) Commit .gitignore (nur wenn neu/dirty)
if ! git diff --quiet -- "${GITIGNORE}" 2>/dev/null; then
  echo "[Y] Committe .gitignore…"
  git add "${GITIGNORE}"
  git commit -m "chore: add gitignore for Project Y"
else
  # Falls .gitignore neu ist, aber diff quiet (z.B. noch untracked): prüfen
  if git ls-files --error-unmatch "${GITIGNORE}" >/dev/null 2>&1; then
    echo "[Y] .gitignore unverändert (ok)."
  else
    echo "[Y] .gitignore ist untracked → committe…"
    git add "${GITIGNORE}"
    git commit -m "chore: add gitignore for Project Y"
  fi
fi

# 5) Commit operating_costs.yaml (nur wenn untracked/changed)
if git ls-files --error-unmatch "${TARGET}" >/dev/null 2>&1; then
  if git diff --quiet -- "${TARGET}"; then
    echo "[Y] ${TARGET} ist bereits getrackt und unverändert (kein Commit nötig)."
  else
    echo "[Y] Committe Änderungen an ${TARGET}…"
    git add "${TARGET}"
    git commit -m "feat(ipro-bk): add operating_costs SSOT skeleton (period 01.02–31.01)"
  fi
else
  echo "[Y] ${TARGET} ist untracked → committe…"
  git add "${TARGET}"
  git commit -m "feat(ipro-bk): add operating_costs SSOT skeleton (period 01.02–31.01)"
fi

echo "[Y] Fertig. Letzte Commits:"
git --no-pager log --oneline -5