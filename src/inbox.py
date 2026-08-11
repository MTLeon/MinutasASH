from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SUFFIXES = frozenset(
    {
        ".vtt",
        ".srt",
        ".txt",
        ".docx",
        ".pdf",
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".ogg",
        ".mp4",
        ".mkv",
        ".webm",
    }
)


@dataclass(frozen=True)
class InboxItem:
    path: Path
    size_bytes: int
    modified_at: float
    ready: bool


def scan_inbox(
    directory: str | Path, *, now: float | None = None, stable_seconds: float = 3.0
) -> list[InboxItem]:
    root = Path(directory).expanduser()
    if not root.is_dir():
        return []
    current = time.time() if now is None else now
    result: list[InboxItem] = []
    for path in root.iterdir():
        if (
            path.name.startswith(".")
            or not path.is_file()
            or path.suffix.casefold() not in SUPPORTED_SUFFIXES
        ):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        result.append(
            InboxItem(
                path.resolve(),
                stat.st_size,
                stat.st_mtime,
                stat.st_size > 0 and current - stat.st_mtime >= stable_seconds,
            )
        )
    return sorted(
        result, key=lambda item: (not item.ready, -item.modified_at, item.path.name.casefold())
    )
