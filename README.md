# Android Link

![CI](https://github.com/Arthurregiani/android-link-cosmic/actions/workflows/ci.yml/badge.svg)

Aplicativo desktop para integrar um **Android ao Linux pela rede Wi-Fi**: conexão ADB, pareamento por QR Code, espelhamento de tela, transmissão das câmeras, **webcam virtual** e monitoramento de bateria — tudo por uma interface GTK4.

Desenvolvido para **Pop!_OS 24.04 com COSMIC/Wayland**. Não é um componente oficial do COSMIC, do Android ou da Samsung.

**Versão atual:** 1.1.0 · **Idioma da interface:** português · **Funcionamento:** sob demanda, sem daemon próprio permanente.

## Funcionalidades

| Recurso | Como funciona |
| --- | --- |
| Descoberta e conexão Wi-Fi | Localiza dispositivos pareados pelo ADB/mDNS e tenta reconectar quando necessário; consolida transportes TCP e mDNS duplicados. |
| Pareamento por QR Code | Gera um QR na interface para o recurso **Depuração sem fio** do Android; dispensa Android Studio e cabo USB. |
| Bateria | Exibe percentual e estado de carga do dispositivo selecionado, com atualização aproximada a cada 30 s enquanto o aplicativo está aberto. |
| Espelhamento | Abre a tela do Android no computador utilizando o scrcpy. |
| Câmera do celular | Transmite a câmera frontal ou traseira em uma janela, com controles de resolução e FPS. |
| Webcam virtual | Envia a imagem para o dispositivo V4L2 `/dev/video42` (**Galaxy Camera**) usando o `v4l2loopback`, para seleção por aplicativos compatíveis. |
| Diagnóstico | Mostra as ferramentas encontradas, estado do ADB/mDNS e disponibilidade da webcam virtual. |

Não é necessário instalar aplicativo no celular. É necessário **habilitar a depuração sem fio** no Android e autorizar o pareamento.

## Requisitos

- **Linux:** testado no Pop!_OS 24.04, sessão COSMIC/Wayland. Outras distribuições e desktops não possuem a mesma validação.
- **Interface:** Python 3, GTK4/PyGObject e `qrencode` (instalados como dependências pelo pacote `.deb`).
- **ADB:** Android SDK Platform-Tools com suporte a pareamento e descoberta mDNS. A versão **37.0.1** foi validada.
- **scrcpy:** versão com suporte a `--video-source=camera` (2.2 ou superior); a **5.0.1** foi validada.
- **Android:** aparelho com depuração sem fio, preferencialmente Android 11 ou superior, na mesma rede local do computador.
- **Somente para webcam virtual:** `v4l2loopback`, `v4l-utils` e módulo compatível com o kernel.

Instale o [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) e o [scrcpy](https://github.com/Genymobile/scrcpy/releases) separadamente. O Android Link aproveita essas ferramentas existentes e não as substitui.

## Instalação

### Opção recomendada: pacote Debian construído a partir do repositório

```bash
git clone https://github.com/Arthurregiani/android-link-cosmic.git
cd android-link-cosmic

./packaging/build_deb.sh
sudo apt install ./dist/android-link-cosmic_1.1.0_all.deb
```

Depois, abra **Android Link** pelo menu de aplicativos do COSMIC ou execute `android-link`.

O pipeline do [GitHub Actions](https://github.com/Arthurregiani/android-link-cosmic/actions) também gera o pacote `.deb` como artefato de build. **O arquivo `.deb` não é mantido no código-fonte do Git.** Se a versão mudar, confira o nome gerado em `dist/`.

### Alternativa: instalação no perfil do usuário

A partir da pasta clonada:

```bash
./instalar.sh
~/.local/bin/android-link
```

Esse instalador copia os arquivos para `~/.local/share/android-link`, cria o lançador no menu e instala via APT somente as dependências gráficas/QR ausentes. Pode solicitar `sudo` para essas dependências; não instala nem modifica ADB/scrcpy.

### Caminhos personalizados para ADB e scrcpy

O aplicativo procura, nesta ordem:

| Ferramenta | Variável de ambiente | Caminho preferencial existente | Alternativa |
| --- | --- | --- | --- |
| ADB | `ANDROID_LINK_ADB` | `~/Android/platform-tools/adb` | `adb` no `PATH` |
| scrcpy | `ANDROID_LINK_SCRCPY` | `~/Downloads/scrcpy-linux-x86_64-v5.0.1/scrcpy` | `scrcpy` no `PATH` |

Caso os executáveis estejam em outros locais:

```bash
ANDROID_LINK_ADB="/caminho/para/adb" \
ANDROID_LINK_SCRCPY="/caminho/para/scrcpy" \
android-link
```

Os caminhos do usuário não são incluídos no repositório. Evite usar o scrcpy 1.25 distribuído por alguns repositórios antigos: ele não suporta a origem de vídeo `camera`.

## Primeira conexão e uso diário

1. Conecte celular e computador à mesma rede local.
2. No Android, abra **Opções do desenvolvedor → Depuração sem fio** e ative a função.
3. Se o celular **ainda não estiver pareado**, clique em **Parear outro Android por QR Code** no Android Link e selecione **Parear dispositivo com QR Code** no Android. O QR expira após 120 segundos.
4. Se já estiver pareado, abra o Android Link e use **Atualizar** / **Conectar** caso a reconexão não ocorra automaticamente. Não é preciso escanear um novo QR em cada utilização.
5. Selecione o aparelho. A bateria e seu estado de carregamento aparecerão na interface.
6. Use **Espelhar Android**, **Abrir câmera** ou **Usar como webcam virtual**. Para encerrar, clique em **Parar transmissão** ou feche a janela.

A reconexão depende de o Android manter a depuração sem fio habilitada, de o mDNS funcionar e de a rede permitir comunicação entre dispositivos. Ela **não é garantida** durante trocas de rede ou quando o sistema desativa a depuração.

## Configurar a webcam virtual

A visualização da câmera funciona sem driver virtual. Para disponibilizá-la ao Google Meet, Discord e outros consumidores V4L2, configure o `v4l2loopback` **uma vez**:

```bash
sudo apt install v4l2loopback-dkms v4l-utils
sudo modprobe v4l2loopback video_nr=42 card_label='Galaxy Camera' exclusive_caps=1

v4l2-ctl --device=/dev/video42 --all
```

Confirme antes que `/dev/video42` não pertence a outro dispositivo. Se o módulo já estiver carregado com opções diferentes, **não o descarregue enquanto estiver em uso**. Em kernels personalizados, o DKMS precisa dos headers compatíveis.

Com o módulo pronto, clique em **Usar como webcam virtual** no Android Link e então selecione **Galaxy Camera** no aplicativo de videochamada. **Inicie a transmissão antes de abrir a lista de câmeras**: com `exclusive_caps=1`, a captura é anunciada quando há um produtor de vídeo ativo.

### Carregar o módulo automaticamente após reiniciar

Opcionalmente, dentro da pasta do projeto:

```bash
sudo ./scripts/configurar-webcam.sh
```

O script escreve uma configuração específica em `/etc/modprobe.d/` e `/etc/modules-load.d/`, verifica conflito no dispositivo e tenta carregar o módulo. Ele **não cria um serviço do Android Link**, não altera o bootloader e não modifica o Secure Boot. Não executá-lo se existir uma configuração incompatível sem antes revisá-la.

Para remover apenas essa configuração de carregamento:

```bash
sudo ./scripts/remover-config-webcam.sh
```

**Secure Boot:** na máquina de referência, o `v4l2loopback` DKMS sem assinatura foi rejeitado com `Key was rejected by service`. A webcam foi testada com Secure Boot desativado. **Reativá-lo sem assinar o módulo com uma chave aceita pelo kernel poderá bloquear a webcam novamente.** O Android Link não muda chaves UEFI, MOK, firmware ou opções de inicialização.

## Compatibilidade e validação

Testes realizados no ambiente de referência em **19/10/2026**:

| Cenário | Resultado |
| --- | --- |
| ADB 37.0.1 e descoberta mDNS do Galaxy A54 | Confirmado |
| Bateria real e transição entre carregando/descarregando na interface GTK4 | Confirmado |
| Execução de espelhamento, câmera e webcam pela lógica da interface | Confirmado; não substitui inspeção visual de todas as janelas |
| Recebimento de quadros reais de `/dev/video42` por consumidor V4L2 | Confirmado |
| Prévia da **Galaxy Camera** no Google Meet | Confirmada no navegador de teste do Codex; não houve chamada |
| Discord e navegador Zen/Firefox do usuário | Validação final ainda pendente |
| Novo pareamento por QR Code | Implementado e coberto por testes, sem novo pareamento físico nessa validação |
| Testes automatizados | 22 aprovados e 1 teste GTK ignorado na execução padrão; teste GTK aprovado separadamente |

Consulte [VALIDACAO.md](VALIDACAO.md) para as evidências, ressalvas e procedimentos específicos, e [CHANGELOG.md](CHANGELOG.md) para o histórico.

### Se a câmera não aparecer no navegador

- Inicie **Usar como webcam virtual** antes de abrir as configurações de vídeo e recarregue a página.
- Confirme as permissões de câmera do site e se `/dev/video42` está recebendo quadros.
- No Firefox/Zen, se a enumeração via PipeWire continuar falhando, uma alternativa **experimental e reversível** é testar `media.webrtc.camera.allow-pipewire=false` em `about:config`. Registre o valor anterior para poder restaurá-lo. Essa alteração **não foi aplicada nem validada no perfil do usuário**.
- Em aplicativos Flatpak, confirme o acesso ao dispositivo antes de modificar permissões; não amplie o acesso ao sistema inteiro sem necessidade.
- Se o Android aparecer duplicado como IP e mDNS, use **Atualizar**; a interface tenta consolidar as entradas correspondentes ao mesmo endpoint.

## Privacidade e funcionamento em segundo plano

- O aplicativo não exige cadastro, servidor próprio ou serviço residente de sincronização.
- O ADB se comunica com o Android pela rede local, após autorização no aparelho. **O ADB possui privilégios elevados de depuração**: habilite-o somente em redes confiáveis.
- O QR de pareamento utiliza segredo temporário; o programa não publica chaves ADB nem armazena histórico de bateria.
- A captura é iniciada sob demanda. Ao fechar o Android Link, suas transmissões scrcpy são encerradas; o **servidor ADB**, compartilhado com outros programas, pode continuar em execução.
- O último log do scrcpy fica em `~/.cache/android-link/scrcpy-last.log`, com acesso restrito ao usuário. O diagnóstico pode exibir IPs da rede local: revise antes de compartilhar capturas ou logs.

## Desenvolvimento

```bash
git clone https://github.com/Arthurregiani/android-link-cosmic.git
cd android-link-cosmic

PYTHONPATH=. python3 -m unittest discover -s tests -v
./packaging/build_deb.sh
```

O CI executa compilação Python, testes unitários, verificação de sintaxe dos scripts e build do pacote Debian.

**Estrutura do projeto:** `android_link/` (interface e integração ADB/scrcpy), `tests/`, `assets/`, `packaging/`, `scripts/` e `.github/workflows/`.

Não envie para o repositório `~/.android/`, chaves de pareamento, logs, gravações, capturas privadas ou outros dados reais do telefone.

## Remoção

Instalação via `.deb`:

```bash
sudo apt remove android-link-cosmic
```

Instalação pelo perfil do usuário (executar da pasta do projeto):

```bash
./desinstalar.sh
```

O aplicativo não remove ADB, scrcpy, pareamentos existentes nem o módulo de terceiros `v4l2loopback`.

## Referências

- [scrcpy — projeto oficial](https://github.com/Genymobile/scrcpy)
- [scrcpy — webcam virtual V4L2](https://github.com/Genymobile/scrcpy/blob/master/doc/v4l2.md)
- [Android — depuração sem fio](https://developer.android.com/tools/adb#connect-to-a-device-over-wi-fi)
- [Código e execuções de CI deste projeto](https://github.com/Arthurregiani/android-link-cosmic)

> **Licenciamento:** este repositório ainda não possui um arquivo `LICENSE`. Disponibilidade pública do código não deve ser interpretada como concessão automática de licença para redistribuição ou modificação.
