from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import requests

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPES = (
    "https://graph.microsoft.com/OnlineMeetings.Read",
    "https://graph.microsoft.com/OnlineMeetingTranscript.Read.All",
)


class TeamsGraphError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, code: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class ImportedTranscript:
    transcript_id: str
    meeting_id: str
    path: Path
    sha256: str


def _graph_error(response: requests.Response) -> TeamsGraphError:
    code = ""
    message = f"Microsoft Graph respondió HTTP {response.status_code}."
    try:
        payload = response.json()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        inner = error.get("innerError", {}) if isinstance(error, dict) else {}
        code = str(inner.get("code") or error.get("code") or "")
        if error.get("message"):
            message = str(error["message"])
    except (ValueError, TypeError):
        pass
    friendly = {
        "GraphAccessToTranscriptsDisabled": (
            "El administrador del tenant deshabilitó el acceso de Graph a transcripciones."
        ),
        "SpeakerAttributionNotAllowed": (
            "El tenant no permite atribución de hablantes en la transcripción."
        ),
    }.get(code)
    return TeamsGraphError(friendly or message, status_code=response.status_code, code=code)


def _safe_graph_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "graph.microsoft.com":
        raise TeamsGraphError("Graph devolvió una URL de contenido no permitida.")
    if not parsed.path.startswith(("/v1.0/", "/beta/")):
        raise TeamsGraphError("Graph devolvió una ruta de contenido no reconocida.")
    return url


def _safe_name(value: str, fallback: str = "reunion-teams") -> str:
    cleaned = re.sub(r"[^0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ._-]+", "-", value).strip("-._")
    return cleaned[:80] or fallback


class TeamsGraphClient:
    """Cliente REST mínimo para importar transcripciones autorizadas de Teams."""

    def __init__(
        self,
        access_token: str,
        *,
        timeout_seconds: int = 60,
        session: requests.Session | None = None,
    ) -> None:
        if not access_token.strip():
            raise ValueError("Se requiere un token de acceso de Microsoft Graph.")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token.strip()}"})

    def _get_json(self, url: str, *, params: dict[str, str] | None = None) -> dict[str, Any]:
        response = self.session.get(
            _safe_graph_url(url), params=params, timeout=self.timeout_seconds
        )
        if not response.ok:
            raise _graph_error(response)
        payload = response.json()
        if not isinstance(payload, dict):
            raise TeamsGraphError("Microsoft Graph devolvió una respuesta JSON inválida.")
        return payload

    def find_meeting_by_join_url(self, join_url: str) -> dict[str, Any]:
        value = join_url.strip()
        parsed = urlparse(value)
        host = parsed.hostname or ""
        trusted_host = host in {"teams.microsoft.com", "teams.cloud.microsoft"} or (
            host.endswith(".teams.microsoft.com") or host.endswith(".teams.cloud.microsoft")
        )
        if parsed.scheme != "https" or not trusted_host:
            raise TeamsGraphError("Ingrese un enlace HTTPS válido de una reunión de Teams.")
        escaped = value.replace("'", "''")
        payload = self._get_json(
            f"{GRAPH_BASE_URL}/me/onlineMeetings",
            params={"$filter": f"JoinWebUrl eq '{escaped}'"},
        )
        meetings = payload.get("value")
        if not isinstance(meetings, list) or not meetings:
            raise TeamsGraphError(
                "No se encontró una reunión accesible para ese enlace. Verifique la cuenta y los permisos."
            )
        meeting = meetings[0]
        if not isinstance(meeting, dict) or not meeting.get("id"):
            raise TeamsGraphError("La reunión encontrada no contiene un identificador válido.")
        return meeting

    def list_transcripts(self, meeting_id: str) -> list[dict[str, Any]]:
        url = f"{GRAPH_BASE_URL}/me/onlineMeetings/{quote(meeting_id, safe='')}/transcripts"
        result: list[dict[str, Any]] = []
        while url:
            payload = self._get_json(url)
            values = payload.get("value", [])
            if not isinstance(values, list):
                raise TeamsGraphError("Graph devolvió una lista de transcripciones inválida.")
            result.extend(value for value in values if isinstance(value, dict) and value.get("id"))
            next_link = payload.get("@odata.nextLink")
            url = _safe_graph_url(str(next_link)) if next_link else ""
        return result

    def download_content(self, meeting_id: str, transcript: dict[str, Any]) -> bytes:
        transcript_id = str(transcript["id"])
        content_url = str(transcript.get("transcriptContentUrl") or "")
        if not content_url:
            content_url = (
                f"{GRAPH_BASE_URL}/me/onlineMeetings/{quote(meeting_id, safe='')}"
                f"/transcripts/{quote(transcript_id, safe='')}/content"
            )
        content_url = _safe_graph_url(content_url)
        response = self.session.get(
            content_url,
            headers={"Accept": "text/vtt"},
            timeout=self.timeout_seconds,
        )
        if response.ok:
            return response.content
        error = _graph_error(response)
        if error.code != "SpeakerAttributionNotAllowed":
            raise error
        response = self.session.get(
            content_url,
            headers={"Accept": "application/vnd.microsoft.graph.transcript+text"},
            timeout=self.timeout_seconds,
        )
        if not response.ok:
            raise _graph_error(response)
        body = response.content.lstrip(b"\xef\xbb\xbf")
        return body if body.startswith(b"WEBVTT") else b"WEBVTT\n\n" + body


