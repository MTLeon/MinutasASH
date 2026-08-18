from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.runtime_paths import config_path, default_output_dir, resource_path


class AppSettings(BaseModel):
    """Configuración validada de la aplicación.

    El modelo se mantiene compatible con el diccionario usado por la línea base
    v5.0.0. Las capas existentes pueden seguir usando ``settings.get(...)``
    sobre el resultado de :func:`load_settings_dict`.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    app_version: str = "2.3.7"
    release_sequence: int = Field(default=2003007, ge=1)
    product_generation: int = Field(default=2, ge=1)
    legacy_predecessor: str = "2.3.2"
    schema_version: int = Field(default=6, ge=1)
    ollama_base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3:8b"
    timeout_seconds: int = Field(default=1200, ge=30, le=14400)
    max_chars_per_chunk: int = Field(default=15000, ge=2000, le=100000)
    single_pass_max_chars: int = Field(default=18000, ge=2000, le=150000)
    context_length: int = Field(default=8192, ge=2048, le=131072)
    temperature: float = Field(default=0.05, ge=0.0, le=1.0)
    keep_alive: str = "30m"

    # Procesamiento resiliente. El perfil automático es la experiencia
    # predeterminada y adapta bloques, contexto y espera al equipo.
    processing_profile: Literal["auto", "fast", "balanced", "precise"] = "auto"
    adaptive_chunking_enabled: bool = True
    adaptive_timeout_enabled: bool = True
    adaptive_timeout_min_seconds: int = Field(default=600, ge=60, le=14400)
    adaptive_timeout_max_seconds: int = Field(default=7200, ge=300, le=14400)
    processing_max_chunk_retries: int = Field(default=3, ge=0, le=8)
    processing_split_on_timeout: bool = True
    processing_split_on_structure_error: bool = True
    processing_min_chunk_chars: int = Field(default=1800, ge=1000, le=10000)
    processing_consolidation_batch_chars: int = Field(default=12000, ge=5000, le=100000)
    processing_overlap_lines: int = Field(default=2, ge=0, le=8)
    processing_checkpoint_enabled: bool = True
    processing_checkpoint_retention_days: int = Field(default=14, ge=1, le=365)
    processing_keep_completed_checkpoint: bool = False
    processing_force_chunking: bool = False
    memory_warning_percent: float = Field(default=88.0, ge=50.0, le=99.0)
    memory_critical_percent: float = Field(default=95.0, ge=60.0, le=100.0)

    company_name: str = "ASH Ingeniería y Proyectos"
    logo_path: str = "assets/logo_ash.png"
    auto_add_transcript_speakers: bool = True
    open_word_after_generation: bool = True
    output_prefix: str = "Minuta"
    output_dir: str | None = None
    border_color: str = "1F497D"
    document_provider: str = "ash_minutes_v1"
    repository_provider: Literal["sqlite", "mssql"] = "sqlite"
    minimum_free_space_bytes: int = Field(default=7 * 1024**3, ge=2 * 1024**3)

    # Gestión del componente local. ``auto`` reutiliza una instalación existente
    # y, si no hay ninguna, prepara el runtime administrado por Minutas ASH.
    runtime_mode: Literal["auto", "managed", "system"] = "auto"
    managed_runtime_url: str = (
        "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip"
    )
    managed_runtime_filename: str = "ollama-windows-amd64.zip"
    managed_runtime_minimum_bytes: int = Field(default=50 * 1024**2, ge=1024**2)
    managed_models_subdir: str = "models"

    # Apariencia y accesibilidad.
    appearance_theme: Literal["system", "light", "dark", "high_contrast"] = "system"
    appearance_accent_color: str = "#1F4E78"
    appearance_font_family: str = "Segoe UI"
    appearance_font_size: int = Field(default=10, ge=8, le=18)
    appearance_scale: float = Field(default=1.0, ge=0.80, le=1.50)
    appearance_density: Literal["compact", "comfortable", "spacious"] = "comfortable"
    remember_window_geometry: bool = True
    window_geometry: str | None = None
    dialog_geometries: dict[str, str] = Field(default_factory=dict)

    # Productividad y revisión masiva.
    review_auto_advance: bool = True
    review_confirm_bulk_actions: bool = True
    review_remember_search: bool = False

    # Proveedor de procesamiento. El modo local permanece como predeterminado.
    processing_provider: Literal[
        "ollama_local", "azure_openai", "openai", "anthropic", "gemini", "openai_compatible"
    ] = "ollama_local"
    remote_timeout_seconds: int = Field(default=300, ge=30, le=3600)
    remote_input_cost_per_million_usd: float = Field(default=0.0, ge=0.0)
    confirm_remote_processing: bool = True
    fallback_to_local: bool = True
    azure_openai_base_url: str = ""
    azure_openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5-mini"
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    anthropic_model: str = "claude-sonnet-4-5"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model: str = "gemini-2.5-flash"
    compatible_base_url: str = ""
    compatible_model: str = ""

    # Control híbrido de cobertura. Contrasta el resultado estructurado con
    # expresiones explícitas de la transcripción para evitar falsos negativos.
    semantic_guard_enabled: bool = True
    semantic_guard_second_pass: bool = True
    semantic_guard_deterministic_fallback: bool = True
    semantic_guard_min_coverage: float = Field(default=0.80, ge=0.0, le=1.0)
    semantic_guard_fallback_min_confidence: float = Field(default=0.82, ge=0.0, le=1.0)
    semantic_guard_max_candidates: int = Field(default=500, ge=10, le=1000)

    # Experiencia de usuario y revelación progresiva.
    interface_mode: Literal["essential", "advanced"] = "essential"
    essential_show_advanced_fields: bool = False
    essential_recent_limit: int = Field(default=5, ge=3, le=10)
    quick_detect_participants: bool = True
    review_focus_attention: bool = True
    default_meeting_type: Literal["cliente", "interna", "kom", "seguimiento", "cartera", "otra"] = (
        "cliente"
    )

    # Flujo guiado, revisión y numeración documental.
    guided_mode: bool = True
    require_item_approval: bool = True
    allow_empty_minutes: bool = False
    duplicate_source_warning: bool = True
    numbering_auto_suggest: bool = True
    numbering_document_type: str = "MRE"
    numbering_discipline: str = "PR"
    numbering_digits: int = Field(default=2, ge=2, le=5)
    recent_project_limit: int = Field(default=8, ge=3, le=30)
    default_minute_taker: str = ""
    remember_last_minute_taker: bool = True
    flexible_sources_enabled: bool = True
    whisper_model: Literal["base", "small"] = "base"
    transcription_language: str = "es"
    whisper_cpu_threads: int = Field(default=0, ge=0, le=64)
    diarization_enabled: bool = False
    diarization_worker_path: str = ""
    transcription_quality_warning: bool = True
    history_trash_retention_days: int = Field(default=30, ge=1, le=3650)
    history_exclude_tests_from_dashboard: bool = True
    learning_capture_enabled: bool = True
    learning_retrieval_enabled: bool = True
    learning_retrieval_limit: int = Field(default=3, ge=1, le=10)

    # Automatizacion de bandeja y revision por excepciones.
    inbox_automation_enabled: bool = False
    inbox_auto_start_processing: bool = False
    inbox_automation_max_retries: int = Field(default=3, ge=1, le=10)
    inbox_scan_recursively: bool = True
    inbox_scan_max_files: int = Field(default=500, ge=10, le=10000)
    review_by_exceptions: bool = False
    review_auto_approval_threshold: float = Field(default=0.90, ge=0.70, le=1.0)
    automation_auto_generate_document: bool = False
    generate_pdf: bool = True
    notify_on_completion: bool = True

    # Importación opcional desde Microsoft Teams mediante permisos delegados.
    # Client y tenant no son secretos; los tokens OAuth nunca se persisten.
    teams_graph_enabled: bool = False
    teams_graph_client_id: str = ""
    teams_graph_tenant_id: str = "organizations"
    teams_graph_timeout_seconds: int = Field(default=60, ge=15, le=300)

    # Plantillas y catálogos corporativos.
    template_selection_mode: Literal["automatic", "standard", "managed"] = "automatic"
    default_template_key: str = ""
    catalog_import_duplicate_policy: Literal["upsert", "skip"] = "upsert"
    backup_auto_enabled: bool = True
    backup_interval_days: int = Field(default=7, ge=1, le=365)
    backup_retention_count: int = Field(default=5, ge=1, le=50)
    administration_enabled: bool = True
    help_center_default_topic: Literal["usuario", "configuracion", "programador"] = "usuario"

    # Preparación del repositorio SQL Server. La conexión productiva se habilitará
    # cuando el proveedor corporativo complete sus pruebas de concurrencia.
    sqlserver_server: str = ""
    sqlserver_database: str = "MinutasASH"
    sqlserver_authentication: Literal["windows", "sql"] = "windows"
    sqlserver_encrypt: bool = True
    sqlserver_trust_server_certificate: bool = False
    sqlserver_timeout_seconds: int = Field(default=15, ge=3, le=300)

    # Actualizaciones asistidas. GitHub público o un manifiesto HTTPS corporativo.
    update_enabled: bool = True
    update_check_on_start: bool = True
    update_check_interval_hours: int = Field(default=24, ge=1, le=720)
    update_source: Literal["manifest", "github"] = "github"
    update_channel: Literal["stable", "beta"] = "stable"
    update_manifest_url: str = ""
    github_owner: str = "MTLeon"
    github_repo: str = "MinutasASH-Releases"
    update_allow_prerelease: bool = False
    update_last_checked_at: str | None = None

    @field_validator("ollama_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value.startswith(("http://127.0.0.1", "http://localhost")):
            raise ValueError("El servicio local debe usar localhost o 127.0.0.1.")
        return value

    @field_validator("border_color")
    @classmethod
    def validate_border_color(cls, value: str) -> str:
        normalized = value.strip().lstrip("#").upper()
        if len(normalized) != 6 or any(char not in "0123456789ABCDEF" for char in normalized):
            raise ValueError("border_color debe ser un color hexadecimal de seis caracteres.")
        return normalized

    @field_validator("appearance_accent_color")
    @classmethod
    def validate_accent_color(cls, value: str) -> str:
        normalized = value.strip().lstrip("#").upper()
        if len(normalized) != 6 or any(char not in "0123456789ABCDEF" for char in normalized):
            raise ValueError("El color de acento debe usar seis caracteres hexadecimales.")
        return f"#{normalized}"

    @field_validator(
        "azure_openai_base_url",
        "openai_base_url",
        "anthropic_base_url",
        "gemini_base_url",
        "compatible_base_url",
        "update_manifest_url",
    )
    @classmethod
    def validate_optional_urls(cls, value: str, info) -> str:
        value = value.strip().rstrip("/")
        if not value:
            return ""
        if not value.startswith("https://"):
            # El servidor compatible puede ejecutarse dentro de una red interna HTTP.
            if info.field_name == "compatible_base_url" and value.startswith("http://"):
                return value
            raise ValueError(f"{info.field_name} debe usar HTTPS.")
        return value

    @field_validator("model", "document_provider")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("El valor no puede quedar vacío.")
        return value

    @model_validator(mode="after")
    def validate_processing_limits(self) -> AppSettings:
        if self.adaptive_timeout_max_seconds < self.adaptive_timeout_min_seconds:
            raise ValueError("adaptive_timeout_max_seconds no puede ser menor que el mínimo.")
        if self.memory_critical_percent <= self.memory_warning_percent:
            raise ValueError("El umbral crítico de memoria debe ser mayor que el de advertencia.")
        return self

    def as_dict(self) -> dict[str, Any]:
        payload = self.model_dump()
        if not payload.get("output_dir"):
            payload["output_dir"] = str(default_output_dir())
        return payload


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_default_settings() -> AppSettings:
    return AppSettings.model_validate(_read_json(resource_path("config.json")))


def _backup_invalid_user_config(path: Path) -> Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.stem}_invalido_{timestamp}{path.suffix}")
    try:
        path.replace(backup)
    except OSError:
        return None
    return backup


def load_settings() -> AppSettings:
    bundled = read_default_settings()
    defaults = bundled.model_dump()
    user_path = config_path()
    if user_path.exists():
        try:
            user_payload = _read_json(user_path)
            if not isinstance(user_payload, dict):
                raise ValueError("La configuración del usuario no es un objeto JSON.")
            defaults.update(user_payload)
            # La versión del producto y del esquema pertenecen al ejecutable, no
            # a las preferencias persistentes. Una configuración creada por una
            # versión anterior nunca debe hacer que la aplicación actual se
            # identifique como obsoleta después de actualizarse.
            defaults["app_version"] = bundled.app_version
            defaults["release_sequence"] = bundled.release_sequence
            defaults["product_generation"] = bundled.product_generation
            defaults["legacy_predecessor"] = bundled.legacy_predecessor
            defaults["schema_version"] = bundled.schema_version
        except (OSError, json.JSONDecodeError, ValueError):
            _backup_invalid_user_config(user_path)
    try:
        settings = AppSettings.model_validate(defaults)
    except Exception:
        # Un valor de usuario inválido nunca debe impedir iniciar. Se respalda el
        # archivo y se vuelve a la configuración incluida con la aplicación.
        _backup_invalid_user_config(user_path)
        settings = read_default_settings()
    if not settings.output_dir:
        settings.output_dir = str(default_output_dir())
    return settings


def load_settings_dict() -> dict[str, Any]:
    return load_settings().as_dict()


def save_settings_dict(payload: dict[str, Any]) -> dict[str, Any]:
    settings = AppSettings.model_validate(payload)
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = settings.as_dict()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return data
