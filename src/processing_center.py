from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any

from src.processing_jobs import ProcessingJobStore
from src.provider_diagnostics import ProviderDiagnostic, diagnose_provider
from src.providers.registry import provider_display_name
from src.ui_state import configure_resizable_window

STATUS_LABELS = {
    "queued": "En espera",
    "running": "En proceso",
    "completed": "Completado",
    "failed": "Con error",
    "cancelled": "Cancelado",
    "interrupted": "Interrumpido",
}


class ProcessingCenterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, settings: dict[str, Any]) -> None:
        super().__init__(parent)
        self.title("Centro de procesamiento")
        configure_resizable_window(self, parent, "processing_center", "980x590", (760, 460))
        self.settings = dict(settings)
        self.store = ProcessingJobStore()
        self.status_var = tk.StringVar(value="Historial de ejecuciones y estado del proveedor.")
        self.diagnostic_var = tk.StringVar(value="Diagnostico pendiente")
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.grid(sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        root.columnconfigure(0, weight=1)

        heading = ttk.Frame(root)
        heading.grid(row=0, column=0, sticky="ew")
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Centro de procesamiento", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(heading, text="Verificar proveedor", command=self.check_provider).grid(
            row=0, column=1, padx=(8, 0)
        )
        ttk.Button(heading, text="Actualizar", command=self.refresh).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Button(heading, text="Cerrar", command=self.destroy).grid(row=0, column=3, padx=(8, 0))

        ttk.Label(root, textvariable=self.diagnostic_var).grid(
            row=1, column=0, sticky="w", pady=(10, 8)
        )

        columns = ("updated", "status", "source", "provider", "progress", "message")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")
        headings = {
            "updated": "Actualizado",
            "status": "Estado",
            "source": "Fuente",
            "provider": "Proveedor",
            "progress": "Avance",
            "message": "Detalle",
        }
        widths = {
            "updated": 145,
            "status": 105,
            "source": 170,
            "provider": 150,
            "progress": 75,
            "message": 260,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column, width=widths[column], minwidth=65, stretch=column in {"source", "message"}
            )
        self.tree.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        ttk.Label(root, textvariable=self.status_var).grid(row=3, column=0, sticky="w", pady=(8, 0))

    def refresh(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        jobs = self.store.list(limit=100)
        for job in jobs:
            updated = job.updated_at.replace("T", " ")[:19]
            self.tree.insert(
                "",
                "end",
                iid=job.job_id,
                values=(
                    updated,
                    STATUS_LABELS.get(job.status, job.status),
                    Path(job.source_path).name,
                    provider_display_name(job.provider_id),
                    f"{job.progress} %",
                    job.error or job.message,
                ),
            )
        self.status_var.set(f"{len(jobs)} ejecucion(es) reciente(s).")

    def check_provider(self) -> None:
        self.diagnostic_var.set("Verificando proveedor...")
        threading.Thread(target=self._diagnostic_worker, daemon=True).start()

    def _diagnostic_worker(self) -> None:
        diagnostic = diagnose_provider(self.settings)
        self.after(0, self._show_diagnostic, diagnostic)

    def _show_diagnostic(self, diagnostic: ProviderDiagnostic) -> None:
        state = "Disponible" if diagnostic.status == "ready" else "No disponible"
        location = "local" if diagnostic.capabilities.get("offline") else "remoto"
        self.diagnostic_var.set(
            f"{state}: {diagnostic.display_name} / {diagnostic.model} "
            f"({location}, {diagnostic.latency_ms} ms). {diagnostic.message}"
        )
