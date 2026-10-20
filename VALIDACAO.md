# Validação — 19/10/2026, Pop!_OS/COSMIC

## Ambiente e evidências

- Sessão real COSMIC/Wayland, kernel 7.2.6-76070206-generic; GTK4 disponível.
- ADB 37.0.1 e scrcpy 5.0.1 existentes foram preservados.
- Samsung Galaxy A54 SM_A546E, Android 16, conectado por transporte ADB TLS/mDNS.
- `/dev/video42`: driver `v4l2 loopback`, rótulo `Galaxy Camera`, exclusive_caps ativo. Não foi descarregado nem reconfigurado.
- GUI real exibiu 74% · Descarregando e depois 74% · Carregando após conectar o carregador. Dados lidos do aparelho, sem simular o estado Android.
- Espelhamento, câmera traseira e webcam frontal iniciados pela implementação da GUI real, através de um harness local que chamou os mesmos handlers dos botões. Não equivale a inspeção visual humana dos vídeos.
- Webcam frontal configurada em até 1280 px/30 FPS; consumidor `v4l2-ctl` recebeu cinco quadros, sem salvá-los. Nenhum dos três processos scrcpy do teste permaneceu ativo após parar.
- Pacote 1.1.0 instalado sobre 1.0.0 via autenticação gráfica autorizada. Fonte instalado comparado byte a byte; permissões do lançador corrigidas para 0644, executável 0755.
- 23 testes descobertos: 22 passaram, um teste GTK ignorado por padrão. O teste GTK também passou separadamente na sessão real, com dispositivos simulados, cobrindo perda/retorno de seleção, ausência de consulta ao outro celular e interrupção do polling após fechar.
- Build passa sob umask 0077; teste de regressão verifica permissões de todos os arquivos e diretórios do pacote. Sintaxe dos scripts e compilação Python verificadas.

## Limites e testes em andamento

- Desligar a depuração sem fio fez a GUI mostrar “Indisponível · desconectado”; ao religar, retornou a 75% · Carregando, sem QR. Confirmado no log da GUI e pelo usuário; o ADB voltou a anunciar o serviço mDNS.
- Carga completa: parsing coberto por teste, sem validação física a 100%.
- Duas entradas simultâneas TCP/mDNS: deduplicação coberta por teste; nesta sessão apareceu apenas um transporte real.
- Pareamento QR novo não executado: o pareamento existente foi preservado. Segredos QR/ADB passam por stdin e não integram os argumentos dos processos.
- Google Meet: prévia real validada pelo agente no navegador interno do Codex, câmera Galaxy Camera, vídeo 1280×720, readyState=4 e tempo de reprodução avançando; imagem do telefone inspecionada. Não houve participação em chamada. Evidência visual fica somente em `.local-validation/meet-preview.png` e não é publicada.
- Houve falha inicial de enumeração no navegador informado pelo usuário e prévia indisponível no teste do agente. Uma ponte GStreamer/PipeWire temporária fez o dispositivo aparecer, mas isso por si só não comprovou vídeo. Depois de encerrar a ponte e recarregar a prévia do Meet, o vídeo V4L2 direto funcionou. Os primeiros quadros estavam quase pretos (luminância média 17,4/255); após reposicionar o telefone foi possível inspecionar imagem real. Não atribuir toda a falha inicial a uma única causa confirmada.
- O teste PipeWire também recebeu cinco quadros em um consumidor GStreamer com formato explícito. A ponte foi encerrada, não integrada como processo permanente e não é requisito para o fluxo Meet validado.
- Discord: interface/recepção de vídeo não testada; o usuário limitou a disponibilidade ao Meet. O acesso ao dispositivo foi confirmado dentro do sandbox Flatpak existente, o que não substitui teste do Discord.
- Navegador Firefox/Zen do usuário: validação visual final não executada pelo agente, pois essa janela não está disponível na automação. A prova de Meet corresponde ao navegador interno do Codex.
- Discord Flatpak já possui `devices=all`; um processo de inspeção no sandbox confirmou acesso de leitura/escrita a `/dev/video42`, e nenhuma permissão foi ampliada. Não aplicar `--filesystem=host` ou outras permissões amplas para tentar resolver câmera.
- `scripts/configurar-webcam.sh` não executado. O dispositivo já está pronto; não há necessidade de modificar `/etc/`. O script preserva arquivos diferentes, valida o driver e não descarrega módulo. Antes de uso futuro, conferir também opções existentes de outros arquivos modprobe para evitar conflito.
- Nenhuma mudança de Secure Boot, MOK, UEFI, EFI, bootloader ou firmware.

