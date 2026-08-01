from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Callable
import zipfile

import requests

from src.runtime_paths import (
    downloads_dir,
    logs_dir,
    managed_models_dir,
    managed_runtime_dir,
    managed_runtime_executable,
)


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]


class RuntimePreparationError(RuntimeError):
    """No fue posible preparar o iniciar el componente local."""


def _system_candidates() -> list[Path]:
    candidates: list[Path] = []
    found = shutil.which("ollama")
    if found:
        candidates.append(Path(found))

    local = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
    candidates.extend(
        [
            local / "Programs" / "Ollama" / "ollama.exe",
            local / "Ollama" / "ollama.exe",
            program_files / "Ollama" / "ollama.exe",
            program_files_x86 / "Ollama" / "ollama.exe",
        ]
    )
    return candidates


def find_system_ollama_executable() -> Path | None:
    for candidate in _system_candidates():
        if candidate.is_file():
            return candidate.resolve()
    return None


def find_ollama_executable(runtime_mode: str = "auto") -> Path | None:
    """Localiza el ejecutable según la política configurada.

    ``auto`` reutiliza una instalación normal de Ollama y luego busca el
    runtime administrado por Minutas ASH. ``managed`` utiliza exclusivamente
    el runtime privado. ``system`` no descarga ni usa el runtime privado.
    """
    mode = (runtime_mode or "auto").casefold()
    if mode not in {"auto", "managed", "system"}:
        mode = "auto"

    if mode in {"auto", "system"}:
        system = find_system_ollama_executable()
        if system:
            return system
    if mode in {"auto", "managed"}:
        managed = managed_runtime_executable()
        if managed.is_file():
            return managed.resolve()
    return None


def api_available(base_url: str, timeout: float = 3.0) -> bool:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        return response.ok
    except requests.RequestException:
        return False


def _managed_environment(executable: Path) -> dict[str, str]:
    env = os.environ.copy()
    if executable.resolve() == managed_runtime_executable().resolve():
        managed_models_dir().mkdir(parents=True, exist_ok=True)
        env["OLLAMA_MODELS"] = str(managed_models_dir())
        env["OLLAMA_HOST"] = "127.0.0.1:11434"
    return env


def start_ollama(
    base_url: str,
    log: LogCallback | None = None,
    runtime_mode: str = "auto",
    wait_seconds: float = 30.0,
) -> bool:
    """Inicia el servicio local sin mostrar consola y espera su API."""
    log = log or (lambda _message: None)
    if api_available(base_url):
        return True

    executable = find_ollama_executable(runtime_mode)
    if not executable:
        log("No se encontró el componente de procesamiento local.")
        return False

    log("Iniciando componente de procesamiento local...")
    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    logs_dir().mkdir(parents=True, exist_ok=True)
    runtime_log = logs_dir() / "componente_local.log"
    try:
        with runtime_log.open("ab", buffering=0) as log_file:
            subprocess.Popen(
                [str(executable), "serve"],
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                startupinfo=startupinfo,
                close_fds=True,
                env=_managed_environment(executable),
                cwd=str(executable.parent),
            )
    except OSError as exc:
        log(f"No fue posible iniciar el componente local: {exc}")
        return False

    deadline = time.monotonic() + max(5.0, wait_seconds)
    while time.monotonic() < deadline:
        if api_available(base_url):
            log("Componente local iniciado correctamente.")
            return True
        time.sleep(0.5)
    log("El componente local se inició, pero todavía no responde.")
    return False


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    """Extrae un ZIP rechazando rutas que escapen del directorio destino."""
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if destination not in target.parents and target != destination:
                raise RuntimePreparationError("El paquete descargado contiene una ruta no segura.")
        bundle.extractall(destination)


