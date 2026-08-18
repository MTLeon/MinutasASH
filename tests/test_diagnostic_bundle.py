from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.diagnostics import DiagnosticItem, DiagnosticReport, save_diagnostic_bundle


def test_diagnostic_bundle_excludes_sensitive_data(tmp_path: Path):
    logs = tmp_path / "logs"
    jobs = tmp_path / "jobs"
    support = tmp_path / "support"
    logs.mkdir()
    jobs.mkdir()
    (logs / "MinutasASH.log").write_text("api_key=secret-123 usuario@cliente.cl", encoding="utf-8")
    (jobs / "job-1.json").write_text(
        json.dumps(
            {
                "job_id": "job-1",
                "source_path": "C:/Clientes/Privado/reunion.vtt",
                "provider_id": "anthropic",
                "model": "modelo",
                "status": "failed",
                "progress": 40,
                "error": "Authorization: Bearer token-privado",
            }
        ),
        encoding="utf-8",
    )
    report = DiagnosticReport(
        generated_at="2026-08-11",
        app_version="test",
        items=[DiagnosticItem("Base", "OK", "Disponible")],
    )
    with (
        patch("src.diagnostics.logs_dir", return_value=logs),
        patch("src.diagnostics.jobs_dir", return_value=jobs),
        patch("src.diagnostics.support_dir", return_value=support),
        patch("src.diagnostics.collect_diagnostics", return_value=report),
    ):
        output = save_diagnostic_bundle(
            {"api_key": "secret-config", "processing_provider": "anthropic"}
        )

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        combined = "\n".join(archive.read(name).decode("utf-8") for name in names)
        failures = json.loads(archive.read("errores_por_proveedor.json"))
        jobs_payload = json.loads(archive.read("trabajos.json"))
    assert "diagnostico.txt" in names
    assert "configuracion_sanitizada.json" in names
    assert failures == {"anthropic": 1}
    assert jobs_payload[0]["source_name"] == "reunion.vtt"
    assert "Privado" not in combined
    assert "secret-123" not in combined
    assert "secret-config" not in combined
    assert "token-privado" not in combined
    assert "usuario@cliente.cl" not in combined