class TeamsGraphImporter:
    def __init__(self, client: TeamsGraphClient, inbox: Path, state_path: Path) -> None:
        self.client = client
        self.inbox = inbox
        self.state_path = state_path

    def _read_state(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)

    def import_join_url(self, join_url: str) -> list[ImportedTranscript]:
        meeting = self.client.find_meeting_by_join_url(join_url)
        meeting_id = str(meeting["id"])
        subject = _safe_name(str(meeting.get("subject") or "reunion-teams"))
        transcripts = self.client.list_transcripts(meeting_id)
        if not transcripts:
            raise TeamsGraphError("La reunión todavía no tiene una transcripción disponible.")
        state = self._read_state()
        imported_ids = set(str(value) for value in state.get("transcript_ids", []))
        self.inbox.mkdir(parents=True, exist_ok=True)
        imported: list[ImportedTranscript] = []
        for transcript in transcripts:
            transcript_id = str(transcript["id"])
            if transcript_id in imported_ids:
                continue
            content = self.client.download_content(meeting_id, transcript)
            digest = hashlib.sha256(content).hexdigest()
            target = self.inbox / f"{subject}-{digest[:12]}.vtt"
            if not target.exists():
                temporary = target.with_suffix(".vtt.tmp")
                temporary.write_bytes(content)
                temporary.replace(target)
            imported.append(ImportedTranscript(transcript_id, meeting_id, target, digest))
            imported_ids.add(transcript_id)
        state["transcript_ids"] = sorted(imported_ids)
        self._write_state(state)
        return imported


def acquire_interactive_token(client_id: str, tenant_id: str = "organizations") -> str:
    """Inicia OAuth interactivo. MSAL conserva el token solo durante este proceso."""

    try:
        import msal
    except ImportError as exc:  # pragma: no cover - solo en instalaciones incompletas.
        raise TeamsGraphError(
            "El componente de autenticación Microsoft no está instalado."
        ) from exc
    clean_client_id = client_id.strip()
    clean_tenant = tenant_id.strip() or "organizations"
    if not clean_client_id:
        raise TeamsGraphError("Configure el identificador de aplicación de Microsoft Entra.")
    authority = f"https://login.microsoftonline.com/{quote(clean_tenant, safe='.-')}"
    app = msal.PublicClientApplication(clean_client_id, authority=authority)
    result = app.acquire_token_interactive(scopes=list(GRAPH_SCOPES), prompt="select_account")
    token = result.get("access_token") if isinstance(result, dict) else None
    if token:
        return str(token)
    detail = result.get("error_description") if isinstance(result, dict) else None
    raise TeamsGraphError(str(detail or "No fue posible iniciar sesión en Microsoft 365."))
