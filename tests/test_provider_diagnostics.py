from __future__ import annotations

from src.provider_diagnostics import diagnose_provider


class FakeProvider:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def check_connection(self) -> None:
        if self.error:
            raise self.error


def test_diagnostic_reports_ready_provider() -> None:
    result = diagnose_provider(
        {"processing_provider": "ollama_local", "model": "qwen3:8b"},
        factory=lambda settings, provider_id, model: FakeProvider(),
    )

    assert result.status == "ready"
    assert result.provider_id == "ollama_local"
    assert result.capabilities["offline"] is True
    assert result.capabilities["sends_content_remotely"] is False


def test_diagnostic_reports_safe_connection_error() -> None:
    result = diagnose_provider(
        {"processing_provider": "anthropic", "anthropic_model": "claude-test"},
        factory=lambda settings, provider_id, model: FakeProvider(RuntimeError("sin conexion")),
    )

    assert result.status == "error"
    assert result.message == "sin conexion"
    assert result.capabilities["schema_fallback"] is True
