from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from src.processing_jobs import ProcessingJobStore, is_retryable_status
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
    def __init__(
        self,
        parent: tk.Misc,
        settings: dict[str, Any],
        *,
        on_retry: Callable[[Path], tuple[bool, str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Centro de procesamiento")
        configure_resizable_window(self, parent, "processing_center", "980x590", (760, 460))
        self.settings = dict(settings)
        self.on_retry = on_retry
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
        ttk.Button(heading, text="Reintentar", command=self.retry_selected).grid(
            row=0, column=3, padx=(8, 0)
        )
        ttk.Button(heading, text="Quitar pendientes", command=self.discard_selected).grid(
            row=0, column=4, padx=(8, 0)
        )
        ttk.Button(heading, text="Limpiar finalizados", command=self.prune_finalized).grid(
            row=0, column=5, padx=(8, 0)
        )
        ttk.Button(heading, text="Cerrar", command=self.destroy).grid(row=0, column=6, padx=(8, 0))

        ttk.Label(root, textvariable=self.diagnostic_var).grid(
            row=1, column=0, sticky="w", pady=(10, 8)
        )

        columns = ("updated", "status", "source", "provider", "progress", "message")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", selectmode="extended")
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
        self.tree.bind("<Delete>", lambda _event: self.discard_selected())
        self.tree.bind("<Control-r>", lambda _event: self.retry_selected())
        self.tree.bind("<Control-R>", lambda _event: self.retry_selected())
        self.tree.bind("<F5>", lambda _event: self.refresh())
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
        retryable = sum(is_retryable_status(job.status) for job in jobs)
        discardable = sum(job.status in {"queued", "interrupted"} for job in jobs)
        self.status_var.set(
            f"{len(jobs)} ejecución(es) reciente(s) · {retryable} reintentable(s) · "
            f"{discardable} pendiente(s) que puede retirar."
        )

    def retry_selected(self) -> None:
        selection = self.tree.selection()
        if len(selection) != 1:
            messagebox.showinfo(
                "Reintentar proceso",
                "Seleccione exactamente un proceso cancelado, interrumpido o con error.",
                parent=self,
            )
            return
        job = self.store.get(selection[0])
        if job is None:
            self.refresh()
            messagebox.showwarning(
                "Reintentar proceso",
                "El proceso ya no está disponible. Se actualizó la lista.",
                parent=self,
            )
            return
        if not is_retryable_status(job.status):
            messagebox.showwarning(
                "Reintentar proceso",
                "Solo se pueden reintentar procesos cancelados, interrumpidos o con error.",
                parent=self,
            )
            return
        source = Path(job.source_path)
        if not source.is_file():
            messagebox.showwarning(
                "Reintentar proceso",
                "No se encontró la fuente original. El registro se conserva, pero no puede reanudarse.",
                parent=self,
            )
            return
        if self.on_retry is None:
            messagebox.showwarning(
                "Reintentar proceso",
                "Esta ventana no está conectada a una sesión de Minutas ASH para iniciar el reintento.",
                parent=self,
            )
            return
        if not messagebox.askyesno(
            "Reintentar proceso",
            "Se iniciará una nueva ejecución usando la misma fuente. Los bloques ya guardados "
            "en el checkpoint se recuperarán cuando sean compatibles.\n\n¿Continuar?",
            parent=self,
        ):
            return
        started, detail = self.on_retry(source)
        if not started:
            messagebox.showwarning("Reintentar proceso", detail, parent=self)
            return
        self.store.update(job.job_id, message="Reintento iniciado desde el centro de procesamiento")
        self.refresh()
        self.status_var.set(detail)

    def discard_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(
                "Quitar pendientes",
                "Seleccione uno o más procesos en espera o interrumpidos.",
                parent=self,
            )
            return
        jobs = [job for item_id in selection if (job := self.store.get(item_id)) is not None]
        if len(jobs) != len(selection):
            self.refresh()
            messagebox.showwarning(
                "Quitar pendientes",
                "La lista cambió antes de completar la acción. Revísela e inténtelo nuevamente.",
                parent=self,
            )
            return
        invalid = [job for job in jobs if job.status not in {"queued", "interrupted"}]
        if invalid:
            messagebox.showwarning(
                "Quitar pendientes",
                "Solo se pueden quitar procesos en espera o interrumpidos. "
                "Los procesos activos deben cancelarse desde la ventana principal.",
                parent=self,
            )
            return
        count = len(jobs)
        if not messagebox.askyesno(
            "Quitar pendientes",
            f"Se quitarán {count} proceso(s) pendiente(s) de la cola.\n\n"
            "No se eliminarán los archivos de origen. ¿Continuar?",
            parent=self,
        ):
            return
        removed = sum(self.store.discard_recoverable(job.job_id) for job in jobs)
        self.refresh()
        if removed == count:
            self.status_var.set(f"Se retiraron {removed} proceso(s) pendiente(s) de la cola.")
        else:
            messagebox.showwarning(
                "Quitar pendientes",
                f"Se retiraron {removed} de {count} proceso(s); los restantes cambiaron de estado.",
                parent=self,
            )

    def prune_finalized(self) -> None:
        if not messagebox.askyesno(
            "Limpiar historial",
            "Se conservarán los 100 trabajos finalizados más recientes y todos los trabajos en espera, activos o interrumpidos. ¿Continuar?",
            parent=self,
        ):
            return
        removed = self.store.prune_finalized(keep=100, max_age_days=30)
        self.refresh()
        self.status_var.set(f"Se eliminaron {removed} ejecucion(es) finalizada(s) antiguas.")

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
