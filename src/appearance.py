from __future__ import annotations

import contextlib
import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any

APPEARANCE_PRESETS: dict[str, dict[str, Any]] = {
    "Corporativo ASH": {
        "appearance_theme": "light",
        "appearance_accent_color": "#1F4E78",
        "appearance_font_family": "Segoe UI",
        "appearance_font_size": 10,
        "appearance_scale": 1.0,
        "appearance_density": "comfortable",
    },
    "Alto contraste": {
        "appearance_theme": "high_contrast",
        "appearance_accent_color": "#FFD400",
        "appearance_font_family": "Segoe UI",
        "appearance_font_size": 11,
        "appearance_scale": 1.1,
        "appearance_density": "spacious",
    },
    "Lectura comoda": {
        "appearance_theme": "light",
        "appearance_accent_color": "#176B52",
        "appearance_font_family": "Segoe UI",
        "appearance_font_size": 12,
        "appearance_scale": 1.1,
        "appearance_density": "spacious",
    },
    "Espacio compacto": {
        "appearance_theme": "system",
        "appearance_accent_color": "#40566F",
        "appearance_font_family": "Segoe UI",
        "appearance_font_size": 9,
        "appearance_scale": 0.9,
        "appearance_density": "compact",
    },
}
ACCENT_PRESETS = (
    ("ASH", "#1F4E78"),
    ("Verde", "#176B52"),
    ("Celeste", "#0078D4"),
    ("Grafito", "#40566F"),
    ("Rojo", "#A4262C"),
)


def appearance_preset(name: str) -> dict[str, Any]:
    return dict(APPEARANCE_PRESETS.get(name, APPEARANCE_PRESETS["Corporativo ASH"]))


@dataclass(frozen=True)
class Palette:
    background: str
    surface: str
    surface_alt: str
    text: str
    muted: str
    border: str
    accent: str
    accent_hover: str
    accent_text: str
    success: str
    danger: str
    warning: str
    selection: str


def _normalize_hex(value: str, fallback: str = "#1F4E78") -> str:
    text = (value or "").strip().lstrip("#")
    if len(text) != 6 or any(char not in "0123456789abcdefABCDEF" for char in text):
        return fallback
    return f"#{text.upper()}"


def _mix(hex_color: str, factor: float) -> str:
    """Aclara (factor positivo) u oscurece (factor negativo) un color."""
    color = _normalize_hex(hex_color).lstrip("#")
    values = [int(color[index : index + 2], 16) for index in (0, 2, 4)]
    if factor >= 0:
        values = [round(value + (255 - value) * min(factor, 1.0)) for value in values]
    else:
        values = [round(value * (1.0 + max(factor, -1.0))) for value in values]
    return "#" + "".join(f"{max(0, min(255, value)):02X}" for value in values)


