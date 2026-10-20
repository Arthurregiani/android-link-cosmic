#!/usr/bin/env bash
set -euo pipefail
if (( EUID != 0 )); then
  echo "Execute com: sudo ./scripts/remover-config-webcam.sh" >&2
  exit 1
fi
for file in /etc/modprobe.d/android-link-camera.conf /etc/modules-load.d/android-link-camera.conf; do
  if [[ -f "$file" ]]; then
    case "$file" in
      /etc/modprobe.d/*) expected='options v4l2loopback video_nr=42 card_label="Galaxy Camera" exclusive_caps=1' ;;
      *) expected='v4l2loopback' ;;
    esac
    if [[ $(cat "$file") == "$expected" ]]; then
      rm -- "$file"
      echo "Removido: $file"
    else
      echo "Preservado (conteúdo modificado): $file"
    fi
  fi
done
printf '%s\n' 'O módulo já carregado não será descarregado: isso pode interromper aplicativos em uso.'
