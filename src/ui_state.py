"""Utilidades de ergonomía y persistencia para ventanas Tkinter."""

from __future__ import annotations

import contextlib
import re
import tkinter as tk
from typing import Any, cast

from src.settings import save_settings_dict

_GEOMETRY_RE = re.compile(r"^(?P<w>\d+)x(?P<h>\d+)(?P<x>[+-]\d+)?(?P<y>[+-]\d+)?$")


def normalized_geometry(
    geometry: str | None,
    default: str,
    min_size: tuple[int, int],
    screen_size: tuple[int, int],
) -> str:
    """Normaliza tamaño/posición y evita ventanas inaccesibles fuera de pantalla."""
    candidate = (geometry or "").strip() or default
    match = _GEOMETRY_RE.match(candidate)
    if not match:
        match = _GEOMETRY_RE.match(default)
    if not match:  # pragma: no cover - contrato interno
        raise ValueError("La geometría predeterminada no es válida.")
    screen_w, screen_h = max(1, screen_size[0]), max(1, screen_size[1])
    min_w, min_h = min_size
    width = min(max(int(match.group("w")), min_w), screen_w)
    height = min(max(int(match.group("h")), min_h), screen_h)
    raw_x = match.group("x")
    raw_y = match.group("y")
    if raw_x is None or raw_y is None:
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
    else:
        x = int(raw_x)
        y = int(raw_y)
        x = min(max(x, 0), max(0, screen_w - width))
        y = min(max(y, 0), max(0, screen_h - height))
    return f"{width}x{height}+{x}+{y}"


def _settings_owner(parent: tk.Misc | None) -> tuple[Any | None, dict[str, Any] | None, str | None]:
    current: Any | None = parent
    while current is not None:
        for attr in ("config_data", "config", "working"):
            value = getattr(current, attr, None)
            if isinstance(value, dict):
                return current, value, attr
        current = getattr(current, "master", None)
    return None, None, None


def configure_resizable_window(
    window: tk.Toplevel | tk.Tk,
    parent: tk.Misc | None,
    key: str,
    default_geometry: str,
    min_size: tuple[int, int],
    *,
    transient: bool = True,
) -> None:
    """Hace redimensionable una ventana y recuerda su geometría de forma segura."""
    window.resizable(True, True)
    window.minsize(*min_size)
    if transient and parent is not None and isinstance(window, tk.Toplevel):
        with contextlib.suppress(tk.TclError):
            window.transient(cast(Any, parent))
    owner, settings, attr = _settings_owner(parent)
    saved = None
    if settings is not None:
        saved = dict(settings.get("dialog_geometries") or {}).get(key)

    def apply_geometry() -> None:
        try:
            screen = (window.winfo_screenwidth(), window.winfo_screenheight())
            window.geometry(normalized_geometry(saved, default_geometry, min_size, screen))
        except tk.TclError:
            return

    window.after_idle(apply_geometry)
    original_destroy = window.destroy
    closing = False

    def save_and_destroy() -> None:
        nonlocal closing
        if closing:
            return
        closing = True
        try:
            geometry = window.winfo_geometry()
            screen = (window.winfo_screenwidth(), window.winfo_screenheight())
            geometry = normalized_geometry(geometry, default_geometry, min_size, screen)
            if settings is not None:
                geometries = dict(settings.get("dialog_geometries") or {})
                geometries[key] = geometry
                settings["dialog_geometries"] = geometries
                try:
                    normalized = save_settings_dict(dict(settings))
                    settings.clear()
                    settings.update(normalized)
                    if owner is not None and attr:
                        setattr(owner, attr, settings)
                except Exception:
                    pass
        except tk.TclError:
            pass
        original_destroy()

    cast(Any, window).destroy = save_and_destroy
    with contextlib.suppress(tk.TclError):
        window.protocol("WM_DELETE_WINDOW", save_and_destroy)
