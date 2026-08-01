from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.provisioning import setup_is_complete


class Hotfix235Tests(unittest.TestCase):
    def test_setup_check_does_not_start_external_processes(self) -> None:
        with TemporaryDirectory() as temp:
            state = Path(temp) / "setup_state.json"
            state.write_text(
                json.dumps({"completed": True, "model": "qwen3:8b"}),
                encoding="utf-8",
            )
            with patch("src.provisioning.setup_state_path", return_value=state), patch(
                "src.provisioning.find_ollama_executable", return_value=Path("ollama.exe")
            ), patch(
                "src.provisioning.start_ollama",
                side_effect=AssertionError("No debe iniciar procesos al abrir la GUI"),
            ):
                self.assertTrue(
                    setup_is_complete(
                        {"model": "qwen3:8b", "runtime_mode": "auto"}
                    )
                )


if __name__ == "__main__":
    unittest.main()
