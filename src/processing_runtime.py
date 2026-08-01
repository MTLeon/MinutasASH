from __future__ import annotations

"""Planificación adaptativa y telemetría del procesamiento.

Este módulo no depende de psutil ni de componentes externos. Permite que la
aplicación adapte el tamaño de los bloques y el tiempo de espera al equipo,
al perfil seleccionado y a la longitud real de la fuente.
"""

from dataclasses import dataclass, asdict
import ctypes
import hashlib
import json
import math
import os
import re
import time
from typing import Any, Iterable


GIB = 1024 ** 3
MIB = 1024 ** 2


@dataclass(frozen=True)
class ResourceSnapshot:
    total_memory_bytes: int | None
    available_memory_bytes: int | None
    memory_percent: float | None
    captured_at: float

    @property
    def total_memory_gib(self) -> float | None:
        if self.total_memory_bytes is None:
            return None
        return self.total_memory_bytes / GIB

    @property
    def available_memory_gib(self) -> float | None:
        if self.available_memory_bytes is None:
            return None
        return self.available_memory_bytes / GIB

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["total_memory_gib"] = self.total_memory_gib
        payload["available_memory_gib"] = self.available_memory_gib
        return payload


@dataclass(frozen=True)
class ProcessingProfile:
    profile_id: str
    display_name: str
    chunk_chars: int
    single_pass_chars: int
    context_length: int
    timeout_seconds: int
    min_chunk_chars: int
    max_retries: int
    consolidation_batch_chars: int
    overlap_lines: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessingPlan:
    requested_profile: str
    effective_profile: ProcessingProfile
    reason: str
    resource_snapshot: ResourceSnapshot
    force_chunking: bool
    memory_warning: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_profile": self.requested_profile,
            "effective_profile": self.effective_profile.to_dict(),
            "reason": self.reason,
            "resource_snapshot": self.resource_snapshot.to_dict(),
            "force_chunking": self.force_chunking,
            "memory_warning": self.memory_warning,
        }


PROFILE_PRESETS: dict[str, ProcessingProfile] = {
    "fast": ProcessingProfile(
        profile_id="fast",
        display_name="Rápido",
        chunk_chars=4500,
        single_pass_chars=5200,
        context_length=4096,
        timeout_seconds=1200,
        min_chunk_chars=1600,
        max_retries=2,
        consolidation_batch_chars=6500,
        overlap_lines=1,
    ),
    "balanced": ProcessingProfile(
        profile_id="balanced",
        display_name="Equilibrado",
        chunk_chars=6000,
        single_pass_chars=7000,
        context_length=6144,
        timeout_seconds=1800,
        min_chunk_chars=1900,
        max_retries=2,
        consolidation_batch_chars=8500,
        overlap_lines=1,
    ),
    "precise": ProcessingProfile(
        profile_id="precise",
        display_name="Preciso",
        chunk_chars=8000,
        single_pass_chars=9500,
        context_length=8192,
        timeout_seconds=2400,
        min_chunk_chars=2200,
        max_retries=3,
        consolidation_batch_chars=10500,
        overlap_lines=2,
    ),
}


def estimate_model_reserve_bytes(model: str | None, config: dict[str, Any] | None = None) -> int:
    """Estima la RAM que ocupará el modelo local antes de cargarlo.

    La estimación es deliberadamente conservadora para evitar elegir 8192 tokens
    cuando el equipo parece holgado únicamente porque Ollama aún no cargó el modelo.
    """

    config = config or {}
    configured = float(config.get("processing_model_memory_reserve_gib", 0.0) or 0.0)
    if configured > 0:
        return int(configured * GIB)
    text = str(model or "").casefold()
    match = re.search(r"(?:^|[:_-])(\d+(?:\.\d+)?)b(?:$|[:_-])", text)
    billions = float(match.group(1)) if match else 8.0
    # Aproximación Q4/Q5 + caché y overhead del runtime.
    reserve_gib = min(16.0, max(2.5, 0.72 * billions + 0.8))
    return int(reserve_gib * GIB)


def _windows_memory() -> ResourceSnapshot | None:
    if os.name != "nt":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
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

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    try:
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    except (AttributeError, OSError):
        return None
    if not ok:
        return None
    return ResourceSnapshot(
        total_memory_bytes=int(status.ullTotalPhys),
        available_memory_bytes=int(status.ullAvailPhys),
        memory_percent=float(status.dwMemoryLoad),
        captured_at=time.time(),
    )


def _posix_memory() -> ResourceSnapshot | None:
    if os.name == "nt":
        return None
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total_pages = int(os.sysconf("SC_PHYS_PAGES"))
        available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        return None
    total = page_size * total_pages
    available = page_size * available_pages
    used = max(total - available, 0)
    percent = (used / total * 100.0) if total else None
    return ResourceSnapshot(total, available, percent, time.time())


def get_resource_snapshot() -> ResourceSnapshot:
    snapshot = _windows_memory() or _posix_memory()
    if snapshot is not None:
        return snapshot
    return ResourceSnapshot(None, None, None, time.time())


