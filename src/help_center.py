from __future__ import annotations

import re
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from src.runtime_paths import install_root, resource_path
from src.ui_state import configure_resizable_window

TOPICS = {
    "maestro": ("Manual maestro", "Manual_Maestro_2.3.3.md"),
    "usuario": ("Manual de usuario", "Manual_Usuario_2.3.3.md"),
    "configuracion": ("Manual de instalación y configuración", "Manual_Configuracion_2.3.3.md"),
    "procesamiento": ("Reuniones extensas y recuperación", "PROCESAMIENTO_RESILIENTE_2.3.3.md"),
    "productividad": ("Atajos y productividad", "QOL_TECLADO_Y_TABLAS_2.3.4.md"),
    "programador": ("Guía del programador y depuración", "Manual_Programador_2.3.3.md"),
}


def _docs_root() -> Path:
    installed = install_root() / "docs"
    if installed.is_dir():
        return installed
    return resource_path("docs")


def _markdown_to_readable_text(markdown: str) -> str:
    text = re.sub(r"```[^\n]*\n", "", markdown)
    text = text.replace("```", "")
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text.strip()


class HelpCenter(tk.Toplevel):
    def __init__(self, parent: tk.Misc, initial_topic: str = "usuario") -> None:
        super().__init__(parent)
        self.title("Centro de ayuda - Minutas ASH")
        configure_resizable_window(self, parent, "help_center", "1040x780", (760, 520))
        self.topic_var = tk.StringVar(value=initial_topic if initial_topic in TOPICS else "usuario")
        self.search_var = tk.StringVar()
        self.current_text = ""
        self._build()
        self._load_topic()

    def _build(self) -> None:
        header = ttk.Frame(self, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="Centro de ayuda", style="Title.TLabel").pack(side="left")
        search = ttk.Entry(header, textvariable=self.search_var, width=34)
        search.pack(side="right")
        search.bind("<Return>", lambda _event: self._search())
        ttk.Button(header, text="Buscar", command=self._search).pack(side="right", padx=6)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        navigation = ttk.Frame(body, padding=8)
        content = ttk.Frame(body, padding=8)
        body.add(navigation, weight=1)
        body.add(content, weight=5)

        ttk.Label(navigation, text="Contenido", style="Section.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        for key, (label, _file) in TOPICS.items():
            ttk.Radiobutton(
                navigation,
                text=label,
                variable=self.topic_var,
                value=key,
                command=self._load_topic,
            ).pack(anchor="w", fill="x", pady=3)
        ttk.Separator(navigation).pack(fill="x", pady=12)
        ttk.Button(navigation, text="Abrir archivo externo", command=self._open_external).pack(
            fill="x"
        )
        ttk.Button(navigation, text="Cerrar", command=self.destroy).pack(fill="x", pady=(8, 0))

        self.title_var = tk.StringVar()
        ttk.Label(content, textvariable=self.title_var, style="Section.TLabel").pack(
            anchor="w", pady=(0, 8)
        )
        self.text = ScrolledText(content, wrap="word", font=("Segoe UI", 10), padx=12, pady=12)
        self.text.pack(fill="both", expand=True)
        self.text.tag_configure("match", background="#FFF2CC")
        self.text.configure(state="disabled")

    def _topic_path(self) -> Path:
        return _docs_root() / TOPICS[self.topic_var.get()][1]

    def _load_topic(self) -> None:
        label, _name = TOPICS[self.topic_var.get()]
        self.title_var.set(label)
        path = self._topic_path()
        try:
            markdown = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            markdown = f"No fue posible abrir la documentación.\n\n{exc}\n\nRuta esperada: {path}"
        self.current_text = _markdown_to_readable_text(markdown)
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.current_text)
        self.text.configure(state="disabled")
        self.search_var.set("")

    def _search(self) -> None:
        term = self.search_var.get().strip()
        self.text.configure(state="normal")
        self.text.tag_remove("match", "1.0", "end")
        if term:
            start = "1.0"
            first = None
            while True:
                index = self.text.search(term, start, stopindex="end", nocase=True)
                if not index:
                    break
                end = f"{index}+{len(term)}c"
                self.text.tag_add("match", index, end)
                first = first or index
                start = end
            if first:
                self.text.see(first)
        self.text.configure(state="disabled")

    def _open_external(self) -> None:
        webbrowser.open(self._topic_path().resolve().as_uri())


def open_help_center(parent: tk.Misc, topic: str = "usuario") -> HelpCenter:
    window = HelpCenter(parent, topic)
    window.grab_set()
    return window
