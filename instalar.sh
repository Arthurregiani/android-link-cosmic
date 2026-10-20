#!/usr/bin/env bash
set -euo pipefail

# Install Android Link for the current Linux user; do not touch existing ADB,
# scrcpy, Wi-Fi, systemd services or Android settings.
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/android-link"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"

if ! command -v apt-get >/dev/null; then
  printf '%s\n' 'Este instalador foi feito para Pop!_OS/Ubuntu com APT.' >&2
  exit 1
fi

printf '%s\n' 'Android Link — instalação para usuário atual' \
  'Dependências: python3-gi, gir1.2-gtk-4.0 e qrencode.' \
  'Nenhum serviço será criado; ADB e scrcpy existentes não serão substituídos.'

MISSING=()
dpkg-query -W -f='${Status}' python3-gi 2>/dev/null | grep -q 'install ok installed' || MISSING+=(python3-gi)
dpkg-query -W -f='${Status}' gir1.2-gtk-4.0 2>/dev/null | grep -q 'install ok installed' || MISSING+=(gir1.2-gtk-4.0)
dpkg-query -W -f='${Status}' qrencode 2>/dev/null | grep -q 'install ok installed' || MISSING+=(qrencode)
if ((${#MISSING[@]})); then
  echo "Instalando apenas pacotes ausentes: ${MISSING[*]}"
  sudo apt-get install -y "${MISSING[@]}"
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
cp -R "$SOURCE_DIR/android_link" "$APP_DIR/"
cp "$SOURCE_DIR/README.md" "$APP_DIR/"
install -m 644 "$SOURCE_DIR/assets/android-link.svg" "$ICON_DIR/net.regiani.AndroidLink.svg"
cat > "$BIN_DIR/android-link" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/python3 "${XDG_DATA_HOME:-$HOME/.local/share}/android-link/android_link/app.py" "$@"
EOF
chmod 755 "$BIN_DIR/android-link"

cat > "$DESKTOP_DIR/net.regiani.AndroidLink.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Android Link
Comment=Wi-Fi ADB, scrcpy e câmera do Android no Linux
Exec=$BIN_DIR/android-link
Icon=net.regiani.AndroidLink
Terminal=false
Categories=Utility;Network;
Keywords=Android;ADB;scrcpy;WiFi;Webcam;COSMIC;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_DIR/net.regiani.AndroidLink.desktop"
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

if [[ -x "$HOME/Android/platform-tools/adb" ]]; then
  echo "ADB oficial encontrado: $HOME/Android/platform-tools/adb"
else
  echo "AVISO: ADB oficial não encontrado no caminho esperado. O aplicativo tentará o adb do PATH."
fi
if [[ -x "$HOME/Downloads/scrcpy-linux-x86_64-v5.0.1/scrcpy" ]]; then
  echo "scrcpy 5.0.1 encontrado na pasta Downloads."
else
  echo "AVISO: scrcpy 5.0.1 não encontrado. Consulte README.md para configurar o caminho."
fi
printf '\n%s\n' 'Instalação concluída.' \
  'Abra "Android Link" pelo menu do COSMIC, ou execute:' \
  "  $BIN_DIR/android-link" \
  'O modo webcam virtual é opcional e requer o módulo v4l2loopback.'