def _profile_with_overrides(profile: ProcessingProfile, config: dict[str, Any]) -> ProcessingProfile:
    """Aplica límites administrativos sin volver frágil el modo automático."""

    configured_timeout = int(config.get("timeout_seconds", profile.timeout_seconds))
    timeout_floor = int(config.get("adaptive_timeout_min_seconds", 600))
    timeout_cap = int(config.get("adaptive_timeout_max_seconds", 7200))
    timeout = min(max(profile.timeout_seconds, configured_timeout, timeout_floor), timeout_cap)

    configured_context = int(config.get("context_length", profile.context_length))
    # El perfil rápido puede reducir el contexto para liberar RAM; los otros no
    # deben exceder el valor elegido por el administrador.
    if profile.profile_id == "fast":
        context = min(configured_context, profile.context_length)
    else:
        context = min(max(4096, configured_context), profile.context_length)

    manual_chunk = int(config.get("max_chars_per_chunk", profile.chunk_chars))
    adaptive_enabled = bool(config.get("adaptive_chunking_enabled", True))
    chunk_chars = profile.chunk_chars if adaptive_enabled else manual_chunk

    manual_single = int(config.get("single_pass_max_chars", profile.single_pass_chars))
    single_pass = profile.single_pass_chars if adaptive_enabled else manual_single

    retries = int(config.get("processing_max_chunk_retries", profile.max_retries))
    retries = max(0, min(retries, 8))

    return ProcessingProfile(
        profile_id=profile.profile_id,
        display_name=profile.display_name,
        chunk_chars=max(2000, chunk_chars),
        single_pass_chars=max(2000, single_pass),
        context_length=max(2048, context),
        timeout_seconds=timeout,
        min_chunk_chars=max(1200, int(config.get("processing_min_chunk_chars", profile.min_chunk_chars))),
        max_retries=retries,
        consolidation_batch_chars=max(
            5000,
            int(config.get("processing_consolidation_batch_chars", profile.consolidation_batch_chars)),
        ),
        overlap_lines=max(0, min(int(config.get("processing_overlap_lines", profile.overlap_lines)), 8)),
    )


def resolve_processing_plan(
    config: dict[str, Any],
    transcript_chars: int,
    *,
    is_remote: bool = False,
    snapshot: ResourceSnapshot | None = None,
    model: str | None = None,
    model_loaded: bool = False,
) -> ProcessingPlan:
    snapshot = snapshot or get_resource_snapshot()
    requested = str(config.get("processing_profile", "auto")).strip().lower()
    if requested not in {"auto", *PROFILE_PRESETS.keys()}:
        requested = "auto"

    reserve = 0 if (is_remote or model_loaded) else estimate_model_reserve_bytes(model, config)
    projected_available = None
    projected_percent = snapshot.memory_percent
    if snapshot.available_memory_bytes is not None:
        projected_available = max(0, snapshot.available_memory_bytes - reserve)
    if snapshot.total_memory_bytes and projected_available is not None:
        projected_percent = (snapshot.total_memory_bytes - projected_available) / snapshot.total_memory_bytes * 100.0

    warning_threshold = float(config.get("memory_warning_percent", 85.0))
    critical_threshold = float(config.get("memory_critical_percent", 93.0))

    if is_remote:
        selected_id = "balanced" if requested == "auto" else requested
        reason = "El proveedor remoto administra sus propios recursos."
    elif requested != "auto":
        selected_id = requested
        reason = f"Perfil {PROFILE_PRESETS[selected_id].display_name} seleccionado por el usuario."
    else:
        total = snapshot.total_memory_bytes
        minimum_free = float(config.get("processing_min_free_memory_gib", 1.5)) * GIB
        if (
            (projected_percent is not None and projected_percent >= warning_threshold)
            or (projected_available is not None and projected_available < minimum_free)
            or (total is not None and total < 12 * GIB)
        ):
            selected_id = "fast"
            reason = (
                "Se reserva memoria para el modelo local antes de procesar; "
                "se usarán bloques pequeños y contexto reducido."
            )
        elif transcript_chars > 140_000:
            selected_id = "fast"
            reason = "La reunión es extensa; se prioriza continuidad y recuperación."
        else:
            selected_id = "balanced"
            reason = "El equipo y la longitud permiten un equilibrio entre velocidad y detalle."

    profile = _profile_with_overrides(PROFILE_PRESETS[selected_id], config)
    memory_warning: str | None = None
    percent = snapshot.memory_percent
    pressure = max(value for value in (percent, projected_percent) if value is not None) if any(
        value is not None for value in (percent, projected_percent)
    ) else None
    if pressure is not None:
        if pressure >= critical_threshold:
            memory_warning = (
                f"Memoria crítica o proyectada ({pressure:.0f} %). Se aplicará el perfil rápido "
                "y se dividirán automáticamente los bloques que tarden demasiado."
            )
            profile = _profile_with_overrides(PROFILE_PRESETS["fast"], config)
            reason = "La memoria está en nivel crítico; se fuerza un plan conservador y recuperable."
        elif pressure >= warning_threshold:
            memory_warning = (
                f"Memoria elevada o proyectada ({pressure:.0f} %). Se limitará el contexto del modelo."
            )
            if requested == "auto" and profile.profile_id != "fast":
                profile = _profile_with_overrides(PROFILE_PRESETS["fast"], config)
                reason = "La presión de memoria proyectada requiere el perfil rápido."

    force_chunking = bool(config.get("processing_force_chunking", False)) or (
        transcript_chars > profile.single_pass_chars
    )
    return ProcessingPlan(
        requested_profile=requested,
        effective_profile=profile,
        reason=reason,
        resource_snapshot=snapshot,
        force_chunking=force_chunking,
        memory_warning=memory_warning,
    )


