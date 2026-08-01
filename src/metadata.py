from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import re

from src.models import Attendee, MeetingMetadata


def load_metadata(path: str | Path | None) -> MeetingMetadata:
    if not path:
        return MeetingMetadata(document_date=date.today().isoformat())
    metadata_path = Path(path)
    if not metadata_path.exists():
        raise FileNotFoundError(f"No existe el archivo de datos: {metadata_path}")
    payload = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    metadata = MeetingMetadata.model_validate(payload)
    if not metadata.document_date:
        metadata.document_date = date.today().isoformat()
    return metadata


def initials_from_name(name: str) -> str:
    words = [word for word in re.split(r"\s+", name.strip()) if word]
    if not words:
        return ""
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def enrich_attendees(
    metadata: MeetingMetadata,
    speakers: list[str],
    auto_add: bool,
) -> MeetingMetadata:
    known = {item.name.casefold(): item for item in metadata.attendees}
    if auto_add:
        for speaker in speakers:
            if speaker.casefold() not in known:
                metadata.attendees.append(
                    Attendee(
                        name=speaker,
                        initials=initials_from_name(speaker),
                        organization="Por confirmar",
                    )
                )
    for index, attendee in enumerate(metadata.attendees, start=1):
        attendee.id = attendee.id or index
        attendee.initials = attendee.initials or initials_from_name(attendee.name)
        attendee.organization = attendee.organization or "Por confirmar"
    metadata.attendees.sort(key=lambda item: item.id or 9999)
    return metadata


def format_date(value: str | None, separator: str = "/") -> str:
    if not value:
        return ""
    clean = value.strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(clean, pattern)
            return parsed.strftime(f"%d{separator}%m{separator}%Y")
        except ValueError:
            pass
    return clean