def accent_text_color(hex_color: str) -> str:
    color = _normalize_hex(hex_color).lstrip("#")
    channels = [int(color[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    return "#000000" if luminance > 0.40 else "#FFFFFF"


def windows_prefers_dark() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _kind = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
    except (OSError, ValueError):
        return False


def resolve_theme(value: str) -> str:
    value = (value or "system").lower()
    if value == "system":
        return "dark" if windows_prefers_dark() else "light"
    return value if value in {"light", "dark", "high_contrast"} else "light"


def palette_for(theme: str, accent: str) -> Palette:
    accent = _normalize_hex(accent)
    if theme == "high_contrast":
        return Palette(
            background="#000000",
            surface="#000000",
            surface_alt="#1A1A1A",
            text="#FFFFFF",
            muted="#E6E6E6",
            border="#FFFFFF",
            accent=accent,
            accent_hover=_mix(accent, -0.15),
            accent_text="#000000",
            success="#57E389",
            danger="#FF7B72",
            warning="#FFD400",
            selection="#264F78",
        )
    if theme == "dark":
        return Palette(
            background="#171A1F",
            surface="#20242B",
            surface_alt="#292E37",
            text="#F2F4F7",
            muted="#AEB7C4",
            border="#3B4350",
            accent=accent,
            accent_hover=_mix(accent, 0.15),
            accent_text=accent_text_color(accent),
            success="#5CC98B",
            danger="#FF7A72",
            warning="#F5C451",
            selection=_mix(accent, -0.25),
        )
    return Palette(
        background="#F3F6FA",
        surface="#FFFFFF",
        surface_alt="#EAF0F6",
        text="#18212F",
        muted="#5E6B7B",
        border="#CDD6E1",
        accent=accent,
        accent_hover=_mix(accent, -0.12),
        accent_text=accent_text_color(accent),
        success="#1B7F3A",
        danger="#B42318",
        warning="#9A6700",
        selection=_mix(accent, 0.72),
    )


def effective_scale(
    requested: float,
    screen_size: tuple[int, int],
    base_minimum: tuple[int, int] = (1000, 700),
) -> float:
    """Limita escala para que la ventana principal siga cabiendo en pantalla."""

    screen_width, screen_height = screen_size
    base_width, base_height = base_minimum
    fit_limit = min(screen_width / base_width, screen_height / base_height)
    return max(0.8, min(1.5, float(requested), fit_limit))


class AppearanceManager:
    """Aplica una apariencia coherente a Tkinter y ttk en tiempo de ejecución."""

    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.style = ttk.Style(root)
        self.palette = palette_for("light", "#1F4E78")
        self.font_family = "Segoe UI"
        self.font_size = 10
        self.density = "comfortable"

    @staticmethod
    def font_families(root: tk.Misc) -> list[str]:
        preferred = ["Segoe UI", "Aptos", "Arial", "Calibri", "Tahoma", "Verdana"]
        available = sorted(set(tkfont.families(root)))
        ordered = [name for name in preferred if name in available]
        ordered.extend(name for name in available if name not in ordered)
        return ordered

    def apply(self, settings: dict[str, Any]) -> Palette:
        theme = resolve_theme(str(settings.get("appearance_theme", "system")))
        accent = str(settings.get("appearance_accent_color", "#1F4E78"))
        self.palette = palette_for(theme, accent)
        self.font_family = str(settings.get("appearance_font_family", "Segoe UI")) or "Segoe UI"
        self.font_size = int(settings.get("appearance_font_size", 10))
        self.density = str(settings.get("appearance_density", "comfortable"))
        requested_scale = float(settings.get("appearance_scale", 1.0))
        try:
            screen_size = (self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        except tk.TclError:
            screen_size = (1920, 1080)
        scale = effective_scale(requested_scale, screen_size)
        with contextlib.suppress(tk.TclError):
            self.root.tk.call("tk", "scaling", 96.0 / 72.0 * scale)

        with contextlib.suppress(tk.TclError):
            self.style.theme_use("clam")

        rowheight = {
            "compact": 23,
            "comfortable": 28,
            "spacious": 33,
        }.get(self.density, 28)
        padding = {
            "compact": (8, 4),
            "comfortable": (10, 6),
            "spacious": (12, 8),
        }.get(self.density, (10, 6))
        p = self.palette
        family = self.font_family
        size = self.font_size

        with contextlib.suppress(tk.TclError):
            self.root.configure({"background": p.background})

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=family, size=size)
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(family=family, size=size)
        fixed_font = tkfont.nametofont("TkFixedFont")
        fixed_font.configure(family="Consolas", size=max(8, size - 1))

        self.style.configure(".", background=p.background, foreground=p.text, font=(family, size))
        self.style.configure("TFrame", background=p.background)
        self.style.configure("Surface.TFrame", background=p.surface)
        self.style.configure("Header.TFrame", background=p.surface)
        self.style.configure("Card.TFrame", background=p.surface, relief="solid", borderwidth=1)
        self.style.configure("TLabel", background=p.background, foreground=p.text)
        self.style.configure("Surface.TLabel", background=p.surface, foreground=p.text)
        self.style.configure("Muted.TLabel", background=p.background, foreground=p.muted)
        self.style.configure("SurfaceMuted.TLabel", background=p.surface, foreground=p.muted)
        self.style.configure(
            "Title.TLabel", background=p.surface, foreground=p.text, font=(family, size + 8, "bold")
        )
        self.style.configure(
            "Subtitle.TLabel", background=p.surface, foreground=p.muted, font=(family, size)
        )
        self.style.configure(
            "Section.TLabel",
            background=p.background,
            foreground=p.text,
            font=(family, size + 1, "bold"),
        )
        self.style.configure(
            "StatusGood.TLabel",
            background=p.surface,
            foreground=p.success,
            font=(family, max(8, size - 1), "bold"),
        )
        self.style.configure(
            "StatusBad.TLabel",
            background=p.surface,
            foreground=p.danger,
            font=(family, max(8, size - 1), "bold"),
        )
        self.style.configure(
            "StatusWarning.TLabel",
            background=p.surface,
            foreground=p.warning,
            font=(family, max(8, size - 1), "bold"),
        )

        self.style.configure(
            "TButton",
            padding=padding,
            font=(family, size),
            background=p.surface_alt,
            foreground=p.text,
            bordercolor=p.border,
        )
        self.style.map(
            "TButton",
            background=[("active", _mix(p.surface_alt, -0.06)), ("disabled", p.surface_alt)],
            foreground=[("disabled", p.muted)],
        )
        self.style.configure(
            "Primary.TButton",
            padding=padding,
            font=(family, size, "bold"),
            background=p.accent,
            foreground=p.accent_text,
            bordercolor=p.accent,
        )
        self.style.map(
            "Primary.TButton",
            background=[
                ("active", p.accent_hover),
                ("pressed", _mix(p.accent, -0.20)),
                ("disabled", p.border),
            ],
            foreground=[("disabled", p.muted)],
        )
        self.style.configure(
            "Step.TButton",
            padding=(12, 7),
            font=(family, size, "bold"),
            background=p.surface_alt,
            foreground=p.text,
            bordercolor=p.border,
        )
        self.style.map(
            "Step.TButton",
            background=[("active", p.selection), ("pressed", p.accent)],
            foreground=[("pressed", p.accent_text)],
        )
        self.style.configure(
            "DashboardValue.TLabel",
            background=p.background,
            foreground=p.accent,
            font=(family, size + 18, "bold"),
        )
        self.style.configure(
            "Danger.TButton",
            padding=padding,
            background=p.danger,
            foreground="#FFFFFF",
            bordercolor=p.danger,
        )

        field_bg = p.surface if theme == "light" else p.surface_alt
        self.style.configure(
            "TEntry",
            fieldbackground=field_bg,
            foreground=p.text,
            insertcolor=p.text,
            bordercolor=p.border,
            padding=(7, 5),
        )
        self.style.map(
            "TEntry",
            bordercolor=[("focus", p.accent)],
            lightcolor=[("focus", p.accent)],
            darkcolor=[("focus", p.accent)],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=field_bg,
            foreground=p.text,
            background=p.surface_alt,
            arrowcolor=p.text,
            bordercolor=p.border,
            padding=(6, 4),
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", field_bg)],
            selectbackground=[("readonly", field_bg)],
            selectforeground=[("readonly", p.text)],
        )
        self.style.configure("TCheckbutton", background=p.background, foreground=p.text)
        self.style.map("TCheckbutton", background=[("active", p.background)])
        self.style.configure("TRadiobutton", background=p.background, foreground=p.text)

        self.style.configure("TNotebook", background=p.background, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            padding=(14, 7),
            background=p.surface_alt,
            foreground=p.muted,
            font=(family, size),
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", p.surface), ("active", _mix(p.surface_alt, -0.04))],
            foreground=[("selected", p.accent), ("active", p.text)],
        )
        self.style.configure(
            "TLabelframe", background=p.background, foreground=p.text, bordercolor=p.border
        )
        self.style.configure(
            "TLabelframe.Label",
            background=p.background,
            foreground=p.text,
            font=(family, size, "bold"),
        )

        self.style.configure(
            "Treeview",
            background=p.surface,
            fieldbackground=p.surface,
            foreground=p.text,
            bordercolor=p.border,
            rowheight=rowheight,
            font=(family, max(8, size - 1)),
        )
        self.style.map(
            "Treeview", background=[("selected", p.selection)], foreground=[("selected", p.text)]
        )
        self.style.configure(
            "Treeview.Heading",
            background=p.surface_alt,
            foreground=p.text,
            bordercolor=p.border,
            font=(family, max(8, size - 1), "bold"),
            padding=(6, 5),
        )
        self.style.map("Treeview.Heading", background=[("active", _mix(p.surface_alt, -0.05))])
        self.style.configure(
            "TProgressbar", troughcolor=p.surface_alt, background=p.accent, bordercolor=p.border
        )
        self.style.configure(
            "Vertical.TScrollbar",
            background=p.surface_alt,
            troughcolor=p.background,
            arrowcolor=p.text,
        )
        self.style.configure(
            "Horizontal.TScrollbar",
            background=p.surface_alt,
            troughcolor=p.background,
            arrowcolor=p.text,
        )
        return p

    def configure_text_widget(self, widget: tk.Text, *, fixed: bool = False) -> None:
        p = self.palette
        family = "Consolas" if fixed else self.font_family
        size = max(8, self.font_size - 1) if fixed else self.font_size
        widget.configure(
            background=p.surface,
            foreground=p.text,
            insertbackground=p.text,
            selectbackground=p.selection,
            selectforeground=p.text,
            highlightbackground=p.border,
            highlightcolor=p.accent,
            font=(family, size),
            relief="solid",
            borderwidth=1,
        )
