from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

from src.runtime_paths import user_data_root

ProgressCallback = Callable[[int, str], None]


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    installer_url: str
    sha256: str
    release_notes: str
    mandatory: bool = False
    published_at: str | None = None
    source: str = "manifest"
    release_sequence: int | None = None


def _version_tuple(value: str) -> tuple[int, ...]:
    text = value.strip().lower().lstrip("v")
    match = re.match(r"^(\d+(?:\.\d+){1,3})", text)
    if not match:
        raise ValueError(f"Versión inválida: {value}")
    parts = tuple(int(part) for part in match.group(1).split("."))
    return parts + (0,) * (4 - len(parts))


def version_sequence(value: str) -> int:
    parts = _version_tuple(value)
    return parts[0] * 1_000_000 + parts[1] * 1_000 + parts[2]


def is_newer_version(
    candidate: str,
    current: str,
    candidate_sequence: int | None = None,
    current_sequence: int | None = None,
) -> bool:
    if candidate_sequence is not None or current_sequence is not None:
        left = int(
            candidate_sequence if candidate_sequence is not None else version_sequence(candidate)
        )
        right = int(current_sequence if current_sequence is not None else version_sequence(current))
        return left > right
    return _version_tuple(candidate) > _version_tuple(current)


def _get_json(url: str, timeout: int = 30, headers: dict[str, str] | None = None) -> dict:
    try:
        response = requests.get(url, timeout=timeout, headers=headers or {})
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise UpdateError(f"No fue posible consultar actualizaciones: {exc}") from exc
    except ValueError as exc:
        raise UpdateError("El servidor de actualizaciones no devolvió JSON válido.") from exc
    if not isinstance(data, dict):
        raise UpdateError("El manifiesto de actualización tiene un formato inválido.")
    return data


def _read_sha256_text(url: str, timeout: int = 30) -> str:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise UpdateError(f"No fue posible descargar la huella de la actualización: {exc}") from exc
    match = re.search(r"\b([a-fA-F0-9]{64})\b", response.text)
    if not match:
        raise UpdateError("El archivo de verificación no contiene una huella SHA-256 válida.")
    return match.group(1).lower()


def check_manifest(manifest_url: str, channel: str = "stable") -> UpdateInfo:
    if not manifest_url.startswith("https://"):
        raise UpdateError("El manifiesto de actualización debe usar HTTPS.")
    data = _get_json(manifest_url)
    if "channels" in data:
        channels = data.get("channels") or {}
        data = channels.get(channel) or channels.get("stable") or {}
    required = ["version", "installer_url", "sha256"]
    missing = [name for name in required if not data.get(name)]
    if missing:
        raise UpdateError(f"El manifiesto no contiene: {', '.join(missing)}.")
    installer_url = str(data["installer_url"])
    if not installer_url.startswith("https://"):
        raise UpdateError("La descarga del instalador debe usar HTTPS.")
    sha256 = str(data["sha256"]).strip().lower()
    if not re.fullmatch(r"[a-f0-9]{64}", sha256):
        raise UpdateError("La huella SHA-256 del manifiesto es inválida.")
    notes = data.get("release_notes", "")
    if isinstance(notes, list):
        notes = "\n".join(f"• {item}" for item in notes)
    return UpdateInfo(
        version=str(data["version"]),
        installer_url=installer_url,
        sha256=sha256,
        release_notes=str(notes),
        mandatory=bool(data.get("mandatory", False)),
        published_at=str(data.get("published_at") or "") or None,
        source="manifest",
        release_sequence=(
            int(data["release_sequence"]) if data.get("release_sequence") is not None else None
        ),
    )


