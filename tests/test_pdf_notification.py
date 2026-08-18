from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

from src.models import Attendee, MeetingItem, MeetingMetadata, MinuteAnalysis
from src.notification_service import _powershell_encoded, notify_local
from src.pdf_writer import generate_minute_pdf


def test_native_pdf_contains_minute_content(tmp_path: Path):
    metadata = MeetingMetadata(
        minute_number="P1-MRE-01",
        document_date="2026-08-11",
        meeting_date="2026-08-10",
        project_code="P1",
        client="Cliente Norte",
        matter="Revisión de ingeniería",
        minute_taker="Ana",
        attendees=[Attendee(name="Ana", role="Jefa de proyecto")],
    )
    analysis = MinuteAnalysis(
        objective="Revisar entregables",
        executive_summary="Se revisó el informe semanal.",
        items=[
            MeetingItem(
                category="compromiso",
                description="Ana enviará el informe actualizado",
                responsible="Ana",
                due_date_text="viernes",
                evidence="00:12:30.000",
                review_status="aprobado",
            )
        ],
    )
    output = generate_minute_pdf(analysis, metadata, tmp_path / "minuta.pdf")
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert output.stat().st_size > 1000
    assert "MINUTA DE REUNIÓN" in text
    assert "informe actualizado" in text
    assert "00:12:30.000" in text


def test_notification_uses_encoded_non_blocking_powershell():
    decoded = base64.b64decode(_powershell_encoded("á")).decode("utf-16-le")
    assert decoded == "á"
    with (
        patch("src.notification_service.sys.platform", "win32"),
        patch("src.notification_service.subprocess.Popen") as popen,
    ):
        assert notify_local("Lista", "Documento listo", "C:/Temp") is True
    arguments = popen.call_args.args[0]
    assert "-EncodedCommand" in arguments
    assert popen.call_args.kwargs["stdout"] is not None


def test_notification_is_safe_noop_outside_windows():
    with patch("src.notification_service.sys.platform", "linux"):
        assert notify_local("Lista", "Documento listo") is False
