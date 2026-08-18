"""Interfaz guiada de Minutas ASH 2.3.4.

La clase conserva los casos de uso estables de la línea 5.x, pero reorganiza
la experiencia en cuatro pasos: reunión, participantes, revisión y emisión.
Las capas de procesamiento, documentos y persistencia continúan desacopladas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import tkinter as tk
from copy import deepcopy
from datetime import UTC, date, datetime
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, cast

try:  # Arrastrar y soltar es una mejora opcional; la aplicación funciona sin ella.
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - depende del entorno del instalador.
    DND_FILES = None
    TkinterDnD = None

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import contextlib

from src.administration import open_administration
from src.audio_transcription import SUPPORTED_MEDIA_SUFFIXES, load_transcription_report
from src.backup_service import maybe_create_automatic_backup
from src.database import AppDatabase
from src.document_numbering import suggest_minute_number
from src.experience import (
    MEETING_TYPE_LABELS,
    attendee_display_columns,
    attendee_readiness,
    interface_mode_label,
    meeting_type_from_label,
    meeting_type_label,
    normalize_interface_mode,
    parse_drop_paths,
    review_display_columns,
    suggested_matter,
)
from src.help_center import open_help_center
from src.history_service import HistoryService
from src.inbox import scan_inbox
from src.learning_context import format_learning_examples
from src.legacy_gui import (
    ItemDialog,
    ProjectPickerDialog,
)
from src.legacy_gui import (
    MinutasApp as LegacyMinutasApp,
)
from src.media_preparation_dialog import MediaPreparationDialog
from src.media_transcription_service import (
    MediaTranscriptionRequest,
    preflight_media,
    transcribe_meeting_media,
)
from src.meeting_automation import (
    InboxAutomationStore,
    apply_exception_review,
    match_project_profile,
)
from src.meeting_sources import (
    SOURCE_QUALITY_LABELS,
    SOURCE_TYPE_LABELS,
    SourceQuality,
    SourceType,
    create_text_source,
    read_meeting_source,
    supported_filetypes,
)
from src.metadata import enrich_attendees
from src.models import Attendee, MeetingMetadata, MinuteAnalysis
from src.notification_service import notify_local
from src.observability import install_exception_hooks, operation
from src.processing_center import ProcessingCenterDialog
from src.project_profiles import ProjectProfile
from src.providers.registry import provider_display_name
from src.provisioning import run_provisioning, setup_is_complete
from src.release_identity import APP_VERSION, RELEASE_SEQUENCE
from src.review_actions import (
    apply_review_status,
    merge_review_items,
    restore_review_items,
    restore_review_statuses,
)
from src.review_quality import assess_item, items_for_document, summarize_review
from src.runtime_paths import cache_dir, inbox_dir, install_root
from src.settings import load_settings_dict
from src.source_dialogs import ManualSourceDialog
from src.teams_graph import TeamsGraphError
from src.teams_graph_service import TeamsGraphImportRequest, import_teams_transcripts
from src.template_service import TemplateService
from src.transcription_dialog import open_transcription_components
from src.ui_productivity import (
    history_matches,
    is_provisional_project_code,
    natural_sort_key,
    selection_range,
    unique_person_labels,
)
from src.ui_state import configure_resizable_window
from src.updater import UpdateInfo
from src.workflow import AnalysisBundle

APP_TITLE = f"Minutas ASH {APP_VERSION}"
DATE_HINT = "AAAA-MM-DD"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class GuidedMinutasApp(LegacyMinutasApp):
    """Aplicación principal con flujo guiado y revisión visual de calidad."""

    STEP_TABS = ("meeting", "attendees", "review", "emit")

    def __init__(self, initial_vtt: str | None = None) -> None:
        super().__init__(initial_vtt=initial_vtt)
        self.inbox_automation_store = InboxAutomationStore(inbox_dir() / ".automation-state.json")
        self._automated_source_path: Path | None = None
        self._automation_claim_scheduled = False
        self._automation_profile_score = 0.0
        self.title(APP_TITLE)
        self.bind_all("<Control-Shift-M>", lambda _event: self.toggle_interface_mode())
        self._enable_drop_support()
        self.template_service = TemplateService(self.db)
        self.history_service = HistoryService(self.db)
        self._apply_experience_mode(initial=True)
        self._refresh_project_choices()
        self._refresh_template_choices()
        self._run_automatic_backup()
        self._refresh_dashboard()
        self._refresh_emission_checklist()
        self._update_step_navigation()

    def _create_variables(self) -> None:
        super()._create_variables()
        default_type = str(self.config_data.get("default_meeting_type", "cliente"))
        self.meta_vars["meeting_type"] = tk.StringVar(value=default_type)
        self.meeting_type_display_var = tk.StringVar(value=meeting_type_label(default_type))
        self.interface_mode_var = tk.StringVar(
            value=normalize_interface_mode(self.config_data.get("interface_mode", "essential"))
        )
        self.advanced_fields_visible_var = tk.BooleanVar(
            value=bool(self.config_data.get("essential_show_advanced_fields", False))
        )
        self.document_type_var = tk.StringVar(
            value=str(self.config_data.get("numbering_document_type", "MRE"))
        )
        self.discipline_var = tk.StringVar(
            value=str(self.config_data.get("numbering_discipline", "PR"))
        )
        self.review_filter_var = tk.BooleanVar(
            value=bool(self.config_data.get("review_focus_attention", True))
        )
        self.review_search_var = tk.StringVar(value="")
        self.review_selected_var = tk.StringVar(value="0 seleccionados")
        self._review_undo_stack: list[tuple[str, str, Any]] = []
        self.review_detail_title_var = tk.StringVar(value="Seleccione un punto para revisarlo.")
        self.review_quality_var = tk.StringVar(value="")
        self.review_reasons_var = tk.StringVar(value="")
        self.review_progress_var = tk.StringVar(value="Sin puntos para revisar")
        self.attendee_summary_var = tk.StringVar(value="No hay participantes confirmados.")
        self.meeting_summary_var = tk.StringVar(
            value="Complete los datos esenciales de la reunión."
        )
        self.dashboard_total_var = tk.StringVar(value="0")
        self.dashboard_pending_var = tk.StringVar(value="0")
        self.dashboard_generated_var = tk.StringVar(value="0")
        self.emission_status_var = tk.StringVar(value="Complete los pasos anteriores.")
        self.emission_summary_var = tk.StringVar(value="")
        self.output_preview_var = tk.StringVar(value="")
        self.step_hint_var = tk.StringVar(value="Seleccione una acción para comenzar.")
        self.project_choice_var = self.meta_vars["project_code"]
        self.template_choice_var = tk.StringVar(value="Automática (recomendada)")
        self.template_choice_map: dict[str, dict | str | None] = {
            "Automática (recomendada)": None,
            "Formato ASH integrado": "standard",
        }
        self.template_summary_var = tk.StringVar(value="Formato: selección automática")
        self.source_type_var = tk.StringVar(value="vtt")
        self.source_quality_var = tk.StringVar(value="alta")
        self.source_status_var = tk.StringVar(value="Seleccione una fuente de reunión.")
        self.record_is_test_var = tk.BooleanVar(value=False)
        self.learning_sample_var = tk.BooleanVar(
            value=bool(self.config_data.get("learning_capture_enabled", True))
        )
        self.history_view_var = tk.StringVar(value="operational")
        self.history_status_var = tk.StringVar(value="Historial operativo")
        self.history_search_var = tk.StringVar(value="")
        self._review_drag_anchor: str | None = None
        self._attendee_drag_anchor: str | None = None
        self._history_drag_anchor: str | None = None

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Nueva minuta", accelerator="Ctrl+N", command=self.new_minute)
        file_menu.add_command(
            label="Abrir fuente de reunión...", accelerator="Ctrl+O", command=self.browse_vtt
        )
        file_menu.add_command(
            label="Pegar conversación o notas...",
            accelerator="Ctrl+Shift+V",
            command=self.open_manual_source_dialog,
        )
        file_menu.add_command(
            label="Guardar borrador", accelerator="Ctrl+S", command=self.save_draft
        )
        file_menu.add_command(
            label="Generar Word", accelerator="Ctrl+Shift+S", command=self.generate_document
        )
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self._on_close)
        menubar.add_cascade(label="Archivo", menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_radiobutton(
            label="Vista esencial",
            variable=self.interface_mode_var,
            value="essential",
            command=self._on_interface_mode_selected,
        )
        view_menu.add_radiobutton(
            label="Vista avanzada",
            variable=self.interface_mode_var,
            value="advanced",
            command=self._on_interface_mode_selected,
        )
        view_menu.add_separator()
        view_menu.add_command(label="Inicio", command=lambda: self.notebook.select(self.tab_home))
        view_menu.add_command(
            label="Historial", command=lambda: self._open_auxiliary_tab(self.tab_history)
        )
        view_menu.add_command(
            label="Configuración", command=lambda: self._open_auxiliary_tab(self.tab_settings)
        )
        view_menu.add_command(
            label="Actividad", command=lambda: self._open_auxiliary_tab(self.tab_activity)
        )
        menubar.add_cascade(label="Vista", menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(
            label="Procesar reunión", accelerator="F5", command=self.start_analysis
        )
        tools_menu.add_command(
            label="Verificar método de procesamiento", command=self.refresh_ollama_status
        )
        tools_menu.add_command(
            label="Centro de procesamiento...", command=self.open_processing_center
        )
        tools_menu.add_command(
            label="Reparar componentes locales", command=self.run_component_repair
        )
        tools_menu.add_command(
            label="Componentes opcionales de transcripción...",
            command=self.open_transcription_components,
        )
        tools_menu.add_command(label="Estado de salud...", command=self.show_health_panel)
        tools_menu.add_separator()
        tools_menu.add_command(label="Administración...", command=self.open_administration_center)
        tools_menu.add_command(
            label="Preferencias...", accelerator="Ctrl+,", command=self.open_preferences
        )
        tools_menu.add_command(
            label="Buscar actualizaciones...", command=lambda: self.check_updates(manual=True)
        )
        menubar.add_cascade(label="Herramientas", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(
            label="Centro de ayuda",
            accelerator="F1",
            command=lambda: self.open_help_topic("usuario"),
        )
        help_menu.add_command(
            label="Manual de usuario", command=lambda: self.open_help_topic("usuario")
        )
        help_menu.add_command(label="Atajos de teclado", command=self.show_keyboard_shortcuts)
        help_menu.add_command(
            label="Instalación y configuración",
            command=lambda: self.open_help_topic("configuracion"),
        )
        help_menu.add_command(
            label="Programación y depuración", command=lambda: self.open_help_topic("programador")
        )
        help_menu.add_separator()
        help_menu.add_command(label="Generar diagnóstico", command=self.generate_diagnostic_report)
        help_menu.add_command(label="Acerca de Minutas ASH", command=self.show_about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        self.configure(menu=menubar)
        self.bind_all("<Control-n>", lambda _event: self.new_minute())
        self.bind_all("<Control-o>", lambda _event: self.browse_vtt())
        self.bind_all("<Control-s>", lambda _event: self.save_draft())
        self.bind_all("<Control-Shift-s>", lambda _event: self.generate_document())
        self.bind_all("<Control-Shift-v>", lambda _event: self.open_manual_source_dialog())
        self.bind_all("<Control-comma>", lambda _event: self.open_preferences())
        self.bind_all("<Control-f>", lambda _event: self._focus_search())
        self.bind_all("<Control-Return>", lambda _event: self._continue_flow())
        self.bind_all("<F5>", lambda _event: self.start_analysis())
        self.bind_all("<F1>", lambda _event: self.open_help_topic("usuario"))

    def save_draft(self) -> None:
        """Guarda explícitamente el estado recuperable sin iniciar la emisión."""

        saved = self._save_autosave_draft()
        draft = self._draft_file()
        if saved:
            self.progress_text_var.set("Borrador guardado · puede continuar más tarde")
            self._log(f"Borrador guardado manualmente: {draft}")
        else:
            messagebox.showwarning(
                "Guardar borrador",
                "No fue posible guardar el borrador. Revise los datos ingresados.",
                parent=self,
            )

    def show_keyboard_shortcuts(self) -> None:
        messagebox.showinfo(
            "Atajos de teclado",
            """Atajos generales
Ctrl+N  Nueva minuta
Ctrl+O  Abrir fuente
Ctrl+S  Guardar borrador
Ctrl+Shift+S  Generar Word
Ctrl+F  Buscar en revisión o historial
Ctrl+Enter  Continuar
F5  Procesar reunión

Tablas
Ctrl+A  Seleccionar visibles
Shift+clic o arrastre  Seleccionar rango
Esc  Limpiar selección

