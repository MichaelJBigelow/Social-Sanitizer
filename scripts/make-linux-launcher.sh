#!/bin/bash
# Adds Social Sanitizer to the Linux app menu, plus a launcher in this repository folder.
#
#   scripts/make-linux-launcher.sh
#
# Writes a freedesktop .desktop entry (GNOME, KDE, Xfce, …) with Terminal=false, so it
# starts with no terminal window. Re-run this script if you move the repository.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python"
ICON="$REPO/src/social_sanitizer/assets/icon.png"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
MENU_ENTRY="$APPS_DIR/social-sanitizer.desktop"  # name must match the app's desktopFileName
LOCAL_ENTRY="$REPO/Social Sanitizer.desktop"

if [[ ! -x "$PY" ]]; then
  echo "No virtualenv at $REPO/.venv. Set it up first (see README), then re-run." >&2
  exit 1
fi

# Desktop-entry Exec lines need double escaping for " ` $ \ — rather than risk getting
# that wrong, refuse those rare characters. Spaces are fine.
case "$REPO" in
  *[\"\`\$\\]*)
    echo "The repository path contains \" \` \$ or \\, which .desktop launchers can't use reliably." >&2
    echo "Move the repository to a simpler path and re-run." >&2
    exit 1
    ;;
esac
exec_quote() { printf '"%s"' "$1"; }

write_entry() {
  cat > "$1" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Social Sanitizer
Comment=Find and report creepy comments on Instagram posts
Exec=$(exec_quote "$PY") -m social_sanitizer
Path=$REPO
Icon=$ICON
Terminal=false
Categories=Network;
StartupWMClass=Social Sanitizer
EOF
  chmod +x "$1"
}

mkdir -p "$APPS_DIR"
write_entry "$MENU_ENTRY"
write_entry "$LOCAL_ENTRY"

# GNOME won't run a .desktop file from a folder until it's marked trusted.
if command -v gio >/dev/null 2>&1; then
  gio set "$LOCAL_ENTRY" metadata::trusted true 2>/dev/null || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

echo "Added to the app menu: $MENU_ENTRY"
echo "Created $LOCAL_ENTRY"
