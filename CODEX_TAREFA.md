# Tarefa para Codex: Android Link COSMIC — estabilizar, validar e publicar

## Resultado esperado

Transformar o código-fonte desta pasta em uma aplicação confiável no Pop!_OS 24.04/COSMIC/Wayland. Validar no **desktop real** o indicador de bateria, conexão Wi-Fi e webcam virtual do Samsung Galaxy A54. Criar um novo repositório **privado** no GitHub (`Arthurregiani/android-link-cosmic`), usando a autenticação do usuário, e publicar o projeto completo após checagem de segurança.

## Estado da base recebida

- Versão 1.1.0 baseada no Android Link 1.0.0 original recuperado da conversa.
- Interface GTK4 usando Python 3, sem serviços `systemd` do aplicativo.
- ADB Wi-Fi 37.0.1: `~/Android/platform-tools/adb`.
- scrcpy 5.0.1: `~/Downloads/scrcpy-linux-x86_64-v5.0.1/scrcpy`.
- Samsung Galaxy A54 / modelo `SM_A546E`; mDNS funcionando, já pareado na rede Wi-Fi doméstica.
- `v4l2loopback` versão 0.15.3 instalado via DKMS, kernel `7.2.6-76070206-generic` no último diagnóstico.
- `/dev/video42`, rótulo `Galaxy Camera`, `exclusive_caps=1`: funcionou no Google Meet com o Secure Boot desligado.
- Antes, com Secure Boot ligado e assinatura do módulo ausente, `modprobe` retornou `Key was rejected by service`.
- O módulo não deve ser desativado ou descarregado se outra aplicação estiver usando a câmera.
- O código adiciona: bateria percentual via `adb -s SERIAL shell dumpsys battery`, estado de carga e atualização sem bloquear a interface.
- Testes unitários em `tests/`, build em `packaging/build_deb.sh`, configuração opcional em `scripts/configurar-webcam.sh`.

## Execução (siga esta ordem)

1. Leia `README.md`, `android_link/core.py`, `android_link/app.py`, `scripts/` e a CI. Verifique o estado do Git e as ferramentas do computador. Não sobrescreva configurações ou projeto existente sem inspecionar.
2. Rode `PYTHONPATH=. python3 -m unittest discover -s tests -v` e `./packaging/build_deb.sh`.
3. Teste o aplicativo numa sessão COSMIC real. Confirme descoberta e seleção do Galaxy A54, sem duplicar o dispositivo por endereço mDNS/TCP.
4. Verifique se a GUI exibe bateria em porcentagem e `Carregando`/`Descarregando`/`Carga completa`. Teste desconexão e retorno. Confirme que o polling só ocorre com o app aberto e que não há consultas a outros celulares conectados.
5. Confirme funcionamento de espelhamento e câmera. Teste iniciar/parar a webcam virtual `/dev/video42` a partir do app com o Android conectado por Wi-Fi. Com o Meet e o Discord, valide recepção de vídeo e ausência de processos scrcpy órfãos. Se uma aplicação depender de permissão V4L2/Flatpak, documente a correção mais restrita possível.
6. Avalie se `scripts/configurar-webcam.sh` é adequado ao ambiente real. Ele só deve ser executado com aprovação para modificar `/etc/`; se o usuário já usa `/dev/video42`, não altere nem descarregue o módulo em uso.
7. Melhore observabilidade e tratamento de erros. Preserve ADB e scrcpy instalados e não crie serviço permanente sem necessidade.
8. Revise `.gitignore`, retire arquivos pessoais, credenciais, tokens e logs. Peça autenticação GitHub caso não exista; crie repositório **privado** usando `gh repo create ...` ou o script fornecido. Não use conta de organização OptikAI, salvo pedido explícito. Faça commit e push do código-fonte; se o repositório já existir, interrompa e solicite orientação antes de sobrescrever.
9. Valide `git status`, conteúdo remoto do repositório, execução do CI e a instalação pelo `.deb` novo. Registre o que foi realmente testado versus o que ainda é pendente.

## Requisitos funcionais

- QR Code apenas quando necessário para novo pareamento; não reautenticar toda vez.
- Detecção/reconexão pelo ADB mDNS, sem depender de IP ou porta fixa.
- Indicador de percentual de bateria do smartphone e informação de carregamento; estado indisponível ao desconectar.
- Webcam frontal ou traseira, resolução e FPS ajustáveis, saída nomeada `Galaxy Camera` para navegadores, Google Meet e Discord.
- Botões para iniciar e parar sem terminal, acesso pela lista de apps do COSMIC.
- A aplicação não deve capturar, armazenar ou divulgar as chaves de emparelhamento do Android.

## Restrições

- Não reativar nem desativar Secure Boot automaticamente.
- Não inscrever chaves MOK/UEFI e não modificar partições EFI, bootloader ou firmware.
- Não forçar `rmmod` de módulo em uso, não sobrescrever `/dev/video42` se não for `v4l2loopback`.
- Não criar um daemon continuamente ativo.
- Mudanças sob sudo apenas com autorização e reversão documentada.
- Não afirmar que o Discord ou o aplicativo versão 1.1.0 foram testados no dispositivo se não houver teste real.

## Entrega final

- URL válida do repositório GitHub privado e commit final.
- Arquivo do projeto atualizado e `.deb` testado.
- Resultados de testes unitários e manuais, falhas, restrições e plano de reversão.
- Instruções de uso sem terminal após a instalação.
