#!/usr/bin/python3
"""Android Link: on-demand GTK4 interface for ADB Wi-Fi and scrcpy.

Launch with the distro Python interpreter (/usr/bin/python3) so python3-gi
installed by apt is visible. No background systemd service is installed.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import threading
import traceback

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gio, GLib, Gtk
except (ImportError, ValueError) as exc:
    print("GTK4/PyGObject não disponível. Execute ./instalar.sh.", file=sys.stderr)
    print(exc, file=sys.stderr)
    raise SystemExit(2)

if __package__:
    from . import core
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from android_link import core

VERSION = "1.1.0"
CAMERA_LABELS = ["Traseira", "Frontal"]
SIZE_LABELS = ["Até 1920 px", "Até 1280 px", "Automático", "Até 2560 px"]
SIZE_VALUES = [1920, 1280, 0, 2560]
FPS_LABELS = ["Padrão (~30)", "30 FPS", "60 FPS"]
FPS_VALUES = [0, 30, 60]


def text_label(text: str, wrap: bool = False) -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_wrap(wrap)
    return label


def button(label: str, callback) -> Gtk.Button:
    b = Gtk.Button(label=label)
    b.connect("clicked", callback)
    return b


class AndroidLink(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="net.regiani.AndroidLink",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.device_choices: list[core.DeviceChoice] = []
        self.busy = False
        self.closed = False
        self.process: subprocess.Popen | None = None
        self.process_log_path: Path | None = None
        self.process_mode = ""
        self.pair_cancel = threading.Event()
        self.pair_dialog = None
        self.pair_tmp: tempfile.TemporaryDirectory | None = None
        self.battery_inflight = False
        self.battery_checked_at = 0.0
        self.battery_serial = ""
        self.updating_dropdown = False
        self.selection_identity = ""
        self.selection_serial = ""
        self.reconnect_at = 0.0

    def do_activate(self):
        if self.window is not None:
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("Android Link")
        self.window.set_default_size(720, 650)
        self.window.connect("close-request", self.on_close)

        header = Gtk.HeaderBar()
        header.set_title_widget(text_label("Android Link · COSMIC"))
        self.window.set_titlebar(header)
        header.pack_end(button("Diagnóstico", self.on_diagnostics))

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main.set_margin_start(22)
        main.set_margin_end(22)
        main.set_margin_top(20)
        main.set_margin_bottom(24)
        scroll.set_child(main)
        self.window.set_child(scroll)

        subtitle = text_label("Controle o Android pelo Wi-Fi. O ADB e o scrcpy só são usados ao abrir ou executar uma ação.", True)
        subtitle.add_css_class("dim-label")
        main.append(subtitle)

        device_title = text_label("Dispositivo")
        device_title.add_css_class("heading")
        main.append(device_title)

        device_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.device_dropdown = Gtk.DropDown(model=Gtk.StringList.new(["Procurando dispositivos…"]))
        self.device_dropdown.set_hexpand(True)
        self.device_dropdown.connect("notify::selected", self.on_device_selected)
        device_row.append(self.device_dropdown)
        self.refresh_btn = button("Atualizar", self.on_refresh)
        self.connect_btn = button("Conectar", self.on_connect)
        device_row.append(self.refresh_btn)
        device_row.append(self.connect_btn)
        main.append(device_row)

        self.connection_label = text_label("Inicializando ADB…", True)
        self.connection_label.add_css_class("dim-label")
        main.append(self.connection_label)

        battery_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        battery_row.append(text_label("Bateria do smartphone"))
        self.battery_bar = Gtk.ProgressBar()
        self.battery_bar.set_hexpand(True)
        self.battery_bar.set_fraction(0)
        battery_row.append(self.battery_bar)
        self.battery_label = text_label("—")
        self.battery_label.set_width_chars(25)
        battery_row.append(self.battery_label)
        main.append(battery_row)

        pair_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pair_btn = button("Parear outro Android por QR Code", self.on_pair)
        pair_row.append(self.pair_btn)
        pair_row.append(text_label("Usar somente se o pareamento anterior foi perdido."))
        main.append(pair_row)
        main.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        camera_title = text_label("Câmera / tela")
        camera_title.add_css_class("heading")
        main.append(camera_title)

        opts = Gtk.Grid(column_spacing=10, row_spacing=10)
        opts.attach(text_label("Câmera"), 0, 0, 1, 1)
        self.facing = Gtk.DropDown(model=Gtk.StringList.new(CAMERA_LABELS))
        opts.attach(self.facing, 1, 0, 1, 1)
        opts.attach(text_label("Resolução"), 2, 0, 1, 1)
        self.size = Gtk.DropDown(model=Gtk.StringList.new(SIZE_LABELS))
        opts.attach(self.size, 3, 0, 1, 1)
        opts.attach(text_label("Taxa de quadros"), 0, 1, 1, 1)
        self.fps = Gtk.DropDown(model=Gtk.StringList.new(FPS_LABELS))
        opts.attach(self.fps, 1, 1, 1, 1)
        main.append(opts)

        actions = Gtk.Grid(column_spacing=8, row_spacing=8)
        self.mirror_btn = button("Espelhar Android", lambda _: self.launch("mirror"))
        self.camera_btn = button("Abrir câmera", lambda _: self.launch("camera"))
        self.webcam_btn = button("Usar como webcam virtual", lambda _: self.launch("webcam"))
        self.stop_btn = button("Parar transmissão", self.on_stop)
        actions.attach(self.mirror_btn, 0, 0, 1, 1)
        actions.attach(self.camera_btn, 1, 0, 1, 1)
        actions.attach(self.webcam_btn, 0, 1, 1, 1)
        actions.attach(self.stop_btn, 1, 1, 1, 1)
        main.append(actions)

        webcam_help = text_label("Webcam virtual requer v4l2loopback em /dev/video42. Sem ele, use 'Abrir câmera' ou 'Espelhar Android'.", True)
        webcam_help.add_css_class("dim-label")
        main.append(webcam_help)
        main.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        status_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.spinner = Gtk.Spinner()
        status_head.append(self.spinner)
        self.status_label = text_label("Pronto.", True)
        self.status_label.set_hexpand(True)
        status_head.append(self.status_label)
        main.append(status_head)

        self.output_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.output_buffer, editable=False, cursor_visible=False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.set_top_margin(8)
        self.log_view.set_bottom_margin(8)
        self.log_view.set_left_margin(8)
        self.log_view.set_right_margin(8)
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_min_content_height(130)
        log_scroll.set_max_content_height(200)
        log_scroll.set_child(self.log_view)
        log_scroll.set_vexpand(False)
        main.append(log_scroll)

        self.window.present()
        self.refresh()
        GLib.timeout_add_seconds(10, self.poll_while_open)
        GLib.timeout_add_seconds(2, self.check_process)

    def status(self, message: str, *, logged: bool = True):
        if self.closed:
            return
        self.status_label.set_text(message)
        if logged:
            now = dt.datetime.now().strftime("%H:%M:%S")
            current = self.output_buffer.get_text(self.output_buffer.get_start_iter(),
                                                  self.output_buffer.get_end_iter(), True)
            lines = (current + f"[{now}] {message}\n")[-14000:]
            self.output_buffer.set_text(lines)
            it = self.output_buffer.get_end_iter()
            self.log_view.scroll_to_iter(it, 0, False, 0, 0)

    def set_busy(self, active: bool):
        self.busy = active
        for b in (self.refresh_btn, self.connect_btn, self.pair_btn):
            b.set_sensitive(not active)
        if active:
            self.spinner.start()
        else:
            self.spinner.stop()

    def background(self, job, finished, message: str, *, quiet: bool = False):
        if self.busy or self.closed:
            return
        self.set_busy(True)
        if not quiet:
            self.status(message)

        def runner():
            try:
                result = job()
            except Exception as exc:
                GLib.idle_add(self._job_error, str(exc))
            else:
                GLib.idle_add(self._job_complete, finished, result)

        threading.Thread(target=runner, daemon=True, name="android-link-worker").start()

    def _job_error(self, message):
        if not self.closed:
            self.set_busy(False)
            self.status(f"Erro: {message}")
        return GLib.SOURCE_REMOVE

    def _job_complete(self, cb, value):
        if not self.closed:
            self.set_busy(False)
            cb(value)
        return GLib.SOURCE_REMOVE

    def poll_while_open(self):
        if self.closed:
            return GLib.SOURCE_REMOVE
        if not self.busy and self.pair_dialog is None:
            self.refresh(silent=True)
        return GLib.SOURCE_CONTINUE

    def on_refresh(self, _button):
        self.refresh()

    def refresh(self, silent=False):
        previous = self.selected_choice()
        old_id = previous.identity if previous else self.selection_identity
        old_serial = previous.serial if previous else self.selection_serial

        def done(result):
            choices, _, _ = result
            self.device_choices = choices
            labels = []
            for c in choices:
                prefix = "Conectado" if c.state == "device" else "Detectado" if c.state == "discovered" else c.state
                labels.append(f"{prefix}: {c.label}")
            if not labels:
                labels = ["Nenhum Android encontrado"]
            self.updating_dropdown = True
            self.device_dropdown.set_model(Gtk.StringList.new(labels))
            preferred = next((i for i, c in enumerate(choices) if (c.identity == old_id or (old_serial and c.serial == old_serial))), None)
            if preferred is None:
                preferred = (Gtk.INVALID_LIST_POSITION if old_id else
                             next((i for i, c in enumerate(choices) if c.state == "device"), 0))
            self.device_dropdown.set_selected(preferred)
            self.updating_dropdown = False
            selected = self.selected_choice()
            if selected:
                self.selection_identity = selected.identity
                self.selection_serial = selected.serial
            connected = sum(c.state == "device" for c in choices)
            self.connection_label.set_text(
                f"{connected} dispositivo(s) conectados · {len(choices)} detectado(s) (conexões duplicadas consolidadas)"
                if choices else "Nenhum dispositivo encontrado. Ative a depuração sem fio no Android e confirme a rede local.")
            if not silent:
                self.status(f"Descoberta concluída: {len(choices)} dispositivo(s).")
            self.refresh_battery()
            selected = self.selected_choice()
            if (selected and selected.state == "discovered" and
                    time.monotonic() - self.reconnect_at >= 30):
                self.reconnect_at = time.monotonic()
                self.on_connect(None)

        self.background(core.snapshot, done, "Atualizando dispositivos…" if not silent else "Verificando conexão…", quiet=silent)

    def selected_choice(self) -> core.DeviceChoice | None:
        if not self.device_choices:
            return None
        i = int(self.device_dropdown.get_selected())
        return self.device_choices[i] if 0 <= i < len(self.device_choices) else None

    def on_device_selected(self, *_args):
        if not self.updating_dropdown and getattr(self, "battery_label", None) is not None:
            choice = self.selected_choice()
            if choice:
                self.selection_identity = choice.identity
                self.selection_serial = choice.serial
            self.refresh_battery(force=True)

    def refresh_battery(self, *, force: bool = False):
        """Battery polling runs only while the UI is open, on a worker thread."""
        if self.closed or getattr(self, "battery_label", None) is None:
            return
        choice = self.selected_choice()
        if not choice or choice.state != "device":
            self.battery_serial = ""
            self.battery_checked_at = 0
            self.battery_label.set_text("Indisponível · desconectado")
            self.battery_bar.set_fraction(0)
            return
        serial = choice.serial
        now = time.monotonic()
        if self.battery_inflight:
            return
        if not force and serial == self.battery_serial and now - self.battery_checked_at < 30:
            return
        self.battery_serial = serial
        self.battery_checked_at = now
        self.battery_inflight = True
        self.battery_label.set_text("Consultando…")

        def worker():
            try:
                result = core.read_battery(serial)
                GLib.idle_add(self._battery_ready, serial, result, "")
            except Exception as exc:
                GLib.idle_add(self._battery_ready, serial, None, str(exc))

        threading.Thread(target=worker, daemon=True, name="android-link-battery").start()

    def _battery_ready(self, serial, battery, error):
        self.battery_inflight = False
        if self.closed:
            return GLib.SOURCE_REMOVE
        choice = self.selected_choice()
        if not choice or choice.state != "device" or choice.serial != serial:
            self.refresh_battery(force=True)
            return GLib.SOURCE_REMOVE
        if battery is None:
            self.battery_label.set_text("Bateria indisponível")
            self.battery_bar.set_fraction(0)
            self.status(f"Bateria indisponível: {error}")
        else:
            self.battery_bar.set_fraction(battery.percent / 100)
            self.battery_label.set_text(f"{battery.percent}% · {battery.status}")
        return GLib.SOURCE_REMOVE

    def on_connect(self, _button):
        choice = self.selected_choice()
        if not choice:
            self.status("Nenhum Android detectado. Ative a depuração sem fio ou use o pareamento QR.")
            return
        self.background(lambda: core.connect_choice(choice), self._did_connect, "Conectando ao dispositivo…")

    def _did_connect(self, output):
        self.status(output)
        self.refresh()

    def on_pair(self, _button):
        if self.pair_dialog is not None or self.busy:
            return
        if not shutil.which("qrencode"):
            self.status("QR indisponível. Instale o pacote 'qrencode' pelo instalador.")
            return
        try:
            name, password, payload = core.new_pairing()
            self.pair_tmp = tempfile.TemporaryDirectory(prefix="android-link-qr-")
            qr_path = str(Path(self.pair_tmp.name) / "pair.png")
            result = subprocess.run(["qrencode", "-m", "4", "-s", "8", "-o", qr_path],
                                    capture_output=True, text=True, input=payload, timeout=8, check=False)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "Não foi possível gerar o QR Code")
        except Exception as exc:
            self._delete_qr()
            self.status(f"Erro ao gerar QR Code: {exc}")
            return

        self.pair_cancel = threading.Event()
        window = Gtk.Window(title="Parear Android por QR Code")
        window.set_transient_for(self.window)
        window.set_modal(True)
        window.set_default_size(430, 500)
        window.connect("close-request", self._on_pair_close)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        for side in ("start", "end", "top", "bottom"):
            getattr(content, f"set_margin_{side}")(20)
        content.append(text_label("No celular: Opções do desenvolvedor → Depuração sem fio → Parear dispositivo com QR Code.", True))
        img = Gtk.Picture()
        img.set_filename(qr_path)
        img.set_size_request(330, 330)
        img.set_can_shrink(True)
        content.append(img)
        self.pair_status = text_label("Aguardando leitura do QR Code (até 120 segundos)…", True)
        content.append(self.pair_status)
        content.append(button("Cancelar pareamento", lambda _: window.close()))
        window.set_child(content)
        self.pair_dialog = window
        window.present()
        self.status("QR Code gerado. Aguardando leitura pelo Samsung…")

        def update_in_window(message: str):
            def render():
                if self.pair_dialog is window and not self.closed:
                    self.pair_status.set_text(message)
                    self.status(message)
                return GLib.SOURCE_REMOVE
            GLib.idle_add(render)

        def worker():
            try:
                outcome = core.pair_with_qr(name, password, self.pair_cancel.is_set,
                                            update_in_window)
                GLib.idle_add(self._pair_finish, outcome, window)
            except Exception as exc:
                GLib.idle_add(self._pair_finish, f"Erro no pareamento: {exc}", window)

        threading.Thread(target=worker, daemon=True, name="android-link-pair").start()

    def _delete_qr(self):
        if self.pair_tmp is not None:
            self.pair_tmp.cleanup()
            self.pair_tmp = None

    def _on_pair_close(self, _window):
        self.pair_cancel.set()
        self.pair_dialog = None
        self._delete_qr()
        return False

    def _pair_finish(self, result: str, window):
        if self.pair_dialog is window and not self.closed:
            window.close()
            self.status(result)
            self.refresh()
        return GLib.SOURCE_REMOVE

    def launch(self, mode: str):
        choice = self.selected_choice()
        if not choice or choice.state != "device":
            self.status("Conecte o Android antes de iniciar o scrcpy.")
            return
        if mode == "webcam":
            valid, reason = core.webcam_loopback_check()
            if not valid:
                self.status(f"Webcam virtual indisponível: {reason}")
                self.status("Configure: sudo apt install v4l2loopback-dkms v4l-utils")
                self.status("Depois: sudo modprobe v4l2loopback video_nr=42 card_label='Galaxy Camera' exclusive_caps=1")
                return
        facing = "back" if self.facing.get_selected() == 0 else "front"
        size = SIZE_VALUES[int(self.size.get_selected())]
        fps = FPS_VALUES[int(self.fps.get_selected())]
        try:
            args = core.scrcpy_args(choice.serial, mode, facing, size, fps)
            self.stop_process()
            cache = Path.home() / ".cache/android-link"
            cache.mkdir(parents=True, exist_ok=True)
            self.process_log_path = cache / "scrcpy-last.log"
            env = os.environ.copy()
            adb = core.get_adb()
            if not adb:
                raise RuntimeError("ADB não encontrado. Verifique ~/Android/platform-tools/adb.")
            env["ADB"] = adb
            env["PATH"] = f"{Path(adb).parent}:{env.get('PATH', '')}"
            log_fd = os.open(self.process_log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            os.fchmod(log_fd, 0o600)
            with os.fdopen(log_fd, "w", encoding="utf-8") as log_file:
                self.process = subprocess.Popen(args, stdout=log_file, stderr=subprocess.STDOUT,
                                                env=env, start_new_session=True)
            self.process_mode = mode
        except Exception as exc:
            self.status(f"Falha ao iniciar scrcpy: {exc}")
            return
        labels = {"mirror": "Espelhamento", "camera": "Câmera", "webcam": "Webcam virtual"}
        self.status(f"{labels[mode]} iniciado(a). Fechar o aplicativo também encerra a transmissão.")

    def stop_process(self):
        proc = self.process
        self.process = None
        self.process_mode = ""
        if proc is None:
            return
        if proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            return
        def force_after_wait():
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
        threading.Thread(target=force_after_wait, name="android-link-stop", daemon=False).start()

    def on_stop(self, _button):
        if self.process is None:
            self.status("Nenhuma transmissão iniciada pelo aplicativo está ativa.")
            return
        self.stop_process()
        self.status("Transmissão encerrada.")

    def check_process(self):
        if self.closed:
            return GLib.SOURCE_REMOVE
        if self.process is not None and self.process.poll() is not None:
            rc = self.process.returncode
            self.process = None
            self.process_mode = ""
            tail = ""
            try:
                tail = "\n".join(self.process_log_path.read_text(errors="replace").splitlines()[-8:])
            except (OSError, AttributeError):
                pass
            self.status(f"scrcpy foi encerrado (código {rc}). {tail}" if rc else "Transmissão encerrada.")
        return GLib.SOURCE_CONTINUE

    def on_diagnostics(self, _button):
        def job():
            adb = core.get_adb()
            scrcpy = core.get_scrcpy()
            try:
                devices, device_text, mdns_text = core.snapshot()
            except RuntimeError as exc:
                device_text, mdns_text = str(exc), ""
            return (f"ADB: {adb or 'não encontrado'}\n{core.tool_version(adb, limit=3)}\n\n"
                    f"scrcpy: {scrcpy or 'não encontrado'}\n{core.tool_version(scrcpy, limit=2)}\n\n"
                    f"ADB devices:\n{device_text}\nmDNS:\n{mdns_text}\n"
                    f"v4l2loopback: {core.webcam_loopback_check()[1]}")
        def done(report):
            self.status("Diagnóstico concluído (exibido abaixo).")
            now = dt.datetime.now().strftime("%H:%M:%S")
            self.output_buffer.set_text(f"[{now}]\n{report}")
        self.background(job, done, "Coletando diagnóstico local…")

    def on_close(self, _window):
        self.closed = True
        self.pair_cancel.set()
        self.stop_process()
        self._delete_qr()
        return False


def main():
    app = AndroidLink()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
