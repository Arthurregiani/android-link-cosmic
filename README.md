# Android Link · COSMIC (versão 1.1.0)

Aplicativo local de **uso sob demanda** para Pop!_OS 24.04/COSMIC/Wayland, com interface GTK4. Não é um aplicativo oficial COSMIC e não instala serviços de fundo próprios. Integra ADB Wi-Fi, scrcpy, QR Code e câmera virtual V4L2.

## Pré-requisitos

- Pop!_OS/Ubuntu, sessão gráfica e Python 3 com GTK4 (`python3-gi`, `gir1.2-gtk-4.0`).
- `qrencode` para o QR Code.
- ADB oficial já configurado: `~/Android/platform-tools/adb` (37.0.1 no ambiente original).
- scrcpy 5.0.1 em `~/Downloads/scrcpy-linux-x86_64-v5.0.1/scrcpy` (ou binário compatível configurado).
- Galaxy A54 e PC na mesma rede local, com **Depuração sem fio** ativa no Android.

**Observação:** pode instalar o aplicativo mesmo se tiver movido os executáveis. Nesse caso, configure as variáveis abaixo.

## Instalação no menu COSMIC

### Opção A — pacote `.deb` (recomendada para Pop!_OS)

Baixe o arquivo `android-link-cosmic_1.1.0_all.deb` e, na pasta Downloads, execute:

```bash
sudo apt install ./android-link-cosmic_1.1.0_all.deb
```

Este pacote instala o app em `/usr/share/android-link/`, o comando `/usr/bin/android-link` e o atalho no menu do COSMIC. A instalação pedirá confirmação do APT para dependências de GUI/QR que não estiverem instaladas. Não substitui sua cópia pessoal do ADB nem do scrcpy e não cria serviço systemd. Para remover: `sudo apt remove android-link-cosmic`.

### Opção B — instalação no perfil do usuário, sem pacote `.deb`

Extraia o arquivo `.tar.gz`, abra o terminal na pasta extraída e rode:

```bash
./instalar.sh
```

O instalador utiliza `sudo apt-get install` **somente para dependências GTK/QR ausentes**, instala o aplicativo em `~/.local/share/android-link`, o iniciador em `~/.local/bin/android-link` e o atalho no menu de aplicativos COSMIC. Ele **não instala systemd, não edita firmware, não desativa firewalls, não executa ADB com root** e não altera a configuração existente do Galaxy.

Abra **Android Link** no menu do COSMIC; ou execute `android-link` (opção `.deb`) ou `~/.local/bin/android-link` (opção `.tar.gz`).

## Uso

1. Abra o app. Ele tenta reconectar um único Android previamente pareado detectado pelo mDNS (não adivinha IP/porta).
2. Caso seja a primeira vez, clique **Parear outro Android por QR Code**. No celular: `Opções do desenvolvedor → Depuração sem fio → Parear dispositivo com QR Code`. Aponte o scanner do próprio Android para o código na tela. O código vence em 120 s e desaparece quando a janela é fechada.
3. Se quiser apenas reconectar, clique **Atualizar** e **Conectar**. O pareamento TLS prévio continua válido em condições normais.
4. Selecione câmera traseira/frontal, limite de tamanho e FPS, então use **Abrir câmera**, **Espelhar Android** ou **Usar como webcam virtual**.
5. Veja a **bateria do smartphone** na própria tela: percentual e situação (carregando, descarregando, carga completa). O app consulta o Galaxy selecionado via `adb shell dumpsys battery` ao conectar/selecionar e aproximadamente a cada 30 segundos enquanto a janela estiver aberta. Não salva o histórico de bateria nem instala aplicativo no celular.
6. Use **Parar transmissão** ou feche o aplicativo para encerrar o scrcpy iniciado pelo app. Nenhum serviço extra é instalado.

Se o mesmo celular aparecer simultaneamente como IP TCP/IP e endereço mDNS, o app consolida as duas entradas (desde que o ADB anuncie o mesmo endpoint).

## Webcam virtual — configuração opcional

Primeiro teste **Abrir câmera**. Para expor o vídeo como webcam em OBS, Discord, navegadores etc., é necessário um dispositivo `v4l2loopback` (um driver/módulo do kernel independente do aplicativo):

```bash
sudo apt install v4l2loopback-dkms v4l-utils
sudo modprobe v4l2loopback video_nr=42 card_label='Galaxy Camera' exclusive_caps=1
v4l2-ctl -D -d /dev/video42
```

Depois, clique **Usar como webcam virtual**. O app valida que `/dev/video42` é mesmo do `v4l2loopback` antes de iniciar a transmissão. A webcam virtual é criada pelo módulo; o app **não carrega módulos como root automaticamente**.

### Deixar a webcam pronta após reiniciar, sem terminal a cada uso

**Opcional, com execução explícita como administrador:**

```bash
sudo ./scripts/configurar-webcam.sh
```

O script confirma que o módulo está instalado, verifica conflito em `/dev/video42`, configura somente dois arquivos próprios em `/etc/modprobe.d/` e `/etc/modules-load.d/` e tenta carregar o módulo. Não cria um daemon, não altera EFI nem Secure Boot. Em reinicializações futuras o `systemd-modules-load` tenta carregar `v4l2loopback` com `video_nr=42`, `card_label=Galaxy Camera` e `exclusive_caps=1`. Se o módulo já estava carregado com parâmetros diferentes, os novos parâmetros não entram em vigor até uma recarga segura ou reinicialização.

Para remover **somente essa configuração de carregamento**:

```bash
sudo ./scripts/remover-config-webcam.sh
```

O script de remoção não descarrega o módulo em uso, não remove o pacote DKMS e não desinstala o Android Link.

