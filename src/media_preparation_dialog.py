"""Decision explicita y segura para optimizar multimedia antes de Whisper."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk


@dataclass(frozen=True)
class MediaPreparationChoice:
    optimize: bool
    output_format: str = "m4a"
    delete_source: bool = False


class MediaPreparationDialog(tk.Toplevel):
    """Solicita la decision antes de tocar el archivo de origen."""

    def __init__(self, parent: tk.Tk, source_path: Path) -> None:
        super().__init__(parent)
        self.source_path = source_path
        self.result: MediaPreparationChoice | None = None
        self.title("Preparar audio para transcripcion")
        self.transient(parent)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.optimize_var = tk.BooleanVar(value=True)
        self.format_var = tk.StringVar(value="M4A")
        self.delete_source_var = tk.BooleanVar(value=False)
        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")
        ttk.Label(
            frame, text="Optimizar multimedia antes de transcribir", style="Title.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            frame,
            text=(
                "Se creara una copia de voz mono a 16 kHz. Reduce almacenamiento y la carga "
                "de Whisper para reuniones largas; no mejora una grabacion de baja calidad."
            ),
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 10))
        ttk.Label(frame, text=f"Fuente: {source_path.name}", style="Muted.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )
        ttk.Checkbutton(
            frame,
            text="Crear copia optimizada antes de transcribir",
            variable=self.optimize_var,
            command=self._refresh_state,
        ).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text="Formato de copia:").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.format_combo = ttk.Combobox(
            frame, textvariable=self.format_var, values=("M4A", "MP3"), state="readonly", width=12
        )
        self.format_combo.grid(row=4, column=1, sticky="w", pady=(10, 0))
        self.delete_check = ttk.Checkbutton(
            frame,
            text="Eliminar la fuente original despues de verificar la copia",
            variable=self.delete_source_var,
        )
        self.delete_check.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 14))
        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Continuar", command=self._continue).pack(
            side="right", padx=(0, 8)
        )
        self._refresh_state()
        self.grab_set()

    def _refresh_state(self) -> None:
        state = "readonly" if self.optimize_var.get() else "disabled"
        self.format_combo.configure(state=state)
        self.delete_check.configure(state="normal" if self.optimize_var.get() else "disabled")
        if not self.optimize_var.get():
            self.delete_source_var.set(False)

    def _continue(self) -> None:
        optimize = self.optimize_var.get()
        delete_source = optimize and self.delete_source_var.get()
        if delete_source and not messagebox.askyesno(
            "Confirmar eliminacion",
            "La fuente original se eliminara permanentemente solo despues de verificar la copia.\n\n"
            "Desea continuar?",
            parent=self,
        ):
            return
        self.result = MediaPreparationChoice(
            optimize=optimize,
            output_format=self.format_var.get().casefold(),
            delete_source=delete_source,
        )
        self.destroy()
