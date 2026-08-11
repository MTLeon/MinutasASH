from __future__ import annotations

import os
import sys
from pathlib import Path

APP_VENDOR = "ASH"
APP_NAME = "MinutasASH"


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return source_root()


def resource_path(relative: str | Path) -> Path:
    """Ruta de solo lectura a un recurso incluido en el proyecto/EXE."""
    relative_path = Path(relative)
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return source_root() / relative_path


def local_app_data() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / APP_VENDOR / APP_NAME


def roaming_app_data() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return base / APP_VENDOR / APP_NAME


def user_data_root() -> Path:
    """Datos editables y privados de la aplicación."""
    if not is_frozen():
        return source_root() / ".runtime"
    return local_app_data()


def _documents_dir() -> Path:
    if os.name == "nt":
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _kind = winreg.QueryValueEx(key, "Personal")
            return Path(os.path.expandvars(str(value))).expanduser()
        except (OSError, ImportError):
            pass
    return Path.home() / "Documents"


def default_output_dir() -> Path:
    return _documents_dir() / "ASH" / "Minutas"


def config_path() -> Path:
    return roaming_app_data() / "config.json" if is_frozen() else user_data_root() / "config.json"


def database_path() -> Path:
    return user_data_root() / "data" / "minutas.db"


def logs_dir() -> Path:
    return user_data_root() / "logs"


def drafts_dir() -> Path:
    return user_data_root() / "drafts"


def inbox_dir() -> Path:
    return user_data_root() / "inbox"


def cache_dir() -> Path:
    return user_data_root() / "cache"


def checkpoints_dir() -> Path:
    return user_data_root() / "checkpoints"


def jobs_dir() -> Path:
    return user_data_root() / "jobs"


def managed_runtime_dir() -> Path:
    return user_data_root() / "runtime" / "ollama"


def managed_runtime_executable() -> Path:
    return managed_runtime_dir() / "ollama.exe"


def managed_models_dir() -> Path:
    return user_data_root() / "models"


def downloads_dir() -> Path:
    return user_data_root() / "downloads"


def templates_dir() -> Path:
    return user_data_root() / "templates"


def backups_dir() -> Path:
    return user_data_root() / "backups"


def exports_dir() -> Path:
    return user_data_root() / "exports"


def support_dir() -> Path:
    return user_data_root() / "support"


def trash_dir() -> Path:
    return user_data_root() / "trash" / "meetings"


def setup_state_path() -> Path:
    return user_data_root() / "setup_state.json"


def records_dir() -> Path:
    return user_data_root() / "records"


def ensure_user_directories() -> None:
    for path in (
        user_data_root(),
        database_path().parent,
        logs_dir(),
        drafts_dir(),
        inbox_dir(),
        cache_dir(),
        checkpoints_dir(),
        jobs_dir(),
        records_dir(),
        managed_runtime_dir(),
        managed_models_dir(),
        downloads_dir(),
        templates_dir(),
        backups_dir(),
        exports_dir(),
        support_dir(),
        trash_dir(),
        config_path().parent,
        default_output_dir(),
    ):
        path.mkdir(parents=True, exist_ok=True)
