from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from src.repositories.base import MeetingRepository
from src.runtime_paths import backups_dir, config_path, database_path, templates_dir


class BackupError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(
    database: MeetingRepository,
    destination: str | Path | None = None,
    *,
    app_version: str | None = None,
) -> Path:
    backups_dir().mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = (
        Path(destination) if destination else backups_dir() / f"MinutasASH_Backup_{timestamp}.zip"
    )
    target.parent.mkdir(parents=True, exist_ok=True)

    ok, message = database.integrity_check()
    if not ok:
        raise BackupError(f"La base local no superó la comprobación de integridad: {message}")

    with tempfile.TemporaryDirectory(prefix="minutas_ash_backup_") as temp_dir:
        root = Path(temp_dir)
        data_dir = root / "data"
        config_dir = root / "config"
        template_copy = root / "templates"
        data_dir.mkdir()
        config_dir.mkdir()

        database.backup_to(data_dir / "minutas.db")
        if config_path().is_file():
            shutil.copy2(config_path(), config_dir / "config.json")
        if templates_dir().is_dir():
            shutil.copytree(templates_dir(), template_copy, dirs_exist_ok=True)

        files = [path for path in root.rglob("*") if path.is_file()]
        manifest = {
            "product": "Minutas ASH",
            "app_version": app_version,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "database_schema": database.get_schema_version(),
            "files": [
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in sorted(files)
            ],
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if target.exists():
            target.unlink()
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root))
    database.log_audit("backup", "application", str(target), None, {"sha256": _sha256(target)})
    return target


def verify_backup(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file():
        raise BackupError("No se encontró el respaldo.")
    with tempfile.TemporaryDirectory(prefix="minutas_ash_verify_") as temp_dir:
        root = Path(temp_dir)
        try:
            with zipfile.ZipFile(source, "r") as archive:
                for member in archive.infolist():
                    destination = (root / member.filename).resolve()
                    if root.resolve() not in destination.parents and destination != root.resolve():
                        raise BackupError("El respaldo contiene rutas no seguras.")
                archive.extractall(root)
        except zipfile.BadZipFile as exc:
            raise BackupError("El archivo no es un respaldo ZIP válido.") from exc
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            raise BackupError("El respaldo no contiene manifest.json.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        issues: list[str] = []
        for entry in manifest.get("files", []):
            file_path = root / str(entry.get("path") or "")
            if not file_path.is_file():
                issues.append(f"Falta {entry.get('path')}")
                continue
            if _sha256(file_path) != str(entry.get("sha256") or ""):
                issues.append(f"Hash no coincide: {entry.get('path')}")
        database_file = root / "data" / "minutas.db"
        if not database_file.is_file():
            issues.append("Falta data/minutas.db")
        if issues:
            raise BackupError("El respaldo no superó la verificación: " + " | ".join(issues))
        return manifest


def restore_backup(path: str | Path) -> dict:
    manifest = verify_backup(path)
    source = Path(path)
    with tempfile.TemporaryDirectory(prefix="minutas_ash_restore_") as temp_dir:
        root = Path(temp_dir)
        with zipfile.ZipFile(source, "r") as archive:
            archive.extractall(root)
        database_path().parent.mkdir(parents=True, exist_ok=True)
        config_path().parent.mkdir(parents=True, exist_ok=True)
        templates_dir().mkdir(parents=True, exist_ok=True)

        db_source = root / "data" / "minutas.db"
        db_target = database_path()
        if db_target.exists():
            safety = db_target.with_name(
                f"{db_target.stem}_antes_restaurar_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db_target.suffix}"
            )
            shutil.copy2(db_target, safety)
        temporary_db = db_target.with_suffix(".restore.tmp")
        shutil.copy2(db_source, temporary_db)
        temporary_db.replace(db_target)

        config_source = root / "config" / "config.json"
        if config_source.is_file():
            temporary_config = config_path().with_suffix(".restore.tmp")
            shutil.copy2(config_source, temporary_config)
            temporary_config.replace(config_path())

        template_source = root / "templates"
        if template_source.is_dir():
            shutil.copytree(template_source, templates_dir(), dirs_exist_ok=True)
    return manifest


def prune_backups(retention_count: int = 5) -> list[Path]:
    retention = max(1, min(int(retention_count), 100))
    files = sorted(
        backups_dir().glob("MinutasASH_Backup_*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    removed: list[Path] = []
    for path in files[retention:]:
        try:
            path.unlink()
            removed.append(path)
        except OSError:
            continue
    return removed


def maybe_create_automatic_backup(
    database: MeetingRepository,
    *,
    enabled: bool,
    interval_days: int,
    retention_count: int,
    app_version: str,
) -> Path | None:
    if not enabled:
        return None
    backups_dir().mkdir(parents=True, exist_ok=True)
    existing = sorted(
        backups_dir().glob("MinutasASH_Backup_*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if existing:
        modified = datetime.fromtimestamp(existing[0].stat().st_mtime)
        if datetime.now() - modified < timedelta(days=max(1, int(interval_days))):
            return None
    result = create_backup(database, app_version=app_version)
    prune_backups(retention_count)
    return result
