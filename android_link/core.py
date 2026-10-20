"""Safe, subprocess-only ADB/scrcpy integration for Android Link.

This module deliberately has no GTK imports so parsing and device selection can
be tested without access to the user's Android phone or desktop session.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import os
import re
import secrets
import shutil
import subprocess
import time

DEFAULT_ADB = Path.home() / "Android/platform-tools/adb"
DEFAULT_SCRCPY = Path.home() / "Downloads/scrcpy-linux-x86_64-v5.0.1/scrcpy"
MDNS_CONNECT_TYPE = "_adb-tls-connect._tcp"
MDNS_PAIR_TYPE = "_adb-tls-pairing._tcp"
ENDPOINT_RE = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3}){3}|\[[0-9a-fA-F:]+\]):\d{1,5}$")


def get_adb() -> str:
    override = os.environ.get("ANDROID_LINK_ADB")
    if override:
        return override
    if DEFAULT_ADB.is_file() and os.access(DEFAULT_ADB, os.X_OK):
        return str(DEFAULT_ADB)
    return shutil.which("adb") or ""


def get_scrcpy() -> str:
    override = os.environ.get("ANDROID_LINK_SCRCPY")
    if override:
        return override
    if DEFAULT_SCRCPY.is_file() and os.access(DEFAULT_SCRCPY, os.X_OK):
        return str(DEFAULT_SCRCPY)
    return shutil.which("scrcpy") or ""


def tool_version(binary: str, *, limit: int = 5) -> str:
    if not binary:
        return "Não encontrado"
    try:
        p = subprocess.run([binary, "--version"], capture_output=True, text=True,
                           timeout=6, check=False)
        lines = (p.stdout or p.stderr).splitlines()
        return "\n".join(lines[:limit]).strip() or f"código {p.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Erro: {exc}"


def run_adb(*args: str, timeout: float = 8, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    adb = get_adb()
    if not adb:
        raise RuntimeError("ADB não encontrado. Esperado: ~/Android/platform-tools/adb")
    try:
        return subprocess.run([adb, *args], capture_output=True, text=True,
                              timeout=timeout, check=False, input=input_text)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"O ADB não respondeu em {timeout:g} segundos") from exc
    except OSError as exc:
        raise RuntimeError(f"Não foi possível executar o ADB: {exc}") from exc


@dataclass(frozen=True)
class MdnsService:
    name: str
    kind: str
    endpoint: str


def parse_mdns(text: str) -> list[MdnsService]:
    found: list[MdnsService] = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        name, kind, endpoint = fields[:3]
        if kind not in (MDNS_CONNECT_TYPE, MDNS_PAIR_TYPE):
            continue
        if not ENDPOINT_RE.fullmatch(endpoint):
            continue
        found.append(MdnsService(name, kind, endpoint))
    return found


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str
    model: str
    product: str


def parse_devices(text: str) -> list[AdbDevice]:
    result: list[AdbDevice] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2 or parts[0] == "List":
            continue
        # adb -l fields are key:value tokens, not necessarily in a fixed order.
        fields = {}
        for item in parts[2:]:
            if ":" in item:
                k, v = item.split(":", 1)
                fields[k] = v
        if parts[1] not in {"device", "offline", "unauthorized", "recovery", "sideload", "bootloader"}:
            continue
        result.append(AdbDevice(serial=parts[0], state=parts[1],
                                model=fields.get("model", ""), product=fields.get("product", "")))
    return result


@dataclass(frozen=True)
class DeviceChoice:
    identity: str
    serial: str
    endpoint: str
    state: str
    model: str
    label: str


def group_devices(devices: list[AdbDevice], services: list[MdnsService]) -> list[DeviceChoice]:
    """Deduplicate ADB TCP and TLS-mDNS transports that point to one endpoint.

    Identity is endpoint rather than model: two phones of the same model must
    never be collapsed into one. Prefer the TLS-mDNS serial if both exist.
    """
    connected_services = [s for s in services if s.kind == MDNS_CONNECT_TYPE]
    mapped: dict[str, DeviceChoice] = {}
    mdns_serial_map = {f"{s.name}.{s.kind}": s.endpoint for s in connected_services}
    for d in devices:
        endpoint = mdns_serial_map.get(d.serial, d.serial if ENDPOINT_RE.fullmatch(d.serial) else "")
        identity = endpoint or d.serial
        label_model = d.model.replace("_", " ") if d.model else "Android"
        readable = f"{label_model} · {endpoint or d.serial}"
        current = mapped.get(identity)
        choice = DeviceChoice(identity, d.serial, endpoint, d.state, d.model, readable)
        if not current:
            mapped[identity] = choice
        else:
            # Preserve the more helpful model, and prefer a connected TLS serial.
            if d.state == "device" and (current.state != "device" or d.serial in mdns_serial_map):
                mapped[identity] = choice
    for service in connected_services:
        if service.endpoint not in mapped:
            mapped[service.endpoint] = DeviceChoice(
                service.endpoint, "", service.endpoint, "discovered", "",
                f"Android detectado · {service.endpoint}")
    return sorted(mapped.values(), key=lambda c: (c.state != "device", c.label.lower()))


def snapshot() -> tuple[list[DeviceChoice], str, str]:
    services_run = run_adb("mdns", "services")
    devices_run = run_adb("devices", "-l")
    services_text = (services_run.stdout or "") + (services_run.stderr or "")
    devices_text = (devices_run.stdout or "") + (devices_run.stderr or "")
    choices = group_devices(parse_devices(devices_text), parse_mdns(services_text))
    return choices, devices_text, services_text


def connect_choice(choice: DeviceChoice) -> str:
    if choice.state == "device":
        return "Dispositivo já está conectado."
    if not choice.endpoint:
        raise RuntimeError("Dispositivo sem endereço Wi-Fi. Ative a depuração sem fio.")
    p = run_adb("connect", choice.endpoint, timeout=15)
    output = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
    if p.returncode != 0 or "failed to connect" in output.lower():
        raise RuntimeError(output or "Falha na conexão ADB")
    return output or "Comando de conexão enviado."


def new_pairing() -> tuple[str, str, str]:
    """Return (name, secret, Android Wi-Fi pairing QR payload)."""
    name = "studio-" + secrets.token_hex(8)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    password = "".join(secrets.choice(alphabet) for _ in range(12))
    return name, password, f"WIFI:T:ADB;S:{name};P:{password};;"


def find_pair_endpoint(services: list[MdnsService], pairing_name: str) -> str:
    for service in services:
        if service.kind == MDNS_PAIR_TYPE and service.name == pairing_name:
            return service.endpoint
    return ""


def connect_after_pairing(pair_ip: str, *, timeout: float = 20,
                          cancelled: Callable[[], bool] = lambda: False) -> str:
    """Favor endpoints on the IP used by the QR scan; avoid other phones."""
    target = pair_ip.rsplit(":", 1)[0]
    end = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < end and not cancelled():
        try:
            choices, _, services_text = snapshot()
            if any(d.state == "device" and d.endpoint.rsplit(":", 1)[0] == target
                   for d in choices if d.endpoint):
                return "Dispositivo pareado e conectado automaticamente."
            services = parse_mdns(services_text)
            for s in services:
                if s.kind == MDNS_CONNECT_TYPE and s.endpoint.rsplit(":", 1)[0] == target:
                    result = run_adb("connect", s.endpoint, timeout=8)
                    response = ((result.stdout or "") + (result.stderr or "")).lower()
                    if result.returncode == 0 and "failed to connect" not in response:
                        return "Pareamento concluído; reconexão solicitada."
                    last_error = ((result.stdout or "") + (result.stderr or "")).strip()
        except RuntimeError as exc:
            last_error = str(exc)
        time.sleep(1.5)
    if cancelled():
        return "Pareamento cancelado."
    return "Pareado, mas não foi possível confirmar a conexão. Use Atualizar/Conectar. " + last_error


def pair_with_qr(pair_name: str, password: str, cancelled: Callable[[], bool],
                 status: Callable[[str], None], *, timeout: float = 120) -> str:
    """Wait for ADB mDNS QR advertisement; pair only with matching service."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cancelled():
            return "Pareamento cancelado."
        result = run_adb("mdns", "services", timeout=6)
        pairing_endpoint = find_pair_endpoint(parse_mdns(result.stdout or ""), pair_name)
        if pairing_endpoint:
            if cancelled():
                return "Pareamento cancelado."
            status("Celular encontrado. Autenticando pelo ADB…")
            response = run_adb("pair", pairing_endpoint, timeout=25, input_text=password + "\n")
            out = ((response.stdout or "") + "\n" + (response.stderr or "")).strip()
            if response.returncode != 0 or "successfully paired" not in out.lower():
                raise RuntimeError("Falha no pareamento ADB. Gere outro QR e confira a rede.")
            status("Pareado. Localizando a conexão Wi-Fi…")
            return connect_after_pairing(pairing_endpoint,
                                         cancelled=cancelled)
        time.sleep(1.2)
    return "Tempo esgotado (120 s). Confirme a rede e a depuração sem fio."