def adaptive_timeout_seconds(
    profile: ProcessingProfile,
    chunk_chars: int,
    config: dict[str, Any],
    *,
    attempt: int = 0,
    snapshot: ResourceSnapshot | None = None,
) -> int:
    if not bool(config.get("adaptive_timeout_enabled", True)):
        return int(config.get("timeout_seconds", profile.timeout_seconds))

    snapshot = snapshot or get_resource_snapshot()
    size_factor = max(0.65, chunk_chars / max(profile.chunk_chars, 1))
    retry_factor = 1.0 + 0.35 * max(attempt, 0)
    memory_factor = 1.0
    if snapshot.memory_percent is not None:
        if snapshot.memory_percent >= 95:
            memory_factor = 1.65
        elif snapshot.memory_percent >= 90:
            memory_factor = 1.35
        elif snapshot.memory_percent >= 85:
            memory_factor = 1.15

    timeout = profile.timeout_seconds * size_factor * retry_factor * memory_factor
    minimum = int(config.get("adaptive_timeout_min_seconds", 600))
    maximum = int(config.get("adaptive_timeout_max_seconds", 7200))
    return int(min(max(timeout, minimum), maximum))


def split_text_chunk(
    text: str,
    target_chars: int,
    *,
    overlap_lines: int = 2,
) -> list[str]:
    """Divide un bloque por líneas completas y conserva un pequeño solapamiento."""

    target_chars = max(int(target_chars), 1000)
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or len(text) <= target_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for line in lines:
        extra = len(line) + 1
        if current and current_size + extra > target_chars:
            chunks.append("\n".join(current))
            overlap = current[-overlap_lines:] if overlap_lines else []
            current = list(overlap)
            current_size = sum(len(item) + 1 for item in current)
        current.append(line)
        current_size += extra
    if current:
        chunks.append("\n".join(current))

    # Un bloque gigantesco sin saltos de línea se divide de forma segura por
    # caracteres; esta rama solo se usa con entradas manuales atípicas.
    if len(chunks) == 1 and len(chunks[0]) > target_chars * 1.5:
        raw = chunks[0]
        chunks = []
        cursor = 0
        overlap_chars = min(500, target_chars // 10)
        while cursor < len(raw):
            end = min(cursor + target_chars, len(raw))
            chunks.append(raw[cursor:end])
            if end >= len(raw):
                break
            cursor = max(end - overlap_chars, cursor + 1)
    return chunks


def group_serialized_payloads(
    payloads: Iterable[Any],
    max_chars: int,
) -> list[list[Any]]:
    """Agrupa análisis sin crear una consolidación final demasiado grande."""

    groups: list[list[Any]] = []
    current: list[Any] = []
    current_size = 0
    for payload in payloads:
        if hasattr(payload, "model_dump"):
            value = payload.model_dump()
        else:
            value = payload
        size = len(json.dumps(value, ensure_ascii=False))
        if current and current_size + size > max_chars:
            groups.append(current)
            current = []
            current_size = 0
        current.append(payload)
        current_size += size
    if current:
        groups.append(current)
    return groups


def format_duration(seconds: float | int | None) -> str:
    if seconds is None or not math.isfinite(float(seconds)) or seconds < 0:
        return "—"
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def estimate_eta_seconds(completed_durations: list[float], remaining_weight: float) -> float | None:
    valid = [float(value) for value in completed_durations if value > 0]
    if not valid or remaining_weight <= 0:
        return None
    # Mediana simplificada para que un primer bloque anormal no distorsione toda
    # la estimación. Se evita importar statistics en la ruta crítica.
    ordered = sorted(valid[-8:])
    middle = len(ordered) // 2
    median = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / 2.0
    )
    return median * remaining_weight


def stable_processing_key(
    source_sha256: str,
    metadata_payload: dict[str, Any],
    provider_id: str,
    model: str,
    profile_id: str,
) -> str:
    relevant = {
        "source_sha256": source_sha256,
        "meeting_date": metadata_payload.get("meeting_date"),
        "meeting_type": metadata_payload.get("meeting_type"),
        "project_code": metadata_payload.get("project_code"),
        "provider_id": provider_id,
        "model": model,
        "profile_id": profile_id,
    }
    encoded = json.dumps(relevant, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
