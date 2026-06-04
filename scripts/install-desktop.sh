#!/usr/bin/env bash
# Install a desktop launcher for Hammurabi into the user's applications menu.
# The launcher runs the project in place (it does not bundle/copy anything), so
# the repo and its .venv must stay where they are.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPS="$HOME/.local/share/applications"
DESKTOP="$APPS/hammurabi.desktop"

if [ ! -x "$HERE/.venv/bin/python" ]; then
    echo "error: $HERE/.venv not found. Create it first (python3 -m venv .venv)." >&2
    exit 1
fi

# Ensure the icon exists.
if [ ! -f "$HERE/assets/hammurabi.png" ]; then
    "$HERE/.venv/bin/python" "$HERE/scripts/make_icon.py"
fi

mkdir -p "$APPS"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Hammurabi
Comment=Agent-based society simulator
Exec=$HERE/scripts/hammurabi
Icon=$HERE/assets/hammurabi.png
Terminal=false
Categories=Education;Science;Simulation;
EOF

chmod +x "$DESKTOP"
update-desktop-database "$APPS" 2>/dev/null || true
echo "installed $DESKTOP"
echo "Hammurabi should now appear in your applications menu."