Revisión
Enter o Espacio  Aprobar selección
F2  Corregir
Supr  Eliminar con deshacer
Ctrl+Z  Deshacer""",
            parent=self,
        )

    def _focus_search(self) -> str:
        if self.notebook.select() == str(self.tab_history):
            entry = self.history_search_entry
        else:
            if self.notebook.select() != str(self.tab_review):
                self.notebook.select(self.tab_review)
                self._update_step_navigation()
            entry = self.review_search_entry
        entry.focus_set()
        entry.selection_range(0, "end")
        return "break"

    @staticmethod
    def _select_all_tree(tree: ttk.Treeview, _event=None) -> str:
        children = tree.get_children("")
        if children:
            tree.selection_set(children)
            tree.focus(children[0])
            tree.see(children[0])
        return "break"

    @staticmethod
    def _clear_tree_selection(tree: ttk.Treeview, _event=None) -> str:
        tree.selection_remove(tree.selection())
        return "break"

    def _configure_sortable_heading(self, tree: ttk.Treeview, column: str, label: str) -> None:
        labels = cast(dict[str, str], getattr(tree, "_qol_heading_labels", {}))
        labels[column] = label
        cast(Any, tree)._qol_heading_labels = labels
        tree.heading(
            column,
            text=label,
            command=partial(self._sort_tree_by_column, tree, column, False),
        )

    def _sort_tree_by_column(self, tree: ttk.Treeview, column: str, reverse: bool = False) -> None:
        children = list(tree.get_children(""))
        children.sort(key=lambda iid: natural_sort_key(tree.set(iid, column)), reverse=reverse)
        for position, iid in enumerate(children):
            tree.move(iid, "", position)
        labels = cast(dict[str, str], getattr(tree, "_qol_heading_labels", {}))
        for key, label in labels.items():
            tree.heading(
                key,
                text=label + (" ▼" if reverse else " ▲") if key == column else label,
                command=partial(
                    self._sort_tree_by_column,
                    tree,
                    key,
                    not reverse if key == column else False,
                ),
            )

    def _copy_tree_selection(self, tree: ttk.Treeview, _event=None) -> str:
        selected = tree.selection()
        if not selected and tree.focus():
            selected = (tree.focus(),)
        if not selected:
            return "break"
        display = tuple(tree["displaycolumns"])
        columns = tuple(tree["columns"]) if display in {(), ("#all",)} else display
        headers = [str(tree.heading(column, "text")).rstrip(" ▲▼") for column in columns]
        lines = ["	".join(headers)]
        for iid in selected:
            lines.append("	".join(str(tree.set(iid, column)) for column in columns))
        self.clipboard_clear()
        self.clipboard_append(chr(10).join(lines))
        self.progress_text_var.set(f"{len(selected)} fila(s) copiadas al portapapeles")
        return "break"

    def _begin_tree_drag(self, tree: ttk.Treeview, attribute: str, event) -> None:
        if tree.identify_region(event.x, event.y) != "cell":
            setattr(self, attribute, None)
            return
        row = tree.identify_row(event.y)
        setattr(self, attribute, row or None)

    def _extend_tree_drag(self, tree: ttk.Treeview, attribute: str, event) -> str | None:
        anchor = cast(str | None, getattr(self, attribute, None))
        target = tree.identify_row(event.y)
        selected = selection_range(tree.get_children(""), anchor, target)
        if not selected:
            return None
        tree.selection_set(selected)
        tree.focus(target)
        tree.see(target)
        return "break"

    def _build_ui(self) -> None:
        self._build_menu()
        self._build_header()

        shell = ttk.Frame(self, padding=(16, 0, 16, 12))
        shell.pack(fill="both", expand=True)
        self._build_step_bar(shell)

        style = ttk.Style(self)
        with contextlib.suppress(tk.TclError):
            style.layout("Essential.TNotebook.Tab", [])
        self.notebook = ttk.Notebook(shell)
        self.notebook.pack(fill="both", expand=True, pady=(8, 0))
        self.notebook.bind("<<NotebookTabChanged>>", lambda _event: self._update_step_navigation())

        self.tab_home = ttk.Frame(self.notebook, padding=16)
        self.tab_meeting = ttk.Frame(self.notebook, padding=16)
        self.tab_attendees = ttk.Frame(self.notebook, padding=16)
        self.tab_review = ttk.Frame(self.notebook, padding=16)
        self.tab_emit = ttk.Frame(self.notebook, padding=16)
        self.tab_history = ttk.Frame(self.notebook, padding=16)
        self.tab_settings = ttk.Frame(self.notebook, padding=16)
        self.tab_activity = ttk.Frame(self.notebook, padding=16)

        self.notebook.add(self.tab_home, text="Inicio")
        self.notebook.add(self.tab_meeting, text="1. Reunión")
        self.notebook.add(self.tab_attendees, text="2. Participantes")
        self.notebook.add(self.tab_review, text="3. Revisión")
        self.notebook.add(self.tab_emit, text="4. Emitir")
        self.notebook.add(self.tab_history, text="Historial")
        self.notebook.add(self.tab_settings, text="Configuración")
        self.notebook.add(self.tab_activity, text="Actividad")

        self._build_home_tab()
        self._build_meeting_tab()
        self._build_attendees_tab()
        self._build_review_tab()
        self._build_emit_tab()
        self._build_history_tab()
        super()._build_settings_tab()
        super()._build_activity_tab()
        self._build_bottom_bar(shell)

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(20, 12), style="Header.TFrame")
        header.pack(fill="x")
        logo = install_root() / "assets" / "logo_ash.png"
        if not logo.is_file():
            from src.runtime_paths import resource_path

            logo = resource_path("assets/logo_ash.png")
        try:
            self.logo_image = tk.PhotoImage(file=str(logo)).subsample(3, 3)
            ttk.Label(header, image=self.logo_image, style="Surface.TLabel").pack(
                side="left", padx=(0, 16)
            )
        except tk.TclError:
            self.logo_image = None

        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text="Minutas ASH", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Preparación rápida y confiable de minutas corporativas",
            style="Subtitle.TLabel",
        ).pack(anchor="w")
        self.provider_label_widget = ttk.Label(
            title_box,
            textvariable=self.provider_summary_var,
            style="SurfaceMuted.TLabel",
        )
        self.provider_label_widget.pack(anchor="w", pady=(2, 0))

        status_box = ttk.Frame(header, style="Header.TFrame")
        status_box.pack(side="right", anchor="n")
        ttk.Label(
            status_box,
            text=f"Versión {APP_VERSION}",
            style="SurfaceMuted.TLabel",
        ).pack(anchor="e")
        self.mode_button = ttk.Button(
            status_box,
            text="Vista esencial",
            command=self.toggle_interface_mode,
        )
        self.mode_button.pack(anchor="e", pady=(4, 0))
        self.ollama_label = ttk.Label(
            status_box,
            textvariable=self.ollama_status_var,
            style="StatusBad.TLabel",
        )
        self.ollama_label.pack(anchor="e", pady=(4, 0))

    def _build_step_bar(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent, style="Surface.TFrame", padding=(10, 8))
        self.step_bar = bar
        bar.pack(fill="x")
        bar.columnconfigure(0, weight=1)
        button_row = ttk.Frame(bar, style="Surface.TFrame")
        button_row.grid(row=0, column=0, sticky="ew")
        self.step_buttons: dict[str, ttk.Button] = {}
        labels = (
            ("home", "Inicio"),
            ("meeting", "1  Reunión"),
            ("attendees", "2  Participantes"),
            ("review", "3  Revisión"),
            ("emit", "4  Emitir"),
        )
        for index, (key, label) in enumerate(labels):
            button_row.columnconfigure(index, weight=1)
            button = ttk.Button(
                button_row,
                text=label,
                style="Step.TButton",
                command=partial(self._select_step, key),
            )
            button.grid(row=0, column=index, sticky="ew", padx=3)
            self.step_buttons[key] = button
        ttk.Label(bar, textvariable=self.step_hint_var, style="SurfaceMuted.TLabel").grid(
            row=1, column=0, sticky="w", padx=4, pady=(6, 0)
        )

    def _build_bottom_bar(self, parent: ttk.Frame) -> None:
        bottom = ttk.Frame(parent, padding=(0, 10, 0, 0))
        bottom.pack(fill="x")
        status_box = ttk.Frame(bottom)
        status_box.pack(side="left", fill="x", expand=True)
        ttk.Label(status_box, textvariable=self.progress_text_var).pack(anchor="w")
        ttk.Label(
            status_box,
            textvariable=self.processing_metrics_var,
            style="Muted.TLabel",
        ).pack(anchor="w")
        self.progressbar = ttk.Progressbar(
            bottom,
            variable=self.progress_var,
            maximum=100,
            length=220,
        )
        self.progressbar.pack(side="left", padx=12)
        ttk.Button(
            bottom,
            text="Abrir carpeta",
            command=self.open_output_folder,
        ).pack(side="right")
        self.continue_button = ttk.Button(
            bottom,
            text="Continuar",
            style="Primary.TButton",
            command=self._continue_flow,
        )
        self.continue_button.pack(side="right", padx=8)
        self.back_button = ttk.Button(bottom, text="Atrás", command=self._back_flow)
        self.back_button.pack(side="right")
        self.cancel_button = ttk.Button(
            bottom,
            text="Cancelar proceso",
            command=self.cancel_analysis,
            state="disabled",
        )
        self.cancel_button.pack(side="right", padx=(0, 8))

    # ------------------------------------------------------------------
    # Inicio y flujo guiado
    # ------------------------------------------------------------------
    def _build_home_tab(self) -> None:
        tab = self.tab_home
        for column in (0, 1, 2):
            tab.columnconfigure(column, weight=1)
        ttk.Label(tab, text="Panel de trabajo", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            tab,
            text="Cree una minuta, continúe una revisión o consulte documentos anteriores.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        quick = ttk.LabelFrame(tab, text="Inicio rápido", padding=18)
        quick.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        ttk.Button(
            quick,
            text="Crear nueva minuta",
            style="Primary.TButton",
            command=self.new_minute,
        ).pack(side="left")
        ttk.Button(
            quick,
            text="Seleccionar fuente",
            command=self._select_source,
        ).pack(side="left", padx=8)
        ttk.Button(
            quick,
            text="Continuar pendiente",
            command=self._continue_pending_meeting,
        ).pack(side="left")
        self.inbox_button = ttk.Button(quick, text="Bandeja", command=self._open_inbox)
        self.inbox_button.pack(side="left", padx=8)
        self.after(1200, self._refresh_inbox)
        ttk.Label(
            quick,
            text="Puede abrir transcripciones, documentos, audio o video, o pegar notas manuales.",
            style="Muted.TLabel",
        ).pack(side="right")

        cards = (
            (
                "Minutas registradas",
                self.dashboard_total_var,
                lambda: self._open_auxiliary_tab(self.tab_history),
            ),
            ("Pendientes de emitir", self.dashboard_pending_var, self._continue_pending_meeting),
            (
                "Documentos generados",
                self.dashboard_generated_var,
                lambda: self._open_auxiliary_tab(self.tab_history),
            ),
        )
        for column, (title, variable, command) in enumerate(cards):
            card = ttk.LabelFrame(tab, text=title, padding=14)
            card.grid(row=3, column=column, sticky="nsew", padx=6)
            ttk.Label(card, textvariable=variable, style="DashboardValue.TLabel").pack()
            ttk.Button(card, text="Abrir", command=command).pack(pady=(8, 0))

        recent_box = ttk.LabelFrame(tab, text="Actividad reciente", padding=10)
        recent_box.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(14, 0))
        tab.rowconfigure(4, weight=1)
        recent_box.rowconfigure(0, weight=1)
        recent_box.columnconfigure(0, weight=1)
        columns = ("date", "number", "project", "matter", "status")
        self.recent_tree = ttk.Treeview(recent_box, columns=columns, show="headings", height=6)
        for key, label, width in (
            ("date", "Fecha", 100),
            ("number", "N.º minuta", 190),
            ("project", "Proyecto", 100),
            ("matter", "Materia", 360),
            ("status", "Estado", 110),
        ):
            self._configure_sortable_heading(self.recent_tree, key, label)
            self.recent_tree.column(key, width=width, anchor="w")
        self.recent_tree.grid(row=0, column=0, sticky="nsew")
        self.recent_tree.bind("<Double-1>", lambda _event: self._load_recent_selected())
        self.recent_tree.bind("<Return>", lambda _event: self._load_recent_selected())
        self.recent_tree.bind(
            "<Control-c>", lambda event: self._copy_tree_selection(self.recent_tree, event)
        )
        footer = ttk.Frame(recent_box)
        footer.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(footer, text="Cargar selección", command=self._load_recent_selected).pack(
            side="right"
        )
        ttk.Button(
            footer,
            text="Historial completo",
            command=lambda: self._open_auxiliary_tab(self.tab_history),
        ).pack(side="right", padx=8)

    def _refresh_dashboard(self) -> None:
        if not hasattr(self, "dashboard_total_var"):
            return
        try:
            stats = self.db.dashboard_stats()
        except Exception as exc:
            self._log(
                f"Panel: no fue posible calcular indicadores rápidos; se usó el recuento compatible ({exc})."
            )
            rows = self.db.list_meetings(limit=5000)
            stats = {
                "total": len(rows),
                "pending_review": sum(row.get("status") == "procesada" for row in rows),
                "generated": sum(row.get("status") == "generada" for row in rows),
            }
        self.dashboard_total_var.set(str(stats.get("total", 0)))
        self.dashboard_pending_var.set(str(stats.get("pending_review", 0)))
        self.dashboard_generated_var.set(str(stats.get("generated", 0)))
        if hasattr(self, "recent_tree"):
            self.recent_tree.delete(*self.recent_tree.get_children())
            limit = (
                int(self.config_data.get("essential_recent_limit", 5))
                if self._is_essential_mode()
                else int(self.config_data.get("recent_project_limit", 8))
            )
            for row in self.db.list_meetings(limit=limit, view="operational"):
                self.recent_tree.insert(
                    "",
                    "end",
                    iid=str(row["id"]),
                    values=(
                        row.get("meeting_date") or "",
                        row.get("minute_number") or "",
                        row.get("project_code") or "",
                        row.get("matter") or "",
                        row.get("status") or "",
                    ),
                )

    def _load_recent_selected(self) -> None:
        selected = self.recent_tree.selection() if hasattr(self, "recent_tree") else ()
        if not selected:
            messagebox.showinfo("Actividad reciente", "Seleccione una reunión.", parent=self)
            return
        self._load_meeting_record(int(selected[0]))

    def _is_essential_mode(self) -> bool:
        return normalize_interface_mode(self.interface_mode_var.get()) == "essential"

    def _is_advanced_mode(self) -> bool:
        return not self._is_essential_mode()

    def _on_interface_mode_selected(self) -> None:
        self._apply_experience_mode()
        self.config_data["interface_mode"] = normalize_interface_mode(self.interface_mode_var.get())
        try:
            from src.settings import save_settings_dict

            self.config_data = save_settings_dict(self.config_data)
        except Exception as exc:
            self._log(f"No se pudo guardar la vista seleccionada: {exc}")

    def toggle_interface_mode(self) -> None:
        self.interface_mode_var.set("advanced" if self._is_essential_mode() else "essential")
        self._on_interface_mode_selected()

    def _apply_experience_mode(self, initial: bool = False) -> None:
        if not hasattr(self, "notebook"):
            return
        mode = normalize_interface_mode(self.interface_mode_var.get())
        self.interface_mode_var.set(mode)
        if mode == "essential":
            with contextlib.suppress(tk.TclError):
                self.notebook.configure(style="Essential.TNotebook")
            if (
                bool(self.config_data.get("guided_mode", True))
                and not self.step_bar.winfo_ismapped()
            ):
                self.step_bar.pack(fill="x", before=self.notebook)
            self.mode_button.configure(text="Avanzada")
            if self.provider_label_widget.winfo_ismapped():
                self.provider_label_widget.pack_forget()
            if self.notebook.select() in {str(self.tab_settings), str(self.tab_activity)}:
                self.notebook.select(self.tab_home)
        else:
            with contextlib.suppress(tk.TclError):
                self.notebook.configure(style="TNotebook")
            self.step_bar.pack_forget()
            self.mode_button.configure(text="Esencial")
            if not self.provider_label_widget.winfo_ismapped():
                self.provider_label_widget.pack(anchor="w", pady=(2, 0))
        if hasattr(self, "attendee_tree"):
            self.attendee_tree.configure(displaycolumns=attendee_display_columns(mode))
        if hasattr(self, "item_tree"):
            self.item_tree.configure(displaycolumns=review_display_columns(mode))
        self._update_advanced_field_visibility()
        self._refresh_dashboard()
        self._refresh_attendees_tree()
        self._refresh_items_tree()
        self._update_step_navigation()
        if not initial:
            self.progress_text_var.set(interface_mode_label(mode))

    def _open_auxiliary_tab(self, tab: ttk.Frame) -> None:
        self.notebook.select(tab)
        self._update_step_navigation()

    def _continue_pending_meeting(self) -> None:
        rows = self.db.list_meetings(limit=500, view="operational")
        pending = next((row for row in rows if row.get("status") == "procesada"), None)
        if pending is None:
            messagebox.showinfo(
                "Minutas pendientes",
                "No hay minutas procesadas pendientes de emisión.",
                parent=self,
            )
            return
        self._load_meeting_record(int(pending["id"]))

    def new_minute(self) -> None:
        meaningful_keys = (
            "minute_number",
            "matter",
            "project_code",
            "project_description",
            "client",
            "minute_taker",
            "approved_by",
        )
        has_content = (
            any(self.meta_vars[key].get().strip() for key in meaningful_keys)
            or self.vtt_var.get().strip()
            or bool(self.items)
        )
        if has_content and not messagebox.askyesno(
            "Nueva minuta",
            "Se limpiará la sesión actual. La recuperación automática conservará el último borrador. ¿Continuar?",
            parent=self,
        ):
            return
        today = date.today().isoformat()
        for variable in self.meta_vars.values():
            variable.set("")
        default_type = str(self.config_data.get("default_meeting_type", "cliente"))
        self.meta_vars["meeting_type"].set(default_type)
        self.meeting_type_display_var.set(meeting_type_label(default_type))
        self.meta_vars["document_date"].set(today)
        self.meta_vars["meeting_date"].set(today)
        self.meta_vars["location"].set("Microsoft Teams")
        self.meta_vars["minute_taker_date"].set(today)
        self.meta_vars["matter"].set(suggested_matter(default_type))
        if bool(self.config_data.get("remember_last_minute_taker", True)):
            self.meta_vars["minute_taker"].set(
                str(self.config_data.get("default_minute_taker", "")).strip()
            )
        self.document_type_var.set(str(self.config_data.get("numbering_document_type", "MRE")))
        self.discipline_var.set(str(self.config_data.get("numbering_discipline", "PR")))
        self.vtt_var.set("")
        self.source_type_var.set("vtt")
        self.source_quality_var.set("alta")
        self.record_is_test_var.set(False)
        self.learning_sample_var.set(bool(self.config_data.get("learning_capture_enabled", True)))
        self._update_source_status()
        self.attendees = []
        self.items = []
        self.analysis_bundle = None
        self.current_meeting_id = None
        self.last_docx = None
        self.review_summary_var.set("Seleccione una transcripción para comenzar.")
        self.advanced_fields_visible_var.set(
            bool(self.config_data.get("essential_show_advanced_fields", False))
        )
        self._refresh_attendees_tree()
        self._refresh_items_tree()
        self._refresh_emission_checklist()
        self._update_advanced_field_visibility()
        self._update_meeting_summary()
        self._select_step("meeting")

    def _select_step(self, step: str) -> None:
        mapping = {
            "home": self.tab_home,
            "meeting": self.tab_meeting,
            "attendees": self.tab_attendees,
            "review": self.tab_review,
            "emit": self.tab_emit,
        }
        if step in mapping:
            self.notebook.select(mapping[step])
            self._update_step_navigation()

    def _refresh_inbox(self) -> None:
        try:
            directory = inbox_dir()
            directory.mkdir(parents=True, exist_ok=True)
            if bool(self.config_data.get("inbox_automation_enabled", False)):
                ready_items = self.inbox_automation_store.discover(
                    directory,
                    max_retries=int(self.config_data.get("inbox_automation_max_retries", 3)),
                    recursive=bool(self.config_data.get("inbox_scan_recursively", True)),
                    max_files=int(self.config_data.get("inbox_scan_max_files", 500)),
                )
                if ready_items and not self.busy and not self._automation_claim_scheduled:
                    self._automation_claim_scheduled = True
                    self.after_idle(self._consume_automated_inbox)
            else:
                ready_items = [
                    item
                    for item in scan_inbox(
                        directory,
                        recursive=bool(self.config_data.get("inbox_scan_recursively", True)),
                        max_files=int(self.config_data.get("inbox_scan_max_files", 500)),
                    )
                    if item.ready
                ]
            if hasattr(self, "inbox_button"):
                self.inbox_button.configure(text=f"Bandeja ({len(ready_items)})")
        except OSError as exc:
            self._log(f"No se pudo actualizar la bandeja: {exc}")
        finally:
            self.after(10000, self._refresh_inbox)

    def _consume_automated_inbox(self) -> None:
        self._automation_claim_scheduled = False
        if self.busy or self._automated_source_path is not None:
            return
        candidates = self.inbox_automation_store.discover(
            inbox_dir(),
            max_retries=int(self.config_data.get("inbox_automation_max_retries", 3)),
            recursive=bool(self.config_data.get("inbox_scan_recursively", True)),
            max_files=int(self.config_data.get("inbox_scan_max_files", 500)),
        )
        if not candidates:
            return
        path = candidates[0].path
        try:
            duplicate = self.db.find_meeting_by_source_sha256(_sha256_file(path))
        except Exception as exc:
            self._log(
                "Automatización: no fue posible comprobar el hash contra el historial; "
                f"se continuará con una revisión manual posterior ({exc})."
            )
            duplicate = None
        if duplicate:
            self.inbox_automation_store.mark(
                path, "completed", "Fuente ya registrada en el historial"
            )
            self._log(f"Automatizacion: se omitio una fuente duplicada: {path.name}")
            return
        self._automated_source_path = path
        self.inbox_automation_store.mark(path, "processing", "Preparando fuente")
        self._log(f"Automatizacion: preparando {path.name}.")
        accepted = self._accept_input_path(path)
        if not accepted:
            self.inbox_automation_store.mark(path, "failed", "No fue posible abrir la fuente")
            self._automated_source_path = None
            return
        if path.suffix.casefold() not in SUPPORTED_MEDIA_SUFFIXES:
            self.after_idle(self._prepare_automated_source)

    def _prepare_automated_source(self) -> None:
        path = self._automated_source_path
        if path is None:
            return
        profiles = self.db.list_projects()
        match = match_project_profile(path, profiles)
        self._automation_profile_score = match.score
        if match.profile and match.score >= 0.70:
            self.meta_vars["project_code"].set(str(match.profile.get("code") or ""))
            self.apply_project_profile(match.profile)
            self._log(
                f"Automatizacion: perfil {match.profile.get('code')} aplicado "
                f"({match.score * 100:.0f} % de coincidencia)."
            )
        else:
            self._log(
                "Automatizacion: no se identifico un perfil de proyecto con suficiente certeza."
            )
        self.inbox_automation_store.mark(path, "prepared", "Fuente cargada y perfil evaluado")
        if bool(self.config_data.get("inbox_auto_start_processing", False)):
            try:
                self._metadata_from_form()
            except Exception as exc:
                self._log(f"Automatizacion detenida para completar datos: {exc}")
                self._automated_source_path = None
                self._select_step("meeting")
                return
            self._log("Automatizacion: iniciando analisis.")
            self.start_analysis()
            if not self.busy:
                self._automated_source_path = None
        else:
            self._automated_source_path = None
            self._select_step("meeting")

    def _open_inbox(self) -> None:
        directory = inbox_dir()
        directory.mkdir(parents=True, exist_ok=True)
        ready = [
            item
            for item in scan_inbox(
                directory,
                recursive=bool(self.config_data.get("inbox_scan_recursively", True)),
                max_files=int(self.config_data.get("inbox_scan_max_files", 500)),
            )
            if item.ready
        ]
        if not ready:
            messagebox.showinfo(
                "Bandeja de entrada",
                "No hay archivos listos. Copie una transcripción, audio o video en la carpeta que se abrirá.",
                parent=self,
            )
            self._open_path(directory)
            return
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de la bandeja",
            initialdir=str(directory),
            filetypes=supported_filetypes(),
        )
        if path:
            self._accept_input_path(Path(path))

    def _select_source(self) -> None:
        self._select_step("meeting")
        self.browse_vtt()

    def _current_step(self) -> str | None:
        selected = self.notebook.select()
        mapping = {
            str(self.tab_home): "home",
            str(self.tab_meeting): "meeting",
            str(self.tab_attendees): "attendees",
            str(self.tab_review): "review",
            str(self.tab_emit): "emit",
        }
        return mapping.get(selected)

    def _update_step_navigation(self) -> None:
        if not hasattr(self, "continue_button"):
            return
        step = self._current_step()
        hints = {
            "home": "Seleccione una acción para comenzar.",
            "meeting": "Paso 1 de 4 · Seleccione la transcripción y confirme los datos esenciales.",
            "attendees": "Paso 2 de 4 · Revise solamente los participantes incompletos.",
            "review": "Paso 3 de 4 · Atienda primero los puntos marcados en rojo o amarillo.",
            "emit": "Paso 4 de 4 · Compruebe el resumen y genere el documento.",
        }
        self.step_hint_var.set(hints.get(step or "", "Seleccione una acción para comenzar."))
        if step == "meeting":
            self.back_button.configure(state="normal", text="Inicio")
            self.continue_button.configure(text="Continuar a participantes", state="normal")
        elif step == "attendees":
            self.back_button.configure(state="normal", text="Atrás")
            self.continue_button.configure(text="Procesar y revisar", state="normal")
        elif step == "review":
            self.back_button.configure(state="normal", text="Atrás")
            self.continue_button.configure(text="Continuar a emisión", state="normal")
        elif step == "emit":
            self.back_button.configure(state="normal", text="Atrás")
            self.continue_button.configure(text="Generar Word", state="normal")
            self._refresh_emission_checklist()
        else:
            self.back_button.configure(state="disabled", text="Atrás")
            self.continue_button.configure(text="Crear nueva minuta", state="normal")
        self._update_step_button_labels()

    def _update_step_button_labels(self) -> None:
        if not hasattr(self, "step_buttons"):
            return
        meeting_ok = bool(
            self.vtt_var.get().strip()
            and not is_provisional_project_code(self.meta_vars["project_code"].get())
        )
        attendees_ok = bool(self.attendees)
        review = summarize_review(self.items)
        review_ok = bool(self.items) and review.pending == 0
        emit_ok = self.last_docx is not None and self.last_docx.is_file()
        statuses = {
            "home": False,
            "meeting": meeting_ok,
            "attendees": attendees_ok,
            "review": review_ok,
            "emit": emit_ok,
        }
        titles = {
            "home": "Inicio",
            "meeting": "1  Reunión",
            "attendees": "2  Participantes",
            "review": "3  Revisión",
            "emit": "4  Emitir",
        }
        for key, button in self.step_buttons.items():
            button.configure(text=(("✓  " if statuses[key] else "") + titles[key]))

    def _back_flow(self) -> None:
        step = self._current_step()
        if step in {"meeting", "home"} or step is None:
            self.notebook.select(self.tab_home)
        elif step == "attendees":
            self._select_step("meeting")
        elif step == "review":
            self._select_step("attendees")
        elif step == "emit":
            self._select_step("review")

    def _continue_flow(self) -> None:
        step = self._current_step()
        if step in {None, "home"}:
            self.new_minute()
            return
        if step == "meeting":
            if not self._validate_meeting_step():
                return
            self.detect_speakers(switch_tab=False)
            self._select_step("attendees")
        elif step == "attendees":
            self.start_analysis()
        elif step == "review":
            if not self._can_continue_from_review():
                return
            self._select_step("emit")
        elif step == "emit":
            self.generate_document()

    # ------------------------------------------------------------------
    # Paso 1: reunión y catálogos
    # ------------------------------------------------------------------
    def _build_meeting_tab(self) -> None:
        tab = self.tab_meeting
        tab.columnconfigure(0, weight=1)

        source = ttk.LabelFrame(tab, text="Fuente de la reunión", padding=14)
        source.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        source.columnconfigure(0, weight=1)
        self.drop_zone = ttk.Label(
            source,
            text="Seleccione o arrastre VTT, SRT, TXT, DOCX, PDF, audio o video",
            style="Section.TLabel",
            anchor="center",
            padding=(18, 16),
            relief="solid",
        )
        self.drop_zone.grid(row=0, column=0, columnspan=6, sticky="ew")
        self.drop_zone.bind("<Button-1>", lambda _event: self.browse_vtt())
        ttk.Entry(source, textvariable=self.vtt_var).grid(
            row=1, column=0, sticky="ew", pady=(10, 0)
        )
        ttk.Button(source, text="Examinar...", command=self.browse_vtt).grid(
            row=1, column=1, padx=(8, 0), pady=(10, 0)
        )
        ttk.Button(source, text="Pegar / notas...", command=self.open_manual_source_dialog).grid(
            row=1, column=2, padx=(8, 0), pady=(10, 0)
        )
        ttk.Button(source, text="Teams / Graph...", command=self.import_from_teams_graph).grid(
            row=1, column=3, padx=(8, 0), pady=(10, 0)
        )
        ttk.Button(source, text="Detectar participantes", command=self.detect_speakers).grid(
            row=1, column=4, padx=(8, 0), pady=(10, 0)
        )
        ttk.Button(source, text="Vista previa", command=self._preview_source).grid(
            row=1, column=5, padx=(8, 0), pady=(10, 0)
        )
        ttk.Label(source, textvariable=self.source_status_var, style="Muted.TLabel").grid(
            row=2, column=0, columnspan=6, sticky="w", pady=(6, 0)
        )

        essential = ttk.LabelFrame(
            tab, text="Datos esenciales para generar el documento", padding=14
        )
        essential.grid(row=1, column=0, sticky="ew")
        for column in (1, 3):
            essential.columnconfigure(column, weight=1)

        ttk.Label(essential, text="Tipo de reunión *").grid(row=0, column=0, sticky="w", pady=6)
        type_combo = ttk.Combobox(
            essential,
            textvariable=self.meeting_type_display_var,
            values=list(MEETING_TYPE_LABELS.values()),
            state="readonly",
        )
        type_combo.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=6)
        type_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_meeting_type_changed())

        ttk.Label(essential, text="Proyecto / cartera *").grid(row=0, column=2, sticky="w", pady=6)
        self.project_combo = ttk.Combobox(essential, textvariable=self.project_choice_var)
        self.project_combo.grid(row=0, column=3, sticky="ew", pady=6)
        self.project_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_project_profile())
        self.project_combo.bind("<FocusOut>", lambda _event: self._maybe_suggest_number())

        ttk.Label(essential, text="Materia *").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(essential, textvariable=self.meta_vars["matter"]).grid(
            row=1, column=1, sticky="ew", padx=(0, 14), pady=6
        )
        ttk.Label(essential, text="Fecha reunión *").grid(row=1, column=2, sticky="w", pady=6)
        ttk.Entry(essential, textvariable=self.meta_vars["meeting_date"]).grid(
            row=1, column=3, sticky="ew", pady=6
        )

        ttk.Label(essential, text="Minuta tomada por *").grid(row=2, column=0, sticky="w", pady=6)
        taker_box = ttk.Frame(essential)
        taker_box.grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=6)
        taker_box.columnconfigure(0, weight=1)
        ttk.Entry(taker_box, textvariable=self.meta_vars["minute_taker"]).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(taker_box, text="Usar participante", command=self._choose_minute_taker).grid(
            row=0, column=1, padx=(6, 0)
        )
        ttk.Label(essential, text="Fecha documento *").grid(row=2, column=2, sticky="w", pady=6)
        ttk.Entry(essential, textvariable=self.meta_vars["document_date"]).grid(
            row=2, column=3, sticky="ew", pady=6
        )

        ttk.Label(essential, text="N.º de minuta").grid(row=3, column=0, sticky="w", pady=6)
        number_box = ttk.Frame(essential)
        number_box.grid(row=3, column=1, sticky="ew", padx=(0, 14), pady=6)
        number_box.columnconfigure(0, weight=1)
        ttk.Entry(number_box, textvariable=self.meta_vars["minute_number"]).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(number_box, text="Sugerir", command=self.suggest_minute_number).grid(
            row=0, column=1, padx=(6, 0)
        )
        ttk.Label(essential, text="Resumen").grid(row=3, column=2, sticky="nw", pady=6)
        ttk.Label(
            essential,
            textvariable=self.meeting_summary_var,
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=3, column=3, sticky="w", pady=6)

        toggle_row = ttk.Frame(tab)
        toggle_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.advanced_fields_button = ttk.Button(
            toggle_row, text="Mostrar más datos", command=self._toggle_advanced_fields
        )
        self.advanced_fields_button.pack(side="left")
        ttk.Label(
            toggle_row,
            text="Los datos obligatorios permanecen visibles; aquí se ocultan solo campos complementarios.",
            style="Muted.TLabel",
        ).pack(side="left", padx=10)

        self.advanced_details_frame = ttk.LabelFrame(
            tab, text="Datos adicionales y configuración documental", padding=14
        )
        self.advanced_details_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        for column in (1, 3):
            self.advanced_details_frame.columnconfigure(column, weight=1)
        fields = [
            ("Descripción proyecto", "project_description", 0, 0),
            ("Cliente", "client", 0, 2),
            ("Lugar", "location", 1, 0),
            ("Fecha elaboración", "minute_taker_date", 1, 2),
            ("Minuta aprobada por", "approved_by", 2, 0),
            ("Fecha aprobación", "approval_date", 2, 2),
        ]
        for label, key, row, column in fields:
            ttk.Label(self.advanced_details_frame, text=label).grid(
                row=row, column=column, sticky="w", pady=6
            )
            ttk.Entry(self.advanced_details_frame, textvariable=self.meta_vars[key]).grid(
                row=row, column=column + 1, sticky="ew", padx=(0, 14), pady=6
            )
        ttk.Label(self.advanced_details_frame, text="Tipo documental").grid(
            row=3, column=0, sticky="w", pady=6
        )
        ttk.Entry(self.advanced_details_frame, textvariable=self.document_type_var, width=12).grid(
            row=3, column=1, sticky="w", pady=6
        )
        ttk.Label(self.advanced_details_frame, text="Disciplina").grid(
            row=3, column=2, sticky="w", pady=6
        )
        ttk.Entry(self.advanced_details_frame, textvariable=self.discipline_var, width=12).grid(
            row=3, column=3, sticky="w", pady=6
        )
        ttk.Checkbutton(
            self.advanced_details_frame,
            text="Marcar este registro como prueba (no cuenta en indicadores ni aprendizaje)",
            variable=self.record_is_test_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Checkbutton(
            self.advanced_details_frame,
            text="Guardar correcciones aprobadas como ejemplos locales",
            variable=self.learning_sample_var,
        ).grid(row=4, column=2, columnspan=2, sticky="w", pady=6)
        ttk.Label(self.advanced_details_frame, text="Formato documental").grid(
            row=5, column=0, sticky="w", pady=6
        )
        self.template_combo = ttk.Combobox(
            self.advanced_details_frame,
            textvariable=self.template_choice_var,
            state="readonly",
            width=44,
        )
        self.template_combo.grid(row=5, column=1, columnspan=3, sticky="ew", pady=6)
        self.template_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self._update_template_summary()
        )
        ttk.Label(
            self.advanced_details_frame,
            textvariable=self.template_summary_var,
            style="Muted.TLabel",
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(2, 0))

        controls = ttk.Frame(tab)
        controls.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(controls, text="Cargar proyecto", command=self.load_project_catalog).pack(
            side="left"
        )
        ttk.Button(controls, text="Guardar perfil", command=self.save_catalogs).pack(
            side="left", padx=8
        )
        self.advanced_file_controls = ttk.Frame(controls)
        self.advanced_file_controls.pack(side="left")
        ttk.Button(
            self.advanced_file_controls, text="Cargar ficha JSON", command=self.load_metadata_file
        ).pack(side="left")
        ttk.Button(
            self.advanced_file_controls, text="Guardar ficha JSON", command=self.save_metadata_file
        ).pack(side="left", padx=8)
        ttk.Label(controls, text=f"Formato de fecha: {DATE_HINT}", style="Muted.TLabel").pack(
            side="right"
        )

        for key in (
            "minute_number",
            "project_code",
            "project_description",
            "client",
            "matter",
            "meeting_date",
            "document_date",
            "minute_taker",
            "approved_by",
        ):
            self.meta_vars[key].trace_add("write", lambda *_args: self._update_meeting_summary())
        self._update_meeting_summary()
        self._update_advanced_field_visibility()

    def import_from_teams_graph(self) -> None:
        """Importa una transcripción autorizada y la entrega al flujo normal."""

        client_id = simpledialog.askstring(
            "Microsoft Teams",
            "Id. de aplicación (cliente) de Microsoft Entra:",
            initialvalue=str(self.config_data.get("teams_graph_client_id", "")),
            parent=self,
        )
        if not client_id or not client_id.strip():
            return
        tenant_id = simpledialog.askstring(
            "Microsoft Teams",
            "Id. o dominio del tenant (use 'organizations' para multitenant):",
            initialvalue=str(self.config_data.get("teams_graph_tenant_id", "organizations")),
            parent=self,
        )
        if tenant_id is None:
            return
        join_url = simpledialog.askstring(
            "Microsoft Teams",
            "Pegue el enlace para unirse a la reunión:",
            parent=self,
        )
        if not join_url or not join_url.strip():
            return
        self.config_data["teams_graph_enabled"] = True
        self.config_data["teams_graph_client_id"] = client_id.strip()
        self.config_data["teams_graph_tenant_id"] = tenant_id.strip() or "organizations"
        try:
            from src.settings import save_settings_dict

            self.config_data = save_settings_dict(self.config_data)
        except Exception as exc:
            self._log(f"No se pudieron guardar las preferencias públicas de Graph: {exc}")
        self._set_busy(True)
        self.progress_var.set(5)
        self.progress_text_var.set("Abriendo inicio de sesión de Microsoft 365...")
        self._log("Microsoft Graph: iniciando autorización interactiva de solo lectura.")

        def worker() -> None:
            try:
                imported = import_teams_transcripts(
                    TeamsGraphImportRequest(
                        client_id=client_id,
                        tenant_id=tenant_id or "organizations",
                        join_url=join_url,
                        inbox_path=inbox_dir(),
                        state_path=cache_dir() / "teams-graph-state.json",
                        timeout_seconds=int(
                            self.config_data.get("teams_graph_timeout_seconds", 60)
                        ),
                    )
                )
                if not imported:
                    raise TeamsGraphError(
                        "La transcripción ya estaba importada; no se creó un duplicado."
                    )
                self.worker_queue.put(
                    ("log", f"Microsoft Graph: {len(imported)} transcripción(es) importada(s).")
                )
                self.worker_queue.put(("media_transcribed", imported[-1].path))
            except Exception as exc:
                self.worker_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def _choose_minute_taker(self) -> None:
        names = [item.name for item in self.attendees if item.name.strip()]
        if not names:
            messagebox.showinfo(
                "Responsable de la minuta",
                "Detecte o agregue participantes primero, o escriba el nombre manualmente.",
                parent=self,
            )
            return
        current = self.meta_vars["minute_taker"].get().strip() or names[0]
        value = simpledialog.askstring(
            "Responsable de la minuta",
            "Ingrese o copie el nombre del participante que prepara la minuta:\n\n"
            + "\n".join(f"• {name}" for name in names),
            initialvalue=current,
            parent=self,
        )
        if value and value.strip():
            self.meta_vars["minute_taker"].set(value.strip())

    def _on_meeting_type_changed(self) -> None:
        key = meeting_type_from_label(self.meeting_type_display_var.get())
        self.meta_vars["meeting_type"].set(key)
        current = self.meta_vars["matter"].get().strip()
        known_defaults = {suggested_matter(value) for value in MEETING_TYPE_LABELS}
        if not current or current in known_defaults:
            self.meta_vars["matter"].set(suggested_matter(key))
        self._update_meeting_summary()

    def _toggle_advanced_fields(self) -> None:
        self.advanced_fields_visible_var.set(not self.advanced_fields_visible_var.get())
        self._update_advanced_field_visibility()

    def _update_advanced_field_visibility(self) -> None:
        if not hasattr(self, "advanced_details_frame"):
            return
        show = self._is_advanced_mode() or bool(self.advanced_fields_visible_var.get())
        if show:
            self.advanced_details_frame.grid()
            self.advanced_fields_button.configure(text="Ocultar datos adicionales")
        else:
            self.advanced_details_frame.grid_remove()
            self.advanced_fields_button.configure(text="Mostrar más datos")
        if self._is_advanced_mode():
            self.advanced_fields_button.pack_forget()
            self.advanced_file_controls.pack(side="left")
        else:
            if not self.advanced_fields_button.winfo_ismapped():
                self.advanced_fields_button.pack(side="left")
            if show:
                self.advanced_file_controls.pack(side="left")
            else:
                self.advanced_file_controls.pack_forget()

    def _update_meeting_summary(self) -> None:
        if not hasattr(self, "meeting_summary_var"):
            return
        client = self.meta_vars["client"].get().strip() or "cliente por confirmar"
        number = self.meta_vars["minute_number"].get().strip() or "número automático pendiente"
        taker = self.meta_vars["minute_taker"].get().strip() or "redactor por confirmar"
        self.meeting_summary_var.set(f"{client} · {number} · {taker}")

    def _metadata_from_form(self) -> MeetingMetadata:
        self.meta_vars["meeting_type"].set(
            meeting_type_from_label(self.meeting_type_display_var.get())
        )
        metadata = super()._metadata_from_form()
        source_type = self.source_type_var.get()
        source_quality = self.source_quality_var.get()
        metadata.source_type = (
            cast(SourceType, source_type) if source_type in SOURCE_TYPE_LABELS else "vtt"
        )
        metadata.source_quality = (
            cast(SourceQuality, source_quality)
            if source_quality in SOURCE_QUALITY_LABELS
            else "media"
        )
        record = self._selected_template_record(metadata)
        if isinstance(record, dict):
            metadata.template_version_id = int(record["id"])
            metadata.template_key = str(record["template_key"])
            metadata.template_version = str(record["version_label"])
        else:
            metadata.template_version_id = None
            metadata.template_key = "ash_integrated" if record == "standard" else None
            metadata.template_version = "integrada" if record == "standard" else None
        return metadata

    def _apply_metadata(self, metadata: MeetingMetadata) -> None:
        super()._apply_metadata(metadata)
        self.meeting_type_display_var.set(meeting_type_label(metadata.meeting_type))
        self.source_type_var.set(metadata.source_type)
        self.source_quality_var.set(metadata.source_quality)
        self._update_source_status()
        if metadata.template_version_id:
            self._select_template_version(metadata.template_version_id)
        elif metadata.template_key == "ash_integrated":
            self.template_choice_var.set("Formato ASH integrado")
        else:
            self.template_choice_var.set("Automática (recomendada)")
        self._update_template_summary()
        self._update_meeting_summary()

    def _validate_meeting_step(self) -> bool:
        path = Path(self.vtt_var.get().strip())
        try:
            source = read_meeting_source(path, self.source_type_var.get() or None)
            self.source_type_var.set(source.source_type)
            self.source_quality_var.set(source.quality)
            self._update_source_status(source)
        except Exception as exc:
            messagebox.showwarning("Fuente de reunión", str(exc), parent=self)
            return False
        today = date.today().isoformat()
        self.meta_vars["document_date"].set(self.meta_vars["document_date"].get().strip() or today)
        self.meta_vars["location"].set(
            self.meta_vars["location"].get().strip() or "Microsoft Teams"
        )
        self.meta_vars["minute_taker_date"].set(
            self.meta_vars["minute_taker_date"].get().strip()
            or self.meta_vars["document_date"].get().strip()
        )
        if not self.meta_vars["matter"].get().strip():
            self.meta_vars["matter"].set(suggested_matter(self.meta_vars["meeting_type"].get()))
        if not self.meta_vars["minute_taker"].get().strip() and self.attendees:
            preferred = next(
                (
                    item
                    for item in self.attendees
                    if (item.organization or "").strip().casefold() == "ash"
                ),
                self.attendees[0],
            )
            self.meta_vars["minute_taker"].set(preferred.name)
        required = (
            ("Código de proyecto", self.meta_vars["project_code"].get()),
            ("Materia", self.meta_vars["matter"].get()),
            ("Fecha de reunión", self.meta_vars["meeting_date"].get()),
            ("Fecha de documento", self.meta_vars["document_date"].get()),
            ("Minuta tomada por", self.meta_vars["minute_taker"].get()),
        )
        missing = [label for label, value in required if not value.strip()]
        if missing:
            messagebox.showwarning(
                "Datos requeridos",
                "Complete los siguientes datos esenciales visibles en esta pantalla:\n\n- "
                + "\n- ".join(missing),
                parent=self,
            )
            return False
        project_code = self.meta_vars["project_code"].get().strip()
        if is_provisional_project_code(project_code):
            messagebox.showwarning(
                "Código de proyecto provisional",
                "Reemplace el valor provisional por el código real del proyecto o cartera. "
                "No se generará una numeración basada en '0'.",
                parent=self,
            )
            if hasattr(self, "project_combo"):
                self.project_combo.focus_set()
            return False
        if not self.meta_vars["minute_number"].get().strip():
            self.suggest_minute_number(silent=True)
        return True

    def _refresh_project_choices(self) -> None:
        if not hasattr(self, "project_combo"):
            return
        projects = self.db.list_projects()
        self.project_combo.configure(values=[row.get("code") or "" for row in projects])

    def suggest_minute_number(self, silent: bool = False) -> str | None:
        code = self.meta_vars["project_code"].get().strip()
        if not code:
            if not silent:
                messagebox.showinfo(
                    "Numeración", "Ingrese primero el código del proyecto.", parent=self
                )
            return None
        try:
            value = suggest_minute_number(
                self.db,
                code,
                self.document_type_var.get().strip() or "MRE",
                self.discipline_var.get().strip() or "PR",
                int(self.config_data.get("numbering_digits", 2)),
            )
            self.meta_vars["minute_number"].set(value)
            self._update_step_button_labels()
            return value
        except Exception as exc:
            if not silent:
                messagebox.showerror("Numeración", str(exc), parent=self)
            return None

    def _maybe_suggest_number(self) -> None:
        if (
            bool(self.config_data.get("numbering_auto_suggest", True))
            and not self.meta_vars["minute_number"].get().strip()
        ):
            self.suggest_minute_number(silent=True)

    def apply_project_profile(self, project: dict | None = None) -> None:
        code = self.meta_vars["project_code"].get().strip().upper()
        if not code:
            return
        row = project or self.db.get_project(code)
        if not row:
            self._maybe_suggest_number()
            return
        mapping = {
            "project_code": row.get("code"),
            "project_description": row.get("description"),
            "client": row.get("client"),
            "approved_by": row.get("approver"),
            "minute_taker": row.get("default_minute_taker") or row.get("project_manager"),
            "location": row.get("default_location"),
        }
        for key, value in mapping.items():
            if value:
                self.meta_vars[key].set(str(value))
        self.document_type_var.set(
            str(row.get("document_type") or self.config_data.get("numbering_document_type", "MRE"))
        )
        self.discipline_var.set(
            str(row.get("discipline") or self.config_data.get("numbering_discipline", "PR"))
        )
        template_version_id = row.get("template_version_id")
        if template_version_id:
            self._select_template_version(int(template_version_id))
        else:
            self.template_choice_var.set("Automática (recomendada)")
        self._update_template_summary()
        members = self.db.list_project_members(code)
        if members:
            existing = {item.name.casefold() for item in self.attendees}
            for member in members:
                if member.name.casefold() not in existing:
                    self.attendees.append(member)
                    existing.add(member.name.casefold())
            self.renumber_attendees()
        self._maybe_suggest_number()

    def load_project_catalog(self) -> None:
        projects = self.db.list_projects()
        if not projects:
            messagebox.showinfo(
                "Catálogo vacío", "Todavía no hay proyectos guardados.", parent=self
            )
            return
        dialog = ProjectPickerDialog(self, projects)
        self.wait_window(dialog)
        if dialog.result:
            self.meta_vars["project_code"].set(dialog.result.get("code") or "")
            self.apply_project_profile(dialog.result)

    def save_catalogs(self, silent: bool = False) -> None:
        try:
            metadata = self._metadata_from_form()
            if not metadata.project_code:
                raise ValueError("Ingrese un código de proyecto antes de guardar el perfil.")
            for attendee in metadata.attendees:
                self.db.upsert_contact(attendee)
            profile = ProjectProfile(
                code=metadata.project_code,
                description=metadata.project_description,
                client=metadata.client,
                project_manager=metadata.minute_taker,
                approver=metadata.approved_by,
                default_minute_taker=metadata.minute_taker,
                default_location=metadata.location or "Microsoft Teams",
                document_type=self.document_type_var.get().strip() or "MRE",
                discipline=self.discipline_var.get().strip() or "PR",
                template_version_id=metadata.template_version_id,
                default_attendee_names=[item.name for item in metadata.attendees],
            )
            self.db.upsert_project_profile(profile.model_dump())
            self.db.set_project_members(profile.code, profile.default_attendee_names)
            self._refresh_project_choices()
            if not silent:
                messagebox.showinfo(
                    "Perfil guardado",
                    "El proyecto, sus datos predeterminados y participantes frecuentes quedaron guardados.",
                    parent=self,
                )
        except Exception as exc:
            if not silent:
                messagebox.showerror("Catálogos", str(exc), parent=self)

    def _preview_source(self) -> None:
        path = Path(self.vtt_var.get().strip())
        if not path.is_file():
            messagebox.showinfo(
                "Vista previa", "Seleccione primero una fuente de reunión.", parent=self
            )
            return
        if path.suffix.casefold() in SUPPORTED_MEDIA_SUFFIXES:
            messagebox.showinfo(
                "Vista previa",
                "El audio o video debe transcribirse antes de mostrar su contenido.",
                parent=self,
            )
            return
        try:
            source = read_meeting_source(path, self.source_type_var.get() or None)
        except Exception as exc:
            messagebox.showerror("Vista previa", str(exc), parent=self)
            return
        window = tk.Toplevel(self)
        window.title("Vista previa de la fuente")
        configure_resizable_window(window, self, "source_preview", "920x640", (680, 420))
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        quality = SOURCE_QUALITY_LABELS.get(source.quality, source.quality)
        ttk.Label(frame, text=f"{source.display_name} · {quality}", style="Section.TLabel").pack(
            anchor="w"
        )
        if source.warnings:
            ttk.Label(
                frame,
                text="\n".join(source.warnings),
                style="Muted.TLabel",
                wraplength=820,
                justify="left",
            ).pack(anchor="w", pady=(4, 8))
        text = ScrolledText(frame, wrap="word")
        text.pack(fill="both", expand=True)
        self.appearance_manager.configure_text_widget(text, fixed=False)
        for segment in source.segments[:80]:
            text.insert("end", f"[{segment.start}] {segment.speaker}\n{segment.text}\n\n")
        if len(source.segments) > 80:
            text.insert("end", f"… {len(source.segments) - 80} segmentos adicionales.")
        text.configure(state="disabled")
        ttk.Button(frame, text="Cerrar", command=window.destroy).pack(anchor="e", pady=(10, 0))

    def browse_vtt(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar fuente de reunión",
            filetypes=supported_filetypes(),
        )
        if path:
            self._accept_input_path(Path(path))

    def _accept_input_path(self, path: Path) -> bool:
        if path.suffix.casefold() not in SUPPORTED_MEDIA_SUFFIXES:
            return self._accept_source_path(path)
        if self.busy:
            return False
        try:
            preflight = preflight_media(
                path, cpu_threads=int(self.config_data.get("whisper_cpu_threads", 0))
            )
            for warning in preflight.warnings:
                self._log(f"Preflight multimedia: {warning}")
            dialog = MediaPreparationDialog(
                self,
                path,
                preflight_summary=preflight.summary,
                preflight_warnings=preflight.warnings,
            )
        except (OSError, ValueError) as exc:
            self._log(f"No se pudo completar el preflight multimedia: {exc}")
            dialog = MediaPreparationDialog(self, path)
        self.wait_window(dialog)
        if dialog.result is None:
            return False
        preparation = dialog.result
        self._set_busy(True)
        self.progress_var.set(5)
        self.progress_text_var.set(
            "Preparando audio para transcripción..."
            if preparation.optimize
            else "Transcribiendo audio o video..."
        )
        self._log(f"Transcripción multimedia iniciada: {path}")

        def worker() -> None:
            try:
                result = transcribe_meeting_media(
                    MediaTranscriptionRequest(
                        source_path=path,
                        optimize_audio=preparation.optimize,
                        output_format=preparation.output_format,
                        delete_source=preparation.delete_source,
                        model_name=str(self.config_data.get("whisper_model", "base")),
                        language=str(self.config_data.get("transcription_language", "es")),
                        cpu_threads=int(self.config_data.get("whisper_cpu_threads", 0)),
                        diarization_enabled=bool(
                            self.config_data.get("diarization_enabled", False)
                        ),
                        diarization_worker=str(self.config_data.get("diarization_worker_path", ""))
                        or None,
                    )
                )
                if result.preparation is not None:
                    prepared = result.preparation
                    self.worker_queue.put(
                        (
                            "log",
                            "Audio preparado: "
                            f"{prepared.output_path.name} ({prepared.output_bytes / 1024 / 1024:.1f} MB).",
                        )
                    )
                self.worker_queue.put(("media_transcribed", result.transcript_path))
            except Exception as exc:
                self.worker_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()
        return True

    def open_manual_source_dialog(self) -> None:
        dialog = ManualSourceDialog(
            self,
            default_name=self.meta_vars["project_code"].get().strip() or "reunion",
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            source = create_text_source(
                dialog.result["text"],
                source_type=dialog.result["source_type"],
                suggested_name=dialog.result.get("name") or "reunion",
            )
            self._accept_source_path(
                source.path, preferred_type=source.source_type, preloaded=source
            )
        except Exception as exc:
            messagebox.showerror("Fuente manual", str(exc), parent=self)

    # Nombre histórico conservado para compatibilidad con accesos directos y pruebas.
    def _accept_vtt_path(self, path: Path) -> bool:
        report = load_transcription_report(path)
        if report:
            self.source_quality_var.set(report.level)
            detail = " · ".join(report.reasons) or "sin advertencias"
            self._log(
                f"Transcripción: calidad {report.level}; idioma "
                f"{report.language or 'no identificado'}; {detail}"
            )
        accepted = self._accept_source_path(path)
        automated = self._automated_source_path
        if (
            accepted
            and automated is not None
            and automated.suffix.casefold() in SUPPORTED_MEDIA_SUFFIXES
        ):
            self.after_idle(self._prepare_automated_source)
        return accepted

    def _accept_source_path(
        self,
        path: Path,
        preferred_type: str | None = None,
        preloaded=None,
    ) -> bool:
        candidate = path.expanduser()
        try:
            source = preloaded or read_meeting_source(candidate, preferred_type)
        except Exception as exc:
            messagebox.showwarning("Fuente de reunión", str(exc), parent=self)
            return False
        candidate = source.path.resolve()
        if bool(self.config_data.get("duplicate_source_warning", True)):
            try:
                row = self.db.find_meeting_by_source_sha256(_sha256_file(candidate))
            except Exception:
                row = None
            if row and messagebox.askyesno(
                "Fuente ya procesada",
                (
                    "Esta fuente coincide con una reunión del historial.\n\n"
                    f"Minuta: {row.get('minute_number') or 'sin número'}\n"
                    f"Estado: {row.get('status') or 'desconocido'}\n\n"
                    "¿Desea cargar esa revisión en lugar de procesarla nuevamente?"
                ),
                parent=self,
            ):
                self._load_meeting_record(int(row["id"]))
                return True
        self.vtt_var.set(str(candidate))
        self.source_type_var.set(source.source_type)
        self.source_quality_var.set(source.quality)
        self._update_source_status(source)
        self.current_meeting_id = None
        self.analysis_bundle = None
        self.items.clear()
        self.review_summary_var.set("Fuente seleccionada. Confirme los datos y continúe.")
        self._refresh_items_tree()
        self.word_button.configure(state="disabled")
        self._log(f"Fuente de reunión seleccionada ({source.display_name}): {candidate}")
        for warning in source.warnings:
            self._log(f"Advertencia de fuente: {warning}")
        if bool(self.config_data.get("quick_detect_participants", True)):
            try:
                self.detect_speakers(switch_tab=False)
            except Exception as exc:
                self._log(f"No se pudieron detectar participantes automáticamente: {exc}")
        self._select_step("meeting")
        self._update_step_button_labels()
        return True

    def _update_source_status(self, source=None) -> None:
        source_type = getattr(source, "source_type", None) or self.source_type_var.get() or "vtt"
        quality = getattr(source, "quality", None) or self.source_quality_var.get() or "media"
        label = SOURCE_TYPE_LABELS.get(source_type, source_type)
        quality_label = SOURCE_QUALITY_LABELS.get(quality, quality)
        self.source_status_var.set(f"Fuente: {label} · Calidad inicial: {quality_label}")
        if hasattr(self, "drop_zone"):
            self.drop_zone.configure(
                text=f"{label} cargada"
                if self.vtt_var.get().strip()
                else "Seleccione o arrastre VTT, SRT, TXT, DOCX, PDF, audio o video"
            )

    def _enable_drop_support(self) -> None:
        if not hasattr(self, "drop_zone") or TkinterDnD is None or DND_FILES is None:
            return
        try:
            TkinterDnD._require(self)
            drop_zone = cast(Any, self.drop_zone)
            drop_zone.drop_target_register(DND_FILES)
            drop_zone.dnd_bind("<<Drop>>", self._on_vtt_drop)
        except Exception as exc:
            self._log(f"Arrastrar y soltar no disponible: {exc}")

    def _on_vtt_drop(self, event) -> str:
        try:
            paths = list(self.tk.splitlist(event.data))
        except Exception:
            paths = parse_drop_paths(getattr(event, "data", ""))
        for raw in paths:
            candidate = Path(str(raw).strip())
            if candidate.suffix.casefold() in (
                {".vtt", ".txt", ".docx"} | SUPPORTED_MEDIA_SUFFIXES
            ) and self._accept_input_path(candidate):
                return "break"
        messagebox.showwarning(
            "Fuente de reunión", "Arrastre VTT, TXT, DOCX, audio o video.", parent=self
        )
        return "break"

    def detect_speakers(self, switch_tab: bool = True) -> None:
        path = Path(self.vtt_var.get().strip())
        try:
            source = read_meeting_source(path, self.source_type_var.get() or None)
            self.source_type_var.set(source.source_type)
            self.source_quality_var.set(source.quality)
            self._update_source_status(source)
            speakers = unique_person_labels(segment.speaker for segment in source.segments)
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
            if not self.meta_vars["minute_taker"].get().strip() and self.attendees:
                preferred = next(
                    (
                        item
                        for item in self.attendees
                        if (item.organization or "").strip().casefold() == "ash"
                    ),
                    self.attendees[0],
                )
                self.meta_vars["minute_taker"].set(preferred.name)
            if switch_tab:
                self.notebook.select(self.tab_attendees)
            self._log(f"Participantes detectados y agregados: {len(speakers)}")
        except Exception as exc:
            messagebox.showerror("No fue posible detectar participantes", str(exc), parent=self)

    def _technical_dictionary_context(self) -> str:
        """Construye contexto de vocabulario sin exponer controles internos al usuario esencial."""
        project_code = self.meta_vars["project_code"].get().strip().upper()
        try:
            terms = self.db.list_technical_terms(project_code)[:100]
        except Exception as exc:
            self._log(f"No se pudo cargar el diccionario técnico: {exc}")
            return ""
        lines: list[str] = []
        for row in terms:
            canonical = " ".join(str(row.get("canonical_term") or "").split()).strip()
            if not canonical:
                continue
            try:
                variants = json.loads(row.get("variants_json") or "[]")
            except (TypeError, json.JSONDecodeError):
                variants = []
            safe_variants = [
                " ".join(str(value).split()).strip() for value in variants if str(value).strip()
            ]
            category = " ".join(str(row.get("category") or "").split()).strip()
            project = " ".join(str(row.get("project_code") or "").split()).strip()
            detail = f"{canonical}"
            if safe_variants:
                detail += " ← variantes: " + ", ".join(safe_variants[:8])
            if category:
                detail += f" | categoría: {category}"
            if project:
                detail += f" | proyecto: {project}"
            lines.append("- " + detail)
        return "\n".join(lines)[:4000]

    def _approved_learning_context(self) -> str:
        if not bool(self.config_data.get("learning_retrieval_enabled", True)):
            return ""
        method = getattr(self.db, "list_learning_examples", None)
        if not callable(method):
            return ""
        try:
            examples = method(
                self.meta_vars["project_code"].get().strip() or None,
                self.meta_vars["meeting_type"].get().strip() or None,
                int(self.config_data.get("learning_retrieval_limit", 3)),
                client=self.meta_vars["client"].get().strip() or None,
                query_text=self.meta_vars["matter"].get().strip() or None,
            )
            return format_learning_examples(examples)
        except Exception as exc:
            self._log(f"No se pudieron recuperar ejemplos aprobados: {exc}")
            return ""

    def start_analysis(self) -> None:
        if self.busy:
            return
        if not self._validate_meeting_step():
            return
        vocabulary = self._technical_dictionary_context()
        examples = self._approved_learning_context()
        sections: list[str] = []
        if vocabulary:
            sections.append("DICCIONARIO TÉCNICO:\n" + vocabulary)
        if examples:
            sections.append("PATRONES DE EJEMPLOS APROBADOS:\n" + examples)
            self._log("Se usarán ejemplos aprobados similares como referencia de clasificación.")
        self.config_data["technical_dictionary_context"] = "\n\n".join(sections)
        super().start_analysis()

    def _build_attendees_tab(self) -> None:
        tab = self.tab_attendees
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=1)
        summary = ttk.Frame(tab)
        summary.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        text_box = ttk.Frame(summary)
        text_box.pack(side="left", fill="x", expand=True)
        ttk.Label(
            text_box,
            text="Confirme solamente los participantes marcados para revisar.",
            style="Section.TLabel",
        ).pack(anchor="w")
        ttk.Label(text_box, textvariable=self.attendee_summary_var, style="Muted.TLabel").pack(
            anchor="w", pady=(3, 0)
        )
        ttk.Button(summary, text="Detectar desde fuente", command=self.detect_speakers).pack(
            side="right"
        )
        ttk.Button(summary, text="Cargar del proyecto", command=self.apply_project_profile).pack(
            side="right", padx=6
        )

        columns = ("id", "initials", "name", "email", "role", "organization", "status")
        self.attendee_tree = ttk.Treeview(
            tab, columns=columns, show="headings", selectmode="extended"
        )
        specs = (
            ("id", "Id", 45),
            ("initials", "Iniciales", 75),
            ("name", "Nombre", 240),
            ("email", "Correo", 210),
            ("role", "Cargo", 220),
            ("organization", "Organización", 150),
            ("status", "Estado", 100),
        )
        for key, label, width in specs:
            self._configure_sortable_heading(self.attendee_tree, key, label)
            self.attendee_tree.column(key, width=width, anchor="w")
        self.attendee_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.attendee_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.attendee_tree.configure(yscrollcommand=scroll.set)
        self.attendee_tree.bind("<Double-1>", lambda _event: self.edit_attendee())
        self.attendee_tree.bind("<Return>", lambda _event: self.edit_attendee())
        self.attendee_tree.bind("<F2>", lambda _event: self.edit_attendee())
        self.attendee_tree.bind("<Delete>", lambda _event: self.delete_attendee())
        self.attendee_tree.bind(
            "<Control-a>", lambda event: self._select_all_tree(self.attendee_tree, event)
        )
        self.attendee_tree.bind(
            "<Control-A>", lambda event: self._select_all_tree(self.attendee_tree, event)
        )
        self.attendee_tree.bind(
            "<Control-c>", lambda event: self._copy_tree_selection(self.attendee_tree, event)
        )
        self.attendee_tree.bind(
            "<Escape>", lambda event: self._clear_tree_selection(self.attendee_tree, event)
        )
        self.attendee_tree.bind("<Button-3>", self._show_attendee_context_menu)
        self.attendee_tree.bind(
            "<ButtonPress-1>",
            lambda event: self._begin_tree_drag(self.attendee_tree, "_attendee_drag_anchor", event),
            add="+",
        )
        self.attendee_tree.bind(
            "<B1-Motion>",
            lambda event: self._extend_tree_drag(
                self.attendee_tree, "_attendee_drag_anchor", event
            ),
            add="+",
        )

        buttons = ttk.Frame(tab)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Agregar", command=self.add_attendee).pack(side="left")
        ttk.Button(buttons, text="Editar", command=self.edit_attendee).pack(side="left", padx=6)
        ttk.Button(buttons, text="Eliminar", command=self.delete_attendee).pack(side="left")
        ttk.Button(
            buttons,
            text="Completar primer pendiente",
            command=self._select_first_incomplete_attendee,
        ).pack(side="left", padx=(12, 0))
        self.advanced_attendee_controls = ttk.Frame(buttons)
        self.advanced_attendee_controls.pack(side="left", padx=6)
        ttk.Button(
            self.advanced_attendee_controls,
            text="Agregar desde contactos",
            command=self.add_from_contacts,
        ).pack(side="left")
        ttk.Button(
            self.advanced_attendee_controls, text="Guardar contactos", command=self.save_contacts
        ).pack(side="left", padx=6)
        self.analyze_button = ttk.Button(
            buttons,
            text="Procesar reunión",
            style="Primary.TButton",
            command=self.start_analysis,
        )
        self.analyze_button.pack(side="right")
        self.attendee_tree.configure(
            displaycolumns=attendee_display_columns(self.interface_mode_var.get())
        )

    def _selected_attendee_indices(self) -> list[int]:
        result: list[int] = []
        for iid in self.attendee_tree.selection():
            try:
                result.append(int(iid))
            except (TypeError, ValueError):
                continue
        return sorted(set(result))

    def edit_attendee(self) -> None:
        selected = self._selected_attendee_indices()
        if len(selected) > 1:
            messagebox.showinfo(
                "Participantes",
                "Seleccione una sola persona para editarla. Use Supr para eliminar varias.",
                parent=self,
            )
            return
        super().edit_attendee()
        self._save_autosave_draft()

    def delete_attendee(self) -> None:
        indices = self._selected_attendee_indices()
        if not indices:
            return
        names = [self.attendees[index].name for index in indices if index < len(self.attendees)]
        separator = chr(10)
        preview = separator.join(f"• {name}" for name in names[:5])
        if len(names) > 5:
            preview += f"{separator}• … y {len(names) - 5} más"
        message = f"¿Eliminar {len(indices)} participante(s)?{separator * 2}{preview}"
        if not messagebox.askyesno(
            "Eliminar participantes",
            message,
            parent=self,
        ):
            return
        for index in reversed(indices):
            if 0 <= index < len(self.attendees):
                self.attendees.pop(index)
        self.renumber_attendees()
        self._save_autosave_draft()
        self.progress_text_var.set(f"Se eliminaron {len(indices)} participante(s)")

    def _show_attendee_context_menu(self, event) -> None:
        row = self.attendee_tree.identify_row(event.y)
        if row and row not in self.attendee_tree.selection():
            self.attendee_tree.selection_set(row)
            self.attendee_tree.focus(row)
        menu = tk.Menu(self.attendee_tree, tearoff=False)
        menu.add_command(label="Editar    Enter/F2", command=self.edit_attendee)
        menu.add_command(label="Eliminar selección    Supr", command=self.delete_attendee)
        menu.add_command(
            label="Copiar selección    Ctrl+C",
            command=lambda: self._copy_tree_selection(self.attendee_tree),
        )
        menu.add_separator()
        menu.add_command(
            label="Seleccionar todos    Ctrl+A",
            command=lambda: self._select_all_tree(self.attendee_tree),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _select_first_incomplete_attendee(self) -> None:
        for index, attendee in enumerate(self.attendees):
            if not attendee_readiness(attendee).complete:
                self.attendee_tree.selection_set(str(index))
                self.attendee_tree.focus(str(index))
                self.attendee_tree.see(str(index))
                self.edit_attendee()
                return
        messagebox.showinfo(
            "Participantes", "Todos los participantes están completos.", parent=self
        )

    def _build_review_tab(self) -> None:
        tab = self.tab_review
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=1)

        top = ttk.Frame(tab)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(0, weight=1)
        summary_box = ttk.Frame(top)
        summary_box.grid(row=0, column=0, columnspan=4, sticky="ew")
        ttk.Label(
            summary_box,
            textvariable=self.review_summary_var,
            style="Section.TLabel",
            wraplength=780,
            justify="left",
        ).pack(anchor="w")
        ttk.Label(summary_box, textvariable=self.review_progress_var, style="Muted.TLabel").pack(
            anchor="w", pady=(3, 0)
        )
        controls_row = ttk.Frame(top)
        controls_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        controls_row.columnconfigure(0, weight=1)
        search_box = ttk.Frame(controls_row)
        search_box.grid(row=0, column=0, sticky="w")
        ttk.Label(search_box, text="Buscar").pack(side="left")
        self.review_search_entry = ttk.Entry(
            search_box, textvariable=self.review_search_var, width=24
        )
        self.review_search_entry.pack(side="left", padx=6)
        self.review_search_entry.bind("<KeyRelease>", lambda _event: self._refresh_items_tree())
        ttk.Button(search_box, text="Limpiar", command=self._clear_review_search).pack(side="left")
        ttk.Button(
            controls_row, text="Siguiente que requiere atención", command=self._next_attention_item
        ).grid(row=0, column=1, padx=8)
        ttk.Checkbutton(
            controls_row,
            text="Solo requiere atención",
            variable=self.review_filter_var,
            command=self._refresh_items_tree,
        ).grid(row=0, column=2)

        pane = ttk.Panedwindow(tab, orient="horizontal")
        pane.grid(row=1, column=0, sticky="nsew")
        left = ttk.Frame(pane)
        right = ttk.Frame(pane, padding=(12, 0, 0, 0))
        pane.add(left, weight=3)
        pane.add(right, weight=2)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        columns = (
            "n",
            "status",
            "quality",
            "project",
            "category",
            "description",
            "responsible",
            "date",
        )
        self.item_tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="extended")
        specs = (
            ("n", "N.º", 48),
            ("status", "Estado", 90),
            ("quality", "Calidad", 110),
            ("project", "Proyecto", 90),
            ("category", "Categoría", 100),
            ("description", "Descripción", 420),
            ("responsible", "Responsable", 160),
            ("date", "Fecha/plazo", 125),
        )
        for key, label, width in specs:
            self._configure_sortable_heading(self.item_tree, key, label)
            self.item_tree.column(key, width=width, anchor="w")
        self.item_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.item_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        hscroll = ttk.Scrollbar(left, orient="horizontal", command=self.item_tree.xview)
        hscroll.grid(row=1, column=0, sticky="ew")
        self.item_tree.configure(yscrollcommand=scroll.set, xscrollcommand=hscroll.set)
        self.item_tree.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_item_context())
        self.item_tree.bind("<Double-1>", lambda _event: self.edit_item())
        self.item_tree.bind("<Control-a>", self._select_all_visible_items)
        self.item_tree.bind("<Control-A>", self._select_all_visible_items)
        self.item_tree.bind(
            "<Control-c>", lambda event: self._copy_tree_selection(self.item_tree, event)
        )
        self.item_tree.bind("<Control-z>", lambda _event: self.undo_review_action())
        self.item_tree.bind("<Return>", lambda _event: self._set_selected_review_status("aprobado"))
        self.item_tree.bind("<space>", lambda _event: self._set_selected_review_status("aprobado"))
        self.item_tree.bind("<F2>", lambda _event: self.edit_item())
        self.item_tree.bind("<Control-f>", lambda _event: self.review_search_entry.focus_set())
        self.item_tree.bind("<Delete>", lambda _event: self.delete_item())
        self.item_tree.bind("<Escape>", lambda _event: self._clear_item_selection())
        self.item_tree.bind(
            "<Control-d>", lambda _event: self._set_selected_review_status("descartado")
        )
        self.item_tree.bind("<Button-3>", self._show_review_context_menu)
        self.item_tree.bind(
            "<ButtonPress-1>",
            lambda event: self._begin_tree_drag(self.item_tree, "_review_drag_anchor", event),
            add="+",
        )
        self.item_tree.bind(
            "<B1-Motion>",
            lambda event: self._extend_tree_drag(self.item_tree, "_review_drag_anchor", event),
            add="+",
        )
        self.item_tree.configure(
            displaycolumns=review_display_columns(self.interface_mode_var.get())
        )
        self.review_context_menu = tk.Menu(self.item_tree, tearoff=False)
        self.review_context_menu.add_command(
            label="Aprobar selección    Enter/Espacio",
            command=lambda: self._set_selected_review_status("aprobado"),
        )
        self.review_context_menu.add_command(
            label="Descartar selección    Ctrl+D",
            command=lambda: self._set_selected_review_status("descartado"),
        )
        self.review_context_menu.add_command(
            label="Volver a pendiente",
            command=lambda: self._set_selected_review_status("pendiente"),
        )
        self.review_context_menu.add_separator()
        self.review_context_menu.add_command(label="Editar punto    F2", command=self.edit_item)
        self.review_context_menu.add_command(
            label="Combinar puntos seleccionados", command=self.merge_selected_items
        )
        self.review_context_menu.add_command(
            label="Eliminar selección    Supr", command=self.delete_item
        )
        self.review_context_menu.add_command(
            label="Copiar selección    Ctrl+C",
            command=lambda: self._copy_tree_selection(self.item_tree),
        )
        self.review_context_menu.add_command(
            label="Seleccionar todos los visibles", command=self._select_all_visible_items
        )
        self.review_context_menu.add_command(
            label="Deshacer última acción", command=self.undo_review_action
        )

        ttk.Label(right, text="Revisión del punto", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            right, textvariable=self.review_detail_title_var, style="Section.TLabel", wraplength=430
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        quality_box = ttk.Frame(right)
        quality_box.grid(row=2, column=0, sticky="ew", pady=(6, 8))
        ttk.Label(
            quality_box, textvariable=self.review_quality_var, style="StatusWarning.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            quality_box,
            textvariable=self.review_reasons_var,
            style="Muted.TLabel",
            wraplength=430,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))
        self.reference_text = ScrolledText(right, wrap="word", height=16, state="disabled")
        self.reference_text.grid(row=3, column=0, sticky="nsew")
        self.appearance_manager.configure_text_widget(self.reference_text, fixed=False)

        review_buttons = ttk.Frame(right)
        review_buttons.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        review_buttons.columnconfigure(0, weight=1)
        review_buttons.columnconfigure(1, weight=1)
        ttk.Button(
            review_buttons,
            text="Aprobar selección",
            style="Primary.TButton",
            command=lambda: self._set_selected_review_status("aprobado"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 4))
        ttk.Button(review_buttons, text="Corregir", command=self.edit_item).grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 4)
        )
        ttk.Button(
            review_buttons,
            text="Descartar selección",
            command=lambda: self._set_selected_review_status("descartado"),
        ).grid(row=1, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(
            review_buttons,
            text="Volver a pendiente",
            command=lambda: self._set_selected_review_status("pendiente"),
        ).grid(row=1, column=1, sticky="ew", padx=(4, 0))

        bottom = ttk.Frame(tab)
        bottom.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(bottom, textvariable=self.review_selected_var, style="Muted.TLabel").pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            bottom,
            text="Pendientes anteriores",
            command=self.show_project_continuity_suggestions,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            bottom,
            text="Comparar con anterior",
            command=self.show_minute_comparison,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            bottom, text="Aprobar sugerencias verdes", command=self.approve_green_items
        ).pack(side="left")
        ttk.Button(bottom, text="Ver referencia ampliada", command=self.show_item_reference).pack(
            side="left", padx=8
        )
        self.bulk_review_button = ttk.Menubutton(bottom, text="Acciones masivas")
        self.bulk_review_menu = tk.Menu(self.bulk_review_button, tearoff=False)
        self.bulk_review_menu.add_command(
            label="Seleccionar todos los visibles    Ctrl+A", command=self._select_all_visible_items
        )
        self.bulk_review_menu.add_command(
            label="Limpiar selección", command=self._clear_item_selection
        )
        self.bulk_review_menu.add_separator()
        self.bulk_review_menu.add_command(
            label="Aprobar selección    Enter/Espacio",
            command=lambda: self._set_selected_review_status("aprobado"),
        )
        self.bulk_review_menu.add_command(
            label="Descartar selección    Ctrl+D",
            command=lambda: self._set_selected_review_status("descartado"),
        )
        self.bulk_review_menu.add_command(
            label="Volver selección a pendiente",
            command=lambda: self._set_selected_review_status("pendiente"),
        )
        self.bulk_review_menu.add_command(
            label="Combinar puntos seleccionados", command=self.merge_selected_items
        )
        self.bulk_review_menu.add_separator()
        self.bulk_review_menu.add_command(
            label="Aprobar todos los visibles", command=self.approve_all_visible_items
        )
        self.bulk_review_menu.add_command(
            label="Descartar todos los visibles", command=self.discard_all_visible_items
        )
        self.bulk_review_menu.add_separator()
        self.bulk_review_menu.add_command(
            label="Deshacer última acción    Ctrl+Z", command=self.undo_review_action
        )
        self.bulk_review_button.configure(menu=self.bulk_review_menu)
        self.bulk_review_button.pack(side="left", padx=8)
        self.advanced_review_controls = ttk.Frame(bottom)
        self.advanced_review_controls.pack(side="right")
        ttk.Button(self.advanced_review_controls, text="Agregar punto", command=self.add_item).pack(
            side="left"
        )
        ttk.Button(self.advanced_review_controls, text="Eliminar", command=self.delete_item).pack(
            side="left", padx=6
        )
        ttk.Button(
            self.advanced_review_controls, text="Subir", command=lambda: self.move_item(-1)
        ).pack(side="left")
        ttk.Button(
            self.advanced_review_controls, text="Bajar", command=lambda: self.move_item(1)
        ).pack(side="left", padx=6)

    def _refresh_items_tree(self, select_index: int | None = None) -> None:
        if not hasattr(self, "item_tree"):
            return
        self.item_tree.delete(*self.item_tree.get_children())
        self.item_tree.configure(
            displaycolumns=review_display_columns(self.interface_mode_var.get())
        )
        palette = self.appearance_manager.palette
        self.item_tree.tag_configure(
            "green", background=palette.surface, foreground=palette.success
        )
        self.item_tree.tag_configure(
            "yellow", background=palette.surface_alt, foreground=palette.text
        )
        self.item_tree.tag_configure("red", background=palette.surface, foreground=palette.danger)
        self.item_tree.tag_configure("discarded", foreground=palette.muted)
        only_pending = (
            bool(self.review_filter_var.get()) if hasattr(self, "review_filter_var") else False
        )
        query = (
            self.review_search_var.get().strip().casefold()
            if hasattr(self, "review_search_var")
            else ""
        )
        for index, item in enumerate(self.items):
            if only_pending and item.review_status != "pendiente":
                continue
            searchable = " ".join(
                filter(
                    None,
                    [
                        item.project_code,
                        item.category,
                        item.description,
                        item.responsible,
                        item.due_date_text,
                        item.due_date_iso,
                        item.source_speaker,
                    ],
                )
            ).casefold()
            if query and query not in searchable:
                continue
            assessment = assess_item(item)
            due = item.due_date_text or item.due_date_iso or ""
            self.item_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    index + 1,
                    item.review_status.capitalize(),
                    assessment.label,
                    item.project_code or self.meta_vars["project_code"].get().strip(),
                    item.category.capitalize(),
                    item.description,
                    item.responsible or "",
                    due,
                ),
                tags=(
                    "discarded"
                    if assessment.level == "descartado"
                    else "green"
                    if assessment.level == "verde"
                    else "red"
                    if assessment.level == "rojo"
                    else "yellow",
                ),
            )
        if select_index is not None and self.item_tree.exists(str(select_index)):
            self.item_tree.selection_set(str(select_index))
            self.item_tree.focus(str(select_index))
            self.item_tree.see(str(select_index))
        elif not self.item_tree.selection():
            visible = self.item_tree.get_children("")
            if visible:
                self.item_tree.selection_set(visible[0])
                self.item_tree.focus(visible[0])
                self.item_tree.see(visible[0])
        if hasattr(self, "advanced_review_controls"):
            if self._is_advanced_mode():
                if not self.advanced_review_controls.winfo_ismapped():
                    self.advanced_review_controls.pack(side="right")
            else:
                self.advanced_review_controls.pack_forget()
        self._refresh_review_summary()
        self._refresh_emission_checklist()
        self._update_step_button_labels()

    def _refresh_review_summary(self) -> None:
        summary = summarize_review(self.items)
        self.review_summary_var.set(
            f"Total: {summary.total} · Aprobados: {summary.approved} · "
            f"Pendientes: {summary.pending} · Descartados: {summary.discarded} · "
            f"Prioridad alta: {summary.red}"
        )
        reviewed = summary.approved + summary.discarded
        self.review_progress_var.set(
            f"Revisados {reviewed} de {summary.total}"
            + (
                f" · {summary.pending} requieren atención"
                if summary.pending
                else " · revisión completa"
            )
        )

    def _next_attention_item(self) -> None:
        if not self.items:
            messagebox.showinfo("Revisión", "No hay puntos para revisar.", parent=self)
            return
        selected = self._selected_item_index()
        start = (selected + 1) if selected is not None else 0
        order = list(range(start, len(self.items))) + list(range(0, start))
        for index in order:
            item = self.items[index]
            assessment = assess_item(item)
            if item.review_status == "pendiente" or assessment.level in {"rojo", "amarillo"}:  # noqa: SIM102
                if self.item_tree.exists(str(index)):
                    self.item_tree.selection_set(str(index))
                    self.item_tree.focus(str(index))
                    self.item_tree.see(str(index))
                    self._show_selected_item_context()
                    return
        messagebox.showinfo("Revisión", "No quedan puntos que requieran atención.", parent=self)

    def _selected_item_indices(self) -> list[int]:
        if not hasattr(self, "item_tree"):
            return []
        result: list[int] = []
        for iid in self.item_tree.selection():
            try:
                result.append(int(iid))
            except (TypeError, ValueError):
                continue
        return sorted(set(result))

    def _visible_item_indices(self) -> list[int]:
        if not hasattr(self, "item_tree"):
            return []
        result: list[int] = []
        for iid in self.item_tree.get_children(""):
            try:
                result.append(int(iid))
            except (TypeError, ValueError):
                continue
        return sorted(set(result))

    def _select_all_visible_items(self, _event=None):
        visible = tuple(str(index) for index in self._visible_item_indices())
        if visible:
            self.item_tree.selection_set(visible)
            self.item_tree.focus(visible[0])
            self.item_tree.see(visible[0])
            self._show_selected_item_context()
        return "break"

    def _clear_review_search(self) -> None:
        self.review_search_var.set("")
        self._refresh_items_tree()

    def _clear_item_selection(self) -> None:
        self.item_tree.selection_remove(self.item_tree.selection())
        self._show_selected_item_context()

    def _show_review_context_menu(self, event) -> None:
        row = self.item_tree.identify_row(event.y)
        if row and row not in self.item_tree.selection():
            self.item_tree.selection_set(row)
            self.item_tree.focus(row)
        try:
            self.review_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.review_context_menu.grab_release()

    def _confirm_bulk_review_action(self, status: str, count: int, scope: str) -> bool:
        if count <= 1 or not bool(self.config_data.get("review_confirm_bulk_actions", True)):
            return True
        labels = {
            "aprobado": "aprobar",
            "descartado": "descartar",
            "pendiente": "devolver a pendiente",
        }
        return messagebox.askyesno(
            "Confirmar acción masiva",
            f"Se van a {labels.get(status, status)} {count} punto(s) {scope}. ¿Desea continuar?",
            parent=self,
        )

    def _apply_review_status_to_indices(self, indices: list[int], status: str, scope: str) -> int:
        if not indices:
            messagebox.showinfo(
                "Revisión", "No hay puntos seleccionados para aplicar la acción.", parent=self
            )
            return 0
        if not self._confirm_bulk_review_action(status, len(indices), scope):
            return 0
        result = apply_review_status(self.items, indices, status)
        if result.changed:
            label = f"{status.capitalize()} ({result.changed})"
            self._review_undo_stack.append(("status", label, result.previous))
            self._review_undo_stack[:] = self._review_undo_stack[-20:]
            self._sync_items_to_bundle()
            first = result.indices[0] if result.indices else None
            self._refresh_items_tree(select_index=first)
            if first is not None and self.item_tree.exists(str(first)):
                self.item_tree.selection_set(
                    tuple(
                        str(index) for index in result.indices if self.item_tree.exists(str(index))
                    )
                )
            self._show_selected_item_context()
            try:
                for index, old_status in result.previous:
                    if old_status == status:
                        continue
                    self.db.record_correction_event(
                        self.current_meeting_id,
                        index,
                        "estado_revision_masivo",
                        {"review_status": old_status},
                        {"review_status": status},
                        approved_for_learning=False,
                    )
            except Exception as exc:
                self._log(f"No se pudo registrar la acción masiva: {exc}")
            self._save_autosave_draft()
        return result.changed

    def approve_all_visible_items(self) -> None:
        count = self._apply_review_status_to_indices(
            self._visible_item_indices(), "aprobado", "visibles"
        )
        if count:
            messagebox.showinfo("Revisión", f"Se aprobaron {count} punto(s) visibles.", parent=self)

    def discard_all_visible_items(self) -> None:
        count = self._apply_review_status_to_indices(
            self._visible_item_indices(), "descartado", "visibles"
        )
        if count:
            messagebox.showinfo(
                "Revisión",
                f"Se descartaron {count} punto(s) visibles. Puede deshacer la acción.",
                parent=self,
            )

    def merge_selected_items(self) -> None:
        indices = self._selected_item_indices()
        if len(indices) < 2:
            messagebox.showinfo(
                "Combinar puntos",
                "Seleccione al menos dos puntos duplicados.",
                parent=self,
            )
            return
        if not messagebox.askyesno(
            "Combinar puntos",
            f"Se combinarán {len(indices)} puntos en una sola fila pendiente de revisión. ¿Continuar?",
            parent=self,
        ):
            return
        try:
            result = merge_review_items(self.items, indices)
        except ValueError as exc:
            messagebox.showwarning("Combinar puntos", str(exc), parent=self)
            return
        label = f"Combinar duplicados ({result.removed + 1})"
        self._review_undo_stack.append(("items", label, result.snapshot))
        self._review_undo_stack[:] = self._review_undo_stack[-20:]
        self._sync_items_to_bundle()
        self._refresh_items_tree(select_index=result.primary_index)
        self._show_selected_item_context()
        self._save_autosave_draft()
        self.progress_text_var.set(
            f"Se combinaron {result.removed + 1} puntos; revise y apruebe la fila resultante."
        )

    def undo_review_action(self) -> None:
        if not self._review_undo_stack:
            messagebox.showinfo(
                "Revisión", "No hay acciones de revisión para deshacer.", parent=self
            )
            return
        kind, label, snapshot = self._review_undo_stack.pop()
        if kind == "items":
            restored = restore_review_items(self.items, cast(Any, snapshot))
            select_index = 0 if snapshot else None
        else:
            restored = restore_review_statuses(self.items, cast(Any, snapshot))
            select_index = snapshot[0][0] if snapshot else None
        self._sync_items_to_bundle()
        self._refresh_items_tree(select_index=select_index)
        self._show_selected_item_context()
        self._save_autosave_draft()
        self.progress_text_var.set(f"Acción deshecha: {label} · {restored} cambio(s) restaurado(s)")

    def _show_selected_item_context(self) -> None:
        selected_indices = self._selected_item_indices()
        self.review_selected_var.set(f"{len(selected_indices)} seleccionado(s)")
        if len(selected_indices) > 1:
            self.reference_text.configure(state="normal")
            self.reference_text.delete("1.0", "end")
            self.review_detail_title_var.set(f"{len(selected_indices)} puntos seleccionados")
            statuses: dict[str, int] = {}
            for selected_index in selected_indices:
                status = self.items[selected_index].review_status
                statuses[status] = statuses.get(status, 0) + 1
            self.review_quality_var.set("Selección múltiple")
            self.review_reasons_var.set(
                " · ".join(
                    f"{name.capitalize()}: {count}" for name, count in sorted(statuses.items())
                )
            )
            self.reference_text.insert(
                "end", "Use Aprobar selección, Descartar selección o Acciones masivas.\n\n"
            )
            for selected_index in selected_indices[:20]:
                item = self.items[selected_index]
                self.reference_text.insert(
                    "end", f"{selected_index + 1}. [{item.category}] {item.description}\n"
                )
            if len(selected_indices) > 20:
                self.reference_text.insert(
                    "end", f"\n… y {len(selected_indices) - 20} punto(s) adicionales."
                )
            self.reference_text.configure(state="disabled")
            return
        index = selected_indices[0] if selected_indices else None
        self.reference_text.configure(state="normal")
        self.reference_text.delete("1.0", "end")
        if index is None or index >= len(self.items):
            self.review_detail_title_var.set("Seleccione un punto para revisarlo.")
            self.review_quality_var.set("")
            self.review_reasons_var.set("")
            self.reference_text.configure(state="disabled")
            return
        item = self.items[index]
        assessment = assess_item(item)
        self.review_detail_title_var.set(f"Punto {index + 1}: {item.description}")
        self.review_quality_var.set(assessment.label)
        self.review_reasons_var.set(
            "\n".join(f"• {reason}" for reason in assessment.reasons)
            or "Sin observaciones automáticas."
        )
        path = Path(self.vtt_var.get().strip())
        if not path.is_file() and self.analysis_bundle:
            path = self.analysis_bundle.source_path
        if path.is_file():
            try:
                segments = read_meeting_source(path, self.source_type_var.get() or None).segments
                target = self._seconds_from_timestamp(item.evidence)
                if target is not None and segments:
                    nearest = min(
                        range(len(segments)),
                        key=lambda position: abs(
                            (self._seconds_from_timestamp(segments[position].start) or 0) - target
                        ),
                    )
                    for position in range(max(0, nearest - 2), min(len(segments), nearest + 4)):
                        segment = segments[position]
                        marker = "▶" if position == nearest else " "
                        self.reference_text.insert(
                            "end",
                            f"{marker} [{segment.start}] {segment.speaker}\n{segment.text}\n\n",
                            "selected" if position == nearest else "normal",
                        )
                    self.reference_text.tag_configure(
                        "selected",
                        font=(
                            self.config_data.get("appearance_font_family", "Segoe UI"),
                            int(self.config_data.get("appearance_font_size", 10)),
                            "bold",
                        ),
                    )
                else:
                    self.reference_text.insert(
                        "end", f"Referencia registrada: {item.evidence or 'sin marca temporal'}"
                    )
            except Exception as exc:
                self.reference_text.insert("end", f"No fue posible cargar el contexto: {exc}")
        else:
            self.reference_text.insert("end", "No se encontró la fuente original de la reunión.")
        self.reference_text.configure(state="disabled")

    def edit_item(self) -> None:
        selected = self._selected_item_indices()
        if len(selected) > 1:
            messagebox.showinfo(
                "Revisión", "Seleccione un solo punto para corregirlo.", parent=self
            )
            return
        index = selected[0] if selected else None
        if index is None:
            messagebox.showinfo("Revisión", "Seleccione un punto de minuta.", parent=self)
            return
        before = self.items[index].model_copy(deep=True)
        dialog = ItemDialog(self, before)
        self.wait_window(dialog)
        if not dialog.result:
            return
        after = dialog.result
        # Una corrección humana conserva el estado de revisión previo, pero se
        # identifica como manual para la auditoría y el aprendizaje supervisado.
        after.review_status = before.review_status
        after.origin = "manual"
        self.items[index] = after
        self._sync_items_to_bundle()
        self._refresh_items_tree(select_index=index)
        self._show_selected_item_context()
        self._save_autosave_draft()
        try:
            if before.model_dump() != after.model_dump():
                self.db.record_correction_event(
                    self.current_meeting_id,
                    index,
                    "edicion_punto",
                    before.model_dump(mode="json"),
                    after.model_dump(mode="json"),
                    approved_for_learning=bool(
                        self.learning_sample_var.get() and not self.record_is_test_var.get()
                    ),
                )
        except Exception as exc:
            self._log(f"No se pudo registrar la corrección para aprendizaje: {exc}")

    def delete_item(self) -> None:
        indices = self._selected_item_indices()
        if not indices:
            return
        if not messagebox.askyesno(
            "Eliminar puntos",
            f"¿Eliminar {len(indices)} punto(s) seleccionados? Puede deshacer con Ctrl+Z.",
            parent=self,
        ):
            return
        snapshot = tuple(item.model_copy(deep=True) for item in self.items)
        for index in reversed(indices):
            if 0 <= index < len(self.items):
                self.items.pop(index)
        self._review_undo_stack.append(("items", f"Eliminar puntos ({len(indices)})", snapshot))
        self._review_undo_stack[:] = self._review_undo_stack[-20:]
        self._sync_items_to_bundle()
        select_index = min(indices[0], len(self.items) - 1) if self.items else None
        self._refresh_items_tree(select_index=select_index)
        self._show_selected_item_context()
        self._save_autosave_draft()
        self.progress_text_var.set(f"Se eliminaron {len(indices)} punto(s) · Ctrl+Z para deshacer")

    def _set_selected_review_status(self, status: str) -> None:
        indices = self._selected_item_indices()
        changed = self._apply_review_status_to_indices(indices, status, "seleccionados")
        if changed == 1 and bool(self.config_data.get("review_auto_advance", True)):
            self._next_attention_item()

    def approve_green_items(self) -> None:
        indices = []
        for index, item in enumerate(self.items):
            if item.review_status != "pendiente":
                continue
            candidate = item.model_copy(update={"review_status": "aprobado"})
            if assess_item(candidate).level == "verde":
                indices.append(index)
        count = (
            self._apply_review_status_to_indices(indices, "aprobado", "verdes") if indices else 0
        )
        messagebox.showinfo(
            "Revisión", f"Se aprobaron {count} punto(s) completos y de alta calidad.", parent=self
        )

    def show_project_continuity_suggestions(self) -> None:
        """Muestra puntos previos que el usuario puede adoptar de forma explícita."""

        from src.meeting_continuity import prior_actionable_items

        project_code = self.meta_vars["project_code"].get().strip()
        if not project_code:
            messagebox.showinfo(
                "Pendientes anteriores",
                "Seleccione o ingrese primero el código de proyecto.",
                parent=self,
            )
            return
        try:
            rows = self.db.list_project_continuity_rows(project_code)
            if self.current_meeting_id:
                rows = [row for row in rows if int(row.get("id") or 0) != self.current_meeting_id]
            suggestions = prior_actionable_items(rows, project_code=project_code)
        except Exception as exc:
            self._log(f"No fue posible consultar pendientes anteriores: {exc}")
            messagebox.showerror(
                "Pendientes anteriores",
                "No fue posible consultar el historial. Revise el diagnóstico.",
                parent=self,
            )
            return
        if not suggestions:
            messagebox.showinfo(
                "Pendientes anteriores",
                "No hay compromisos o pendientes aprobados para este proyecto.",
                parent=self,
            )
            return

        window = tk.Toplevel(self)
        window.title("Pendientes anteriores del proyecto")
        window.transient(self)
        configure_resizable_window(window, self, "project_continuity", "980x500", (700, 380))
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=(
                "Seleccione los puntos que desea traer. Se agregarán como pendientes para "
                "revisión; no se emiten automáticamente."
            ),
            style="Muted.TLabel",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        columns = ("date", "minute", "category", "description", "responsible", "due")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        for key, label, width in (
            ("date", "Fecha", 95),
            ("minute", "N.º minuta", 135),
            ("category", "Categoría", 105),
            ("description", "Descripción", 390),
            ("responsible", "Responsable", 150),
            ("due", "Plazo", 115),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="w")
        for index, suggestion in enumerate(suggestions):
            item = suggestion.item
            tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    suggestion.meeting_date,
                    suggestion.minute_number,
                    item.category.capitalize(),
                    item.description,
                    item.responsible or "Sin responsable",
                    item.due_date_text or item.due_date_iso or "Sin plazo",
                ),
            )
        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        actions = ttk.Frame(window, padding=(14, 0, 14, 14))
        actions.pack(fill="x")

        def adopt_selection() -> None:
            selected = [int(value) for value in tree.selection()]
            if not selected:
                messagebox.showinfo(
                    "Pendientes anteriores", "Seleccione al menos un punto.", parent=window
                )
                return
            existing = {" ".join(item.description.casefold().split()) for item in self.items}
            added = 0
            for index in selected:
                source = suggestions[index]
                key = " ".join(source.item.description.casefold().split())
                if key in existing:
                    continue
                self.items.append(
                    source.item.model_copy(
                        update={
                            "review_status": "pendiente",
                            "origin": "importado",
                            "review_notes": (
                                f"Sugerido desde {source.minute_number or 'minuta anterior'} "
                                f"del {source.meeting_date or 'historial del proyecto'}."
                            ),
                        }
                    )
                )
                existing.add(key)
                added += 1
            if added:
                self._sync_items_to_bundle()
                self._refresh_items_tree(select_index=len(self.items) - added)
                self._save_autosave_draft()
                self.progress_text_var.set(
                    f"Se agregaron {added} pendiente(s) anterior(es) para revisión manual"
                )
            messagebox.showinfo(
                "Pendientes anteriores",
                f"Se agregaron {added} punto(s). Los duplicados se omitieron.",
                parent=window,
            )
            window.destroy()

        ttk.Button(actions, text="Cerrar", command=window.destroy).pack(side="right")
        ttk.Button(
            actions,
            text="Agregar seleccionados para revisión",
            command=adopt_selection,
            style="Primary.TButton",
        ).pack(side="right", padx=(0, 8))
        tree.focus_set()

    def show_health_panel(self) -> None:
        """Presenta el diagnóstico operativo sin bloquear la ventana principal."""

        from src.diagnostics import collect_diagnostics

        window = tk.Toplevel(self)
        window.title("Estado de salud")
        configure_resizable_window(window, self, "health_panel", "940x580", (680, 420))
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        status_var = tk.StringVar(value="Comprobando recursos y componentes…")
        ttk.Label(frame, textvariable=status_var, style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text="El informe es de solo lectura. Para soporte puede generar el ZIP sanitizado desde Ayuda.",
            style="Muted.TLabel",
            wraplength=850,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))
        columns = ("status", "name", "detail")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for key, label, width in (
            ("status", "Estado", 85),
            ("name", "Componente", 210),
            ("detail", "Detalle", 600),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="w")
        tree.tag_configure("OK", foreground=self.appearance_manager.palette.success)
        tree.tag_configure("AVISO", foreground=self.appearance_manager.palette.warning)
        tree.tag_configure("ERROR", foreground=self.appearance_manager.palette.danger)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        ttk.Button(window, text="Cerrar", command=window.destroy).pack(
            anchor="e", padx=14, pady=(0, 14)
        )

        def display_report(report: object) -> None:
            if not window.winfo_exists():
                return
            items = getattr(report, "items", [])
            tree.delete(*tree.get_children())
            errors = 0
            warnings = 0
            for index, item in enumerate(items):
                status = str(getattr(item, "status", "AVISO"))
                errors += int(status == "ERROR")
                warnings += int(status == "AVISO")
                tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(status, getattr(item, "name", ""), getattr(item, "detail", "")),
                    tags=(status,),
                )
            status_var.set(
                f"Estado actualizado · {errors} error(es) · {warnings} aviso(s) · {len(items)} comprobaciones"
            )

        def report_error(exc: Exception) -> None:
            if window.winfo_exists():
                status_var.set("No fue posible completar el diagnóstico.")
            self._log(f"No fue posible construir el estado de salud: {exc}")

        def worker() -> None:
            try:
                report = collect_diagnostics(dict(self.config_data))
                self.worker_queue.put(("ui_callback", partial(display_report, report)))
            except Exception as exc:
                self.worker_queue.put(("ui_callback", partial(report_error, exc)))

        threading.Thread(target=worker, daemon=True, name="minutas-health-check").start()

    def show_minute_comparison(self) -> None:
        """Compara el borrador actual con la última minuta válida del proyecto."""

        from src.meeting_continuity import compare_minute_analyses

        project_code = self.meta_vars["project_code"].get().strip()
        if not project_code:
            messagebox.showinfo(
                "Comparar minutas", "Ingrese primero el código de proyecto.", parent=self
            )
            return
        if not self.items:
            messagebox.showinfo(
                "Comparar minutas", "No hay puntos actuales para comparar.", parent=self
            )
            return
        try:
            rows = self.db.list_project_continuity_rows(project_code)
            if self.current_meeting_id:
                rows = [row for row in rows if int(row.get("id") or 0) != self.current_meeting_id]
            previous_row = next(
                (
                    row
                    for row in rows
                    if isinstance(row.get("analysis_json"), str)
                    and row.get("analysis_json", "").strip()
                ),
                None,
            )
            if previous_row is None:
                raise ValueError("No hay una minuta anterior con análisis disponible.")
            previous = MinuteAnalysis.model_validate_json(str(previous_row["analysis_json"]))
            current = MinuteAnalysis(items=[item.model_copy(deep=True) for item in self.items])
        except ValueError as exc:
            messagebox.showinfo("Comparar minutas", str(exc), parent=self)
            return
        except Exception as exc:
            self._log(f"No fue posible comparar minutas: {exc}")
            messagebox.showerror(
                "Comparar minutas",
                "La referencia histórica no es válida. Revise el diagnóstico.",
                parent=self,
            )
            return

        comparison = compare_minute_analyses(previous, current)
        window = tk.Toplevel(self)
        window.title("Comparación con minuta anterior")
        configure_resizable_window(window, self, "minute_comparison", "900x560", (640, 420))
        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=(
                f"Referencia: {previous_row.get('minute_number') or 'sin número'} · "
                f"{previous_row.get('meeting_date') or 'sin fecha'}"
            ),
            style="Section.TLabel",
        ).pack(anchor="w")
        summary = (
            f"{len(comparison.added)} agregado(s) · {len(comparison.removed)} retirado(s) · "
            f"{len(comparison.changed)} cambio(s)"
        )
        ttk.Label(frame, text=summary, style="Muted.TLabel").pack(anchor="w", pady=(4, 10))
        text = ScrolledText(frame, wrap="word", state="normal", height=22)
        self.appearance_manager.configure_text_widget(text, fixed=False)
        text.pack(fill="both", expand=True)
        for label, values in (
            ("AGREGADOS", comparison.added),
            ("RETIRADOS", comparison.removed),
        ):
            text.insert("end", f"{label}\n")
            if values:
                for item in values:
                    text.insert("end", f"• {item.description}\n")
            else:
                text.insert("end", "Sin cambios.\n")
            text.insert("end", "\n")
        text.insert("end", "CAMBIOS DE DATOS\n")
        if comparison.changed:
            labels = {
                "category": "categoría",
                "responsible": "responsable",
                "due_date_text": "plazo",
                "due_date_iso": "fecha",
                "review_status": "estado de revisión",
            }
            for change in comparison.changed:
                fields = ", ".join(labels.get(field, field) for field in change.fields)
                text.insert("end", f"• {change.current.description}: {fields}.\n")
        else:
            text.insert("end", "Sin cambios de responsable, plazo, categoría o estado.\n")
        text.configure(state="disabled")
        ttk.Button(window, text="Cerrar", command=window.destroy).pack(
            anchor="e", padx=14, pady=(0, 14)
        )

    def add_item(self) -> None:
        dialog = ItemDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            dialog.result.origin = "manual"
            dialog.result.review_status = "aprobado"
            self.items.append(dialog.result)
            self._sync_items_to_bundle()
            self._refresh_items_tree(select_index=len(self.items) - 1)
            self._save_autosave_draft()

    def _can_continue_from_review(self) -> bool:
        active = items_for_document(self.items)
        if not active:
            messagebox.showwarning(
                "Revisión", "No existen puntos activos para emitir.", parent=self
            )
            return False
        summary = summarize_review(active)
        if bool(self.config_data.get("require_item_approval", True)) and summary.pending:
            messagebox.showwarning(
                "Revisión pendiente",
                f"Aún existen {summary.pending} punto(s) sin aprobar. Apruébelos, corríjalos o descártelos antes de continuar.",
                parent=self,
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Paso 4: emisión
    # ------------------------------------------------------------------
    def _build_emit_tab(self) -> None:
        tab = self.tab_emit
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        ttk.Label(tab, text="Emitir minuta", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            tab,
            textvariable=self.emission_summary_var,
            style="Section.TLabel",
            wraplength=900,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 10))

        columns = ("status", "check", "detail")
        self.emission_tree = ttk.Treeview(tab, columns=columns, show="headings", height=8)
        for key, label, width in (
            ("status", "Estado", 110),
            ("check", "Comprobación", 260),
            ("detail", "Detalle", 650),
        ):
            self.emission_tree.heading(key, text=label)
            self.emission_tree.column(key, width=width, anchor="w")
        self.emission_tree.grid(row=2, column=0, sticky="nsew")

        summary = ttk.LabelFrame(tab, text="Documento", padding=14)
        summary.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        summary.columnconfigure(1, weight=1)
        ttk.Label(summary, text="Resultado esperado").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        ttk.Label(
            summary, textvariable=self.output_preview_var, style="Muted.TLabel", wraplength=760
        ).grid(row=0, column=1, sticky="w")
        ttk.Label(summary, text="Estado").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=(8, 0)
        )
        ttk.Label(summary, textvariable=self.emission_status_var, style="Section.TLabel").grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )

        buttons = ttk.Frame(tab)
        buttons.grid(row=4, column=0, sticky="e", pady=(12, 0))
        ttk.Button(
            buttons, text="Volver a revisión", command=lambda: self._select_step("review")
        ).pack(side="left")
        ttk.Button(
            buttons, text="Actualizar validación", command=self._refresh_emission_checklist
        ).pack(side="left", padx=8)
        self.word_button = ttk.Button(
            buttons,
            text="Generar minuta Word",
            style="Primary.TButton",
            command=self.generate_document,
            state="disabled",
        )
        self.word_button.pack(side="left")

    def _refresh_emission_checklist(self) -> None:
        if not hasattr(self, "emission_tree"):
            return
        self.emission_tree.delete(*self.emission_tree.get_children())
        try:
            metadata = self._metadata_from_form()
        except Exception:
            metadata = None
        active = items_for_document(self.items)
        review = summarize_review(active)
        diagnostics = self.analysis_bundle.diagnostics if self.analysis_bundle else {}
        coverage = (diagnostics or {}).get("final_coverage") or {}
        uncovered = int(coverage.get("uncovered_count") or 0)
        categories = {name: 0 for name in ("informativo", "acuerdo", "compromiso", "pendiente")}
        for item in active:
            categories[item.category] = categories.get(item.category, 0) + 1
        self.emission_summary_var.set(
            f"{len(self.attendees)} participante(s) · {categories['acuerdo']} acuerdo(s) · "
            f"{categories['compromiso']} compromiso(s) · {categories['pendiente']} pendiente(s) · "
            f"{review.approved} aprobado(s) de {review.total}"
        )
        checks = [
            (
                bool(self.vtt_var.get().strip()),
                "Transcripción seleccionada",
                self.vtt_var.get().strip() or "Pendiente",
            ),
            (
                bool(
                    metadata
                    and metadata.project_code
                    and metadata.minute_number
                    and metadata.matter
                ),
                "Datos corporativos completos",
                metadata.minute_number if metadata else "Pendiente",
            ),
            (
                bool(self.attendees),
                "Participantes confirmados",
                f"{len(self.attendees)} participante(s)",
            ),
            (bool(active), "Puntos activos", f"{len(active)} punto(s) para el documento"),
            (
                review.pending == 0,
                "Revisión finalizada",
                f"{review.pending} pendiente(s), {review.discarded} descartado(s)",
            ),
            (
                uncovered == 0,
                "Cobertura del contenido",
                "Sin expresiones pendientes"
                if uncovered == 0
                else f"{uncovered} expresión(es) pendiente(s)",
            ),
        ]
        ready = all(value for value, _label, _detail in checks)
        for index, (ok, label, detail) in enumerate(checks):
            self.emission_tree.insert(
                "", "end", iid=str(index), values=("Correcto" if ok else "Revisar", label, detail)
            )
        output_root = Path(self.output_dir_var.get().strip())
        number = self.meta_vars["minute_number"].get().strip() or "MINUTA"
        self.output_preview_var.set(str(output_root / number / f"{number}.docx"))
        self.emission_status_var.set(
            "Lista para generar" if ready else "Requiere completar información"
        )
        self.word_button.configure(state="normal" if ready and self.analysis_bundle else "disabled")

    def generate_document(self) -> None:
        if is_provisional_project_code(self.meta_vars["project_code"].get()):
            messagebox.showwarning(
                "Código de proyecto provisional",
                "Confirme el código real del proyecto antes de generar el documento.",
                parent=self,
            )
            self._select_step("meeting")
            return
        if not self.attendees:
            messagebox.showwarning(
                "Participantes requeridos",
                "Confirme al menos un participante antes de emitir el documento.",
                parent=self,
            )
            self._select_step("attendees")
            return
        active = items_for_document(self.items)
        if not active and not bool(self.config_data.get("allow_empty_minutes", False)):
            messagebox.showwarning(
                "Documento sin contenido",
                "No existen puntos aprobados o pendientes activos para emitir.",
                parent=self,
            )
            self._select_step("review")
            return
        if bool(self.config_data.get("require_item_approval", True)):
            summary = summarize_review(active)
            if summary.pending:
                messagebox.showwarning(
                    "Aprobación requerida",
                    f"Existen {summary.pending} punto(s) pendientes de aprobación.",
                    parent=self,
                )
                self._select_step("review")
                return
        try:
            metadata = self._metadata_from_form()
            document_config = self._document_config_for_current_template(metadata)
        except Exception as exc:
            messagebox.showerror("Formato documental", str(exc), parent=self)
            return
        original_config = self.config_data
        automated_emission = bool(getattr(self, "_automated_emission_pending", False))
        self.config_data = document_config
        try:
            super().generate_document()
        finally:
            self.config_data = original_config
            self._automated_emission_pending = False
        if (
            self.last_docx
            and self.last_docx.is_file()
            and bool(self.config_data.get("notify_on_completion", True))
        ):
            pdf_path = self.last_docx.with_suffix(".pdf")
            generated = (
                f"Word y PDF listos: {self.last_docx.stem}"
                if pdf_path.is_file()
                else f"Word listo: {self.last_docx.stem}"
            )
            notify_local("Minuta generada", generated, self.last_docx.parent)
            if automated_emission:
                self._log("Automatizacion: emisión completada y notificada localmente.")
        if (
            self.current_meeting_id
            and self.learning_sample_var.get()
            and not self.record_is_test_var.get()
        ):
            try:
                self.db.register_learning_sample(
                    self.current_meeting_id,
                    approved=True,
                    anonymized=False,
                    approved_by=self.meta_vars["minute_taker"].get().strip() or None,
                )
                self._log("La minuta aprobada quedó registrada como ejemplo local supervisado.")
            except Exception as exc:
                self._log(f"No se pudo registrar el ejemplo de aprendizaje: {exc}")
        self._refresh_dashboard()
        self._refresh_emission_checklist()
        self._update_step_button_labels()

    # ------------------------------------------------------------------
    # Plantillas, administración y ayuda
    # ------------------------------------------------------------------
    def _refresh_template_choices(self) -> None:
        mapping: dict[str, dict | str | None] = {
            "Automática (recomendada)": None,
            "Formato ASH integrado": "standard",
        }
        try:
            for row in self.db.list_template_versions(include_retired=False):
                if row.get("state") not in {"active", "testing"}:
                    continue
                suffix = " - activa" if row.get("is_active") else " - en prueba"
                label = f"{row.get('display_name')} v{row.get('version_label')}{suffix}"
                mapping[label] = row
        except Exception as exc:
            self._log(f"No se pudieron cargar plantillas: {exc}")
        self.template_choice_map = mapping
        if hasattr(self, "template_combo"):
            self.template_combo.configure(values=list(mapping))
            if self.template_choice_var.get() not in mapping:
                self.template_choice_var.set("Automática (recomendada)")
        self._update_template_summary()

    def _select_template_version(self, version_id: int) -> None:
        self._refresh_template_choices()
        for label, record in self.template_choice_map.items():
            if isinstance(record, dict) and int(record.get("id") or 0) == int(version_id):
                self.template_choice_var.set(label)
                return

    def _selected_template_record(self, metadata: MeetingMetadata | None = None):
        selection = self.template_choice_map.get(self.template_choice_var.get())
        if selection is not None:
            return selection
        meta = metadata
        if meta is None:
            try:
                meta = super()._metadata_from_form()
            except Exception:
                meta = None
        try:
            return (
                self.db.resolve_template_version(
                    meta.project_code if meta else self.meta_vars["project_code"].get().strip(),
                    meta.meeting_type if meta else self.meta_vars["meeting_type"].get().strip(),
                    str(self.config_data.get("default_template_key") or "") or None,
                )
                or "standard"
            )
        except Exception:
            return "standard"

    def _update_template_summary(self) -> None:
        if not hasattr(self, "template_summary_var"):
            return
        record = self.template_choice_map.get(self.template_choice_var.get())
        if isinstance(record, dict):
            self.template_summary_var.set(
                f"Formato: {record.get('display_name')} v{record.get('version_label')} ({record.get('state')})"
            )
        elif record == "standard":
            self.template_summary_var.set("Formato: ASH integrado en la aplicación")
        else:
            self.template_summary_var.set(
                "Formato: selección automática por proyecto y tipo de reunión"
            )

    def _document_config_for_current_template(self, metadata: MeetingMetadata) -> dict:
        config = deepcopy(self.config_data)
        record = self._selected_template_record(metadata)
        if isinstance(record, dict):
            config["document_provider"] = "managed_template_v1"
            config["managed_template_path"] = str(record["file_path"])
            config["managed_template_version_id"] = int(record["id"])
            config["managed_template_key"] = str(record["template_key"])
            config["managed_template_version"] = str(record["version_label"])
        else:
            config["document_provider"] = "ash_minutes_v1"
            config.pop("managed_template_path", None)
        return config

    def _refresh_administration_choices(self) -> None:
        self._refresh_project_choices()
        self._refresh_template_choices()

    def open_administration_center(self) -> None:
        open_administration(
            self,
            cast(AppDatabase, self.db),
            self.config_data,
            refresh_callback=self._refresh_administration_choices,
        )

    def open_help_topic(self, topic: str = "usuario") -> None:
        open_help_center(self, topic)

    def _run_automatic_backup(self) -> None:
        try:
            path = maybe_create_automatic_backup(
                self.db,
                enabled=bool(self.config_data.get("backup_auto_enabled", True)),
                interval_days=int(self.config_data.get("backup_interval_days", 7)),
                retention_count=int(self.config_data.get("backup_retention_count", 5)),
                app_version=str(self.config_data.get("app_version", APP_VERSION)),
            )
            if path:
                self._log(f"Respaldo automático creado: {path}")
        except Exception as exc:
            self._log(f"No se pudo crear el respaldo automático: {exc}")

    def _build_history_tab(self) -> None:
        tab = self.tab_history
        tab.rowconfigure(1, weight=1)
        tab.columnconfigure(0, weight=1)

        filters = ttk.Frame(tab)
        filters.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(filters, text="Mostrar").pack(side="left")
        values = ("Operativas", "Pruebas", "Papelera", "Activas", "Todas")
        self.history_view_combo = ttk.Combobox(filters, state="readonly", values=values, width=16)
        self.history_view_combo.pack(side="left", padx=6)
        self.history_view_combo.set("Operativas")
        self.history_view_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self._refresh_history_tree()
        )
        ttk.Label(filters, text="Buscar").pack(side="left", padx=(12, 0))
        self.history_search_entry = ttk.Entry(
            filters, textvariable=self.history_search_var, width=26
        )
        self.history_search_entry.pack(side="left", padx=6)
        self.history_search_entry.bind("<KeyRelease>", lambda _event: self._refresh_history_tree())
        ttk.Button(filters, text="Limpiar", command=self._clear_history_search).pack(side="left")
        ttk.Button(filters, text="Limpiar intentos", command=self._show_cleanup_candidates).pack(
            side="left", padx=(8, 0)
        )
        ttk.Label(filters, textvariable=self.history_status_var, style="Muted.TLabel").pack(
            side="right"
        )

        columns = (
            "id",
            "date",
            "number",
            "project",
            "matter",
            "source",
            "status",
            "kind",
            "updated",
        )
        self.history_tree = ttk.Treeview(
            tab, columns=columns, show="headings", selectmode="extended"
        )
        specs = (
            ("id", "Id", 45),
            ("date", "Fecha", 95),
            ("number", "N.º minuta", 170),
            ("project", "Proyecto", 90),
            ("matter", "Materia", 280),
            ("source", "Fuente", 90),
            ("status", "Estado", 90),
            ("kind", "Tipo", 75),
            ("updated", "Actualizado", 145),
        )
        for column, title, width in specs:
            self._configure_sortable_heading(self.history_tree, column, title)
            self.history_tree.column(column, width=width, anchor="w")
        self.history_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.history_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.bind("<Double-1>", lambda _event: self.load_history_meeting())
        self.history_tree.bind("<Return>", lambda _event: self.load_history_meeting())
        self.history_tree.bind("<Delete>", lambda _event: self._history_delete_key())
        self.history_tree.bind(
            "<Control-a>", lambda event: self._select_all_tree(self.history_tree, event)
        )
        self.history_tree.bind(
            "<Control-A>", lambda event: self._select_all_tree(self.history_tree, event)
        )
        self.history_tree.bind(
            "<Control-c>", lambda event: self._copy_tree_selection(self.history_tree, event)
        )
        self.history_tree.bind(
            "<Escape>", lambda event: self._clear_tree_selection(self.history_tree, event)
        )
        self.history_tree.bind("<Control-f>", lambda _event: self.history_search_entry.focus_set())
        self.history_tree.bind("<F5>", lambda _event: self._refresh_history_tree())
        self.history_tree.bind("<Button-3>", self._show_history_context_menu)
        self.history_tree.bind(
            "<ButtonPress-1>",
            lambda event: self._begin_tree_drag(self.history_tree, "_history_drag_anchor", event),
            add="+",
        )
        self.history_tree.bind(
            "<B1-Motion>",
            lambda event: self._extend_tree_drag(self.history_tree, "_history_drag_anchor", event),
            add="+",
        )

        buttons = ttk.Frame(tab)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Actualizar", command=self._refresh_history_tree).pack(side="left")
        ttk.Button(buttons, text="Cargar en editor", command=self.load_history_meeting).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Abrir Word", command=self.open_history_document).pack(side="left")
        ttk.Button(buttons, text="Abrir carpeta", command=self.open_history_folder).pack(
            side="left", padx=6
        )
        self.history_test_button = ttk.Button(
            buttons, text="Marcar como prueba", command=lambda: self._mark_history_test(True)
        )
        self.history_test_button.pack(side="left", padx=(14, 6))
        self.history_trash_button = ttk.Button(
            buttons, text="Mover a papelera", command=self._move_history_to_trash
        )
        self.history_trash_button.pack(side="left")
        ttk.Label(
            buttons,
            text="Las eliminaciones pasan primero por una papelera recuperable.",
            style="Muted.TLabel",
        ).pack(side="right")

    def _clear_history_search(self) -> None:
        self.history_search_var.set("")
        self._refresh_history_tree()
        if hasattr(self, "history_search_entry"):
            self.history_search_entry.focus_set()

    def _history_delete_key(self) -> None:
        if self._history_view_key() == "trash":
            self._purge_history()
        else:
            self._move_history_to_trash()

    def _history_view_key(self) -> str:
        label = (
            self.history_view_combo.get() if hasattr(self, "history_view_combo") else "Operativas"
        )
        return {
            "Operativas": "operational",
            "Pruebas": "tests",
            "Papelera": "trash",
            "Activas": "active",
            "Todas": "all",
        }.get(label, "operational")

    def _selected_history_ids(self) -> list[int]:
        if not hasattr(self, "history_tree"):
            return []
        return [int(value) for value in self.history_tree.selection()]

    def _refresh_history_tree(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        view = self._history_view_key()
        self.history_tree.delete(*self.history_tree.get_children())
        rows = self.db.list_meetings(limit=2000, view=view)
        query = self.history_search_var.get() if hasattr(self, "history_search_var") else ""
        rows = [row for row in rows if history_matches(row, query)]
        for row in rows:
            source_label = SOURCE_TYPE_LABELS.get(
                row.get("source_type") or "vtt", row.get("source_type") or ""
            )
            short_source = source_label.split(" (")[0].replace("Transcripción de Teams", "VTT")
            kind = (
                "Prueba"
                if row.get("is_test")
                else ("Papelera" if row.get("deleted_at") else "Operativa")
            )
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
                    short_source,
                    row.get("status") or "",
                    kind,
                    row.get("updated_at") or "",
                ),
            )
        self.history_status_var.set(f"{len(rows)} registro(s) · vista {view}")
        in_trash = view == "trash"
        self.history_test_button.configure(
            text="Restaurar como operativa" if view == "tests" else "Marcar como prueba"
        )
        self.history_trash_button.configure(
            text="Restaurar" if in_trash else "Mover a papelera",
            command=self._restore_history if in_trash else self._move_history_to_trash,
        )
        self._refresh_dashboard()

    def _mark_history_test(self, value: bool) -> None:
        ids = self._selected_history_ids()
        if not ids:
            messagebox.showinfo("Historial", "Seleccione al menos una minuta.", parent=self)
            return
        target = False if self._history_view_key() == "tests" else value
        for meeting_id in ids:
            self.db.set_meeting_test(meeting_id, target)
        self._refresh_history_tree()

    def _move_history_to_trash(self) -> None:
        ids = self._selected_history_ids()
        if not ids:
            messagebox.showinfo("Papelera", "Seleccione al menos una minuta.", parent=self)
            return
        reason = simpledialog.askstring(
            "Mover a papelera",
            f"Se moverán {len(ids)} registro(s). Motivo:",
            initialvalue="Prueba o creación accidental",
            parent=self,
        )
        if reason is None:
            return
        if not messagebox.askyesno(
            "Confirmar papelera",
            f"¿Mover {len(ids)} registro(s) y sus carpetas asociadas a la papelera?",
            parent=self,
        ):
            return
        errors: list[str] = []
        for meeting_id in ids:
            try:
                self.history_service.move_to_trash(
                    meeting_id, reason.strip() or "Sin motivo indicado"
                )
            except Exception as exc:
                errors.append(f"{meeting_id}: {exc}")
        self._refresh_history_tree()
        if errors:
            messagebox.showwarning(
                "Papelera",
                "Algunos registros no pudieron moverse:\n" + "\n".join(errors),
                parent=self,
            )

    def _restore_history(self) -> None:
        ids = self._selected_history_ids()
        if not ids:
            messagebox.showinfo("Papelera", "Seleccione al menos una minuta.", parent=self)
            return
        for meeting_id in ids:
            self.history_service.restore(meeting_id)
        self._refresh_history_tree()

    def _purge_history(self) -> None:
        ids = self._selected_history_ids()
        if not ids:
            return
        if not messagebox.askyesno(
            "Eliminar definitivamente",
            f"Esta acción no se puede deshacer. ¿Eliminar {len(ids)} registro(s) definitivamente?",
            icon="warning",
            parent=self,
        ):
            return
        for meeting_id in ids:
            self.history_service.purge(meeting_id)
        self._refresh_history_tree()

    def _show_cleanup_candidates(self) -> None:
        rows = self.db.list_cleanup_candidates()
        if not rows:
            messagebox.showinfo(
                "Limpieza asistida",
                "No se encontraron intentos incompletos ni registros de prueba.",
                parent=self,
            )
            return
        summary = "\n".join(
            f"• Id {row['id']} · {row.get('minute_number') or 'sin número'} · {row.get('status') or ''}"
            for row in rows[:20]
        )
        if len(rows) > 20:
            summary += f"\n• … y {len(rows) - 20} registro(s) más"
        if messagebox.askyesno(
            "Limpieza asistida",
            f"Se encontraron {len(rows)} posible(s) intento(s) incompleto(s):\n\n{summary}\n\n¿Moverlos todos a la papelera?",
            parent=self,
        ):
            for row in rows:
                self.history_service.move_to_trash(int(row["id"]), "Limpieza asistida de intentos")
            self._refresh_history_tree()

    def _show_history_context_menu(self, event) -> None:
        row = self.history_tree.identify_row(event.y)
        if row and row not in self.history_tree.selection():
            self.history_tree.selection_set(row)
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Cargar", command=self.load_history_meeting)
        menu.add_command(label="Abrir Word", command=self.open_history_document)
        menu.add_command(label="Abrir PDF", command=self.open_history_pdf)
        menu.add_command(label="Abrir carpeta", command=self.open_history_folder)
        menu.add_command(
            label="Copiar selección    Ctrl+C",
            command=lambda: self._copy_tree_selection(self.history_tree),
        )
        menu.add_separator()
        if self._history_view_key() == "trash":
            menu.add_command(label="Restaurar", command=self._restore_history)
            menu.add_command(label="Eliminar definitivamente", command=self._purge_history)
        else:
            menu.add_command(
                label="Marcar como prueba", command=lambda: self._mark_history_test(True)
            )
            menu.add_command(label="Mover a papelera", command=self._move_history_to_trash)
        menu.tk_popup(event.x_root, event.y_root)

    # ------------------------------------------------------------------
    # Integración con lógica heredada estable
    # ------------------------------------------------------------------
    def _analysis_complete(self, bundle: AnalysisBundle) -> None:
        super()._analysis_complete(bundle)
        attention_count = len(self.items)
        if bool(self.config_data.get("review_by_exceptions", False)):
            outcome = apply_exception_review(
                self.items,
                float(self.config_data.get("review_auto_approval_threshold", 0.90)),
            )
            attention_count = outcome.requires_attention
            self._log(
                f"Revision por excepciones: {outcome.auto_approved} punto(s) preaprobados; "
                f"{outcome.requires_attention} requieren atencion."
            )
        else:
            for item in self.items:
                item.review_status = "pendiente"
        self._sync_items_to_bundle()
        self._refresh_items_tree()
        automated = self._automated_source_path
        if automated is not None:
            self.inbox_automation_store.mark(
                automated,
                "completed",
                f"Analisis terminado; {attention_count} excepcion(es)",
            )
            self._automated_source_path = None
        if (
            bool(self.config_data.get("automation_auto_generate_document", False))
            and attention_count == 0
            and self.items
        ):
            self._log("Automatizacion: no quedan excepciones; preparando documento.")
            self._automated_emission_pending = True
            self.after(300, self.generate_document)
        else:
            self._select_step("review")

    def _handle_worker_error(self, exc: object) -> None:
        automated = self._automated_source_path
        if automated is not None:
            status = "cancelled" if isinstance(exc, InterruptedError) else "failed"
            self.inbox_automation_store.mark(automated, status, str(exc))
            self._automated_source_path = None
        super()._handle_worker_error(exc)

    def _refresh_attendees_tree(self) -> None:
        if not hasattr(self, "attendee_tree"):
            return
        self.attendee_tree.delete(*self.attendee_tree.get_children())
        palette = self.appearance_manager.palette
        self.attendee_tree.tag_configure("complete", foreground=palette.success)
        self.attendee_tree.tag_configure("review", foreground=palette.warning)
        incomplete = 0
        for index, attendee in enumerate(self.attendees):
            readiness = attendee_readiness(attendee)
            if not readiness.complete:
                incomplete += 1
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
                    readiness.label,
                ),
                tags=("complete" if readiness.complete else "review",),
            )
        total = len(self.attendees)
        if not total:
            self.attendee_summary_var.set("No hay participantes confirmados.")
        elif incomplete:
            self.attendee_summary_var.set(
                f"{total} participante(s) · {incomplete} requieren completar información"
            )
        else:
            self.attendee_summary_var.set(f"{total} participante(s) · todos completos")
        self.attendee_tree.configure(
            displaycolumns=attendee_display_columns(self.interface_mode_var.get())
        )
        if hasattr(self, "advanced_attendee_controls"):
            if self._is_advanced_mode():
                if not self.advanced_attendee_controls.winfo_ismapped():
                    self.advanced_attendee_controls.pack(side="left", padx=6)
            else:
                self.advanced_attendee_controls.pack_forget()
        self._update_step_button_labels()
        self._refresh_emission_checklist()

    def _load_meeting_record(self, meeting_id: int) -> None:
        row = self.db.get_meeting(meeting_id)
        if not row:
            return
        try:
            metadata = MeetingMetadata.model_validate_json(row["metadata_json"])
            self._apply_metadata(metadata)
            self.vtt_var.set(row.get("source_vtt") or "")
            self.source_type_var.set(row.get("source_type") or metadata.source_type)
            self.source_quality_var.set(row.get("source_quality") or metadata.source_quality)
            self.record_is_test_var.set(bool(row.get("is_test")))
            self._update_source_status()
            self.current_meeting_id = meeting_id
            analysis_json = row.get("analysis_json")
            if analysis_json:
                analysis = MinuteAnalysis.model_validate_json(analysis_json)
                source_path = Path(row.get("source_vtt") or "")
                segments = (
                    read_meeting_source(source_path, self.source_type_var.get() or None).segments
                    if source_path.is_file()
                    else []
                )
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
            self._select_step("review" if self.items else "meeting")
            self._log(f"Reunión cargada desde historial: {meeting_id}")
        except Exception as exc:
            messagebox.showerror("Historial", str(exc), parent=self)

    def load_history_meeting(self) -> None:
        meeting_id = self._selected_history_id()
        if meeting_id is None:
            messagebox.showinfo("Historial", "Seleccione una reunión.", parent=self)
            return
        self._load_meeting_record(meeting_id)

    def _save_config(self) -> None:
        self.config_data["app_version"] = APP_VERSION
        self.config_data["release_sequence"] = RELEASE_SEQUENCE
        self.config_data["interface_mode"] = normalize_interface_mode(self.interface_mode_var.get())
        self.config_data["numbering_document_type"] = self.document_type_var.get().strip() or "MRE"
        self.config_data["numbering_discipline"] = self.discipline_var.get().strip() or "PR"
        self.config_data["default_meeting_type"] = meeting_type_from_label(
            self.meeting_type_display_var.get()
        )
        self.config_data["default_minute_taker"] = self.meta_vars["minute_taker"].get().strip()
        self.config_data["learning_capture_enabled"] = bool(self.learning_sample_var.get())
        if bool(self.config_data.get("review_remember_search", False)):
            self.config_data["review_last_search"] = self.review_search_var.get().strip()
        super()._save_config()

    def _apply_update_result(self, payload: tuple[UpdateInfo, bool]) -> None:
        info, manual = payload
        self.config_data["update_last_checked_at"] = datetime.now(UTC).isoformat()
        try:
            from src.settings import save_settings_dict

            self.config_data = save_settings_dict(self.config_data)
        except Exception as exc:
            self._log(f"No se pudo guardar la fecha de actualización: {exc}")
        from src.updater import is_newer_version

        current = APP_VERSION
        current_sequence = int(self.config_data.get("release_sequence", RELEASE_SEQUENCE))
        if not is_newer_version(
            info.version,
            current,
            candidate_sequence=info.release_sequence,
            current_sequence=current_sequence,
        ):
            self.progress_text_var.set("Aplicación actualizada")
            if manual:
                messagebox.showinfo(
                    "Actualizaciones",
                    f"Minutas ASH {current} es la versión más reciente disponible.",
                    parent=self,
                )
            return
        # Reutiliza el flujo de descarga de la clase base evitando su comparación
        # semántica histórica.
        self.pending_update = info
        notes = (info.release_notes or "Sin notas de versión.").strip()
        if len(notes) > 1800:
            notes = notes[:1800] + "…"
        if messagebox.askyesno(
            "Actualización disponible",
            (
                f"Versión instalada: {current}\n"
                f"Versión disponible: {info.version}\n\n"
                f"{notes}\n\n"
                "La descarga será verificada mediante SHA-256. ¿Desea descargarla ahora?"
            ),
            parent=self,
        ):
            self._download_pending_update()

    def _retry_processing_source(self, source_path: Path) -> tuple[bool, str]:
        """Recarga una fuente registrada y delega al flujo normal de análisis.

        El centro no ejecuta trabajo en segundo plano directamente: esta clase valida
        el formulario, crea un nuevo identificador de proceso y deja que el pipeline
        decida si el checkpoint existente es compatible.
        """

        if self.busy:
            return False, "Espere a que termine o cancele el proceso activo antes de reintentar."
        if not source_path.is_file():
            return False, "La fuente original ya no existe o no se puede leer."
        if not self._accept_input_path(source_path):
            return False, "No fue posible cargar la fuente seleccionada para el reintento."
        self.start_analysis()
        if not self.busy:
            return False, "Complete los datos requeridos de la reunión y vuelva a intentar."
        self._log(f"Reintento solicitado desde el centro: {source_path.name}")
        return True, "Reintento iniciado. El avance compatible se recuperará automáticamente."

    def open_processing_center(self) -> None:
        ProcessingCenterDialog(self, self.config_data, on_retry=self._retry_processing_source)

    def open_transcription_components(self) -> None:
        def save(payload: dict) -> None:
            from src.settings import save_settings_dict

            self.config_data = save_settings_dict(payload)
            self._log(
                f"Transcripción configurada: modelo {self.config_data.get('whisper_model', 'base')}."
            )

        open_transcription_components(self, self.config_data, save)

    def open_preferences(self) -> None:
        super().open_preferences()
        self.document_type_var.set(str(self.config_data.get("numbering_document_type", "MRE")))
        self.discipline_var.set(str(self.config_data.get("numbering_discipline", "PR")))
        self.interface_mode_var.set(
            normalize_interface_mode(self.config_data.get("interface_mode", "essential"))
        )
        self.advanced_fields_visible_var.set(
            bool(self.config_data.get("essential_show_advanced_fields", False))
        )
        default_type = str(self.config_data.get("default_meeting_type", "cliente"))
        if not self.meta_vars["meeting_type"].get().strip():
            self.meta_vars["meeting_type"].set(default_type)
            self.meeting_type_display_var.set(meeting_type_label(default_type))
        self._apply_experience_mode()
        self._refresh_emission_checklist()

    def show_about(self) -> None:
        messagebox.showinfo(
            "Acerca de Minutas ASH",
            (
                f"Minutas ASH {APP_VERSION}\n\n"
                "Experiencia Esencial para preparar minutas de forma rápida, guiada y confiable.\n"
                "La vista avanzada mantiene disponibles las herramientas de revisión, configuración y soporte."
            ),
            parent=self,
        )


def _parse_startup_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--provision", action="store_true")
    parser.add_argument("--launch-after", action="store_true")
    parser.add_argument("--provision-auto", action="store_true")
    parser.add_argument("--skip-setup-check", action="store_true")
    parser.add_argument(
        "--help-topic",
        choices=["maestro", "usuario", "configuracion", "procesamiento", "programador"],
        default=None,
    )
    parser.add_argument("vtt", nargs="?", default=None)
    args, _unknown = parser.parse_known_args()
    return args


def _show_gui_error(app: GuidedMinutasApp, message: str) -> None:
    messagebox.showerror("Minutas ASH", message, parent=app)


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

    app = GuidedMinutasApp(initial_vtt=args.vtt)
    install_exception_hooks(
        app.logger,
        lambda message: _show_gui_error(app, message),
    )
    if args.help_topic:
        app.after(250, partial(app.open_help_topic, args.help_topic))
    with operation("gui-session"):
        app.logger.info("gui_session_started")
        app.mainloop()
        app.logger.info("gui_session_completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
