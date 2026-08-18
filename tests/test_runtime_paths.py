from __future__ import annotations

from pathlib import Path

from src import runtime_paths


def test_data_root_override_isolates_runtime_and_configuration(monkeypatch, tmp_path: Path) -> None:
    isolated = tmp_path / "isolated-profile"
    monkeypatch.setenv("MINUTAS_ASH_DATA_ROOT", str(isolated))

    assert runtime_paths.user_data_root() == isolated.resolve()
    assert runtime_paths.config_path() == isolated.resolve() / "config.json"
    assert runtime_paths.database_path() == isolated.resolve() / "data" / "minutas.db"


def test_empty_data_root_override_keeps_development_default(monkeypatch) -> None:
    monkeypatch.setenv("MINUTAS_ASH_DATA_ROOT", "   ")

    assert runtime_paths.user_data_root() == runtime_paths.source_root() / ".runtime"
