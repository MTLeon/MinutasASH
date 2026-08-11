from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from collections.abc import Callable
from functools import partial
from tkinter import messagebox, ttk

from src.transcription_components import MODELS, default_model_cache, diagnose, worker_path
from src.ui_state import configure_resizable_window


class TranscriptionComponentsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, settings: dict, on_save: Callable[[dict], None]) -> None:
        super().__init__(parent)
        self.title("Componentes opcionales de transcripción")
        configure_resizable_window(self, parent, "transcription_components", "700x480", (620, 420))
        self.settings = settings
        self.on_save = on_save
        self.model_var = tk.StringVar(value=str(settings.get("whisper_model", "base")))
        self.language_var = tk.StringVar(value=str(settings.get("transcription_language", "es")))
        self.status_var = tk.StringVar()
        self.detail_var = tk.StringVar()
        self.progress: ttk.Progressbar
        self._build()
        self._refresh()
        self.transient(parent)  # type: ignore[call-overload]
        self.grab_set()

    def _build(self) -> None:
        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        self.progress = ttk.Progressbar(body, mode="indeterminate")
        ttk.Label(body, text="Transcripción local", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            body,
            text="Whisper puede seleccionarse como componente opcional durante la instalación.",
            style="Muted.TLabel",
            wraplength=620,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 16))
        ttk.Label(body, text="Estado").grid(row=2, column=0, sticky="nw", padx=(0, 14), pady=6)
        ttk.Label(body, textvariable=self.status_var, wraplength=500, justify="left").grid(
            row=2, column=1, sticky="w", pady=6
        )
        ttk.Label(body, text="Modelo").grid(row=3, column=0, sticky="w", padx=(0, 14), pady=6)
        combo = ttk.Combobox(
            body, textvariable=self.model_var, values=list(MODELS), state="readonly"
        )
        combo.grid(row=3, column=1, sticky="ew", pady=6)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh())
        ttk.Label(body, text="Idioma").grid(row=4, column=0, sticky="w", padx=(0, 14), pady=6)
        ttk.Combobox(
            body, textvariable=self.language_var, values=("es", "en", "auto"), state="readonly"
        ).grid(row=4, column=1, sticky="ew", pady=6)
        ttk.Label(
            body, textvariable=self.detail_var, style="Muted.TLabel", wraplength=560, justify="left"
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 8))
        self.progress.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(4, 14))
        actions = ttk.Frame(body)
        actions.grid(row=7, column=0, columnspan=2, sticky="ew")
        self.download_button = ttk.Button(actions, text="Descargar modelo", command=self._download)
        self.download_button.pack(side="left")
        ttk.Button(actions, text="Actualizar diagnóstico", command=self._refresh).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="Guardar", style="Primary.TButton", command=self._save).pack(
            side="right"
        )
        ttk.Button(actions, text="Cerrar", command=self.destroy).pack(side="right", padx=8)

    def _refresh(self) -> None:
        model = self.model_var.get() if self.model_var.get() in MODELS else "base"
        info = MODELS[model]  # type: ignore[index]
        state = diagnose(model, cache_dir=default_model_cache())  # type: ignore[arg-type]
        engine = "disponible" if state.engine_available else "no instalado"
        downloaded = "descargado" if state.model_downloaded else "pendiente de descarga"
        self.status_var.set(f"Motor faster-whisper: {engine}. Modelo {model}: {downloaded}.")
        self.detail_var.set(
            f"{info.description} Descarga aproximada: {info.download_mb} MB. "
            f"Memoria recomendada: {info.recommended_ram_gb} GB. Caché: {state.model_cache}"
        )
        self.download_button.configure(state="normal" if state.engine_available else "disabled")

    def _download(self) -> None:
        model_name = self.model_var.get()
        info = MODELS[model_name]  # type: ignore[index]
        if not messagebox.askyesno(
            "Descargar modelo",
            f"Se descargarán aproximadamente {info.download_mb} MB para Whisper {model_name}. ¿Continuar?",
            parent=self,
        ):
            return
        self.download_button.configure(state="disabled")
        self.progress.start(12)

        def worker() -> None:
            try:
                executable = worker_path()
                if executable.is_file():
                    completed = subprocess.run(
                        [str(executable), "--download-only", "--model", model_name],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=7200,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    if completed.returncode:
                        raise RuntimeError(
                            completed.stderr.strip() or "No fue posible descargar el modelo."
                        )
                else:
                    from faster_whisper import WhisperModel  # type: ignore[import-not-found]

                    WhisperModel(
                        model_name,
                        device="cpu",
                        compute_type="int8",
                        download_root=str(default_model_cache()),
                    )
                self.after(0, lambda: self._download_done(None))
            except Exception as exc:
                self.after(0, partial(self._download_done, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _download_done(self, error: Exception | None) -> None:
        self.progress.stop()
        if error:
            messagebox.showerror("Modelo Whisper", str(error), parent=self)
        else:
            messagebox.showinfo(
                "Modelo Whisper", "El modelo quedó disponible sin conexión.", parent=self
            )
        self._refresh()

    def _save(self) -> None:
        payload = dict(self.settings)
        payload["whisper_model"] = self.model_var.get()
        payload["transcription_language"] = (
            "" if self.language_var.get() == "auto" else self.language_var.get()
        )
        self.on_save(payload)
        self.destroy()


def open_transcription_components(
    parent: tk.Misc, settings: dict, on_save: Callable[[dict], None]
) -> None:
    TranscriptionComponentsDialog(parent, settings, on_save)