## Segurança e publicação

- Publicação pública no repositório existente autorizada expressamente pelo usuário, substituindo o pedido inicial de repositório privado.
- Não publicar `.local-validation/`, logs, capturas, dados reais de ADB, chaves de pareamento ou pacote de reversão.
- `.gitignore` exclui chaves, ambientes, logs, binários, arquivos compactados e evidências locais. Testes usam dados sintéticos de documentação (192.0.2.0/24).
- O programa usa os dados de pareamento mantidos pelo ADB; não copia nem publica `~/.android/`.

## Reversão

- Uma cópia reinstalável dos arquivos e metadados da versão 1.0.0 anterior foi preservada localmente em `.local-validation/android-link-cosmic_1.0.0_rollback.deb` (não publicada).
- Para retornar: `sudo dpkg -i .local-validation/android-link-cosmic_1.0.0_rollback.deb`, executado na raiz do projeto. A reversão foi preparada, mas não executada.
- Para remover o app: `sudo apt remove android-link-cosmic`. ADB, scrcpy, pareamento e v4l2loopback ficam preservados.
- Nenhum arquivo de `/etc/` foi alterado por esta tarefa.

## Uso após a instalação, sem terminal

1. PC e telefone na mesma rede; habilite Depuração sem fio no Android.
2. Abra **Android Link** na lista de aplicativos do COSMIC.
3. Confirme o Galaxy selecionado e a bateria; use **Atualizar/Conectar** se necessário. QR apenas para pareamento perdido ou novo aparelho.
4. Escolha frontal/traseira, resolução e FPS; clique **Usar como webcam virtual**.
5. No Meet ou Discord, selecione **Galaxy Camera** e confira a prévia antes de participar de chamada.
6. Use **Parar transmissão** ou feche o Android Link ao terminar.

## Quando a câmera não aparece no navegador

- Inicie **Usar como webcam virtual** antes de abrir a seleção de câmera. Com `exclusive_caps=1`, o loopback anuncia saída antes de receber scrcpy e captura enquanto transmite.
- Recarregue a aba do Meet, reabra a seleção e escolha **Galaxy Camera**. Confira a permissão de câmera do site. Uma prévia escura também pode ser a lente traseira coberta pelo apoio do telefone.
- Nesta sessão o PipeWire tinha um dispositivo Galaxy Camera com capacidades antigas de saída, sem fonte de vídeo. Isso é compatível com o [problema documentado pela Mozilla](https://bugzilla.mozilla.org/show_bug.cgi?id=1946916), mas não prova que todos os navegadores usem esse caminho.
- Para Firefox/Zen que use o backend de câmera PipeWire e continue sem enumerar a webcam, uma alternativa reversível é testar `media.webrtc.camera.allow-pipewire=false` em `about:config`, passando a captura de câmera para V4L2. Anote o valor anterior e restaure-o para reverter. Esta preferência não foi alterada automaticamente nem validada no perfil do usuário.
- Não reinicie PipeWire/WirePlumber nem amplie permissões globais apenas para tentar resolver enumeração. Essas ações não foram necessárias para a prévia Meet validada.

## Publicação e CI

- Repositório público autorizado: https://github.com/Arthurregiani/android-link-cosmic.
- Commit de implementação `44c469687eeaa862cc71289ea9769de87d736131`; CI passou em https://github.com/Arthurregiani/android-link-cosmic/actions/runs/39358929049.
- A revisão final de documentação complementa os resultados de testes no navegador, sem alterar os binários instalados.
