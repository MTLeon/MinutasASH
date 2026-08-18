from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from src.ui_state import configure_resizable_window


class ManualSourceDialog(tk.Toplevel):
    """Captura simple de una conversación copiada o notas estructuradas."""

    def __init__(self, parent: tk.Misc, default_name: str = "reunion") -> None:
        super().__init__(parent)
        self.title("Ingresar contenido de la reunión")
        configure_resizable_window(self, parent, "manual_source", "900x700", (720, 520))
        self.grab_set()
        self.result: dict | None = None

        shell = ttk.Frame(self, padding=16)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)

        ttk.Label(shell, text="Fuente manual de la reunión", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            shell,
            text=(
                "Use esta opción cuando Teams permite visualizar el contenido, pero no descargar el VTT. "
                "Puede pegar la conversación, el resumen de Teams o notas tomadas durante la reunión."
            ),
            wraplength=810,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 12))

        options = ttk.Frame(shell)
        options.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        options.columnconfigure(3, weight=1)
        self.source_type_var = tk.StringVar(value="pasted")
        ttk.Radiobutton(
            options,
            text="Conversación pegada",
            variable=self.source_type_var,
            value="pasted",
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            options,
            text="Notas o resumen",
            variable=self.source_type_var,
            value="notes",
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))
        ttk.Label(options, text="Nombre de referencia").grid(
            row=0, column=2, sticky="e", padx=(24, 8)
        )
        self.name_var = tk.StringVar(value=default_name)
        ttk.Entry(options, textvariable=self.name_var).grid(row=0, column=3, sticky="ew")

        editor_box = ttk.LabelFrame(shell, text="Contenido", padding=10)
        editor_box.grid(row=3, column=0, sticky="nsew")
        editor_box.rowconfigure(0, weight=1)
        editor_box.columnconfigure(0, weight=1)
        self.editor = ScrolledText(editor_box, wrap="word", undo=True)
        self.editor.grid(row=0, column=0, sticky="nsew")
        self.editor.insert(
            "1.0",
            "[00:04:35] Nombre Apellido: Texto de la intervención.\n\n"
            "Nombre Apellido: También puede omitir la marca de tiempo.\n\n"
            "Acuerdo: Describa aquí una decisión cuando solo disponga de notas.\n"
            "Compromiso: Responsable — acción — plazo.\n"
            "Pendiente: Información o definición por confirmar.\n",
        )
        self.editor.tag_add("sel", "1.0", "end")
        self.editor.focus_set()

        ttk.Label(
            shell,
            text=(
                "Recomendación: conserve el nombre del hablante antes de dos puntos. Las marcas de tiempo son "
                "opcionales. La aplicación guardará esta fuente localmente y exigirá una revisión reforzada."
            ),
            wraplength=810,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=4, column=0, sticky="ew", pady=(10, 0))

        buttons = ttk.Frame(shell)
        buttons.grid(row=5, column=0, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Usar este contenido", command=self._accept).pack(
            side="right", padx=(0, 8)
        )

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-Return>", lambda _event: self._accept())

    def _accept(self) -> None:
        text = self.editor.get("1.0", "end").strip()
        if len(text) < 8:
            messagebox.showwarning(
                "Contenido insuficiente",
                "Pegue la conversación o escriba las notas de la reunión.",
                parent=self,
            )
            return
        self.result = {
            "source_type": self.source_type_var.get(),
            "name": self.name_var.get().strip() or "reunion",
            "text": text,
        }
        self.destroy()
