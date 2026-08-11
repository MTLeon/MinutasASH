import os
import time
from pathlib import Path

from src.inbox import scan_inbox


def test_scan_inbox_filters_and_marks_files_stable(tmp_path: Path):
    ready = tmp_path / "reunion.vtt"
    ready.write_text("WEBVTT", encoding="utf-8")
    copying = tmp_path / "audio.mp3"
    copying.write_bytes(b"audio")
    (tmp_path / "ignorar.exe").write_bytes(b"x")
    now = time.time()
    os.utime(ready, (now - 10, now - 10))
    os.utime(copying, (now - 1, now - 1))
    items = scan_inbox(tmp_path, now=now, stable_seconds=3)
    assert [entry.path.name for entry in items] == ["reunion.vtt", "audio.mp3"]
    assert items[0].ready is True
    assert items[1].ready is False


def test_missing_inbox_is_empty(tmp_path: Path):
    assert scan_inbox(tmp_path / "missing") == []
