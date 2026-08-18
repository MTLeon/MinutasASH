from __future__ import annotations

import json
import logging
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.observability import configure_logger, failure_record, operation, sanitize_text


class ObservabilityTests(unittest.TestCase):
    def tearDown(self) -> None:
        logger = logging.getLogger("minutas_ash")
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    def test_operation_id_is_written_to_log(self):
        with TemporaryDirectory() as directory:
            logger = configure_logger(Path(directory))
            with operation("meeting-42"):
                logger.info("processing_started")
            for handler in logger.handlers:
                handler.flush()

            content = (Path(directory) / "MinutasASH.log").read_text(encoding="utf-8")
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                handler.close()

        self.assertIn("op=meeting-42", content)
        self.assertIn("processing_started", content)

    def test_sensitive_values_are_redacted(self):
        value = sanitize_text(
            "api_key=super-secret Authorization: Bearer abc123 usuario@cliente.cl"
        )
        self.assertNotIn("super-secret", value)
        self.assertNotIn("abc123", value)
        self.assertNotIn("usuario@cliente.cl", value)
        self.assertIn("<redacted>", value)

    def test_failure_record_is_machine_readable(self):
        with operation("operation-7"):
            record = failure_record(RuntimeError("provider timeout"), origin="worker")

        payload = json.loads(record.to_json())
        self.assertEqual(payload["operation_id"], "operation-7")
        self.assertEqual(payload["origin"], "worker")
        self.assertEqual(payload["exception_type"], "RuntimeError")
        self.assertEqual(payload["message"], "provider timeout")


if __name__ == "__main__":
    unittest.main()
