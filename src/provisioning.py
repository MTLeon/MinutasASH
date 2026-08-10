from __future__ import annotations

import contextlib
import json
import queue
import shutil
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import cast

from src.ollama_client import OllamaClient
from src.ollama_manager import (
    api_available,
    ensure_runtime,
    find_ollama_executable,
    pull_model_stream,
    start_ollama,
)
from src.runtime_paths import (
    ensure_user_directories,
    managed_models_dir,
    resource_path,
    setup_state_path,
    user_data_root,
)
from src.settings import load_settings_dict, read_default_settings
from src.storage_policy import local_runtime_required, required_free_space_bytes
from src.ui_state import configure_resizable_window


class ProvisioningError(RuntimeError):
    pass


def read_default_config() -> dict:
    return read_default_settings().as_dict()


def setup_is_complete(config: dict | None = None) -> bool:
    config = config or load_settings_dict()
    if not local_runtime_required(config):
        return True
    state = setup_state_path()
    if not state.exists():
        return False
    try:
        payload = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if payload.get("model") != config.get("model"):
        return False
    if not bool(payload.get("completed", True)):
        return False
    runtime_mode = str(config.get("runtime_mode", "auto"))
    # La comprobación de inicio no levanta procesos externos; Ollama se inicia al procesar.
    return find_ollama_executable(runtime_mode) is not None


