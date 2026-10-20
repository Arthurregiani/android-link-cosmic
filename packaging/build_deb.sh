#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="$(sed -n 's/^VERSION = "\([0-9.]*\)"$/\1/p' android_link/app.py)"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Versão inválida em app.py' >&2; exit 1; }
DEST="${1:-$ROOT/dist}"
mkdir -p "$DEST"
DEST="$(cd -- "$DEST" && pwd)"
PKG="$(mktemp -d)"
trap 'rm -rf -- "$PKG"' EXIT
mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/share/android-link/android_link" \
  "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/scalable/apps" \
  "$PKG/usr/share/doc/android-link-cosmic"
install -m 644 android_link/*.py "$PKG/usr/share/android-link/android_link/"
install -m 644 assets/android-link.svg "$PKG/usr/share/icons/hicolor/scalable/apps/net.regiani.AndroidLink.svg"
install -m 644 README.md "$PKG/usr/share/doc/android-link-cosmic/README.md"
install -m 644 CHANGELOG.md "$PKG/usr/share/doc/android-link-cosmic/changelog.md"
cat > "$PKG/usr/bin/android-link" <<'SCRIPT'
#!/bin/sh
exec /usr/bin/python3 /usr/share/android-link/android_link/app.py "$@"
SCRIPT
chmod 755 "$PKG/usr/bin/android-link"
cat > "$PKG/usr/share/applications/net.regiani.AndroidLink.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Android Link
Comment=Android Wi-Fi, bateria e webcam para COSMIC
Exec=android-link
Icon=net.regiani.AndroidLink
Terminal=false
Categories=Utility;Network;
Keywords=Android;ADB;scrcpy;WiFi;Webcam;COSMIC;Battery;
StartupNotify=true
DESKTOP
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: android-link-cosmic
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: Android Link Contributors <noreply@localhost.invalid>
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0, qrencode
Description: Android wireless webcam and battery manager for COSMIC Linux
 GTK4 application for wireless ADB, QR pairing, scrcpy and virtual V4L2 webcam.
 Includes on-demand battery readings, with no permanent background service.
CONTROL
# Package permissions must not depend on the caller's umask (often 0077).
find "$PKG" -type d -exec chmod 0755 {} +
find "$PKG" -type f -exec chmod 0644 {} +
chmod 0755 "$PKG/usr/bin/android-link"
dpkg-deb --build --root-owner-group "$PKG" "$DEST/android-link-cosmic_${VERSION}_all.deb"