def download_managed_runtime(
    url: str,
    filename: str = "ollama-windows-amd64.zip",
    minimum_bytes: int = 50 * 1024**2,
    progress: ProgressCallback | None = None,
    log: LogCallback | None = None,
    timeout_seconds: int = 3600,
) -> Path:
    """Descarga y prepara el runtime autónomo oficial para Windows.

    La descarga se escribe primero en ``.part`` y la carpeta extraída se
    reemplaza solo después de validar que contiene ``ollama.exe``. Así se evita
    dejar una instalación incompleta si la red se interrumpe.
    """
    progress = progress or (lambda _value, _message: None)
    log = log or (lambda _message: None)

    if os.name != "nt":
        raise RuntimePreparationError("El runtime administrado solo se prepara en Windows.")

    downloads_dir().mkdir(parents=True, exist_ok=True)
    managed_runtime_dir().parent.mkdir(parents=True, exist_ok=True)
    final_archive = downloads_dir() / filename
    partial_archive = final_archive.with_suffix(final_archive.suffix + ".part")

    log("Descargando el componente local desde la distribución oficial...")
    try:
        with requests.get(url, stream=True, timeout=(30, timeout_seconds), allow_redirects=True) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or 0)
            completed = 0
            with partial_archive.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    completed += len(chunk)
                    if total > 0:
                        percent = max(1, min(99, int(completed * 100 / total)))
                        progress(percent, f"Descargando componentes... {percent}%")
            partial_archive.replace(final_archive)
    except (requests.RequestException, OSError) as exc:
        partial_archive.unlink(missing_ok=True)
        raise RuntimePreparationError(
            "No fue posible descargar el componente local. Revise la conexión a Internet."
        ) from exc

    if final_archive.stat().st_size < minimum_bytes:
        final_archive.unlink(missing_ok=True)
        raise RuntimePreparationError("La descarga terminó incompleta o no corresponde al paquete esperado.")
    if not zipfile.is_zipfile(final_archive):
        final_archive.unlink(missing_ok=True)
        raise RuntimePreparationError("El archivo descargado no es un paquete ZIP válido.")

    progress(99, "Instalando componentes locales...")
    parent = managed_runtime_dir().parent
    with tempfile.TemporaryDirectory(prefix="ollama_extract_", dir=parent) as temporary:
        extracted = Path(temporary)
        _safe_extract_zip(final_archive, extracted)
        candidates = list(extracted.rglob("ollama.exe"))
        if not candidates:
            raise RuntimePreparationError("El paquete descargado no contiene el ejecutable requerido.")

        source_root = candidates[0].parent
        staged = parent / "ollama_staged"
        if staged.exists():
            shutil.rmtree(staged, ignore_errors=True)
        shutil.copytree(source_root, staged)
        if not (staged / "ollama.exe").is_file():
            shutil.rmtree(staged, ignore_errors=True)
            raise RuntimePreparationError("No fue posible preparar el ejecutable local.")

        destination = managed_runtime_dir()
        backup = parent / "ollama_previous"
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
        if destination.exists():
            destination.replace(backup)
        staged.replace(destination)
        shutil.rmtree(backup, ignore_errors=True)

    progress(100, "Componente local preparado")
    log("Componente local preparado correctamente.")
    return managed_runtime_executable()


def ensure_runtime(
    config: dict,
    progress: ProgressCallback | None = None,
    log: LogCallback | None = None,
) -> Path:
    """Garantiza que exista un ejecutable local compatible con la configuración."""
    mode = str(config.get("runtime_mode", "auto"))
    existing = find_ollama_executable(mode)
    if existing:
        return existing
    if mode == "system":
        raise RuntimePreparationError(
            "No se encontró una instalación del componente local en el equipo."
        )
    return download_managed_runtime(
        str(config.get("managed_runtime_url")),
        str(config.get("managed_runtime_filename", "ollama-windows-amd64.zip")),
        int(config.get("managed_runtime_minimum_bytes", 50 * 1024**2)),
        progress=progress,
        log=log,
    )


def list_models(base_url: str) -> list[str]:
    response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=15)
    response.raise_for_status()
    return sorted(
        item.get("name")
        for item in response.json().get("models", [])
        if item.get("name")
    )


def pull_model_stream(
    base_url: str,
    model: str,
    progress: ProgressCallback | None = None,
    log: LogCallback | None = None,
    timeout_seconds: int = 7200,
) -> None:
    """Descarga un modelo mediante la API local con progreso real."""
    progress = progress or (lambda _value, _message: None)
    log = log or (lambda _message: None)
    response = requests.post(
        f"{base_url.rstrip('/')}/api/pull",
        json={"model": model, "stream": True},
        stream=True,
        timeout=(30, timeout_seconds),
    )
    response.raise_for_status()

    last_percent = -1
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))
        status = str(payload.get("status") or "Preparando componentes")
        total = int(payload.get("total") or 0)
        completed = int(payload.get("completed") or 0)
        if total > 0:
            percent = max(0, min(100, int(completed * 100 / total)))
        elif status.lower() == "success":
            percent = 100
        else:
            percent = max(last_percent, 1)
        if percent != last_percent:
            progress(percent, status)
            last_percent = percent
        log(status)

    progress(100, "Componente preparado")


def pull_model(model: str, log: LogCallback | None = None) -> int:
    """Compatibilidad con la interfaz anterior mediante la línea de comandos."""
    log = log or (lambda _message: None)
    executable = find_ollama_executable()
    if not executable:
        raise FileNotFoundError(
            "No se encontró el componente de procesamiento local. "
            "Use la opción 'Reparar componentes'."
        )

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        [str(executable), "pull", model],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creationflags,
        env=_managed_environment(executable),
    )
    assert process.stdout is not None
    for line in process.stdout:
        text = line.strip()
        if text:
            log(text)
    return process.wait()
