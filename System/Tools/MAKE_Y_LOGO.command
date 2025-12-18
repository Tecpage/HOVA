#!/bin/bash
set -euo pipefail

ROOT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Y"
cd "$ROOT"

mkdir -p assets

cat > "assets/Y_logo.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <rect width="1024" height="1024" fill="transparent"/>
  <text x="512" y="700"
        text-anchor="middle"
        font-family="Avenir Next, SF Pro Display, Helvetica, Arial, sans-serif"
        font-size="720"
        font-weight="800"
        fill="#d0021b">Y</text>
</svg>
SVG

# Kopie auf Desktop (damit du es sofort siehst)
cp -f "assets/Y_logo.svg" "$HOME/Desktop/Y_logo.svg"

# Öffnen (optional, rein zur Sichtkontrolle)
open "$HOME/Desktop/Y_logo.svg"

echo "Logo erstellt:"
echo " - $ROOT/assets/Y_logo.svg"
echo " - $HOME/Desktop/Y_logo.svg"
read -n 1 -s -r -p "Fenster schließen mit beliebiger Taste…"