def check_github_release(
    owner: str,
    repo: str,
    *,
    allow_prerelease: bool = False,
    channel: str = "stable",
) -> UpdateInfo:
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        raise UpdateError("Configure el propietario y el repositorio de GitHub.")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "MinutasASH-Updater",
    }
    if allow_prerelease or channel != "stable":
        url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=20"
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            releases = response.json()
        except requests.RequestException as exc:
            raise UpdateError(f"No fue posible consultar GitHub Releases: {exc}") from exc
        if not isinstance(releases, list):
            raise UpdateError("GitHub devolvió un listado de releases inválido.")
        release = next(
            (
                item
                for item in releases
                if isinstance(item, dict)
                and not item.get("draft")
                and (allow_prerelease or not item.get("prerelease"))
            ),
            None,
        )
        if not release:
            raise UpdateError("No se encontraron releases publicadas.")
    else:
        release = _get_json(
            f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
            headers=headers,
        )

    assets = release.get("assets") or []
    installer = next(
        (
            asset
            for asset in assets
            if isinstance(asset, dict)
            and str(asset.get("name", "")).lower().endswith(".exe")
            and "minutasash_setup" in str(asset.get("name", "")).lower()
        ),
        None,
    )
    if not installer:
        raise UpdateError("La release no contiene el instalador de Minutas ASH.")
    checksum_asset = next(
        (
            asset
            for asset in assets
            if isinstance(asset, dict)
            and "sha256" in str(asset.get("name", "")).lower()
            and str(asset.get("name", "")).lower().endswith((".txt", ".sha256"))
        ),
        None,
    )
    if not checksum_asset:
        raise UpdateError("La release no contiene el archivo SHA-256 requerido.")
    sha256 = _read_sha256_text(str(checksum_asset.get("browser_download_url")))
    version = str(release.get("tag_name") or release.get("name") or "").lstrip("v")
    return UpdateInfo(
        version=version,
        installer_url=str(installer.get("browser_download_url")),
        sha256=sha256,
        release_notes=str(release.get("body") or ""),
        mandatory=False,
        published_at=str(release.get("published_at") or "") or None,
        source="github",
        release_sequence=None,
    )


def check_for_updates(settings: dict) -> UpdateInfo:
    source = str(settings.get("update_source", "manifest"))
    channel = str(settings.get("update_channel", "stable"))
    if source == "github":
        return check_github_release(
            str(settings.get("github_owner", "")),
            str(settings.get("github_repo", "")),
            allow_prerelease=bool(settings.get("update_allow_prerelease", False)),
            channel=channel,
        )
    return check_manifest(str(settings.get("update_manifest_url", "")), channel)


def update_source_is_configured(settings: dict) -> bool:
    source = str(settings.get("update_source", "manifest"))
    if source == "github":
        return bool(
            str(settings.get("github_owner", "")).strip()
            and str(settings.get("github_repo", "")).strip()
        )
    return bool(str(settings.get("update_manifest_url", "")).strip())


def should_check_now(settings: dict) -> bool:
    if not bool(settings.get("update_enabled", True)):
        return False
    if not update_source_is_configured(settings):
        return False
    if not bool(settings.get("update_check_on_start", True)):
        return False
    last = str(settings.get("update_last_checked_at") or "").strip()
    if not last:
        return True
    try:
        moment = datetime.fromisoformat(last.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
    except ValueError:
        return True
    hours = max(1, int(settings.get("update_check_interval_hours", 24)))
    return datetime.now(UTC) - moment >= timedelta(hours=hours)


def download_update(
    info: UpdateInfo,
    progress: ProgressCallback | None = None,
) -> Path:
    progress = progress or (lambda _value, _text: None)
    updates_dir = user_data_root() / "updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        Path(info.installer_url.split("?", 1)[0]).name or f"MinutasASH_Setup_{info.version}.exe"
    )
    final_path = updates_dir / filename
    temporary = final_path.with_suffix(final_path.suffix + ".download")
    digest = hashlib.sha256()
    try:
        with requests.get(info.installer_url, stream=True, timeout=(30, 300)) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or 0)
            completed = 0
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    digest.update(chunk)
                    completed += len(chunk)
                    value = int(completed * 100 / total) if total else 0
                    progress(
                        value,
                        f"Descargando actualización... {value}%"
                        if total
                        else "Descargando actualización...",
                    )
    except requests.RequestException as exc:
        temporary.unlink(missing_ok=True)
        raise UpdateError(f"No fue posible descargar la actualización: {exc}") from exc
    actual = digest.hexdigest().lower()
    if actual != info.sha256.lower():
        temporary.unlink(missing_ok=True)
        raise UpdateError(
            "La verificación SHA-256 falló. La actualización fue descartada por seguridad."
        )
    temporary.replace(final_path)
    progress(100, "Actualización descargada y verificada")
    return final_path


def launch_installer(path: str | Path) -> None:
    installer = Path(path)
    if not installer.is_file():
        raise UpdateError("No se encontró el instalador descargado.")
    if os.name != "nt":
        raise UpdateError("La instalación automática solo está disponible en Windows.")
    try:
        subprocess.Popen(
            [str(installer), "/SP-", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
            close_fds=True,
        )
    except OSError as exc:
        raise UpdateError(f"No fue posible iniciar el instalador: {exc}") from exc


def write_update_record(info: UpdateInfo, installer_path: Path) -> Path:
    records = user_data_root() / "records"
    records.mkdir(parents=True, exist_ok=True)
    path = records / "ultima_actualizacion_descargada.json"
    path.write_text(
        json.dumps(
            {
                "version": info.version,
                "release_sequence": info.release_sequence,
                "source": info.source,
                "sha256": info.sha256,
                "installer_path": str(installer_path),
                "downloaded_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
