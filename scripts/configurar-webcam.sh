#!/usr/bin/env bash
set -euo pipefail

# Optional, explicit system-level setup. Nothing here modifies Secure Boot or EFI.
if (( EUID != 0 )); then
  echo "Execute explicitamente com: sudo ./scripts/configurar-webcam.sh" >&2
  exit 1
fi
if ! modinfo -n v4l2loopback >/dev/null 2>&1; then
  echo "v4l2loopback não está instalado para o kernel atual: $(uname -r)" >&2
  echo "Instale v4l2loopback-dkms e os headers compatíveis primeiro." >&2
  exit 1
fi
if [[ -e /dev/video42 ]]; then
  if ! command -v v4l2-ctl >/dev/null 2>&1; then
    echo "Instale v4l-utils para verificar /dev/video42 antes de prosseguir." >&2
    exit 1
  fi
  if ! v4l2-ctl -D -d /dev/video42 2>/dev/null | grep -Eiq 'v4l2.?loopback'; then
    echo "ERRO: /dev/video42 já pertence a outro dispositivo. Não será alterado." >&2
    exit 1
  fi
fi

MODPROBE_CONF=/etc/modprobe.d/android-link-camera.conf
MODULES_CONF=/etc/modules-load.d/android-link-camera.conf
EXPECTED_MOD='options v4l2loopback video_nr=42 card_label="Galaxy Camera" exclusive_caps=1'
EXPECTED_LOAD='v4l2loopback'

for file in "$MODPROBE_CONF" "$MODULES_CONF"; do
  if [[ -e "$file" ]]; then
    case "$file" in
      "$MODPROBE_CONF") expected="$EXPECTED_MOD" ;;
      *) expected="$EXPECTED_LOAD" ;;
    esac
    if [[ $(cat "$file") != "$expected" ]]; then
      echo "ERRO: $file já existe e contém uma configuração diferente. Não sobrescreveremos." >&2
      exit 1
    fi
  fi
done

printf '%s\n' "$EXPECTED_MOD" > "$MODPROBE_CONF"
printf '%s\n' "$EXPECTED_LOAD" > "$MODULES_CONF"
chmod 0644 "$MODPROBE_CONF" "$MODULES_CONF"

echo "Configuração de carregamento no boot instalada."
if [[ ! -e /sys/module/v4l2loopback ]]; then
  if ! modprobe v4l2loopback; then
    echo "O módulo foi configurado, mas não pôde ser carregado agora." >&2
    echo "Verifique Secure Boot, assinatura do módulo e DKMS. Para reverter:" >&2
    echo "  sudo ./scripts/remover-config-webcam.sh" >&2
    exit 1
  fi
else
  echo "O módulo já estava carregado. Os parâmetros novos serão usados na próxima carga/reinicialização."
fi

echo "Sem daemon do Android Link; não foram alteradas chaves UEFI, bootloader ou Secure Boot."
if [[ -e /dev/video42 ]]; then
  echo "Dispositivo atual: /dev/video42"
else
  echo "ATENÇÃO: /dev/video42 não apareceu. Verifique opções de módulo e configurações existentes."
fi