def write_setup_state(config: dict) -> None:
    path = setup_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    executable = find_ollama_executable(str(config.get("runtime_mode", "auto")))
    path.write_text(
        json.dumps(
            {
                "completed": True,
                "app_version": config.get("app_version"),
                "model": config.get("model"),
                "runtime": str(executable) if executable else None,
                "models_dir": str(managed_models_dir()),
                "completed_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


class ProvisioningWizard(tk.Tk):
    """Preparación inicial visible sin exponer detalles de implementación."""

    def __init__(self, config: dict, launch_after: bool = False) -> None:
        super().__init__()
        ensure_user_directories()
        self.config_data = config
        self.launch_after = launch_after
        self.result_code = 1
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.running = False

        self.title("Configuración inicial de Minutas ASH")
        with contextlib.suppress(tk.TclError, OSError):
            self.iconbitmap(str(resource_path("assets/ash.ico")))
        configure_resizable_window(self, None, "provisioning", "720x520", (640, 440), transient=False)
        self.protocol("WM_DELETE_WINDOW", self._close)

        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("WizardTitle.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("WizardSubtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))

        outer = ttk.Frame(self, padding=22)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        logo = resource_path("assets/logo_ash.png")
        self.logo_image: tk.PhotoImage | None
        try:
            self.logo_image = tk.PhotoImage(file=str(logo)).subsample(3, 3)
            ttk.Label(header, image=self.logo_image).pack(side="left", padx=(0, 16))
        except tk.TclError:
            self.logo_image = None
        title_box = ttk.Frame(header)
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text="Minutas ASH", style="WizardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Preparación inicial del entorno local",
            style="WizardSubtitle.TLabel",
        ).pack(anchor="w")

        ttk.Separator(outer).pack(fill="x", pady=18)
        self.message_var = tk.StringVar(
            value=(
                "La aplicación verificará y preparará automáticamente los componentes "
                "necesarios. Este proceso se realiza una sola vez y puede requerir "
                "conexión a Internet y varios minutos."
            )
        )
        ttk.Label(
            outer,
            textvariable=self.message_var,
            wraplength=610,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(fill="x", pady=(0, 16))

        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(outer, maximum=100, variable=self.progress_var)
        self.progress.pack(fill="x", pady=8)
        self.status_var = tk.StringVar(value="Listo para comenzar")
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")

        self.details = tk.Text(
            outer,
            height=8,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 9),
            relief="flat",
            background=self.cget("background"),
        )
        self.details.pack(fill="both", expand=True, pady=(12, 0))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(14, 0))
        self.cancel_button = ttk.Button(buttons, text="Cancelar", command=self._close)
        self.cancel_button.pack(side="right")
        self.start_button = ttk.Button(
            buttons,
            text="Preparar aplicación",
            style="Primary.TButton",
            command=self.start,
        )
        self.start_button.pack(side="right", padx=(0, 8))

        self.after(150, self._poll)
        self.after(300, self._autostart_if_ready)

    def _autostart_if_ready(self) -> None:
        if self.launch_after:
            self.start()

    def _append(self, text: str) -> None:
        self.details.configure(state="normal")
        self.details.insert("end", text.rstrip() + "\n")
        self.details.see("end")
        self.details.configure(state="disabled")

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.progress_var.set(2)
        self.status_var.set("Verificando el equipo...")

        def worker() -> None:
            try:
                base_url = str(self.config_data.get("ollama_base_url", "http://127.0.0.1:11434"))
                model = str(self.config_data.get("model", "qwen3:8b"))
                runtime_mode = str(self.config_data.get("runtime_mode", "auto"))

                if not local_runtime_required(self.config_data):
                    write_setup_state(self.config_data)
                    self.worker_queue.put(("complete", None))
                    return

                api_ready = api_available(base_url)
                model_installed = False
                if api_ready:
                    probe = OllamaClient(base_url, model)
                    model_installed = model in probe.list_models()

                free_bytes = shutil.disk_usage(user_data_root()).free
                required_bytes = required_free_space_bytes(
                    self.config_data,
                    api_ready=api_ready,
                    model_installed=model_installed,
                )
                if free_bytes < required_bytes:
                    raise ProvisioningError(
                        "No hay espacio suficiente para completar la preparación. "
                        f"Se requieren al menos {required_bytes / 1024**3:.0f} GB libres y hay "
                        f"{free_bytes / 1024**3:.1f} GB disponibles."
                    )

                if not api_ready:
                    self.worker_queue.put(("status", (5, "Preparando componentes locales...")))

                    def runtime_progress(value: int, text: str) -> None:
                        mapped = 5 + int(value * 0.25)
                        self.worker_queue.put(("status", (mapped, text)))

                    ensure_runtime(
                        self.config_data,
                        progress=runtime_progress,
                        log=lambda m: self.worker_queue.put(("log", m)),
                    )

                self.worker_queue.put(("status", (31, "Iniciando servicio local...")))
                if not start_ollama(
                    base_url,
                    log=lambda m: self.worker_queue.put(("log", m)),
                    runtime_mode=runtime_mode,
                    wait_seconds=45,
                ):
                    raise ProvisioningError(
                        "No fue posible iniciar el servicio local. Reinicie Windows y use "
                        "'Reparar componentes' si el problema continúa."
                    )

                client = OllamaClient(
                    base_url,
                    model,
                    int(self.config_data.get("timeout_seconds", 1200)),
                    float(self.config_data.get("temperature", 0.05)),
                    int(self.config_data.get("context_length", 8192)),
                    str(self.config_data.get("keep_alive", "30m")),
                )
                installed = client.list_models()
                if model not in installed:
                    self.worker_queue.put(("status", (35, "Descargando perfil de procesamiento...")))
                    self.worker_queue.put(("log", "Descarga inicial en curso. No cierre esta ventana."))

                    def model_progress(value: int, _text: str) -> None:
                        mapped = 35 + int(value * 0.57)
                        self.worker_queue.put((
                            "status",
                            (mapped, f"Preparando perfil de procesamiento... {value}%"),
                        ))

                    pull_model_stream(
                        base_url,
                        model,
                        progress=model_progress,
                        log=lambda _m: None,
                    )

                self.worker_queue.put(("status", (94, "Verificando funcionamiento...")))
                client.check_connection()
                client.warmup()
                write_setup_state(self.config_data)
                self.worker_queue.put(("complete", None))
            except Exception as exc:
                self.worker_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.worker_queue.get_nowait()
                if kind == "status":
                    value, text = cast(tuple[int, str], payload)
                    self.progress_var.set(int(value))
                    self.status_var.set(str(text))
                elif kind == "log":
                    self._append(str(payload))
                elif kind == "complete":
                    self.progress_var.set(100)
                    self.status_var.set("Configuración completada")
                    self.message_var.set(
                        "La aplicación quedó preparada correctamente y ya puede utilizarse."
                    )
                    self.result_code = 0
                    self.running = False
                    self.cancel_button.configure(text="Finalizar", state="normal", command=self._finish)
                    self.start_button.pack_forget()
                    if self.launch_after:
                        self.after(900, self._finish)
                elif kind == "error":
                    self.running = False
                    self.status_var.set("No fue posible completar la configuración")
                    self._append(f"Error: {payload}")
                    self.start_button.configure(text="Reintentar", state="normal")
                    self.cancel_button.configure(state="normal")
                    messagebox.showerror(
                        "Configuración incompleta",
                        str(payload),
                        parent=self,
                    )
        except queue.Empty:
            pass
        self.after(150, self._poll)

    def _finish(self) -> None:
        self.destroy()

    def _close(self) -> None:
        if self.running:
            return
        self.destroy()


def run_provisioning(config: dict | None = None, launch_after: bool = False) -> int:
    wizard = ProvisioningWizard(config or load_settings_dict(), launch_after=launch_after)
    wizard.mainloop()
    return wizard.result_code
