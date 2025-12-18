#!/bin/bash
set -euo pipefail

ROOT="/Users/ericschone/Library/Mobile Documents/com~apple~CloudDocs/Y"
cd "$ROOT"

echo "== 1) Launcher Wrapper =="

mkdir -p "$ROOT/Launcher"

cat > "$ROOT/Launcher/Start_Y_Launcher.command" <<'CMD'
#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
INNER="$ROOT/Launcher/start_launcher.command"
PORT="${1:-8090}"

chmod +x "$INNER" 2>/dev/null || true
exec "$INNER" "$PORT"
CMD

chmod +x "$ROOT/Launcher/Start_Y_Launcher.command"

echo "== 2) y CLI (symlink-robust) =="

mkdir -p "$ROOT/cli"

cat > "$ROOT/cli/y" <<'YCLI'
#!/bin/bash
set -euo pipefail

# Resolve symlink of this script (macOS)
SCRIPT="$0"
if [ -L "$SCRIPT" ]; then
  TARGET="$(readlink "$SCRIPT")"
  case "$TARGET" in
    /*) SCRIPT="$TARGET" ;;
    *)  SCRIPT="$(cd "$(dirname "$SCRIPT")" && pwd)/$TARGET" ;;
  esac
fi

ROOT="$(cd "$(dirname "$SCRIPT")/.." && pwd)"

cmd="${1:-help}"
shift || true

case "$cmd" in
  help)
    cat <<'HLP'
y — Projekt Y CLI

Discovery:
  y scan
  y files
  y status
  y diff

Git flow:
  y branch <name>
  y baseline-commit "<msg>"

HLP
    ;;

  scan)
    echo "ROOT: $ROOT"
    echo
    echo "Top-level:"
    ls -la "$ROOT"
    echo
    echo "YAML:"
    find "$ROOT" -type f \( -iname "*.yaml" -o -iname "*.yml" \) | sed "s|^$ROOT/||"
    ;;

  files)
    find "$ROOT" -type f \( -iname "*.yaml" -o -iname "*.yml" \) | sed "s|^$ROOT/||"
    ;;

  status)
    (cd "$ROOT" && git status -sb)
    ;;

  diff)
    (cd "$ROOT" && git diff)
    ;;

  branch)
    name="${1:-}"
    if [ -z "$name" ]; then
      echo "Usage: y branch <name>"
      exit 1
    fi
    (cd "$ROOT" && git checkout -b "$name" 2>/dev/null || git checkout "$name")
    ;;

  baseline-commit)
    msg="${1:-Bootstrap: initial content}"
    (cd "$ROOT" && git add -A && git commit -m "$msg")
    ;;

  *)
    echo "Unknown command: $cmd"
    exit 1
    ;;
esac
YCLI

chmod +x "$ROOT/cli/y"

echo "== 3) Hook scaffold (.y/hooks.sh) =="

mkdir -p "$ROOT/.y"

cat > "$ROOT/.y/hooks.sh" <<'HOOK'
#!/bin/bash
set -euo pipefail

# Implement your deterministic generator here.
# y gen will call y_gen <repo_root>

y_gen() {
  local root="$1"

  # Best-effort autodetect:
  if [ -x "$root/DocuGenerator/generate.sh" ]; then
    "$root/DocuGenerator/generate.sh"
    return 0
  fi
  if [ -f "$root/DocuGenerator/generate.py" ]; then
    python3 "$root/DocuGenerator/generate.py"
    return 0
  fi

  echo "y gen: Kein Generator gefunden. Ergänze DocuGenerator/generate.(sh|py) oder implementiere y_gen in .y/hooks.sh."
  return 0
}
HOOK

chmod +x "$ROOT/.y/hooks.sh"

echo "== 4) .gitignore ergänzen (DS_Store, *.bak-*) =="

touch "$ROOT/.gitignore"

# Append only if missing
grep -q '^\.\DS_Store$' "$ROOT/.gitignore" 2>/dev/null || printf "\n# macOS\n.DS_Store\n" >> "$ROOT/.gitignore"
grep -q '^\*\.bak-\*$' "$ROOT/.gitignore" 2>/dev/null || printf "\n# Backups\n*.bak-*\n" >> "$ROOT/.gitignore"

echo "== 5) Symlink y in /usr/local/bin =="

sudo mkdir -p /usr/local/bin
sudo chown -R "$(whoami)":staff /usr/local/bin
ln -sf "$ROOT/cli/y" /usr/local/bin/y

echo "== 6) Optional: Backup-Dateien entfernen =="
if ls "$ROOT"/IPRO/*.bak-* >/dev/null 2>&1; then
  rm -f "$ROOT"/IPRO/*.bak-*
  echo "Backups entfernt: IPRO/*.bak-*"
else
  echo "Keine IPRO/*.bak-* vorhanden."
fi

echo "== 7) Branch agent/bootstrap anlegen/wechseln =="

cd "$ROOT"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Kein Git-Repo gefunden in $ROOT"; exit 1; }
git checkout -b agent/bootstrap 2>/dev/null || git checkout agent/bootstrap

echo "== 8) Status =="

y scan
y status

echo
echo "Fertig. Optionaler Baseline-Commit:"
echo "  y baseline-commit \"Bootstrap: Projektstruktur + YAML + Launcher + CLI\""
