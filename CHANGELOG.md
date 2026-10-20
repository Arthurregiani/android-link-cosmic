# Histórico de versões

## 1.1.0 — 2026-10-19

- Corrigida permissão DEBIAN do build sob umask restritiva; CI constrói e disponibiliza o pacote.
- Segredo QR/ADB enviado por stdin, fora da lista de argumentos; erros de pareamento não expõem a resposta contendo segredo.
- Seleção preservada quando o celular desaparece, evitando consultar outro automaticamente.
- Reconexão do dispositivo selecionado descoberto via mDNS a cada 30 segundos enquanto aberto.
- Logs scrcpy privados (0600), erros de bateria visíveis e espera pelo encerramento do scrcpy ao sair.

- Indicador de percentual de bateria e status de carga do dispositivo Android selecionado.
- Leitura de bateria via ADB sem aplicativo extra, com atualização em até 30 segundos durante o uso e tratamento de desconexões.
- Scripts opcionais e reversíveis para carregar o módulo v4l2loopback no boot, preservando Secure Boot e sem daemon próprio.
- Script de build do pacote `.deb`, script de publicação de repositório GitHub privado e testes adicionais.
- Mantidos: QR Code de pareamento, mDNS, deduplicação de conexões, câmera frontal/traseira, espelhamento e saída V4L2.

## 1.0.0 — 2026-10-19

- Primeira versão com GUI GTK4/COSMIC, ADB Wi-Fi, scrcpy, QR Code e suporte à webcam virtual.
