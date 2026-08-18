from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from src.inbox import InboxItem, scan_inbox
from src.models import MeetingItem
from src.review_quality import assess_item


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class ProfileMatch:
    profile: dict[str, Any] | None
    score: float
    reasons: tuple[str, ...]


def match_project_profile(path: Path, profiles: list[dict[str, Any]]) -> ProfileMatch:
    haystack = _normalized(f"{path.stem} {path.parent.name}")
    best: tuple[float, dict[str, Any] | None, list[str]] = (0.0, None, [])
    for profile in profiles:
        if not bool(profile.get("active", True)):
            continue
        score = 0.0
        reasons: list[str] = []
        code = _normalized(profile.get("code"))
        if code and code in haystack:
            score += 0.75
            reasons.append("codigo de proyecto presente en el archivo")
        description = _normalized(profile.get("description"))
        description_tokens = [token for token in description.split() if len(token) >= 5]
        matched_tokens = [token for token in description_tokens if token in haystack]
        if description_tokens and matched_tokens:
            score += min(0.20, 0.05 * len(matched_tokens))
            reasons.append("descripcion de proyecto coincidente")
        client = _normalized(profile.get("client"))
        if client and len(client) >= 3 and client in haystack:
            score += 0.15
            reasons.append("cliente presente en el archivo")
        score = min(score, 1.0)
        if score > best[0]:
            best = (score, profile, reasons)
    return ProfileMatch(best[1], best[0], tuple(best[2]))


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("_", " ").replace("-", " ").split())


@dataclass(frozen=True)
class ExceptionReviewResult:
    auto_approved: int
    requires_attention: int
    attention_indices: tuple[int, ...]


def apply_exception_review(
    items: list[MeetingItem], minimum_confidence: float = 0.90
) -> ExceptionReviewResult:
    approved = 0
    attention: list[int] = []
    for index, item in enumerate(items):
        candidate = item.model_copy(update={"review_status": "aprobado"})
        assessment = assess_item(candidate)
        if not assessment.reasons and item.confidence >= minimum_confidence:
            item.review_status = "aprobado"
            approved += 1
        else:
            item.review_status = "pendiente"
            attention.append(index)
    return ExceptionReviewResult(approved, len(attention), tuple(attention))


@dataclass(frozen=True)
class AutomationRecord:
    fingerprint: str
    source_path: str
    status: str
    attempts: int
    updated_at: float
    message: str = ""


class InboxAutomationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def discover(
        self,
        directory: Path,
        *,
        max_retries: int = 3,
        processing_stale_seconds: float = 3600,
        recursive: bool = False,
        max_files: int = 500,
    ) -> list[InboxItem]:
        records = self._load()
        now = time.time()
        result: list[InboxItem] = []
        for item in scan_inbox(directory, recursive=recursive, max_files=max_files):
            if not item.ready:
                continue
            fingerprint = source_sha256(item.path)
            record = records.get(fingerprint)
            if (
                record is None
                or record.status == "failed"
                and record.attempts < max_retries
                or record.status == "processing"
                and now - record.updated_at >= processing_stale_seconds
            ):
                result.append(item)
        return result

    def mark(self, path: Path, status: str, message: str = "") -> AutomationRecord:
        with self._lock:
            records = self._load()
            fingerprint = source_sha256(path)
            previous = records.get(fingerprint)
            attempts = (previous.attempts if previous else 0) + (1 if status == "processing" else 0)
            record = AutomationRecord(
                fingerprint=fingerprint,
                source_path=str(path.resolve()),
                status=status,
                attempts=attempts,
                updated_at=time.time(),
                message=message[:500],
            )
            records[fingerprint] = record
            self._write(records)
            return record

    def _load(self) -> dict[str, AutomationRecord]:
        if not self.path.is_file():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return {key: AutomationRecord(**value) for key, value in payload.items()}
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return {}

    def _write(self, records: dict[str, AutomationRecord]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {key: asdict(value) for key, value in records.items()}, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)
