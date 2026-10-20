#!/usr/bin/env bash
set -euo pipefail
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
# Only remove files created by the user-level installer.
rm -f "$HOME/.local/bin/android-link"
rm -f "$DATA_HOME/applications/net.regiani.AndroidLink.desktop"
rm -f "$DATA_HOME/icons/hicolor/scalable/apps/net.regiani.AndroidLink.svg"
rm -rf "$DATA_HOME/android-link"
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$DATA_HOME/applications" 2>/dev/null || true
fi
echo 'Android Link removido. ADB, scrcpy, dados de pareamento e módulos do kernel foram preservados.'
