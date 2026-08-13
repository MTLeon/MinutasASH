from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Literal, cast

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import contextlib

from pydantic import ValidationError

from src.app_logging import get_logger
from src.appearance import AppearanceManager
from src.diagnostics import save_diagnostic_bundle
from src.metadata import enrich_attendees, initials_from_name
from src.models import Attendee, MeetingItem, MeetingMetadata, MinuteAnalysis
from src.observability import operation
from src.ollama_manager import (
    ensure_runtime,
    pull_model_stream,
    start_ollama,
)
from src.preferences import PreferencesDialog
from src.processing_jobs import JobStatus, ProcessingJobStore
from src.providers.registry import (
    configured_model,
    create_processing_provider,
    descriptor_for,
    provider_display_name,
)
from src.provisioning import run_provisioning, setup_is_complete
from src.repositories.factory import create_repository
from src.runtime_paths import (
    default_output_dir,
    drafts_dir,
    ensure_user_directories,
    install_root,
    logs_dir,
    resource_path,
    source_root,
    user_data_root,
)
from src.settings import load_settings_dict, save_settings_dict
from src.ui_state import configure_resizable_window
from src.updater import (
    UpdateInfo,
    check_for_updates,
    download_update,
    is_newer_version,
    launch_installer,
    should_check_now,
    write_update_record,
)
from src.vtt_reader import read_teams_vtt, unique_speakers
from src.workflow import AnalysisBundle, analyze_meeting, generate_word_package

APP_TITLE = "Minutas ASH 2.3.4"
DATE_HINT = "AAAA-MM-DD"


class AttendeeDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, attendee: Attendee | None = None) -> None:
        super().__init__(parent)
        self.title("Asistente")
        configure_resizable_window(self, parent, "attendee_dialog", "640x430", (520, 340))
        self.grab_set()
        self.result: Attendee | None = None
        self.vars = {
            "id": tk.StringVar(value=str(attendee.id or "") if attendee else ""),
            "initials": tk.StringVar(value=attendee.initials or "" if attendee else ""),
            "name": tk.StringVar(value=attendee.name if attendee else ""),
            "email": tk.StringVar(value=attendee.email or "" if attendee else ""),
            "role": tk.StringVar(value=attendee.role or "" if attendee else ""),
            "organization": tk.StringVar(
                value=attendee.organization or "ASH" if attendee else "ASH"
            ),
        }
        frame = ttk.Frame(self, padding=14)
        frame.grid(sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        labels = [
            ("Id", "id"),
            ("Iniciales", "initials"),
            ("Nombre *", "name"),
            ("Correo", "email"),
            ("Cargo", "role"),
            ("Organización", "organization"),
        ]
        for row, (label, key) in enumerate(labels):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
            entry = ttk.Entry(frame, textvariable=self.vars[key], width=45)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            if key == "name":
                entry.focus_set()
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(labels), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Guardar", command=self._save).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.wait_visibility()
        self.focus_force()

    def _save(self) -> None:
        name = self.vars["name"].get().strip()
        if not name:
            messagebox.showwarning(
                "Dato requerido", "Ingrese el nombre del asistente.", parent=self
            )
            return
        id_text = self.vars["id"].get().strip()
        try:
            attendee_id = int(id_text) if id_text else None
        except ValueError:
            messagebox.showwarning("Id inválido", "El Id debe ser numérico.", parent=self)
            return
        self.result = Attendee(
            id=attendee_id,
            initials=self.vars["initials"].get().strip() or initials_from_name(name),
            name=name,
            email=self.vars["email"].get().strip() or None,
            role=self.vars["role"].get().strip() or None,
            organization=self.vars["organization"].get().strip() or "Por confirmar",
        )
        self.destroy()


class ItemDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, item: MeetingItem | None = None) -> None:
        super().__init__(parent)
        self.title("Punto de minuta")
        configure_resizable_window(self, parent, "item_dialog", "760x600", (650, 480))
        self.grab_set()
        self.result: MeetingItem | None = None
        self._confidence = item.confidence if item else 0.80
        self.vars = {
            "category": tk.StringVar(value=item.category if item else "informativo"),
            "project_code": tk.StringVar(value=item.project_code or "" if item else ""),
            "title": tk.StringVar(value=item.title or "" if item else ""),
            "source_speaker": tk.StringVar(value=item.source_speaker or "" if item else ""),
            "responsible": tk.StringVar(value=item.responsible or "" if item else ""),
            "due_date_text": tk.StringVar(value=item.due_date_text or "" if item else ""),
            "due_date_iso": tk.StringVar(value=item.due_date_iso or "" if item else ""),
            "evidence": tk.StringVar(value=item.evidence or "" if item else ""),
        }
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Categoría").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.vars["category"],
            values=["informativo", "acuerdo", "compromiso", "pendiente"],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Título").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.vars["title"]).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Descripción *").grid(row=2, column=0, sticky="nw", pady=4)
        self.description = ScrolledText(frame, height=9, wrap="word", font=("Segoe UI", 10))
        self.description.grid(row=2, column=1, sticky="nsew", pady=4)
        self.description.insert("1.0", item.description if item else "")
        frame.rowconfigure(2, weight=1)

        rows = [
            ("Proyecto asociado", "project_code"),
            ("Hablante fuente", "source_speaker"),
            ("Responsable", "responsible"),
            ("Plazo mencionado", "due_date_text"),
            ("Fecha ISO", "due_date_iso"),
            ("Evidencia", "evidence"),
        ]
        for offset, (label, key) in enumerate(rows, start=3):
            ttk.Label(frame, text=label).grid(row=offset, column=0, sticky="w", pady=4)
            ttk.Entry(frame, textvariable=self.vars[key]).grid(
                row=offset, column=1, sticky="ew", pady=4
            )

        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Guardar", command=self._save).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _event: self.destroy())
        self.wait_visibility()
        self.focus_force()

    def _save(self) -> None:
        description = self.description.get("1.0", "end").strip()
        if not description:
            messagebox.showwarning("Dato requerido", "Ingrese una descripción.", parent=self)
            return
        due_iso = self.vars["due_date_iso"].get().strip() or None
        if due_iso:
            try:
                datetime.strptime(due_iso, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning(
                    "Fecha inválida", "La fecha ISO debe usar AAAA-MM-DD.", parent=self
                )
                return
        self.result = MeetingItem(
            project_code=self.vars["project_code"].get().strip() or None,
            category=cast(
                Literal["informativo", "acuerdo", "compromiso", "pendiente"],
                self.vars["category"].get(),
            ),
            title=self.vars["title"].get().strip() or None,
            description=description,
            source_speaker=self.vars["source_speaker"].get().strip() or None,
            responsible=self.vars["responsible"].get().strip() or None,
            due_date_text=self.vars["due_date_text"].get().strip() or None,
            due_date_iso=due_iso,
            evidence=self.vars["evidence"].get().strip() or None,
            confidence=self._confidence,
        )
        self.destroy()


class ContactPickerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, contacts: list[Attendee]) -> None:
        super().__init__(parent)
        self.title("Catálogo de contactos")
        configure_resizable_window(self, parent, "contact_picker", "800x500", (640, 360))
        self.grab_set()
        self.result: Attendee | None = None
        self.contacts = contacts
        self.search_var = tk.StringVar()

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        search = ttk.Frame(frame)
        search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(search, text="Buscar").pack(side="left")
        entry = ttk.Entry(search, textvariable=self.search_var)
        entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        entry.bind("<KeyRelease>", lambda _event: self._refresh())

        columns = ("name", "email", "role", "organization")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col, title, width in (
            ("name", "Nombre", 210),
            ("email", "Correo", 210),
            ("role", "Cargo", 190),
            ("organization", "Organización", 110),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self._accept())

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Agregar", command=self._accept).pack(side="right", padx=(0, 8))
        self._refresh()
        entry.focus_set()

    def _refresh(self) -> None:
        query = self.search_var.get().strip().casefold()
        self.tree.delete(*self.tree.get_children())
        for index, contact in enumerate(self.contacts):
            text = " ".join(
                filter(None, [contact.name, contact.email, contact.role, contact.organization])
            ).casefold()
            if query and query not in text:
                continue
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    contact.name,
                    contact.email or "",
                    contact.role or "",
                    contact.organization or "",
                ),
            )

    def _accept(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        self.result = self.contacts[int(selected[0])].model_copy(deep=True)
        self.destroy()


class ProjectPickerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, projects: list[dict]) -> None:
        super().__init__(parent)
        self.title("Catálogo de proyectos")
        configure_resizable_window(self, parent, "project_picker", "780x480", (620, 320))
        self.grab_set()
        self.result: dict | None = None
        self.projects = projects
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        columns = ("code", "description", "client")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column, title, width in (
            ("code", "Código", 110),
            ("description", "Descripción", 350),
            ("client", "Cliente", 210),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self._accept())
        for index, project in enumerate(projects):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    project.get("code") or "",
                    project.get("description") or "",
                    project.get("client") or "",
                ),
            )
        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Seleccionar", command=self._accept).pack(
            side="right", padx=(0, 8)
        )

    def _accept(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        self.result = self.projects[int(selected[0])]
        self.destroy()


class MinutasApp(tk.Tk):
    def __init__(self, initial_vtt: str | None = None) -> None:
        super().__init__()
        ensure_user_directories()
        self.logger = get_logger()
        self.processing_job_store = ProcessingJobStore(recover_on_open=True)
        self.config_data = self._load_config()
        self.appearance_manager = AppearanceManager(self)
        self.appearance_manager.apply(self.config_data)

        self.title(APP_TITLE)
        with contextlib.suppress(tk.TclError, OSError):
            self.iconbitmap(str(resource_path("assets/ash.ico")))
        saved_geometry = str(self.config_data.get("window_geometry") or "").strip()
        self.geometry(saved_geometry or "1180x790")
        self.minsize(1000, 700)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.db = create_repository(self.config_data)
        self.analysis_bundle: AnalysisBundle | None = None
        self.current_meeting_id: int | None = None
        self.cancel_requested = False
        self.last_docx: Path | None = None
        self.attendees: list[Attendee] = []
        self.items: list[MeetingItem] = []
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.record_is_test_var: tk.BooleanVar
        self.busy = False
        self.pending_update: UpdateInfo | None = None

        self._setup_style()
        self._create_variables()
        self._build_ui()
        self._apply_appearance(self.config_data)
        self.bind_all("<Control-o>", lambda _event: self.browse_vtt())
        self.bind_all("<F5>", lambda _event: self.start_analysis())
        self.bind_all("<Control-s>", lambda _event: self.generate_document())
        self.bind_all("<Control-comma>", lambda _event: self.open_preferences())
        self._load_default_metadata()
        self._load_autosave_draft()
        if initial_vtt:
            candidate = Path(initial_vtt).expanduser()
            if candidate.is_file() and candidate.suffix.lower() == ".vtt":
                self.vtt_var.set(str(candidate.resolve()))
        self._refresh_history_tree()
        self.after(150, self._poll_worker_queue)
        self.after(300, self.refresh_ollama_status)
        self.after(2500, self._check_updates_on_start)
        self.after(30000, self._autosave_tick)

    def _load_config(self) -> dict:
        return load_settings_dict()

    def _save_config(self) -> None:
        payload = dict(self.config_data)
        payload.update(
            {
                "ollama_base_url": self.ollama_url_var.get().strip(),
                "model": self.model_var.get().strip(),
                "output_dir": self.output_dir_var.get().strip(),
                "auto_add_transcript_speakers": self.auto_speakers_var.get(),
                "open_word_after_generation": self.open_word_var.get(),
            }
        )
        if bool(payload.get("remember_window_geometry", True)):
            payload["window_geometry"] = self.geometry()
        self.config_data = save_settings_dict(payload)

    def _setup_style(self) -> None:
        self.appearance_manager.apply(self.config_data)

    def _apply_appearance(self, settings: dict | None = None) -> None:
        if settings is not None:
            self.config_data.update(settings)
        self.appearance_manager.apply(self.config_data)
        if hasattr(self, "log_text"):
            self.appearance_manager.configure_text_widget(self.log_text, fixed=True)
        if hasattr(self, "provider_summary_var"):
            provider_id = str(self.config_data.get("processing_provider", "ollama_local"))
            self.provider_summary_var.set(provider_display_name(provider_id))

    def _create_variables(self) -> None:
        today = date.today().isoformat()
        self.vtt_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(
            value=str(self.config_data.get("output_dir", default_output_dir()))
        )
        self.ollama_url_var = tk.StringVar(
            value=str(self.config_data.get("ollama_base_url", "http://localhost:11434"))
        )
        self.model_var = tk.StringVar(value=str(self.config_data.get("model", "qwen3:8b")))
        self.auto_speakers_var = tk.BooleanVar(
            value=bool(self.config_data.get("auto_add_transcript_speakers", True))
        )
        self.open_word_var = tk.BooleanVar(
            value=bool(self.config_data.get("open_word_after_generation", True))
        )
        self.ollama_status_var = tk.StringVar(value="Verificando componentes...")
        self.progress_text_var = tk.StringVar(value="Listo")
        self.processing_metrics_var = tk.StringVar(value="")
        self.progress_var = tk.IntVar(value=0)
        self.processing_started_monotonic: float | None = None
        self.processing_last_event_monotonic: float | None = None
        self.processing_telemetry_state: dict = {}
        self.processing_tick_job: str | None = None
        self.provider_summary_var = tk.StringVar(
            value=provider_display_name(
                str(self.config_data.get("processing_provider", "ollama_local"))
            )
        )
        self.review_summary_var = tk.StringVar(
            value="Procese una transcripción para revisar los puntos detectados."
        )

        self.meta_vars = {
            "minute_number": tk.StringVar(value=""),
            "document_date": tk.StringVar(value=today),
            "meeting_date": tk.StringVar(value=today),
            "location": tk.StringVar(value="Microsoft Teams"),
            "matter": tk.StringVar(value=""),
            "project_code": tk.StringVar(value=""),
            "project_description": tk.StringVar(value=""),
            "client": tk.StringVar(value=""),
            "minute_taker": tk.StringVar(value=""),
            "minute_taker_date": tk.StringVar(value=today),
            "approved_by": tk.StringVar(value=""),
            "approval_date": tk.StringVar(value=""),
        }

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="Abrir transcripción...", accelerator="Ctrl+O", command=self.browse_vtt
        )
        file_menu.add_command(
            label="Generar Word", accelerator="Ctrl+S", command=self.generate_document
        )
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self._on_close)
        menubar.add_cascade(label="Archivo", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(
            label="Procesar reunión", accelerator="F5", command=self.start_analysis
        )
        tools_menu.add_command(
            label="Verificar método de procesamiento", command=self.refresh_ollama_status
        )
        tools_menu.add_command(
            label="Reparar componentes locales", command=self.run_component_repair
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Preferencias...", accelerator="Ctrl+,", command=self.open_preferences
        )
        tools_menu.add_command(
            label="Buscar actualizaciones...", command=lambda: self.check_updates(manual=True)
        )
        menubar.add_cascade(label="Herramientas", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(
            label="Manual de usuario",
            command=lambda: self._open_path(install_root() / "docs" / "Manual_Usuario.html"),
        )
        help_menu.add_command(label="Generar diagnóstico", command=self.generate_diagnostic_report)
        help_menu.add_separator()
        help_menu.add_command(label="Acerca de Minutas ASH", command=self.show_about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        self.configure(menu=menubar)

    def _build_ui(self) -> None:
        self._build_menu()
        header = ttk.Frame(self, padding=(18, 12), style="Header.TFrame")
        header.pack(fill="x")
        logo = resource_path("assets/logo_ash.png")
        self.logo_image: tk.PhotoImage | None
        try:
            self.logo_image = tk.PhotoImage(file=str(logo)).subsample(3, 3)
            ttk.Label(header, image=self.logo_image).pack(side="left", padx=(0, 14))
        except tk.TclError:
            self.logo_image = None
        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text="Gestor de Minutas ASH", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Preparación, revisión y emisión de documentos corporativos",
            style="Subtitle.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            title_box,
            textvariable=self.provider_summary_var,
            style="SurfaceMuted.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        self.ollama_label = ttk.Label(
            header, textvariable=self.ollama_status_var, style="StatusBad.TLabel"
        )
        self.ollama_label.pack(side="right", anchor="n", padx=8)

        main = ttk.Frame(self, padding=(14, 0, 14, 10))
        main.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True)

        self.tab_meeting = ttk.Frame(self.notebook, padding=14)
        self.tab_attendees = ttk.Frame(self.notebook, padding=14)
        self.tab_review = ttk.Frame(self.notebook, padding=14)
        self.tab_history = ttk.Frame(self.notebook, padding=14)
        self.tab_settings = ttk.Frame(self.notebook, padding=14)
        self.tab_activity = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.tab_meeting, text="1. Reunión")
        self.notebook.add(self.tab_attendees, text="2. Asistentes")
        self.notebook.add(self.tab_review, text="3. Revisión")
        self.notebook.add(self.tab_history, text="4. Historial")
        self.notebook.add(self.tab_settings, text="Configuración")
        self.notebook.add(self.tab_activity, text="Actividad")

        self._build_meeting_tab()
        self._build_attendees_tab()
        self._build_review_tab()
        self._build_history_tab()
        self._build_settings_tab()
        self._build_activity_tab()

        bottom = ttk.Frame(main, padding=(0, 10, 0, 0))
        bottom.pack(fill="x")
        status_box = ttk.Frame(bottom)
        status_box.pack(side="left", fill="x", expand=True)
        ttk.Label(status_box, textvariable=self.progress_text_var).pack(anchor="w")
        ttk.Label(status_box, textvariable=self.processing_metrics_var, style="Muted.TLabel").pack(
            anchor="w"
        )
        self.progressbar = ttk.Progressbar(
            bottom, variable=self.progress_var, maximum=100, length=240
        )
        self.progressbar.pack(side="left", padx=12)
        ttk.Button(bottom, text="Abrir carpeta de salida", command=self.open_output_folder).pack(
            side="right"
        )
        self.word_button = ttk.Button(
            bottom,
            text="Generar Word",
            style="Primary.TButton",
            command=self.generate_document,
            state="disabled",
        )
        self.word_button.pack(side="right", padx=8)
        self.cancel_button = ttk.Button(
            bottom, text="Cancelar", command=self.cancel_analysis, state="disabled"
        )
        self.cancel_button.pack(side="right")
        self.analyze_button = ttk.Button(
            bottom, text="Procesar reunión", style="Primary.TButton", command=self.start_analysis
        )
        self.analyze_button.pack(side="right", padx=(0, 8))

    def _build_meeting_tab(self) -> None:
        tab = self.tab_meeting
        tab.columnconfigure(1, weight=1)
        source = ttk.LabelFrame(tab, text="Transcripción", padding=10)
        source.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 12))
        source.columnconfigure(1, weight=1)
        ttk.Label(source, text="Archivo VTT").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(source, textvariable=self.vtt_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(source, text="Examinar...", command=self.browse_vtt).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Button(source, text="Detectar hablantes", command=self.detect_speakers).grid(
            row=0, column=3, padx=(8, 0)
        )

        form = ttk.LabelFrame(tab, text="Datos de la minuta", padding=12)
        form.grid(row=1, column=0, columnspan=4, sticky="nsew")
        for col in (1, 3):
            form.columnconfigure(col, weight=1)
        fields = [
            ("N.º de minuta", "minute_number", 0, 0),
            ("Fecha documento", "document_date", 0, 2),
            ("Fecha reunión", "meeting_date", 1, 0),
            ("Lugar", "location", 1, 2),
            ("Materia", "matter", 2, 0),
            ("Código proyecto", "project_code", 2, 2),
            ("Descripción proyecto", "project_description", 3, 0),
            ("Cliente", "client", 3, 2),
            ("Minuta tomada por", "minute_taker", 4, 0),
            ("Fecha elaboración", "minute_taker_date", 4, 2),
            ("Minuta aprobada por", "approved_by", 5, 0),
            ("Fecha aprobación", "approval_date", 5, 2),
        ]
        for label, key, row, col in fields:
            ttk.Label(form, text=label).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=6)
            ttk.Entry(form, textvariable=self.meta_vars[key]).grid(
                row=row, column=col + 1, sticky="ew", padx=(0, 18), pady=6
            )

        controls = ttk.Frame(tab)
        controls.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        ttk.Button(controls, text="Cargar ficha JSON", command=self.load_metadata_file).pack(
            side="left"
        )
        ttk.Button(controls, text="Guardar ficha JSON", command=self.save_metadata_file).pack(
            side="left", padx=8
        )
        ttk.Button(controls, text="Limpiar formulario", command=self.clear_form).pack(side="left")
        ttk.Button(controls, text="Guardar en catálogos", command=self.save_catalogs).pack(
            side="left", padx=8
        )
        ttk.Button(controls, text="Cargar proyecto", command=self.load_project_catalog).pack(
            side="left"
        )
        ttk.Label(
            controls,
            text=f"Fechas recomendadas: {DATE_HINT}",
        ).pack(side="right")

    def _build_attendees_tab(self) -> None:
        tab = self.tab_attendees
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        columns = ("id", "initials", "name", "email", "role", "organization")
        self.attendee_tree = ttk.Treeview(
            tab, columns=columns, show="headings", selectmode="browse"
        )
        headings = {
            "id": "Id",
            "initials": "Iniciales",
            "name": "Nombre",
            "email": "Correo",
            "role": "Cargo",
            "organization": "Organización",
        }
        widths = {
            "id": 45,
            "initials": 75,
            "name": 210,
            "email": 210,
            "role": 210,
            "organization": 110,
        }
        for col in columns:
            self.attendee_tree.heading(col, text=headings[col])
            self.attendee_tree.column(
                col,
                width=widths[col],
                anchor="center" if col in {"id", "initials", "organization"} else "w",
            )
        self.attendee_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.attendee_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.attendee_tree.configure(yscrollcommand=scroll.set)
        self.attendee_tree.bind("<Double-1>", lambda _event: self.edit_attendee())

        buttons = ttk.Frame(tab)
        buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Agregar", command=self.add_attendee).pack(side="left")
        ttk.Button(buttons, text="Editar", command=self.edit_attendee).pack(side="left", padx=6)
        ttk.Button(buttons, text="Eliminar", command=self.delete_attendee).pack(side="left")
        ttk.Button(buttons, text="Renumerar", command=self.renumber_attendees).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Guardar contactos", command=self.save_contacts).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Agregar desde catálogo", command=self.add_from_contacts).pack(
            side="left"
        )

    def _build_review_tab(self) -> None:
        tab = self.tab_review
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=1)
        summary = ttk.Frame(tab)
        summary.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(
            summary,
            textvariable=self.review_summary_var,
            style="Section.TLabel",
            wraplength=980,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
        columns = ("n", "category", "description", "responsible", "date", "evidence")
        self.item_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        headings = {
            "n": "N.º",
            "category": "Categoría",
            "description": "Descripción",
            "responsible": "Responsable",
            "date": "Fecha/plazo",
            "evidence": "Referencia",
        }
        widths = {
            "n": 45,
            "category": 100,
            "description": 500,
            "responsible": 175,
            "date": 130,
            "evidence": 100,
        }
        for col in columns:
            self.item_tree.heading(col, text=headings[col])
            self.item_tree.column(
                col, width=widths[col], anchor="center" if col != "description" else "w"
            )
        self.item_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.item_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.item_tree.configure(yscrollcommand=scroll.set)
        self.item_tree.bind("<Double-1>", lambda _event: self.edit_item())

        buttons = ttk.Frame(tab)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Agregar", command=self.add_item).pack(side="left")
        ttk.Button(buttons, text="Editar", command=self.edit_item).pack(side="left", padx=6)
        ttk.Button(buttons, text="Ver referencia", command=self.show_item_reference).pack(
            side="left"
        )
        ttk.Button(buttons, text="Eliminar", command=self.delete_item).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(buttons, text="Subir", command=lambda: self.move_item(-1)).pack(
            side="left", padx=(14, 6)
        )
        ttk.Button(buttons, text="Bajar", command=lambda: self.move_item(1)).pack(side="left")
        ttk.Label(
            buttons,
            text="Revise especialmente responsables, fechas y categorías antes de generar el Word.",
        ).pack(side="right")

    def _build_history_tab(self) -> None:
        tab = self.tab_history
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        columns = ("id", "date", "number", "project", "matter", "status", "updated")
        self.history_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        specs = (
            ("id", "Id", 45),
            ("date", "Fecha", 95),
            ("number", "N.º minuta", 175),
            ("project", "Proyecto", 100),
            ("matter", "Materia", 300),
            ("status", "Estado", 90),
            ("updated", "Actualizado", 145),
        )
        for column, title, width in specs:
            self.history_tree.heading(column, text=title)
            self.history_tree.column(column, width=width, anchor="w")
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.history_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.bind("<Double-1>", lambda _event: self.open_history_document())

        buttons = ttk.Frame(tab)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Actualizar", command=self._refresh_history_tree).pack(side="left")
        ttk.Button(buttons, text="Cargar en editor", command=self.load_history_meeting).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Abrir Word", command=self.open_history_document).pack(side="left")
        ttk.Button(buttons, text="Abrir carpeta", command=self.open_history_folder).pack(
            side="left", padx=6
        )
        ttk.Label(
            buttons,
            text="El historial se guarda localmente en SQLite.",
        ).pack(side="right")

    def _build_settings_tab(self) -> None:
        tab = self.tab_settings
        tab.columnconfigure(0, weight=1)

        system_box = ttk.LabelFrame(tab, text="Estado y método de procesamiento", padding=14)
        system_box.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        system_box.columnconfigure(0, weight=1)
        ttk.Label(
            system_box,
            textvariable=self.provider_summary_var,
            style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            system_box,
            text=(
                "El método local mantiene la transcripción en el equipo. Los métodos remotos "
                "se habilitan de forma explícita y sus credenciales se guardan en Windows."
            ),
            wraplength=800,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        system_buttons = ttk.Frame(system_box)
        system_buttons.grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Button(system_buttons, text="Verificar", command=self.refresh_ollama_status).pack(
            side="left"
        )
        ttk.Button(
            system_buttons, text="Reparar componentes locales", command=self.run_component_repair
        ).pack(side="left", padx=6)
        ttk.Button(
            system_buttons,
            text="Preferencias...",
            style="Primary.TButton",
            command=self.open_preferences,
        ).pack(side="left")

        documents = ttk.LabelFrame(tab, text="Documentos", padding=14)
        documents.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        documents.columnconfigure(1, weight=1)
        ttk.Label(documents, text="Carpeta de documentos").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=7
        )
        ttk.Entry(documents, textvariable=self.output_dir_var).grid(
            row=0, column=1, sticky="ew", pady=7
        )
        ttk.Button(documents, text="Examinar...", command=self.browse_output).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Checkbutton(
            documents,
            text="Agregar automáticamente participantes detectados",
            variable=self.auto_speakers_var,
        ).grid(row=1, column=1, sticky="w", pady=7)
        ttk.Checkbutton(
            documents, text="Abrir el documento después de generarlo", variable=self.open_word_var
        ).grid(row=2, column=1, sticky="w", pady=7)

        maintenance = ttk.LabelFrame(tab, text="Mantenimiento", padding=14)
        maintenance.grid(row=2, column=0, sticky="ew")
        buttons = ttk.Frame(maintenance)
        buttons.pack(anchor="w")
        ttk.Button(buttons, text="Guardar configuración", command=self.save_settings).pack(
            side="left"
        )
        ttk.Button(
            buttons, text="Buscar actualizaciones", command=lambda: self.check_updates(manual=True)
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Abrir datos locales", command=lambda: self._open_path(user_data_root())
        ).pack(side="left")
        ttk.Button(
            buttons, text="Abrir registros", command=lambda: self._open_path(logs_dir())
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Generar diagnóstico", command=self.generate_diagnostic_report
        ).pack(side="left")
        ttk.Label(
            maintenance,
            text=(
                "Los documentos, catálogos, historial, preferencias y credenciales se mantienen "
                "fuera de la carpeta del programa para conservarlos durante las actualizaciones."
            ),
            wraplength=820,
            justify="left",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(14, 0))

    def _build_activity_tab(self) -> None:
        tab = self.tab_activity
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        self.log_text = ScrolledText(tab, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.appearance_manager.configure_text_widget(self.log_text, fixed=True)
        ttk.Button(tab, text="Limpiar registro", command=self.clear_log).grid(
            row=1, column=0, sticky="e", pady=(8, 0)
        )

    def _load_default_metadata(self) -> None:
        default = source_root() / "entrada" / "datos_reunion.json"
        if default.exists():
            try:
                self._apply_metadata(
                    MeetingMetadata.model_validate_json(default.read_text(encoding="utf-8-sig"))
                )
            except (OSError, json.JSONDecodeError, ValidationError) as exc:
                self.logger.warning("No se pudieron cargar los metadatos predeterminados: %s", exc)

    def _metadata_from_form(self) -> MeetingMetadata:
        payload: dict[str, Any] = {
            key: variable.get().strip() or None for key, variable in self.meta_vars.items()
        }
        enriched_attendees: list[Attendee] = []
        for attendee in self.attendees:
            saved = self.db.find_contact(attendee.name)
            if saved:
                merged = attendee.model_copy(deep=True)
                merged.initials = merged.initials or saved.initials
                merged.email = merged.email or saved.email
                merged.role = merged.role or saved.role
                if not merged.organization or merged.organization == "Por confirmar":
                    merged.organization = saved.organization
                enriched_attendees.append(merged)
            else:
                enriched_attendees.append(attendee.model_copy(deep=True))
        payload["attendees"] = [attendee.model_dump() for attendee in enriched_attendees]
        metadata = MeetingMetadata.model_validate(payload)
        for key in ("document_date", "meeting_date", "minute_taker_date", "approval_date"):
            value = getattr(metadata, key)
            if value:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError as exc:
                    raise ValueError(f"'{key}' debe usar el formato AAAA-MM-DD.") from exc
        return metadata

    def _apply_metadata(self, metadata: MeetingMetadata) -> None:
        for key, variable in self.meta_vars.items():
            variable.set(getattr(metadata, key) or "")
        self.attendees = [attendee.model_copy(deep=True) for attendee in metadata.attendees]
        self._refresh_attendees_tree()

    def browse_vtt(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar transcripción de Teams",
            filetypes=[("Transcripción VTT", "*.vtt"), ("Todos los archivos", "*.*")],
        )
        if path:
            self.vtt_var.set(path)
            self.current_meeting_id = None
            self.analysis_bundle = None
            self.items.clear()
            self.review_summary_var.set("Transcripción seleccionada. Presione Procesar reunión.")
            self._refresh_items_tree()
            self.word_button.configure(state="disabled")
            self._log(f"Transcripción seleccionada: {path}")
            self.detect_speakers(switch_tab=False)

    def _accept_vtt_path(self, path: Path) -> bool:
        self.vtt_var.set(str(path))
        self.current_meeting_id = None
        self.analysis_bundle = None
        self.items.clear()
        self.review_summary_var.set("Transcripción seleccionada. Presione Procesar reunión.")
        self._refresh_items_tree()
        self.word_button.configure(state="disabled")
        self._log(f"Transcripción seleccionada: {path}")
        self.detect_speakers(switch_tab=False)
        return True

    def browse_output(self) -> None:
        path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if path:
            self.output_dir_var.set(path)

    def load_metadata_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Cargar ficha de reunión",
            filetypes=[("Archivo JSON", "*.json")],
        )
        if not path:
            return
        try:
            metadata = MeetingMetadata.model_validate_json(
                Path(path).read_text(encoding="utf-8-sig")
            )
            self._apply_metadata(metadata)
            self._log(f"Ficha cargada: {path}")
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            messagebox.showerror("No fue posible cargar la ficha", str(exc), parent=self)

    def save_metadata_file(self) -> None:
        try:
            metadata = self._metadata_from_form()
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)
            return
        default_name = f"datos_{metadata.project_code or 'reunion'}.json"
        path = filedialog.asksaveasfilename(
            title="Guardar ficha de reunión",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("Archivo JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        self._log(f"Ficha guardada: {path}")

    def clear_form(self) -> None:
        if not messagebox.askyesno(
            "Limpiar", "¿Desea limpiar los datos de la reunión?", parent=self
        ):
            return
        today = date.today().isoformat()
        for variable in self.meta_vars.values():
            variable.set("")
        self.meta_vars["document_date"].set(today)
        self.meta_vars["meeting_date"].set(today)
        self.meta_vars["meeting_date"].set(today)
        self.meta_vars["location"].set("Microsoft Teams")
        self.meta_vars["minute_taker_date"].set(today)
        self.attendees.clear()
        self.items.clear()
        self.analysis_bundle = None
        self.current_meeting_id = None
        self.review_summary_var.set(
            "Formulario limpio. Seleccione una transcripción para comenzar."
        )
        self._refresh_attendees_tree()
        self._refresh_items_tree()
        self.word_button.configure(state="disabled")

    def detect_speakers(self, switch_tab: bool = True) -> None:
        path = Path(self.vtt_var.get().strip())
        if not path.exists():
            messagebox.showwarning(
                "Transcripción", "Seleccione primero un archivo VTT válido.", parent=self
            )
            return
        try:
            speakers = unique_speakers(read_teams_vtt(path))
            metadata = self._metadata_from_form()
            metadata = enrich_attendees(metadata, speakers, True)
            enriched: list[Attendee] = []
            for attendee in metadata.attendees:
                saved = self.db.find_contact(attendee.name)
                if saved:
                    saved.id = attendee.id
                    enriched.append(saved)
                else:
                    enriched.append(attendee)
            self.attendees = enriched
            self.renumber_attendees()
            if switch_tab:
                self.notebook.select(self.tab_attendees)
            self._log(f"Hablantes detectados y agregados: {len(speakers)}")
        except Exception as exc:
            messagebox.showerror("No fue posible detectar hablantes", str(exc), parent=self)

    def add_attendee(self) -> None:
        dialog = AttendeeDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.attendees.append(dialog.result)
            self.renumber_attendees()

    def _selected_attendee_index(self) -> int | None:
        selected = self.attendee_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def edit_attendee(self) -> None:
        index = self._selected_attendee_index()
        if index is None:
            messagebox.showinfo("Asistentes", "Seleccione un asistente.", parent=self)
            return
        dialog = AttendeeDialog(self, self.attendees[index])
        self.wait_window(dialog)
        if dialog.result:
            self.attendees[index] = dialog.result
            self.renumber_attendees()

    def delete_attendee(self) -> None:
        index = self._selected_attendee_index()
        if index is None:
            return
        if messagebox.askyesno(
            "Eliminar", f"¿Eliminar a {self.attendees[index].name}?", parent=self
        ):
            self.attendees.pop(index)
            self.renumber_attendees()

    def renumber_attendees(self) -> None:
        for index, attendee in enumerate(self.attendees, start=1):
            attendee.id = index
            attendee.initials = attendee.initials or initials_from_name(attendee.name)
        self._refresh_attendees_tree()

    def _refresh_attendees_tree(self) -> None:
        self.attendee_tree.delete(*self.attendee_tree.get_children())
        for index, attendee in enumerate(self.attendees):
            self.attendee_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    attendee.id or index + 1,
                    attendee.initials or "",
                    attendee.name,
                    attendee.email or "",
                    attendee.role or "",
                    attendee.organization or "Por confirmar",
                ),
            )

    @staticmethod
    def _seconds_from_timestamp(value: str | None) -> float | None:
        if not value:
            return None
        try:
            parts = value.replace(",", ".").split(":")
            if len(parts) == 2:
                hours = "0"
                minutes, seconds = parts
            else:
                hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except (TypeError, ValueError):
            return None

    def show_item_reference(self) -> None:
        index = self._selected_item_index()
        if index is None:
            messagebox.showinfo("Referencia", "Seleccione primero un punto.", parent=self)
            return
        item = self.items[index]
        if not item.evidence:
            messagebox.showinfo(
                "Referencia",
                "Este punto no tiene una marca temporal asociada.",
                parent=self,
            )
            return
        path = Path(self.vtt_var.get().strip())
        if not path.is_file() and self.analysis_bundle:
            path = self.analysis_bundle.source_path
        if not path.is_file():
            messagebox.showwarning(
                "Referencia",
                "No se encontró la transcripción de origen.",
                parent=self,
            )
            return
        try:
            segments = read_teams_vtt(path, merge_adjacent=False)
        except Exception as exc:
            messagebox.showerror("Referencia", str(exc), parent=self)
            return
        target = self._seconds_from_timestamp(item.evidence)
        if target is None:
            messagebox.showinfo(
                "Referencia",
                f"Referencia registrada: {item.evidence}",
                parent=self,
            )
            return
        nearest = min(
            range(len(segments)),
            key=lambda position: abs(
                (self._seconds_from_timestamp(segments[position].start) or 0) - target
            ),
        )
        start = max(0, nearest - 2)
        end = min(len(segments), nearest + 4)

        window = tk.Toplevel(self)
        window.title("Referencia en la transcripción")
        configure_resizable_window(window, self, "transcript_reference", "900x560", (650, 320))
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=f"Punto {index + 1}: {item.description}",
            style="Section.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        text = ScrolledText(frame, wrap="word")
        text.pack(fill="both", expand=True)
        self.appearance_manager.configure_text_widget(text, fixed=True)
        for position in range(start, end):
            segment = segments[position]
            prefix = "▶ " if position == nearest else "  "
            text.insert(
                "end",
                f"{prefix}[{segment.start}] {segment.speaker}: {segment.text}\n\n",
                "selected" if position == nearest else "normal",
            )
        with contextlib.suppress(tk.TclError):
            text.tag_configure(
                "selected",
                font=(self.config_data.get("appearance_font_family", "Segoe UI"), 10, "bold"),
            )
        text.configure(state="disabled")
        ttk.Button(frame, text="Cerrar", command=window.destroy).pack(anchor="e", pady=(10, 0))

    def add_item(self) -> None:
        dialog = ItemDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.items.append(dialog.result)
            self._sync_items_to_bundle()
            self._refresh_items_tree()

    def _selected_item_index(self) -> int | None:
        selected = self.item_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def edit_item(self) -> None:
        index = self._selected_item_index()
        if index is None:
            messagebox.showinfo("Revisión", "Seleccione un punto de minuta.", parent=self)
            return
        dialog = ItemDialog(self, self.items[index])
        self.wait_window(dialog)
        if dialog.result:
            self.items[index] = dialog.result
            self._sync_items_to_bundle()
            self._refresh_items_tree()

    def delete_item(self) -> None:
        index = self._selected_item_index()
        if index is None:
            return
        if messagebox.askyesno("Eliminar", "¿Eliminar el punto seleccionado?", parent=self):
            self.items.pop(index)
            self._sync_items_to_bundle()
            self._refresh_items_tree()
            self._save_autosave_draft()

    def move_item(self, delta: int) -> None:
        index = self._selected_item_index()
        if index is None:
            return
        target = index + delta
        if target < 0 or target >= len(self.items):
            return
        self.items[index], self.items[target] = self.items[target], self.items[index]
        self._sync_items_to_bundle()
        self._refresh_items_tree(select_index=target)
        self._save_autosave_draft()

    def _refresh_items_tree(self, select_index: int | None = None) -> None:
        self.item_tree.delete(*self.item_tree.get_children())
        for index, item in enumerate(self.items):
            due = item.due_date_text or item.due_date_iso or ""
            self.item_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    index + 1,
                    item.category,
                    item.description,
                    item.responsible or "",
                    due,
                    item.evidence or "",
                ),
            )
        if select_index is not None and 0 <= select_index < len(self.items):
            self.item_tree.selection_set(str(select_index))
            self.item_tree.focus(str(select_index))

    def _sync_items_to_bundle(self) -> None:
        if self.analysis_bundle:
            self.analysis_bundle.analysis.items = [
                item.model_copy(deep=True) for item in self.items
            ]

    def start_analysis(self) -> None:
        if self.busy:
            return
        vtt_path = Path(self.vtt_var.get().strip())
        if not vtt_path.exists():
            messagebox.showwarning(
                "Transcripción", "Seleccione un archivo VTT válido.", parent=self
            )
            return
        try:
            metadata = self._metadata_from_form()
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)
            return
        provider_id = str(self.config_data.get("processing_provider", "ollama_local"))
        model = configured_model(self.config_data, provider_id)
        if not model:
            messagebox.showwarning(
                "Perfil de procesamiento",
                "Configure un modelo o perfil de procesamiento.",
                parent=self,
            )
            return
        descriptor = descriptor_for(provider_id)
        if descriptor.is_remote and bool(self.config_data.get("confirm_remote_processing", True)):  # noqa: SIM102
            if not messagebox.askyesno(
                "Procesamiento remoto",
                (
                    f"El método seleccionado es '{descriptor.display_name}'.\n\n"
                    "La transcripción y los datos de contexto se enviarán al servicio configurado. "
                    "Confirme que este uso está autorizado por ASH y por el cliente.\n\n"
                    "¿Desea continuar?"
                ),
                parent=self,
            ):
                return

        config = deepcopy(self.config_data)
        config.update(
            {
                "ollama_base_url": self.ollama_url_var.get().strip(),
                "model": self.model_var.get().strip()
                or str(self.config_data.get("model", "qwen3:8b")),
                "auto_add_transcript_speakers": self.auto_speakers_var.get(),
            }
        )
        self.cancel_requested = False
        self._set_busy(True)
        self.progress_var.set(0)
        self.progress_text_var.set("Iniciando procesamiento")
        self.processing_metrics_var.set("Evaluando duración y recursos del equipo…")
        self.processing_started_monotonic = time.monotonic()
        self.processing_last_event_monotonic = self.processing_started_monotonic
        self.processing_telemetry_state = {"stage": "startup"}
        self._schedule_processing_tick()
        self.notebook.select(self.tab_activity)
        self._log("=" * 60)
        self._log("INICIO DEL PROCESAMIENTO")

        job_store = ProcessingJobStore()
        job = job_store.create(str(vtt_path), provider_id, model)
        job_store.update(job.job_id, status="running", message="Iniciando procesamiento")
        self.active_processing_job_id = job.job_id

        thread = threading.Thread(
            target=self._analysis_worker,
            args=(vtt_path, metadata, config, model, job.job_id),
            daemon=True,
        )
        thread.start()

    def _analysis_worker(
        self,
        vtt_path: Path,
        metadata: MeetingMetadata,
        config: dict,
        model: str,
        job_id: str,
    ) -> None:
        job_store = ProcessingJobStore()

        def report_progress(value: int, message: str) -> None:
            try:
                job_store.update(job_id, status="running", progress=value, message=message)
            except (KeyError, OSError, TypeError, ValueError) as exc:
                self.logger.warning("No se pudo guardar el avance del trabajo %s: %s", job_id, exc)
            self.worker_queue.put(("progress", (value, message)))

        try:
            with operation(job_id):
                bundle = analyze_meeting(
                    vtt_path,
                    metadata,
                    config,
                    model,
                    log=lambda message: self.worker_queue.put(("log", message)),
                    progress=report_progress,
                    telemetry=lambda event: self.worker_queue.put(("telemetry", event)),
                    cancelled=lambda: self.cancel_requested,
                )
            try:
                job_store.update(
                    job_id,
                    status="completed",
                    progress=100,
                    message="Contenido listo para revision",
                )
            except (KeyError, OSError, TypeError, ValueError) as exc:
                self.logger.warning(
                    "No se pudo cerrar el trabajo %s como completado: %s", job_id, exc
                )
            self.worker_queue.put(("analysis_success", bundle))
        except Exception as exc:
            status: JobStatus = "cancelled" if isinstance(exc, InterruptedError) else "failed"
            try:
                job_store.update(
                    job_id,
                    status=status,
                    message=str(exc),
                    error=str(exc) if status == "failed" else "",
                )
            except (KeyError, OSError, TypeError, ValueError) as persistence_error:
                self.logger.warning(
                    "No se pudo guardar el estado final del trabajo %s: %s",
                    job_id,
                    persistence_error,
                )
            self.worker_queue.put(("error", exc))

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                kind, payload = self.worker_queue.get_nowait()
                if kind == "log":
                    self._log(str(payload))
                elif kind == "progress":
                    value, message = cast(tuple[int, str], payload)
                    self.progress_var.set(int(value))
                    self.progress_text_var.set(str(message))
                elif kind == "telemetry":
                    self._apply_processing_telemetry(cast(dict[str, object], payload))
                elif kind == "analysis_success":
                    self._analysis_complete(cast(AnalysisBundle, payload))
                elif kind == "provider_status" or kind == "ollama_status":
                    self._apply_provider_status(
                        cast(tuple[bool, str, list[str], Exception | None], payload)
                    )
                elif kind == "refresh_ollama":
                    self.refresh_ollama_status()
                elif kind == "update_result":
                    self._apply_update_result(cast(tuple[UpdateInfo, bool], payload))
                elif kind == "update_progress":
                    value, message = cast(tuple[int, str], payload)
                    self.progress_var.set(int(value))
                    self.progress_text_var.set(str(message))
                elif kind == "update_downloaded":
                    self._apply_update_downloaded(cast(tuple[UpdateInfo, Path], payload))
                elif kind == "update_error":
                    self._set_busy(False)
                    self.progress_text_var.set("No fue posible actualizar")
                    self._log(f"Actualización: {payload}")
                    messagebox.showerror("Actualizaciones", str(payload), parent=self)
                elif kind == "model_installed":
                    self._set_busy(False)
                    self._log("Componentes preparados correctamente.")
                    self.refresh_ollama_status()
                    messagebox.showinfo(
                        "Componentes", "Los componentes quedaron disponibles.", parent=self
                    )
                elif kind == "media_transcribed":
                    self._set_busy(False)
                    self._accept_vtt_path(cast(Path, payload))
                elif kind == "error":
                    self._handle_worker_error(payload)
        except queue.Empty:
            pass
        self.after(150, self._poll_worker_queue)

    @staticmethod
    def _format_runtime_duration(seconds: float | int | None) -> str:
        if seconds is None:
            return "—"
        total = max(int(seconds), 0)
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_runtime_memory(value: object) -> str:
        try:
            if not isinstance(value, (str, bytes, int, float)):
                return ""
            number = int(value)
        except (TypeError, ValueError):
            return ""
        if number <= 0:
            return ""
        return f"{number / (1024**3):.1f} GB libres"

    def _schedule_processing_tick(self) -> None:
        if self.processing_tick_job is None:
            self.processing_tick_job = self.after(1000, self._processing_tick)

    def _render_processing_metrics(self) -> None:
        if not self.busy or self.processing_started_monotonic is None:
            return
        now = time.monotonic()
        elapsed = now - self.processing_started_monotonic
        last = now - (self.processing_last_event_monotonic or now)
        state = self.processing_telemetry_state or {}
        pieces = [f"Transcurrido {self._format_runtime_duration(elapsed)}"]
        block_index = state.get("block_index")
        total_blocks = state.get("total_blocks")
        if block_index and total_blocks:
            pieces.append(f"bloque {block_index}/{total_blocks}")
        eta = state.get("eta_seconds")
        if eta is not None:
            pieces.append(f"restante aprox. {self._format_runtime_duration(eta)}")
        memory_percent = state.get("memory_percent")
        if memory_percent is not None:
            with contextlib.suppress(TypeError, ValueError):
                pieces.append(f"memoria {float(memory_percent):.0f} %")
        available = self._format_runtime_memory(state.get("available_memory_bytes"))
        if available:
            pieces.append(available)
        if last >= 5:
            pieces.append(f"esperando actividad hace {self._format_runtime_duration(last)}")
        else:
            pieces.append("modelo activo")
        self.processing_metrics_var.set(" · ".join(pieces))

    def _processing_tick(self) -> None:
        self.processing_tick_job = None
        if not self.busy or self.processing_started_monotonic is None:
            return
        self._render_processing_metrics()
        self._schedule_processing_tick()

    def _apply_processing_telemetry(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        self.processing_last_event_monotonic = time.monotonic()
        state = dict(self.processing_telemetry_state or {})
        state.update(payload)
        event_type = str(payload.get("type") or "")
        if event_type == "processing_plan":
            profile = payload.get("effective_profile") or {}
            if isinstance(profile, dict):
                state["profile_name"] = profile.get("display_name")
            snapshot = payload.get("resource_snapshot") or {}
            if isinstance(snapshot, dict):
                state["memory_percent"] = snapshot.get("memory_percent")
                state["available_memory_bytes"] = snapshot.get("available_memory_bytes")
            name = state.get("profile_name") or "Automático"
            self._log(f"Perfil efectivo: {name}.")
        elif event_type in {"pipeline_progress", "chunk_completed"}:
            percent = payload.get("percent")
            if percent is not None:
                with contextlib.suppress(TypeError, ValueError):
                    self.progress_var.set(max(0, min(int(percent), 99)))
        elif event_type == "chunk_split":
            self._log(
                "El bloque lento fue dividido automáticamente en "
                f"{payload.get('child_count', '?')} partes."
            )
        elif event_type == "chunk_retry":
            self._log(f"Reintento adaptativo del bloque · intento {payload.get('attempt', '?')}.")
        elif event_type == "request_timeout":
            self.progress_text_var.set("Ajustando bloque después de una espera prolongada")
        elif event_type == "request_cancelled":
            self.progress_text_var.set("Cancelación confirmada por el motor local")
        self.processing_telemetry_state = state
        self._render_processing_metrics()

    def _analysis_complete(self, bundle: AnalysisBundle) -> None:
        self.analysis_bundle = bundle
        self.attendees = [attendee.model_copy(deep=True) for attendee in bundle.metadata.attendees]
        self.items = [item.model_copy(deep=True) for item in bundle.analysis.items]
        diagnostics = bundle.diagnostics or {}
        final_coverage = diagnostics.get("final_coverage") or {}
        candidate_count = int(diagnostics.get("candidate_count") or 0)
        covered_count = int(final_coverage.get("covered_count") or 0)
        fallback_added = int(diagnostics.get("fallback_added") or 0)
        unresolved = int(final_coverage.get("uncovered_count") or 0)
        if candidate_count:
            summary = (
                f"Puntos para revisar: {len(self.items)} · "
                f"Cobertura de expresiones explícitas: {covered_count}/{candidate_count}"
            )
            if fallback_added:
                summary += f" · Recuperados automáticamente: {fallback_added}"
            if unresolved:
                summary += f" · Pendientes de comprobar: {unresolved}"
        else:
            summary = f"Puntos para revisar: {len(self.items)} · No se detectaron marcadores explícitos adicionales."
        self.review_summary_var.set(summary)
        self._refresh_attendees_tree()
        self._refresh_items_tree()
        self.progress_var.set(100)
        self.progress_text_var.set("Contenido listo para revisión")
        elapsed = None
        if self.processing_started_monotonic is not None:
            elapsed = time.monotonic() - self.processing_started_monotonic
        self.processing_metrics_var.set(
            f"Completado en {self._format_runtime_duration(elapsed)} · avance recuperable cerrado"
        )
        self._log("PROCESAMIENTO FINALIZADO")
        self._log(f"Puntos para revisar: {len(self.items)}")
        self._set_busy(False)
        self.word_button.configure(state="normal")
        try:
            self.current_meeting_id = self.db.save_meeting(
                metadata=bundle.metadata,
                analysis=bundle.analysis,
                source_vtt=str(bundle.source_path),
                output_dir=self.output_dir_var.get().strip(),
                model=bundle.model,
                status="procesada",
                meeting_id=self.current_meeting_id,
                app_version=str(self.config_data.get("app_version", "2.3.4")),
                document_provider=str(self.config_data.get("document_provider", "ash_minutes_v1")),
                processing_provider=bundle.provider_id,
                processing_provider_name=bundle.provider_name,
                source_type=bundle.metadata.source_type,
                source_quality=bundle.metadata.source_quality,
                is_test=bool(
                    getattr(self, "record_is_test_var", None) and self.record_is_test_var.get()
                ),
            )
            self._refresh_history_tree()
        except Exception as exc:
            self._log(f"No se pudo actualizar historial: {exc}")
        self._save_autosave_draft()
        self.notebook.select(self.tab_review)
        diagnostics = bundle.diagnostics or {}
        final_coverage = diagnostics.get("final_coverage") or {}
        fallback_added = int(diagnostics.get("fallback_added") or 0)
        unresolved = int(final_coverage.get("uncovered_count") or 0)
        if unresolved:
            messagebox.showwarning(
                "Revisión requerida",
                "El contenido fue procesado, pero quedaron expresiones explícitas que no "
                "pudieron asociarse con certeza. Revise la pestaña Revisión y el registro "
                "de actividad antes de generar el Word.",
                parent=self,
            )
        elif fallback_added:
            messagebox.showinfo(
                "Contenido recuperado",
                f"El control de cobertura recuperó {fallback_added} punto(s) explícito(s). "
                "Revise su redacción, responsables y fechas antes de generar el Word.",
                parent=self,
            )
        else:
            messagebox.showinfo(
                "Procesamiento finalizado",
                "Revise las categorías, responsables y fechas. Luego presione 'Generar Word'.",
                parent=self,
            )

    def _handle_worker_error(self, exc: object) -> None:
        self._set_busy(False)
        self.progress_text_var.set("Error")
        if isinstance(exc, InterruptedError):
            self.progress_text_var.set("Proceso cancelado")
            self.processing_metrics_var.set(
                "El avance completado quedó guardado para continuar después."
            )
            self._log(str(exc))
            messagebox.showinfo("Proceso cancelado", str(exc), parent=self)
            return
        self.processing_metrics_var.set(
            "El avance por bloques se conservó. Puede corregir la causa y volver a procesar."
        )
        self._log(f"ERROR: {exc}")
        if isinstance(exc, BaseException):
            self.logger.error(
                "Error en proceso de fondo",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
        messagebox.showerror("No fue posible completar el proceso", str(exc), parent=self)

    def _set_busy(self, value: bool) -> None:
        self.busy = value
        self.analyze_button.configure(state="disabled" if value else "normal")
        self.cancel_button.configure(state="normal" if value else "disabled")
        if value:
            self.word_button.configure(state="disabled")

    def generate_document(self) -> None:
        if not self.analysis_bundle:
            messagebox.showwarning(
                "Revisión", "Primero procese una fuente de reunión.", parent=self
            )
            return
        try:
            metadata = self._metadata_from_form()
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)
            return
        missing = []
        for label, value in (
            ("N.º de minuta", metadata.minute_number),
            ("Fecha de documento", metadata.document_date),
            ("Fecha de reunión", metadata.meeting_date),
            ("Materia", metadata.matter),
            ("Código de proyecto", metadata.project_code),
            ("Minuta tomada por", metadata.minute_taker),
        ):
            if not value:
                missing.append(label)
        if missing:
            messagebox.showwarning(
                "Datos requeridos",
                "Complete antes de generar el Word:\n\n- " + "\n- ".join(missing),
                parent=self,
            )
            return
        if not self.items and not messagebox.askyesno(
            "Minuta sin puntos",
            "No existen acuerdos, compromisos, pendientes ni antecedentes en la "
            "pestaña Revisión. ¿Desea generar igualmente una minuta vacía?",
            parent=self,
        ):
            self.notebook.select(self.tab_review)
            return
        diagnostics = self.analysis_bundle.diagnostics or {}
        final_coverage = diagnostics.get("final_coverage") or {}
        if int(final_coverage.get("uncovered_count") or 0) and not messagebox.askyesno(
            "Cobertura pendiente",
            "El control de cobertura informa expresiones pendientes de comprobar. "
            "Se recomienda revisar el registro y la transcripción antes de emitir. "
            "¿Desea continuar de todas maneras?",
            parent=self,
        ):
            self.notebook.select(self.tab_review)
            return
        self.analysis_bundle.metadata = metadata
        self.analysis_bundle.analysis.items = [item.model_copy(deep=True) for item in self.items]
        output = Path(self.output_dir_var.get().strip())
        try:
            docx_path, json_path, transcript_path, meeting_folder = generate_word_package(
                self.analysis_bundle,
                output,
                self.config_data,
            )
            self.last_docx = docx_path
            self.save_catalogs(silent=True)
            self.current_meeting_id = self.db.save_meeting(
                metadata=metadata,
                analysis=self.analysis_bundle.analysis,
                source_vtt=str(self.analysis_bundle.source_path),
                output_dir=str(meeting_folder.root),
                model=self.analysis_bundle.model,
                status="generada",
                docx_path=str(docx_path),
                json_path=str(json_path),
                pdf_path=(
                    str(docx_path.with_suffix(".pdf"))
                    if docx_path.with_suffix(".pdf").is_file()
                    else None
                ),
                meeting_id=self.current_meeting_id,
                app_version=str(self.config_data.get("app_version", "2.3.4")),
                document_provider=str(self.config_data.get("document_provider", "ash_minutes_v1")),
                processing_provider=self.analysis_bundle.provider_id,
                processing_provider_name=self.analysis_bundle.provider_name,
                source_type=metadata.source_type,
                source_quality=metadata.source_quality,
                is_test=bool(
                    getattr(self, "record_is_test_var", None) and self.record_is_test_var.get()
                ),
            )
            self._refresh_history_tree()
            self.progress_var.set(100)
            self.progress_text_var.set("Documento generado")
            self._log(f"Word: {docx_path}")
            self._log(f"JSON: {json_path}")
            self._log(f"Transcripción: {transcript_path}")
            self._log(f"Carpeta de reunión: {meeting_folder.root}")
            self._save_config()
            pdf_path = docx_path.with_suffix(".pdf")
            if pdf_path.is_file():
                self._log(f"PDF: {pdf_path}")
            if not bool(getattr(self, "_automated_emission_pending", False)):
                messagebox.showinfo(
                    "Minuta generada",
                    f"Documento creado correctamente:\n\n{docx_path}\n\nRevíselo antes de distribuirlo.",
                    parent=self,
                )
            if self.open_word_var.get():
                self._open_path(docx_path)
        except Exception as exc:
            messagebox.showerror("No fue posible generar el Word", str(exc), parent=self)

    def open_preferences(self) -> None:
        dialog = PreferencesDialog(self, self.config_data, apply_appearance=self._apply_appearance)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.config_data = save_settings_dict(dialog.result)
        except Exception as exc:
            messagebox.showerror("Preferencias", str(exc), parent=self)
            self._apply_appearance(self.config_data)
            return
        self.output_dir_var.set(str(self.config_data.get("output_dir", default_output_dir())))
        self.ollama_url_var.set(
            str(self.config_data.get("ollama_base_url", "http://127.0.0.1:11434"))
        )
        self.model_var.set(str(self.config_data.get("model", "qwen3:8b")))
        self.auto_speakers_var.set(bool(self.config_data.get("auto_add_transcript_speakers", True)))
        self.open_word_var.set(bool(self.config_data.get("open_word_after_generation", True)))
        self._apply_appearance(self.config_data)
        self.refresh_ollama_status()
        messagebox.showinfo("Preferencias", "Las preferencias fueron guardadas.", parent=self)

    def refresh_ollama_status(self) -> None:
        """Compatibilidad histórica: verifica el proveedor seleccionado."""
        provider_id = str(self.config_data.get("processing_provider", "ollama_local"))
        self.ollama_status_var.set("Verificando método...")
        self.ollama_label.configure(style="StatusWarning.TLabel")

        def worker() -> None:
            try:
                provider = create_processing_provider(self.config_data, provider_id)
                provider.check_connection()
                models: list[str] = []
                if provider_id == "ollama_local" and hasattr(provider, "client"):
                    try:
                        models = provider.client.list_models()
                    except Exception:
                        models = []
                self.worker_queue.put(("provider_status", (True, provider_id, models, None)))
            except Exception as exc:
                self.worker_queue.put(("provider_status", (False, provider_id, [], exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_provider_status(
        self, payload: tuple[bool, str, list[str], Exception | None]
    ) -> None:
        ok, provider_id, models, error = payload
        self.provider_summary_var.set(provider_display_name(str(provider_id)))
        if ok:
            if provider_id == "ollama_local" and models:
                current = self.model_var.get().strip()
                if not current:
                    self.model_var.set(models[0])
            self.ollama_status_var.set("Sistema listo")
            self.ollama_label.configure(style="StatusGood.TLabel")
        else:
            self.ollama_status_var.set("Configuración requerida")
            self.ollama_label.configure(style="StatusBad.TLabel")
            if error:
                self._log(f"Método de procesamiento: {error}")

    # Alias usado por eventos de versiones anteriores.
    def _apply_ollama_status(self, payload: tuple[bool, str, list[str], Exception | None]) -> None:
        self._apply_provider_status(payload)

    def _check_updates_on_start(self) -> None:
        if should_check_now(self.config_data):
            self.check_updates(manual=False)

    def check_updates(self, manual: bool = True) -> None:
        if self.busy:
            if manual:
                messagebox.showinfo(
                    "Actualizaciones", "Espere a que termine el proceso actual.", parent=self
                )
            return
        if manual:
            self.progress_text_var.set("Buscando actualizaciones...")
        settings = deepcopy(self.config_data)

        def worker() -> None:
            try:
                info = check_for_updates(settings)
                self.worker_queue.put(("update_result", (info, manual)))
            except Exception as exc:
                if manual:
                    self.worker_queue.put(("update_error", exc))
                else:
                    self.worker_queue.put(("log", f"Búsqueda automática de actualizaciones: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_update_result(self, payload: tuple[UpdateInfo, bool]) -> None:
        info, manual = payload
        self.config_data["update_last_checked_at"] = datetime.now(UTC).isoformat()
        try:
            self.config_data = save_settings_dict(self.config_data)
        except Exception as exc:
            self._log(f"No se pudo guardar la fecha de actualización: {exc}")
        current = str(self.config_data.get("app_version", "2.3.4"))
        if not is_newer_version(info.version, current):
            self.progress_text_var.set("Aplicación actualizada")
            if manual:
                messagebox.showinfo(
                    "Actualizaciones",
                    f"Minutas ASH {current} es la versión más reciente disponible.",
                    parent=self,
                )
            return
        self.pending_update = info
        notes = (info.release_notes or "Sin notas de versión.").strip()
        if len(notes) > 1800:
            notes = notes[:1800] + "…"
        answer = messagebox.askyesno(
            "Actualización disponible",
            (
                f"Versión instalada: {current}\n"
                f"Versión disponible: {info.version}\n\n"
                f"{notes}\n\n"
                "La descarga será verificada mediante SHA-256 antes de ejecutarse. "
                "¿Desea descargarla ahora?"
            ),
            parent=self,
        )
        if answer:
            self._download_pending_update()
        else:
            self.progress_text_var.set("Actualización disponible")

    def _download_pending_update(self) -> None:
        if self.pending_update is None:
            return
        info = self.pending_update
        self._set_busy(True)
        self.progress_var.set(0)
        self.progress_text_var.set("Descargando actualización")

        def worker() -> None:
            try:
                path = download_update(
                    info,
                    progress=lambda value, message: self.worker_queue.put(
                        ("update_progress", (value, message))
                    ),
                )
                self.worker_queue.put(("update_downloaded", (info, path)))
            except Exception as exc:
                self.worker_queue.put(("update_error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_update_downloaded(self, payload: tuple[UpdateInfo, Path]) -> None:
        info, path = payload
        self._set_busy(False)
        self.progress_var.set(100)
        self.progress_text_var.set("Actualización lista")
        write_update_record(info, path)
        if not messagebox.askyesno(
            "Actualización lista",
            (
                f"La versión {info.version} fue descargada y verificada.\n\n"
                "La aplicación debe cerrarse para ejecutar el instalador. ¿Actualizar ahora?"
            ),
            parent=self,
        ):
            self._log(f"Instalador disponible para más tarde: {path}")
            return
        try:
            self._save_config()
            self._save_autosave_draft()
            launch_installer(path)
        except Exception as exc:
            messagebox.showerror("Actualizaciones", str(exc), parent=self)
            return
        self.after(300, self.destroy)

    def show_about(self) -> None:
        provider_id = str(self.config_data.get("processing_provider", "ollama_local"))
        messagebox.showinfo(
            "Acerca de Minutas ASH",
            (
                "Minutas ASH 2.3.4\n\n"
                "Gestión, revisión y emisión de minutas corporativas.\n"
                f"Método configurado: {provider_display_name(provider_id)}\n\n"
                "ASH Ingeniería y Proyectos"
            ),
            parent=self,
        )

    def save_settings(self) -> None:
        self._save_config()
        messagebox.showinfo("Configuración", "Configuración guardada.", parent=self)

    def open_output_folder(self) -> None:
        path = Path(self.output_dir_var.get().strip())
        path.mkdir(parents=True, exist_ok=True)
        self._open_path(path)

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("Abrir archivo", str(exc))

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{stamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.logger.info(message)

    def clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def load_project_catalog(self) -> None:
        projects = self.db.list_projects()
        if not projects:
            messagebox.showinfo(
                "Catálogo vacío",
                "Todavía no hay proyectos guardados.",
                parent=self,
            )
            return
        dialog = ProjectPickerDialog(self, projects)
        self.wait_window(dialog)
        if dialog.result:
            self.meta_vars["project_code"].set(dialog.result.get("code") or "")
            self.meta_vars["project_description"].set(dialog.result.get("description") or "")
            self.meta_vars["client"].set(dialog.result.get("client") or "")

    def save_contacts(self, silent: bool = False) -> None:
        for attendee in self.attendees:
            self.db.upsert_contact(attendee)
        if not silent:
            messagebox.showinfo(
                "Catálogo",
                f"Se guardaron {len(self.attendees)} contacto(s).",
                parent=self,
            )

    def add_from_contacts(self) -> None:
        contacts = self.db.list_contacts()
        if not contacts:
            messagebox.showinfo(
                "Catálogo vacío",
                "Todavía no hay contactos guardados.",
                parent=self,
            )
            return
        dialog = ContactPickerDialog(self, contacts)
        self.wait_window(dialog)
        if dialog.result:
            existing = {item.name.casefold() for item in self.attendees}
            if dialog.result.name.casefold() not in existing:
                self.attendees.append(dialog.result)
                self.renumber_attendees()

    def save_catalogs(self, silent: bool = False) -> None:
        try:
            metadata = self._metadata_from_form()
            for attendee in metadata.attendees:
                self.db.upsert_contact(attendee)
            self.db.upsert_project(
                metadata.project_code or "",
                metadata.project_description,
                metadata.client,
            )
            if not silent:
                messagebox.showinfo(
                    "Catálogos",
                    "Proyecto y asistentes guardados localmente.",
                    parent=self,
                )
        except Exception as exc:
            if not silent:
                messagebox.showerror("Catálogos", str(exc), parent=self)

    def _selected_history_id(self) -> int | None:
        selected = self.history_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def _refresh_history_tree(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        self.history_tree.delete(*self.history_tree.get_children())
        for row in self.db.list_meetings():
            self.history_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row.get("meeting_date") or "",
                    row.get("minute_number") or "",
                    row.get("project_code") or "",
                    row.get("matter") or "",
                    row.get("status") or "",
                    row.get("updated_at") or "",
                ),
            )

    def load_history_meeting(self) -> None:
        meeting_id = self._selected_history_id()
        if meeting_id is None:
            messagebox.showinfo("Historial", "Seleccione una reunión.", parent=self)
            return
        row = self.db.get_meeting(meeting_id)
        if not row:
            return
        try:
            metadata = MeetingMetadata.model_validate_json(row["metadata_json"])
            self._apply_metadata(metadata)
            self.vtt_var.set(row.get("source_vtt") or "")
            self.current_meeting_id = meeting_id
            analysis_json = row.get("analysis_json")
            if analysis_json:
                analysis = MinuteAnalysis.model_validate_json(analysis_json)
                source_path = Path(row.get("source_vtt") or "")
                segments = read_teams_vtt(source_path) if source_path.is_file() else []
                self.analysis_bundle = AnalysisBundle(
                    metadata=metadata,
                    analysis=analysis,
                    segments=segments,
                    source_path=source_path,
                    model=row.get("model") or self.model_var.get(),
                    provider_id=row.get("processing_provider") or "ollama_local",
                    provider_name=row.get("processing_provider_name")
                    or provider_display_name(row.get("processing_provider") or "ollama_local"),
                )
                self.items = [item.model_copy(deep=True) for item in analysis.items]
                self._refresh_items_tree()
                self.word_button.configure(state="normal")
            self.notebook.select(self.tab_meeting)
            self._log(f"Reunión cargada desde historial: {meeting_id}")
        except Exception as exc:
            messagebox.showerror("Historial", str(exc), parent=self)

    def open_history_document(self) -> None:
        meeting_id = self._selected_history_id()
        if meeting_id is None:
            return
        row = self.db.get_meeting(meeting_id)
        path = Path(row.get("docx_path") or "") if row else Path()
        if path.is_file():
            self._open_path(path)
        else:
            messagebox.showinfo(
                "Historial", "La reunión aún no tiene un Word disponible.", parent=self
            )

    def open_history_pdf(self) -> None:
        meeting_id = self._selected_history_id()
        if meeting_id is None:
            return
        row = self.db.get_meeting(meeting_id)
        path = Path(row.get("pdf_path") or "") if row else Path()
        if path.is_file():
            self._open_path(path)
        else:
            messagebox.showinfo(
                "Historial", "La reunión aún no tiene un PDF disponible.", parent=self
            )

    def open_history_folder(self) -> None:
        meeting_id = self._selected_history_id()
        if meeting_id is None:
            return
        row = self.db.get_meeting(meeting_id)
        path = Path(row.get("output_dir") or "") if row else Path()
        if path.is_dir():
            self._open_path(path)
        else:
            messagebox.showinfo(
                "Historial", "No se encontró la carpeta de la reunión.", parent=self
            )

    def cancel_analysis(self) -> None:
        if self.busy:
            self.cancel_requested = True
            job_id = getattr(self, "active_processing_job_id", "")
            if job_id:
                try:
                    self.processing_job_store.update(
                        job_id,
                        status="running",
                        progress=int(self.progress_var.get()),
                        message="Cancelacion solicitada; guardando avance",
                    )
                except (KeyError, OSError, TypeError, ValueError) as exc:
                    self.logger.warning("No se pudo guardar la cancelacion de %s: %s", job_id, exc)
            self.cancel_button.configure(state="disabled")
            self.progress_text_var.set("Cancelando solicitud actual y guardando avance...")
            self._log("Se solicitó cancelar la solicitud actual y conservar el avance.")

    def generate_diagnostic_report(self) -> None:
        try:
            self._save_config()
            path = save_diagnostic_bundle(self.config_data)
            self._log(f"Informe de diagnóstico generado: {path}")
            if messagebox.askyesno(
                "Diagnóstico generado",
                "El paquete ZIP sanitizado se generó correctamente. ¿Desea abrirlo?",
                parent=self,
            ):
                self._open_path(path)
        except Exception as exc:
            messagebox.showerror("Diagnóstico", str(exc), parent=self)

    def start_ollama_service(self) -> None:
        url = self.ollama_url_var.get().strip()
        self._log("Intentando iniciar el servicio local...")

        def worker() -> None:
            ok = start_ollama(
                url,
                log=lambda text: self.worker_queue.put(("log", text)),
                runtime_mode=str(self.config_data.get("runtime_mode", "auto")),
            )
            if ok:
                self.worker_queue.put(("log", "Servicio local disponible."))
            else:
                self.worker_queue.put(
                    ("log", "No fue posible iniciar el servicio local automáticamente.")
                )
            self.worker_queue.put(("refresh_ollama", None))

        threading.Thread(target=worker, daemon=True).start()

    def run_component_repair(self) -> None:
        if self.busy:
            return
        model = self.model_var.get().strip() or "qwen3:8b"
        url = self.ollama_url_var.get().strip()
        if not messagebox.askyesno(
            "Reparar componentes",
            "Se verificarán y actualizarán los componentes locales. "
            "Este proceso puede requerir conexión a Internet y descargar varios GB.\n\n"
            "¿Desea continuar?",
            parent=self,
        ):
            return

        self.notebook.select(self.tab_activity)
        self._log("Iniciando reparación de componentes...")
        self._set_busy(True)
        self.progress_var.set(1)
        self.progress_text_var.set("Preparando componentes")

        def worker() -> None:
            try:

                def runtime_progress(value: int, text: str) -> None:
                    mapped = int(value * 0.30)
                    self.worker_queue.put(("progress", (mapped, text)))

                ensure_runtime(
                    self.config_data,
                    progress=runtime_progress,
                    log=lambda text: self.worker_queue.put(("log", text)),
                )
                if not start_ollama(
                    url,
                    log=lambda text: self.worker_queue.put(("log", text)),
                    runtime_mode=str(self.config_data.get("runtime_mode", "auto")),
                    wait_seconds=45,
                ):
                    raise RuntimeError("No fue posible iniciar el servicio local.")

                def progress(value: int, _text: str) -> None:
                    mapped = 30 + int(value * 0.70)
                    self.worker_queue.put(
                        (
                            "progress",
                            (mapped, f"Actualizando componentes... {value}%"),
                        )
                    )

                pull_model_stream(
                    url,
                    model,
                    progress=progress,
                    log=lambda _text: None,
                )
                self.worker_queue.put(("model_installed", model))
            except Exception as exc:
                self.worker_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()

    # Compatibilidad con accesos internos de versiones anteriores.
    def install_selected_model(self) -> None:
        self.run_component_repair()

    def _draft_file(self) -> Path:
        return drafts_dir() / "ultima_sesion.json"

    def _save_autosave_draft(self) -> bool:
        try:
            metadata = self._metadata_from_form()
            payload = {
                "vtt_path": self.vtt_var.get().strip(),
                "metadata": metadata.model_dump(),
                "items": [item.model_dump() for item in self.items],
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            path = self._draft_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def _load_autosave_draft(self) -> None:
        path = self._draft_file()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            metadata = MeetingMetadata.model_validate(payload.get("metadata", {}))
            has_content = bool(
                metadata.minute_number or metadata.project_code or payload.get("vtt_path")
            )
            if not has_content:
                return
            if not messagebox.askyesno(
                "Recuperar sesión",
                "Se encontró una sesión guardada automáticamente. ¿Desea recuperarla?",
                parent=self,
            ):
                return
            self._apply_metadata(metadata)
            self.vtt_var.set(payload.get("vtt_path") or "")
            self.items = [MeetingItem.model_validate(item) for item in payload.get("items", [])]
            self._refresh_items_tree()
        except Exception as exc:
            self._log(f"No fue posible recuperar la sesión: {exc}")

    def _autosave_tick(self) -> None:
        self._save_autosave_draft()
        self.after(30000, self._autosave_tick)

    def _on_close(self) -> None:
        if self.busy and not messagebox.askyesno(
            "Proceso en ejecución",
            "Hay un proceso en curso. ¿Desea cerrar igualmente?",
            parent=self,
        ):
            return
        try:
            self._save_config()
            self._save_autosave_draft()
        except OSError:
            pass
        self.destroy()


def _parse_startup_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--provision", action="store_true")
    parser.add_argument("--launch-after", action="store_true")
    parser.add_argument("--provision-auto", action="store_true")
    parser.add_argument("--skip-setup-check", action="store_true")
    parser.add_argument("vtt", nargs="?", default=None)
    args, _unknown = parser.parse_known_args()
    return args


def main() -> int:
    args = _parse_startup_args()
    config = load_settings_dict()

    if args.provision_auto:
        return run_provisioning(config, launch_after=True)
    if args.provision:
        result = run_provisioning(config, launch_after=False)
        if result != 0:
            return result
        if not args.launch_after:
            return 0
    elif not args.skip_setup_check and not setup_is_complete(config):
        result = run_provisioning(config, launch_after=False)
        if result != 0:
            return result

    app = MinutasApp(initial_vtt=args.vtt)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