**Secure Boot:** o Galaxy Camera foi validado pelo usuário com Secure Boot desativado porque o módulo DKMS estava sem assinatura reconhecida. Se reativar o Secure Boot, `v4l2loopback` poderá voltar a falhar com `Key was rejected by service`. Não habilite o Secure Boot de volta assumindo que a simples instalação do script resolve essa exigência: configurar assinatura de módulo/raízes confiáveis exige diagnóstico específico do boot com `systemd-boot` e consentimento explícito para mudanças de confiança.

**Compatibilidade:** o fluxo scrcpy → V4L2 deve ser verificado no Google Meet, Discord e em outros aplicativos. O Meet foi validado pelo usuário na configuração anterior; a versão **1.1.0** ainda requer validação presencial da interface.

**Atenção ao Pop!_OS:** a instalação do `v4l2loopback-dkms` depende dos headers compatíveis com seu kernel customizado. Se o DKMS não compilar, não force a instalação nem descarregue módulos em uso; o espelhamento e a câmera em janela continuarão funcionando sem esse driver.

Se `/dev/video42` estiver ocupado, ou o módulo já estiver ativo com outros parâmetros, não execute `modprobe -r` sem verificar os processos que usam a webcam. Consulte `v4l2-ctl --list-devices` e `lsmod | grep v4l2loopback`.

## Configuração de caminhos customizados

O aplicativo prioriza:

- `ANDROID_LINK_ADB`, senão `~/Android/platform-tools/adb`, senão o `adb` no PATH.
- `ANDROID_LINK_SCRCPY`, senão `~/Downloads/scrcpy-linux-x86_64-v5.0.1/scrcpy`, senão o `scrcpy` no PATH.

Exemplo:

```bash
ANDROID_LINK_ADB="$HOME/Android/platform-tools/adb" \
ANDROID_LINK_SCRCPY="$HOME/Downloads/scrcpy-linux-x86_64-v5.0.1/scrcpy" \
~/.local/bin/android-link
```

Para configurar caminhos permanentes no lançador da opção B, edite `~/.local/bin/android-link` e exporte as variáveis. Na opção A, crie um script usuário que exporte as variáveis e lance `/usr/bin/android-link`, depois ajuste o campo `Exec=` numa cópia do `.desktop` em `~/.local/share/applications/`. **Use scrcpy >= 2.2** para suportar `--video-source=camera`.

## Segurança e ciclo de vida

- O ADB oferece acesso poderoso ao Android; mantenha a depuração sem fio habilitada **somente na rede confiável**, desligue-a quando não estiver usando e revogue dispositivos desconhecidos nas opções de desenvolvedor.
- Cada QR gera um nome e segredo aleatórios, armazenados apenas durante o pareamento e num diretório temporário privado enquanto a janela está aberta.
- Não são usados shell arbitrário, comandos recebidos pela rede, servidores HTTP ou permissões adicionais de acesso remoto.
- O app encerra suas próprias sessões de scrcpy ao fechar. O servidor ADB nativo, compartilhado com outras ferramentas, pode permanecer em segundo plano; ele não é um serviço criado por este aplicativo.
- Logs de execução do scrcpy ficam em `~/.cache/android-link/scrcpy-last.log`. O app não registra o segredo do QR nesses logs.
- A conexão ADB pode cair quando a depuração sem fio é desativada pelo Android, ao mudar de rede ou após reiniciar. A reconexão automática pode ocorrer quando o aplicativo for aberto de novo e o mDNS estiver ativo.

## Diagnóstico

Clique **Diagnóstico** no canto superior direito. Ele informa versão/caminhos de ADB e scrcpy, dispositivos conectados, mDNS e situação da webcam virtual, sem modificar o sistema. Os comandos de diagnóstico podem exibir endereços IP locais.

## Testes de código

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Os testes exercitam parsing de ADB/mDNS, tratamento de duplicatas, QR, argumentos scrcpy e leitura de bateria (incluindo carga, descarga, erros e seleção explícita de dispositivo). **Não substituem teste real com GTK/COSMIC, Galaxy A54 ou o módulo de kernel**.

## Desenvolvimento, build e GitHub

O repositório deve conter o código-fonte (`android_link/`), testes (`tests/`), ícone, scripts, documentação de evolução para Codex (`CODEX_TAREFA.md`) e pipeline de CI (`.github/workflows/ci.yml`). O `.deb` é construído a partir do projeto, não versionado no Git.

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
./packaging/build_deb.sh
```

Para criar **um novo repositório privado** na sua conta GitHub pelo terminal do Pop!_OS, com `gh` instalado e `gh auth login` concluído:

```bash
./scripts/publicar-github.sh android-link-cosmic
```

O script recusa publicar em repositório que já exista ou em um remote configurado, para não sobrescrever código por acidente. Não transfira para GitHub chaves ADB (`~/.android/`), log de telefone, APKs não licenciados ou variáveis de ambiente privadas. A visibilidade inicial recomendada é **privada**; altere-a manualmente se quiser tornar o projeto público.

## Desinstalação

Se usou o `.deb`, rode `sudo apt remove android-link-cosmic`. Se usou o instalador da pasta extraída:

```bash
./desinstalar.sh
```

Somente arquivos instalados pelo app no usuário são removidos. ADB, scrcpy, chaves de pareamento e drivers de terceiros permanecem intactos.

## Referências técnicas

- [scrcpy oficial](https://github.com/Genymobile/scrcpy) — espelhamento, câmera e V4L2.
- [Guia de webcam V4L2 do scrcpy](https://github.com/Genymobile/scrcpy/blob/master/doc/v4l2.md).
- [adb-qr](https://github.com/aleixrodriala/adb-qr) — descrição do formato de QR e pareamento via mDNS.

Este projeto é uma implementação independente, sem associação oficial com Samsung, Android, RustDesk ou System76.
