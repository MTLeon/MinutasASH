from __future__ import annotations

from copy import deepcopy
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable

from src.providers.registry import descriptor_for, provider_descriptors
from src.secret_store import delete_secret, has_secret, set_secret
from src.ui_state import configure_resizable_window


PROCESSING_PROFILE_LABELS = {
    "auto": "Automático (recomendado)",
    "fast": "Rápido",
    "balanced": "Equilibrado",
    "precise": "Preciso",
}
PROCESSING_PROFILE_IDS = {label: key for key, label in PROCESSING_PROFILE_LABELS.items()}


class PreferencesDialog(tk.Toplevel):
    """Editor de apariencia, proveedor de procesamiento y actualizaciones."""

    def __init__(
        self,
        parent: tk.Misc,
        settings: dict,
        apply_appearance: Callable[[dict], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Preferencias de Minutas ASH")
        configure_resizable_window(self, parent, "preferences", "860x720", (720, 590))
        self.grab_set()
        self.result: dict | None = None
        self.original = deepcopy(settings)
        self.working = deepcopy(settings)
        self.apply_appearance = apply_appearance
        self._provider_by_label = {
            descriptor.display_name: descriptor.provider_id
            for descriptor in provider_descriptors()
        }
        self._label_by_provider = {
            descriptor.provider_id: descriptor.display_name
            for descriptor in provider_descriptors()
        }
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _event: self._cancel())
        self.wait_visibility()
        self.focus_force()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        notebook = ttk.Notebook(outer)
        notebook.grid(row=0, column=0, sticky="nsew")

        appearance = ttk.Frame(notebook, padding=16)
        workflow = ttk.Frame(notebook, padding=16)
        processing = ttk.Frame(notebook, padding=16)
        data_documents = ttk.Frame(notebook, padding=16)
        updates = ttk.Frame(notebook, padding=16)
        notebook.add(appearance, text="Apariencia")
        notebook.add(workflow, text="Flujo y documentos")
        notebook.add(processing, text="Procesamiento")
        notebook.add(data_documents, text="Datos y formatos")
        notebook.add(updates, text="Actualizaciones")
        self._build_appearance(appearance)
        self._build_workflow(workflow)
        self._build_processing(processing)
        self._build_data_documents(data_documents)
        self._build_updates(updates)

        buttons = ttk.Frame(outer)
        buttons.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="Restablecer", command=self._reset).pack(side="left")
        ttk.Button(buttons, text="Cancelar", command=self._cancel).pack(side="right")
        ttk.Button(buttons, text="Guardar", style="Primary.TButton", command=self._save).pack(side="right", padx=(0, 8))

    def _build_appearance(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        self.theme_var = tk.StringVar(value=str(self.working.get("appearance_theme", "system")))
        self.accent_var = tk.StringVar(value=str(self.working.get("appearance_accent_color", "#1F4E78")))
        self.font_var = tk.StringVar(value=str(self.working.get("appearance_font_family", "Segoe UI")))
        self.font_size_var = tk.IntVar(value=int(self.working.get("appearance_font_size", 10)))
        self.scale_var = tk.DoubleVar(value=float(self.working.get("appearance_scale", 1.0)))
        self.density_var = tk.StringVar(value=str(self.working.get("appearance_density", "comfortable")))
        self.remember_geometry_var = tk.BooleanVar(value=bool(self.working.get("remember_window_geometry", True)))

        rows = [
            ("Tema", ttk.Combobox(frame, textvariable=self.theme_var, values=["system", "light", "dark"], state="readonly")),
            ("Color de acento", None),
            ("Fuente", ttk.Combobox(frame, textvariable=self.font_var, values=sorted(set(tkfont.families(self))), state="readonly")),
            ("Tamaño de fuente", ttk.Spinbox(frame, from_=8, to=18, textvariable=self.font_size_var, width=8)),
            ("Escala", ttk.Combobox(frame, textvariable=self.scale_var, values=[0.8, 0.9, 1.0, 1.1, 1.25, 1.5], state="readonly")),
            ("Densidad", ttk.Combobox(frame, textvariable=self.density_var, values=["compact", "comfortable", "spacious"], state="readonly")),
        ]
        for row, (label, widget) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
            if row == 1:
                color_row = ttk.Frame(frame)
                color_row.grid(row=row, column=1, sticky="ew", pady=7)
                ttk.Entry(color_row, textvariable=self.accent_var, width=16).pack(side="left")
                ttk.Button(color_row, text="Elegir color...", command=self._choose_color).pack(side="left", padx=8)
            else:
                widget.grid(row=row, column=1, sticky="ew", pady=7)

        ttk.Checkbutton(
            frame,
            text="Recordar tamaño y posición de la ventana",
            variable=self.remember_geometry_var,
        ).grid(row=6, column=1, sticky="w", pady=8)
        ttk.Label(
            frame,
            text=(
                "El tema Sistema sigue la preferencia clara u oscura de Windows. "
                "Los cambios se aplican al guardar; algunas medidas se verán completamente al reiniciar."
            ),
            wraplength=570,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(18, 0))
        ttk.Button(frame, text="Vista previa", command=self._preview_appearance).grid(row=8, column=1, sticky="w", pady=(14, 0))

    def _build_workflow(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        self.interface_mode_var = tk.StringVar(value=str(self.working.get("interface_mode", "essential")))
        self.show_advanced_fields_var = tk.BooleanVar(value=bool(self.working.get("essential_show_advanced_fields", False)))
        self.quick_detect_var = tk.BooleanVar(value=bool(self.working.get("quick_detect_participants", True)))
        self.review_focus_var = tk.BooleanVar(value=bool(self.working.get("review_focus_attention", True)))
        self.review_auto_advance_var = tk.BooleanVar(value=bool(self.working.get("review_auto_advance", True)))
        self.review_confirm_bulk_var = tk.BooleanVar(value=bool(self.working.get("review_confirm_bulk_actions", True)))
        self.default_meeting_type_var = tk.StringVar(value=str(self.working.get("default_meeting_type", "cliente")))
        self.guided_mode_var = tk.BooleanVar(value=bool(self.working.get("guided_mode", True)))
        self.require_approval_var = tk.BooleanVar(value=bool(self.working.get("require_item_approval", True)))
        self.allow_empty_var = tk.BooleanVar(value=bool(self.working.get("allow_empty_minutes", False)))
        self.duplicate_warning_var = tk.BooleanVar(value=bool(self.working.get("duplicate_source_warning", True)))
        self.numbering_auto_var = tk.BooleanVar(value=bool(self.working.get("numbering_auto_suggest", True)))
        self.numbering_type_var = tk.StringVar(value=str(self.working.get("numbering_document_type", "MRE")))
        self.numbering_discipline_var = tk.StringVar(value=str(self.working.get("numbering_discipline", "PR")))
        self.numbering_digits_var = tk.IntVar(value=int(self.working.get("numbering_digits", 2)))

        ttk.Label(frame, text="Experiencia predeterminada").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Combobox(
            frame,
            textvariable=self.interface_mode_var,
            values=["essential", "advanced"],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", pady=7)
        ttk.Label(frame, text="Tipo de reunión predeterminado").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Combobox(
            frame,
            textvariable=self.default_meeting_type_var,
            values=["cliente", "interna", "kom", "seguimiento", "otra"],
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", pady=7)
        ttk.Checkbutton(frame, text="Mostrar datos avanzados al iniciar la vista esencial", variable=self.show_advanced_fields_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Detectar participantes automáticamente al seleccionar el VTT", variable=self.quick_detect_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Enfocar primero los puntos que requieren atención", variable=self.review_focus_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Avanzar automáticamente después de revisar un punto", variable=self.review_auto_advance_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Confirmar acciones masivas sobre varios puntos", variable=self.review_confirm_bulk_var).grid(row=10, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Usar flujo guiado de cuatro pasos", variable=self.guided_mode_var).grid(row=11, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Exigir aprobación de cada punto antes de emitir", variable=self.require_approval_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Permitir minutas sin puntos", variable=self.allow_empty_var).grid(row=7, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Advertir cuando una transcripción ya fue procesada", variable=self.duplicate_warning_var).grid(row=8, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Sugerir automáticamente el número documental", variable=self.numbering_auto_var).grid(row=9, column=0, columnspan=2, sticky="w", pady=7)

        fields = [
            ("Tipo documental", ttk.Entry(frame, textvariable=self.numbering_type_var)),
            ("Disciplina", ttk.Entry(frame, textvariable=self.numbering_discipline_var)),
            ("Dígitos del correlativo", ttk.Spinbox(frame, from_=2, to=5, textvariable=self.numbering_digits_var, width=8)),
        ]
        for row, (label, widget) in enumerate(fields, start=12):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
            widget.grid(row=row, column=1, sticky="ew" if row < 7 else "w", pady=7)

        ttk.Label(
            frame,
            text=(
                "La numeración predeterminada utiliza PROYECTO-TIPO-DISCIPLINA-CORRELATIVO. "
                "Los perfiles de proyecto pueden reemplazar el tipo, la disciplina, el lugar, "
                "el redactor, el aprobador y los participantes frecuentes."
            ),
            wraplength=600,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=15, column=0, columnspan=2, sticky="w", pady=(18, 0))

    def _build_processing(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        current_provider = str(self.working.get("processing_provider", "ollama_local"))
        self.provider_label_var = tk.StringVar(value=self._label_by_provider.get(current_provider, self._label_by_provider["ollama_local"]))
        self.provider_model_var = tk.StringVar()
        self.provider_endpoint_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.confirm_remote_var = tk.BooleanVar(value=bool(self.working.get("confirm_remote_processing", True)))
        self.fallback_local_var = tk.BooleanVar(value=bool(self.working.get("fallback_to_local", True)))
        self.remote_timeout_var = tk.IntVar(value=int(self.working.get("remote_timeout_seconds", 300)))
        self.credential_status_var = tk.StringVar()
        self.provider_description_var = tk.StringVar()
        self.processing_profile_var = tk.StringVar(
            value=PROCESSING_PROFILE_LABELS.get(
                str(self.working.get("processing_profile", "auto")),
                PROCESSING_PROFILE_LABELS["auto"],
            )
        )
        self.adaptive_timeout_var = tk.BooleanVar(value=bool(self.working.get("adaptive_timeout_enabled", True)))
        self.checkpoint_enabled_var = tk.BooleanVar(value=bool(self.working.get("processing_checkpoint_enabled", True)))
        self.split_timeout_var = tk.BooleanVar(value=bool(self.working.get("processing_split_on_timeout", True)))
        self.warmup_recheck_var = tk.BooleanVar(value=bool(self.working.get("processing_warmup_resource_recheck", True)))
        self.release_model_var = tk.BooleanVar(value=bool(self.working.get("unload_model_after_processing", True)))
        self.transcript_cleanup_var = tk.BooleanVar(value=bool(self.working.get("transcript_remove_noise", True)))
        self.timeout_max_minutes_var = tk.IntVar(
            value=max(10, int(self.working.get("adaptive_timeout_max_seconds", 7200)) // 60)
        )

        ttk.Label(frame, text="Método").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=7)
        combo = ttk.Combobox(
            frame,
            textvariable=self.provider_label_var,
            values=list(self._provider_by_label),
            state="readonly",
        )
        combo.grid(row=0, column=1, sticky="ew", pady=7)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._load_provider_fields())

        ttk.Label(frame, text="Modelo / perfil").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Entry(frame, textvariable=self.provider_model_var).grid(row=1, column=1, sticky="ew", pady=7)
        ttk.Label(frame, text="Dirección del servicio").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Entry(frame, textvariable=self.provider_endpoint_var).grid(row=2, column=1, sticky="ew", pady=7)
        ttk.Label(frame, text="Tiempo máximo (s)").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Spinbox(frame, from_=30, to=3600, textvariable=self.remote_timeout_var, width=10).grid(row=3, column=1, sticky="w", pady=7)

        key_box = ttk.LabelFrame(frame, text="Credencial de acceso", padding=10)
        key_box.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 8))
        key_box.columnconfigure(0, weight=1)
        ttk.Entry(key_box, textvariable=self.api_key_var, show="•").grid(row=0, column=0, sticky="ew")
        ttk.Button(key_box, text="Guardar credencial", command=self._store_credential).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(key_box, text="Eliminar", command=self._delete_credential).grid(row=0, column=2, padx=(8, 0))
        ttk.Label(key_box, textvariable=self.credential_status_var, style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Checkbutton(
            frame,
            text="Solicitar confirmación antes de enviar una transcripción fuera del equipo",
            variable=self.confirm_remote_var,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(
            frame,
            text="Continuar con procesamiento local si el método remoto no está disponible",
            variable=self.fallback_local_var,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Label(
            frame,
            textvariable=self.provider_description_var,
            wraplength=600,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(12, 0))

        resilience = ttk.LabelFrame(frame, text="Duración, recuperación y recursos", padding=10)
        resilience.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        resilience.columnconfigure(1, weight=1)
        ttk.Label(resilience, text="Perfil de rendimiento").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Combobox(
            resilience,
            textvariable=self.processing_profile_var,
            values=list(PROCESSING_PROFILE_LABELS.values()),
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Label(resilience, text="Espera máxima por solicitud (min)").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Spinbox(
            resilience,
            from_=10,
            to=240,
            textvariable=self.timeout_max_minutes_var,
            width=10,
        ).grid(row=1, column=1, sticky="w", pady=5)
        ttk.Checkbutton(
            resilience,
            text="Adaptar bloques y tiempo de espera al equipo",
            variable=self.adaptive_timeout_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            resilience,
            text="Guardar avance para continuar después de cancelaciones o fallos",
            variable=self.checkpoint_enabled_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            resilience,
            text="Dividir automáticamente un bloque que exceda el tiempo",
            variable=self.split_timeout_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            resilience,
            text="Comprobar la memoria real después de cargar el modelo",
            variable=self.warmup_recheck_var,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            resilience,
            text="Liberar la memoria del modelo al finalizar",
            variable=self.release_model_var,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            resilience,
            text="Compactar subtítulos repetidos y ruido antes del análisis",
            variable=self.transcript_cleanup_var,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Label(
            resilience,
            text=(
                "Automático es la opción recomendada: comprueba la RAM con el modelo cargado, "
                "reduce el contexto cuando es necesario y conserva el avance por bloques."
            ),
            style="Muted.TLabel",
            wraplength=540,
            justify="left",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(7, 0))
        self._load_provider_fields()

    def _build_data_documents(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        self.template_selection_var = tk.StringVar(value=str(self.working.get("template_selection_mode", "automatic")))
        self.default_template_key_var = tk.StringVar(value=str(self.working.get("default_template_key", "")))
        self.duplicate_policy_var = tk.StringVar(value=str(self.working.get("catalog_import_duplicate_policy", "upsert")))
        self.backup_auto_var = tk.BooleanVar(value=bool(self.working.get("backup_auto_enabled", True)))
        self.backup_interval_var = tk.IntVar(value=int(self.working.get("backup_interval_days", 7)))
        self.backup_retention_var = tk.IntVar(value=int(self.working.get("backup_retention_count", 5)))
        self.administration_enabled_var = tk.BooleanVar(value=bool(self.working.get("administration_enabled", True)))
        self.help_topic_var = tk.StringVar(value=str(self.working.get("help_center_default_topic", "usuario")))
        self.repository_provider_var = tk.StringVar(value=str(self.working.get("repository_provider", "sqlite")))
        self.sqlserver_server_var = tk.StringVar(value=str(self.working.get("sqlserver_server", "")))
        self.sqlserver_database_var = tk.StringVar(value=str(self.working.get("sqlserver_database", "MinutasASH")))

        fields = [
            ("Selección de plantilla", ttk.Combobox(frame, textvariable=self.template_selection_var, values=["automatic", "standard", "managed"], state="readonly")),
            ("Plantilla predeterminada", ttk.Entry(frame, textvariable=self.default_template_key_var)),
            ("Duplicados al importar", ttk.Combobox(frame, textvariable=self.duplicate_policy_var, values=["upsert", "skip"], state="readonly")),
            ("Intervalo de respaldo (días)", ttk.Spinbox(frame, from_=1, to=365, textvariable=self.backup_interval_var, width=10)),
            ("Respaldos a conservar", ttk.Spinbox(frame, from_=1, to=50, textvariable=self.backup_retention_var, width=10)),
            ("Tema inicial de ayuda", ttk.Combobox(frame, textvariable=self.help_topic_var, values=["usuario", "configuracion", "programador"], state="readonly")),
        ]
        for row, (label, widget) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
            widget.grid(row=row, column=1, sticky="ew" if row not in {3, 4} else "w", pady=7)
        ttk.Checkbutton(frame, text="Crear respaldo automático", variable=self.backup_auto_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Habilitar centro de administración", variable=self.administration_enabled_var).grid(row=7, column=0, columnspan=2, sticky="w", pady=7)

        repository = ttk.LabelFrame(frame, text="Repositorio corporativo", padding=10)
        repository.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        repository.columnconfigure(1, weight=1)
        ttk.Label(repository, text="Proveedor activo").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Combobox(repository, textvariable=self.repository_provider_var, values=["sqlite"], state="readonly").grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Label(repository, text="Servidor SQL futuro").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Entry(repository, textvariable=self.sqlserver_server_var).grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(repository, text="Base SQL futura").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Entry(repository, textvariable=self.sqlserver_database_var).grid(row=2, column=1, sticky="ew", pady=5)
        ttk.Label(
            repository,
            text="SQLite es el repositorio productivo local de 2.3.5. Los campos SQL Server se conservan para preparar la migración 2.4.x.",
            style="Muted.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_updates(self, frame: ttk.Frame) -> None:
        frame.columnconfigure(1, weight=1)
        self.update_enabled_var = tk.BooleanVar(value=bool(self.working.get("update_enabled", True)))
        self.update_start_var = tk.BooleanVar(value=bool(self.working.get("update_check_on_start", True)))
        self.update_source_var = tk.StringVar(value=str(self.working.get("update_source", "manifest")))
        self.update_channel_var = tk.StringVar(value=str(self.working.get("update_channel", "stable")))
        self.update_interval_var = tk.IntVar(value=int(self.working.get("update_check_interval_hours", 24)))
        self.manifest_url_var = tk.StringVar(value=str(self.working.get("update_manifest_url", "")))
        self.github_owner_var = tk.StringVar(value=str(self.working.get("github_owner", "")))
        self.github_repo_var = tk.StringVar(value=str(self.working.get("github_repo", "")))
        self.prerelease_var = tk.BooleanVar(value=bool(self.working.get("update_allow_prerelease", False)))

        ttk.Checkbutton(frame, text="Habilitar búsqueda de actualizaciones", variable=self.update_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(frame, text="Buscar al iniciar (según intervalo)", variable=self.update_start_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=7)
        fields = [
            ("Origen", ttk.Combobox(frame, textvariable=self.update_source_var, values=["manifest", "github"], state="readonly")),
            ("Canal", ttk.Combobox(frame, textvariable=self.update_channel_var, values=["stable", "beta"], state="readonly")),
            ("Intervalo (horas)", ttk.Spinbox(frame, from_=1, to=720, textvariable=self.update_interval_var, width=10)),
            ("URL de manifiesto", ttk.Entry(frame, textvariable=self.manifest_url_var)),
            ("GitHub propietario", ttk.Entry(frame, textvariable=self.github_owner_var)),
            ("GitHub repositorio", ttk.Entry(frame, textvariable=self.github_repo_var)),
        ]
        for row, (label, widget) in enumerate(fields, start=2):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
            widget.grid(row=row, column=1, sticky="ew", pady=7)
        ttk.Checkbutton(frame, text="Permitir versiones preliminares", variable=self.prerelease_var).grid(row=8, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Label(
            frame,
            text=(
                "Para un repositorio privado no se debe incrustar un token en la aplicación. "
                "Use un manifiesto HTTPS o un repositorio de releases accesible a los usuarios. "
                "Toda descarga exige verificación SHA-256 antes de ejecutarse."
            ),
            wraplength=600,
            justify="left",
            style="Muted.TLabel",
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(18, 0))

    def _choose_color(self) -> None:
        result = colorchooser.askcolor(color=self.accent_var.get(), parent=self)
        if result and result[1]:
            self.accent_var.set(result[1].upper())

    def _appearance_payload(self) -> dict:
        return {
            "appearance_theme": self.theme_var.get(),
            "appearance_accent_color": self.accent_var.get().strip(),
            "appearance_font_family": self.font_var.get().strip() or "Segoe UI",
            "appearance_font_size": int(self.font_size_var.get()),
            "appearance_scale": float(self.scale_var.get()),
            "appearance_density": self.density_var.get(),
            "remember_window_geometry": bool(self.remember_geometry_var.get()),
        }

    def _preview_appearance(self) -> None:
        if self.apply_appearance:
            preview = deepcopy(self.working)
            preview.update(self._appearance_payload())
            self.apply_appearance(preview)

    def _selected_provider_id(self) -> str:
        return self._provider_by_label.get(self.provider_label_var.get(), "ollama_local")

    @staticmethod
    def _provider_keys(provider_id: str) -> tuple[str, str]:
        return {
            "ollama_local": ("model", "ollama_base_url"),
            "azure_openai": ("azure_openai_model", "azure_openai_base_url"),
            "openai": ("openai_model", "openai_base_url"),
            "anthropic": ("anthropic_model", "anthropic_base_url"),
            "gemini": ("gemini_model", "gemini_base_url"),
            "openai_compatible": ("compatible_model", "compatible_base_url"),
        }[provider_id]

    def _save_current_provider_fields(self) -> None:
        previous = str(self.working.get("processing_provider", "ollama_local"))
        model_key, endpoint_key = self._provider_keys(previous)
        self.working[model_key] = self.provider_model_var.get().strip()
        self.working[endpoint_key] = self.provider_endpoint_var.get().strip()

    def _load_provider_fields(self) -> None:
        provider_id = self._selected_provider_id()
        old = str(self.working.get("processing_provider", provider_id))
        if self.provider_model_var.get() or self.provider_endpoint_var.get():
            model_key, endpoint_key = self._provider_keys(old)
            self.working[model_key] = self.provider_model_var.get().strip()
            self.working[endpoint_key] = self.provider_endpoint_var.get().strip()
        self.working["processing_provider"] = provider_id
        model_key, endpoint_key = self._provider_keys(provider_id)
        descriptor = descriptor_for(provider_id)
        self.provider_model_var.set(str(self.working.get(model_key) or descriptor.default_model))
        self.provider_endpoint_var.set(str(self.working.get(endpoint_key) or ""))
        self.provider_description_var.set(descriptor.description)
        self.api_key_var.set("")
        if descriptor.requires_api_key or provider_id == "openai_compatible":
            self.credential_status_var.set("Credencial guardada" if has_secret(provider_id) else "Sin credencial guardada")
        else:
            self.credential_status_var.set("No se requiere credencial")

    def _store_credential(self) -> None:
        provider_id = self._selected_provider_id()
        descriptor = descriptor_for(provider_id)
        if not descriptor.requires_api_key and provider_id != "openai_compatible":
            messagebox.showinfo("Credencial", "Este método no requiere una credencial.", parent=self)
            return
        value = self.api_key_var.get().strip()
        if not value:
            messagebox.showwarning("Credencial", "Ingrese una credencial antes de guardarla.", parent=self)
            return
        try:
            set_secret(provider_id, value)
            self.api_key_var.set("")
            self.credential_status_var.set("Credencial guardada de forma segura en Windows")
        except Exception as exc:
            messagebox.showerror("Credencial", str(exc), parent=self)

    def _delete_credential(self) -> None:
        provider_id = self._selected_provider_id()
        try:
            deleted = delete_secret(provider_id)
            self.credential_status_var.set("Credencial eliminada" if deleted else "No existía una credencial guardada")
        except Exception as exc:
            messagebox.showerror("Credencial", str(exc), parent=self)

    def _collect(self) -> dict:
        self._save_current_provider_fields()
        result = deepcopy(self.working)
        result.update(self._appearance_payload())
        result.update(
            {
                "processing_provider": self._selected_provider_id(),
                "remote_timeout_seconds": int(self.remote_timeout_var.get()),
                "confirm_remote_processing": bool(self.confirm_remote_var.get()),
                "fallback_to_local": bool(self.fallback_local_var.get()),
                "processing_profile": PROCESSING_PROFILE_IDS.get(
                    self.processing_profile_var.get(), "auto"
                ),
                "adaptive_timeout_enabled": bool(self.adaptive_timeout_var.get()),
                "processing_checkpoint_enabled": bool(self.checkpoint_enabled_var.get()),
                "processing_split_on_timeout": bool(self.split_timeout_var.get()),
                "processing_warmup_resource_recheck": bool(self.warmup_recheck_var.get()),
                "unload_model_after_processing": bool(self.release_model_var.get()),
                "transcript_remove_noise": bool(self.transcript_cleanup_var.get()),
                "adaptive_timeout_max_seconds": int(self.timeout_max_minutes_var.get()) * 60,
                "update_enabled": bool(self.update_enabled_var.get()),
                "update_check_on_start": bool(self.update_start_var.get()),
                "update_source": self.update_source_var.get(),
                "update_channel": self.update_channel_var.get(),
                "update_check_interval_hours": int(self.update_interval_var.get()),
                "update_manifest_url": self.manifest_url_var.get().strip(),
                "github_owner": self.github_owner_var.get().strip(),
                "github_repo": self.github_repo_var.get().strip(),
                "update_allow_prerelease": bool(self.prerelease_var.get()),
                "interface_mode": self.interface_mode_var.get(),
                "essential_show_advanced_fields": bool(self.show_advanced_fields_var.get()),
                "quick_detect_participants": bool(self.quick_detect_var.get()),
                "review_focus_attention": bool(self.review_focus_var.get()),
                "review_auto_advance": bool(self.review_auto_advance_var.get()),
                "review_confirm_bulk_actions": bool(self.review_confirm_bulk_var.get()),
                "default_meeting_type": self.default_meeting_type_var.get(),
                "guided_mode": bool(self.guided_mode_var.get()),
                "require_item_approval": bool(self.require_approval_var.get()),
                "allow_empty_minutes": bool(self.allow_empty_var.get()),
                "duplicate_source_warning": bool(self.duplicate_warning_var.get()),
                "numbering_auto_suggest": bool(self.numbering_auto_var.get()),
                "numbering_document_type": self.numbering_type_var.get().strip().upper() or "MRE",
                "numbering_discipline": self.numbering_discipline_var.get().strip().upper() or "PR",
                "numbering_digits": int(self.numbering_digits_var.get()),
                "template_selection_mode": self.template_selection_var.get(),
                "default_template_key": self.default_template_key_var.get().strip(),
                "catalog_import_duplicate_policy": self.duplicate_policy_var.get(),
                "backup_auto_enabled": bool(self.backup_auto_var.get()),
                "backup_interval_days": int(self.backup_interval_var.get()),
                "backup_retention_count": int(self.backup_retention_var.get()),
                "administration_enabled": bool(self.administration_enabled_var.get()),
                "help_center_default_topic": self.help_topic_var.get(),
                "repository_provider": self.repository_provider_var.get(),
                "sqlserver_server": self.sqlserver_server_var.get().strip(),
                "sqlserver_database": self.sqlserver_database_var.get().strip() or "MinutasASH",
            }
        )
        return result

    def _save(self) -> None:
        try:
            self.result = self._collect()
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Preferencias", str(exc), parent=self)
            return
        self.destroy()

    def _reset(self) -> None:
        if not messagebox.askyesno(
            "Restablecer preferencias",
            "Se restablecerán los valores visuales y de procesamiento de esta ventana. ¿Continuar?",
            parent=self,
        ):
            return
        self.working = deepcopy(self.original)
        self.theme_var.set("system")
        self.accent_var.set("#1F4E78")
        self.font_var.set("Segoe UI")
        self.font_size_var.set(10)
        self.scale_var.set(1.0)
        self.density_var.set("comfortable")
        self.interface_mode_var.set("essential")
        self.show_advanced_fields_var.set(False)
        self.quick_detect_var.set(True)
        self.review_focus_var.set(True)
        self.review_auto_advance_var.set(True)
        self.review_confirm_bulk_var.set(True)
        self.default_meeting_type_var.set("cliente")
        self.template_selection_var.set("automatic")
        self.default_template_key_var.set("")
        self.duplicate_policy_var.set("upsert")
        self.backup_auto_var.set(True)
        self.backup_interval_var.set(7)
        self.backup_retention_var.set(5)
        self.administration_enabled_var.set(True)
        self.help_topic_var.set("usuario")
        self.repository_provider_var.set("sqlite")
        self.processing_profile_var.set(PROCESSING_PROFILE_LABELS["auto"])
        self.adaptive_timeout_var.set(True)
        self.checkpoint_enabled_var.set(True)
        self.split_timeout_var.set(True)
        self.warmup_recheck_var.set(True)
        self.release_model_var.set(True)
        self.transcript_cleanup_var.set(True)
        self.timeout_max_minutes_var.set(120)
        self.provider_label_var.set(self._label_by_provider["ollama_local"])
        self.working["processing_provider"] = "ollama_local"
        self._load_provider_fields()

    def _cancel(self) -> None:
        if self.apply_appearance:
            self.apply_appearance(self.original)
        self.result = None
        self.destroy()
