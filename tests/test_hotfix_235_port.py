from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import BaseModel, ValidationError

from src.ollama_client import _validation_indicates_truncation
from src.ollama_manager import _hidden_process_kwargs
from src.provisioning import setup_is_complete


class Payload(BaseModel):
    values: list[str]


def test_truncated_json_is_detected() -> None:
    content = '{"values":["uno"'
    try:
        Payload.model_validate_json(content)
    except ValidationError as exc:
        assert _validation_indicates_truncation(content, exc, {})


def test_setup_check_does_not_start_ollama() -> None:
    with TemporaryDirectory() as temp:
        state = Path(temp) / "setup_state.json"
        state.write_text(
            json.dumps({"completed": True, "model": "qwen3:8b"}),
            encoding="utf-8",
        )
        with (
            patch("src.provisioning.setup_state_path", return_value=state),
            patch("src.provisioning.find_ollama_executable", return_value=Path("ollama.exe")),
            patch(
                "src.provisioning.start_ollama",
                side_effect=AssertionError("No debe iniciar procesos al abrir la GUI"),
            ),
        ):
            assert setup_is_complete({"model": "qwen3:8b", "runtime_mode": "auto"})


def test_windows_subprocess_is_hidden() -> None:
    class FakeStartupInfo:
        def __init__(self) -> None:
            self.dwFlags = 0
            self.wShowWindow: int | None = None

    with (
        patch("src.ollama_manager.os.name", "nt"),
        patch("src.ollama_manager.subprocess.CREATE_NO_WINDOW", 0x08000000, create=True),
        patch("src.ollama_manager.subprocess.STARTUPINFO", FakeStartupInfo, create=True),
        patch("src.ollama_manager.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
        patch("src.ollama_manager.subprocess.SW_HIDE", 0, create=True),
    ):
        kwargs = _hidden_process_kwargs()
    assert kwargs["creationflags"] == 0x08000000
    assert kwargs["startupinfo"].dwFlags == 1
    assert kwargs["startupinfo"].wShowWindow == 0
