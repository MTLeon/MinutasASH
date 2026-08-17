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
FILTER_LABELS = {
    "Todos": None,
    "Activos": {"queued", "running"},
    "Reintentables": {"failed", "cancelled", "interrupted"},
    "Con error": {"failed"},
    "Interrumpidos": {"interrupted"},
    "Finalizados": {"completed", "cancelled", "failed"},
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
        self.diagnostic_var = tk.StringVar(value="Diagnóstico pendiente")
        self.filter_var = tk.StringVar(value="Todos")
        self.detail_var = tk.StringVar(
            value="Seleccione una ejecución para ver su fuente, modelo y acción recomendada."
        )
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

        toolbar = ttk.Frame(root)
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 8))
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(toolbar, textvariable=self.diagnostic_var, style="Muted.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(toolbar, text="Mostrar:").grid(row=0, column=1, padx=(12, 4))
        filter_combo = ttk.Combobox(
            toolbar,
            textvariable=self.filter_var,
            values=tuple(FILTER_LABELS),
            state="readonly",
            width=16,
        )
        filter_combo.grid(row=0, column=2, sticky="e")
        filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())

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
        self.tree.tag_configure("running", foreground="#1769aa")
        self.tree.tag_configure("queued", foreground="#735d00")
        self.tree.tag_configure("interrupted", foreground="#b66a00")
        self.tree.tag_configure("failed", foreground="#b42318")
        self.tree.tag_configure("cancelled", foreground="#6b7280")
        self.tree.tag_configure("completed", foreground="#147a46")
        self.tree.bind("<<TreeviewSelect>>", self._show_selected_detail)
        self.tree.bind("<Delete>", lambda _event: self.discard_selected())
        self.tree.bind("<Control-r>", lambda _event: self.retry_selected())
        self.tree.bind("<Control-R>", lambda _event: self.retry_selected())
        self.tree.bind("<F5>", lambda _event: self.refresh())

        details = ttk.LabelFrame(root, text="Detalle de la ejecución", padding=(10, 7))
        details.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        details.columnconfigure(0, weight=1)
        ttk.Label(details, textvariable=self.detail_var, justify="left", wraplength=880).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Label(root, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=4, column=0, sticky="w", pady=(8, 0)
        )

    def refresh(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        all_jobs = self.store.list(limit=100)
        allowed = FILTER_LABELS.get(self.filter_var.get())
        jobs = [job for job in all_jobs if allowed is None or job.status in allowed]
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
                tags=(job.status,),
            )
        retryable = sum(is_retryable_status(job.status) for job in all_jobs)
        discardable = sum(job.status in {"queued", "interrupted"} for job in all_jobs)
        self.status_var.set(
            f"{len(jobs)} de {len(all_jobs)} ejecución(es) · {retryable} reintentable(s) · "
            f"{discardable} pendiente(s) que puede retirar."
        )
        self._show_selected_detail()

    def _show_selected_detail(self, _event=None) -> None:
        selection = self.tree.selection()
        if len(selection) != 1:
            self.detail_var.set(
                "Seleccione una ejecución para ver su fuente, modelo y acción recomendada."
            )
            return
        job = self.store.get(selection[0])
        if job is None:
            self.detail_var.set("La ejecución ya no está disponible; actualice la lista.")
            return
        source = Path(job.source_path)
        source_state = "disponible" if source.is_file() else "no encontrada"
        action = (
            "Puede reintentarse y recuperar el checkpoint compatible."
            if is_retryable_status(job.status) and source.is_file()
            else (
                "Puede retirarse de la cola sin borrar su fuente."
                if job.status in {"queued", "interrupted"}
                else "No requiere acción; use la limpieza de historial cuando corresponda."
            )
        )
        detail = job.error or job.message or "Sin detalle adicional."
        self.detail_var.set(
            f"Fuente: {source.name} ({source_state}) · Proveedor: "
            f"{provider_display_name(job.provider_id)} · Modelo: {job.model or 'sin especificar'} · "
            f"Avance: {job.progress} %.\n{detail}\n{action}"
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