def webcam_loopback_check(device: str = "/dev/video42") -> tuple[bool, str]:
    if not Path(device).exists():
        return False, f"{device} não existe. Configure o v4l2loopback (instruções no README)."
    ctl = shutil.which("v4l2-ctl")
    if not ctl:
        return False, "v4l2-ctl não instalado. Instale v4l-utils para validar a câmera virtual."
    try:
        result = subprocess.run([ctl, "--info", "--device", device],
                                capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Falha ao inspecionar {device}: {exc}"
    output = ((result.stdout or "") + (result.stderr or "")).lower()
    if result.returncode != 0:
        return False, f"Não foi possível acessar {device}: {output.strip()}"
    if "v4l2 loopback" not in output and "v4l2loopback" not in output:
        return False, f"{device} não é um dispositivo v4l2loopback. Não será sobrescrito."
    return True, device + " validado como v4l2loopback."



@dataclass(frozen=True)
class BatteryInfo:
    """Battery status from Android's dumpsys battery (no Android-side app needed)."""

    percent: int
    status: str
    charging: bool
    temperature_c: float | None = None


def parse_battery(text: str) -> BatteryInfo:
    """Parse dumpsys battery across Android versions and locales.

    Supports scale != 100; never infer a battery level when ADB output is empty,
    truncated or malformed.  """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip().lower()

    try:
        level = int(fields["level"])
        scale = int(fields.get("scale", "100"))
        status_code = int(fields.get("status", "1"))
    except (ValueError, KeyError) as exc:
        raise RuntimeError("O Android não retornou um nível de bateria válido") from exc
    if scale <= 0 or not (0 <= level <= scale):
        raise RuntimeError("O nível de bateria retornado pelo Android é inválido")

    percent = min(100, max(0, round(level * 100 / scale)))
    states = {1: "Desconhecido", 2: "Carregando", 3: "Descarregando",
              4: "Conectado, sem carregar", 5: "Carga completa"}
    temp_c = None
    if "temperature" in fields:
        try:
            temp_c = int(fields["temperature"]) / 10
        except ValueError:
            pass
    return BatteryInfo(percent, states.get(status_code, "Desconhecido"),
                       charging=status_code in (2, 5), temperature_c=temp_c)


def read_battery(serial: str) -> BatteryInfo:
    """Read battery of the *selected* connected Android, never an arbitrary phone."""
    if not serial or any(c in serial for c in "\r\n\0"):
        raise RuntimeError("Identificador de dispositivo inválido")
    reply = run_adb("-s", serial, "shell", "dumpsys", "battery", timeout=10)
    if reply.returncode != 0:
        detail = (reply.stderr or reply.stdout or "dispositivo indisponível").strip()
        raise RuntimeError(f"Não foi possível consultar a bateria: {detail[:240]}")
    return parse_battery(reply.stdout or "")


def scrcpy_args(serial: str, mode: str, facing: str = "back", size: int = 1920,
                fps: int = 0, sink: str = "/dev/video42") -> list[str]:
    exe = get_scrcpy()
    if not exe:
        raise RuntimeError("scrcpy não encontrado em ~/Downloads/scrcpy-linux-x86_64-v5.0.1/")
    if not serial:
        raise RuntimeError("Selecione e conecte um dispositivo primeiro.")
    if mode not in {"mirror", "camera", "webcam"}:
        raise ValueError("Modo não suportado")
    if facing not in {"front", "back"} or size not in {0, 1280, 1920, 2560} or fps not in {0, 30, 60}:
        raise ValueError("Opções de câmera inválidas")
    args = [exe, "--serial", serial, "--no-audio"]
    if mode == "mirror":
        return [*args, "--max-size=1920"]
    args.extend(["--video-source=camera", f"--camera-facing={facing}"])
    if size:
        args.append(f"--max-size={size}")
    if fps:
        args.append(f"--camera-fps={fps}")
    if mode == "webcam":
        args.extend([f"--v4l2-sink={sink}", "--no-video-playback"])
    return args
