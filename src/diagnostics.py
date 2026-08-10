from __future__ import annotations

import os
import platform
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ollama_manager import api_available, find_ollama_executable, list_models
from src.processing_runtime import get_resource_snapshot
from src.providers.registry import create_processing_provider, provider_display_name
from src.release_identity import (
    ANALYSIS_PIPELINE_VERSION,
    DATABASE_SCHEMA_VERSION,
    LEGACY_PREDECESSOR,
    RELEASE_SEQUENCE,
)
from src.runtime_paths import (
    checkpoints_dir,
    config_path,
    database_path,
    default_output_dir,
    is_frozen,
    logs_dir,
    managed_models_dir,
    managed_runtime_executable,
    records_dir,
    user_data_root,
)
from src.updater import update_source_is_configured


@dataclass(frozen=True)
class DiagnosticItem:
    name: str
    status: str
    detail: str


@dataclass
class DiagnosticReport:
    generated_at: str
    app_version: str
    items: list[DiagnosticItem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(item.status != "ERROR" for item in self.items)

    def to_text(self) -> str:
        lines = [
            "MINUTAS ASH - INFORME DE DIAGNÓSTICO",
            f"Generado: {self.generated_at}",
            f"Versión: {self.app_version}",
            "",
        ]
        lines.extend(f"[{item.status}] {item.name}: {item.detail}" for item in self.items)
        return "\n".join(lines) + "\n"


def _memory_bytes() -> int | None:
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except Exception:
            return None
    sysconf = getattr(os, "sysconf", None)
    if not callable(sysconf):
        return None
    try:
        pages = sysconf("SC_PHYS_PAGES")
        page_size = sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except (AttributeError, ValueError, OSError):
        return None


def _writable_check(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="minutas_", suffix=".tmp", dir=path, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(b"ok")
        temporary.unlink(missing_ok=True)
        return True, str(path)
    except OSError as exc:
        return False, f"{path} ({exc})"


def collect_diagnostics(config: dict[str, Any]) -> DiagnosticReport:
    report = DiagnosticReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        app_version=str(config.get("app_version", "desconocida")),
    )

    system = platform.platform()
    architecture = platform.machine() or "desconocida"
    report.items.append(DiagnosticItem("Sistema operativo", "OK", f"{system}; {architecture}"))
    report.items.append(
        DiagnosticItem(
            "Ejecución",
            "OK",
            f"{'Aplicación instalada' if is_frozen() else 'Modo desarrollo'}; Python {platform.python_version()}",
        )
    )
    report.items.append(
        DiagnosticItem(
            "Identidad de release",
            "OK",
            f"Secuencia {RELEASE_SEQUENCE}; canal {config.get('update_channel', 'stable')}; predecesora {LEGACY_PREDECESSOR}.",
        )
    )
    report.items.append(
        DiagnosticItem(
            "Flujo de análisis",
            "OK",
            f"Pipeline {ANALYSIS_PIPELINE_VERSION}; control semántico {'activo' if config.get('semantic_guard_enabled', True) else 'inactivo'}.",
        )
    )

    memory = _memory_bytes()
    if memory is None:
        report.items.append(DiagnosticItem("Memoria RAM", "AVISO", "No fue posible determinarla."))
    else:
        gb = memory / 1024**3
        status = "OK" if gb >= 15 else "AVISO"
        report.items.append(
            DiagnosticItem(
                "Memoria RAM",
                status,
                f"{gb:.1f} GB; se recomiendan 16 GB o más para el perfil predeterminado.",
            )
        )

    snapshot = get_resource_snapshot()
    if snapshot.memory_percent is not None:
        available = snapshot.available_memory_gib
        detail = f"Uso actual {snapshot.memory_percent:.0f} %"
        if available is not None:
            detail += f"; {available:.1f} GB disponibles"
        threshold = float(config.get("memory_warning_percent", 88.0))
        critical = float(config.get("memory_critical_percent", 95.0))
        status = "ERROR" if snapshot.memory_percent >= critical else (
            "AVISO" if snapshot.memory_percent >= threshold else "OK"
        )
        report.items.append(DiagnosticItem("Memoria disponible ahora", status, detail))

    checkpoint_path = checkpoints_dir()
    try:
        checkpoint_count = len(list(checkpoint_path.glob("*.json"))) if checkpoint_path.exists() else 0
    except OSError:
        checkpoint_count = -1
    report.items.append(
        DiagnosticItem(
            "Procesamiento resiliente",
            "OK",
            (
                f"Perfil {config.get('processing_profile', 'auto')}; tiempo adaptativo "
                f"{'activo' if config.get('adaptive_timeout_enabled', True) else 'inactivo'}; "
                f"checkpoint {'activo' if config.get('processing_checkpoint_enabled', True) else 'inactivo'}; "
                f"sesiones recuperables {checkpoint_count if checkpoint_count >= 0 else 'desconocidas'}."
            ),
        )
    )

    data_usage = shutil.disk_usage(user_data_root())
    free_gb = data_usage.free / 1024**3
    required_gb = min(int(config.get("minimum_free_space_bytes", 7 * 1024**3)), 7 * 1024**3) / 1024**3
    report.items.append(
        DiagnosticItem(
            "Espacio en datos locales",
            "OK" if free_gb >= required_gb else "ERROR",
            f"{free_gb:.1f} GB libres; reserva inicial máxima {required_gb:.1f} GB.",
        )
    )

    output_path = Path(str(config.get("output_dir") or default_output_dir())).expanduser()
    for label, path in (
        ("Datos locales", user_data_root()),
        ("Carpeta documental", output_path),
        ("Registros", logs_dir()),
    ):
        writable, detail = _writable_check(path)
        report.items.append(DiagnosticItem(label, "OK" if writable else "ERROR", detail))

    provider_id = str(config.get("processing_provider", "ollama_local"))
    report.items.append(
        DiagnosticItem(
            "Método configurado",
            "OK",
            provider_display_name(provider_id),
        )
    )
    try:
        provider = create_processing_provider(config, provider_id)
        provider.check_connection()
        report.items.append(
            DiagnosticItem("Conexión del método", "OK", f"{provider.display_name}; perfil {provider.model}")
        )
    except Exception as exc:
        report.items.append(DiagnosticItem("Conexión del método", "ERROR", str(exc)))

    executable = find_ollama_executable(str(config.get("runtime_mode", "auto")))
    local_required = provider_id == "ollama_local" or bool(config.get("fallback_to_local", True))
    if executable:
        detail = str(executable)
        if executable.resolve() == managed_runtime_executable().resolve():
            detail += " (administrado por Minutas ASH)"
        report.items.append(DiagnosticItem("Componente local", "OK", detail))
    else:
        report.items.append(
            DiagnosticItem(
                "Componente local",
                "ERROR" if local_required else "AVISO",
                "No se encontró el ejecutable.",
            )
        )

    base_url = str(config.get("ollama_base_url", "http://127.0.0.1:11434"))
    if api_available(base_url):
        report.items.append(DiagnosticItem("Servicio local", "OK", base_url))
        try:
            models = list_models(base_url)
            configured = str(config.get("model", "qwen3:8b"))
            report.items.append(
                DiagnosticItem(
                    "Perfil local",
                    "OK" if configured in models else ("ERROR" if local_required else "AVISO"),
                    f"Configurado: {configured}; disponibles: {', '.join(models) or 'ninguno'}",
                )
            )
        except Exception as exc:
            report.items.append(DiagnosticItem("Perfil local", "ERROR" if local_required else "AVISO", str(exc)))
    else:
        report.items.append(
            DiagnosticItem(
                "Servicio local",
                "ERROR" if local_required else "AVISO",
                f"Sin respuesta en {base_url}",
            )
        )

    report.items.append(
        DiagnosticItem(
            "Apariencia",
            "OK",
            f"Tema {config.get('appearance_theme', 'system')}; fuente {config.get('appearance_font_family', 'Segoe UI')} {config.get('appearance_font_size', 10)} pt; escala {config.get('appearance_scale', 1.0)}",
        )
    )
    report.items.append(
        DiagnosticItem(
            "Actualizaciones",
            "OK" if update_source_is_configured(config) else "AVISO",
            "Origen configurado" if update_source_is_configured(config) else "Aún no se configuró un origen de releases.",
        )
    )

    db_path = database_path()
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as db:
                row = db.execute("SELECT version FROM app_schema WHERE id=1").fetchone()
            detected_schema = int(row[0]) if row else 0
            schema_status = "OK" if detected_schema == DATABASE_SCHEMA_VERSION else "AVISO"
            schema_detail = f"{db_path}; esquema {detected_schema}, esperado {DATABASE_SCHEMA_VERSION}."
        except (sqlite3.Error, OSError, ValueError) as exc:
            schema_status = "AVISO"
            schema_detail = f"{db_path}; no fue posible leer la versión ({exc})."
    else:
        schema_status = "AVISO"
        schema_detail = f"{db_path}; aún no creada."

    report.items.extend(
        [
            DiagnosticItem("Configuración", "OK" if config_path().exists() else "AVISO", str(config_path())),
            DiagnosticItem("Base local", schema_status, schema_detail),
            DiagnosticItem(
                "Experiencia guiada",
                "OK",
                f"Vista {config.get('interface_mode', 'essential')}; modo guiado {'activo' if config.get('guided_mode', True) else 'inactivo'}; aprobación de puntos {'obligatoria' if config.get('require_item_approval', True) else 'opcional'}; numeración automática {'activa' if config.get('numbering_auto_suggest', True) else 'inactiva'}.",
            ),
            DiagnosticItem("Modelos administrados", "OK", str(managed_models_dir())),
        ]
    )
    return report


def save_diagnostic_report(config: dict[str, Any]) -> Path:
    report = collect_diagnostics(config)
    records_dir().mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = records_dir() / f"diagnostico_{timestamp}.txt"
    path.write_text(report.to_text(), encoding="utf-8")
    return path
