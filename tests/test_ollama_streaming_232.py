from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from pydantic import BaseModel

from src.ollama_client import OllamaClient


class SampleOutput(BaseModel):
    value: str


class FakeResponse:
    def __init__(self, packets: list[dict]) -> None:
        self.packets = packets
        self.closed = False

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self, decode_unicode=True):
        for packet in self.packets:
            yield json.dumps(packet)

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict] = []
        self.closed = False

    def post(self, url, json=None, stream=None, timeout=None):
        self.requests.append(
            {"url": url, "json": json, "stream": stream, "timeout": timeout}
        )
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


class OllamaStreaming232Tests(unittest.TestCase):
    def test_streamed_structured_output_is_reassembled(self) -> None:
        packets = [
            {"message": {"content": '{"value":'}, "done": False},
            {
                "message": {"content": '"ok"}'},
                "done": True,
                "eval_count": 5,
                "eval_duration": 1000,
            },
        ]
        response = FakeResponse(packets)
        session = FakeSession([response])
        events: list[dict] = []
        client = OllamaClient("http://127.0.0.1:11434", "fake", timeout_seconds=60)
        client.configure_runtime(telemetry=events.append, cancelled=lambda: False)
        client.configure_request(operation={"stage": "unit", "block_index": 1})
        with patch("src.ollama_client.requests.Session", return_value=session):
            result = client.structured_chat("system", "user", SampleOutput)
        self.assertEqual(result.value, "ok")
        self.assertTrue(response.closed)
        self.assertTrue(session.closed)
        self.assertTrue(session.requests[0]["stream"])
        self.assertTrue(any(event.get("type") == "stream_activity" for event in events))
        finished = [event for event in events if event.get("type") == "request_finished"]
        self.assertEqual(finished[0].get("eval_count"), 5)
        self.assertEqual(finished[0].get("stage"), "unit")

    def test_invalid_schema_is_retried_with_a_new_stream(self) -> None:
        first = FakeResponse(
            [{"message": {"content": '{"wrong": 1}'}, "done": True}]
        )
        second = FakeResponse(
            [{"message": {"content": '{"value": "fixed"}'}, "done": True}]
        )
        session = FakeSession([first, second])
        events: list[dict] = []
        client = OllamaClient("http://127.0.0.1:11434", "fake", timeout_seconds=60)
        client.configure_runtime(telemetry=events.append, cancelled=lambda: False)
        with patch("src.ollama_client.requests.Session", return_value=session):
            result = client.structured_chat("system", "user", SampleOutput)
        self.assertEqual(result.value, "fixed")
        self.assertEqual(len(session.requests), 2)
        self.assertTrue(
            any(event.get("type") == "schema_validation_failed" for event in events)
        )


if __name__ == "__main__":
    unittest.main()
