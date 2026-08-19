from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from src.providers.base import RemoteRateLimitError
from src.providers.http_common import post_json


class FakeResponse:
    status_code = 200
    text = "{}"

    def json(self) -> dict:
        return {"ok": True}


class RateLimitedResponse:
    status_code = 429
    text = '{"error":"slow down"}'
    headers = {"retry-after": "2.5"}

    def json(self) -> dict:
        return {"error": "slow down"}


class HttpCancellationTests(unittest.TestCase):
    def test_rate_limit_preserves_retry_after(self) -> None:
        with (
            patch("src.providers.http_common.requests.post", return_value=RateLimitedResponse()),
            self.assertRaises(RemoteRateLimitError) as raised,
        ):
            post_json(
                "https://example.invalid/v1",
                headers={},
                payload={},
                timeout=30,
            )
        self.assertEqual(raised.exception.retry_after_seconds, 2.5)

    def test_in_flight_remote_request_can_be_cancelled(self) -> None:
        started = threading.Event()
        release = threading.Event()
        cancelled = threading.Event()

        def slow_post(*args, **kwargs):
            started.set()
            release.wait(2)
            return FakeResponse()

        def request_cancel() -> None:
            started.wait(1)
            time.sleep(0.05)
            cancelled.set()

        threading.Thread(target=request_cancel, daemon=True).start()
        try:
            with (
                patch("src.providers.http_common.requests.post", side_effect=slow_post),
                self.assertRaises(InterruptedError),
            ):
                post_json(
                    "https://example.invalid/v1",
                    headers={},
                    payload={},
                    timeout=30,
                    cancelled=cancelled.is_set,
                )
        finally:
            release.set()


if __name__ == "__main__":
    unittest.main()
