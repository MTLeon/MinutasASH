from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import requests

from src.teams_graph import TeamsGraphClient, TeamsGraphError, TeamsGraphImporter


def response(status: int, *, payload=None, content: bytes = b"") -> Mock:
    item = Mock(spec=requests.Response)
    item.status_code = status
    item.ok = 200 <= status < 300
    item.content = content
    item.json.return_value = payload
    return item


class TeamsGraphClientTests(unittest.TestCase):
    def test_finds_meeting_and_encodes_filter_as_parameter(self):
        session = Mock(spec=requests.Session)
        session.headers = {}
        session.get.return_value = response(200, payload={"value": [{"id": "meeting-1"}]})
        client = TeamsGraphClient("token", session=session)

        meeting = client.find_meeting_by_join_url("https://teams.microsoft.com/l/meetup-join/abc")

        self.assertEqual(meeting["id"], "meeting-1")
        params = session.get.call_args.kwargs["params"]
        self.assertIn("JoinWebUrl eq", params["$filter"])
        self.assertNotIn("token", str(session.get.call_args))

    def test_rejects_non_teams_join_url(self):
        session = Mock(spec=requests.Session)
        session.headers = {}
        client = TeamsGraphClient("token", session=session)
        with self.assertRaises(TeamsGraphError):
            client.find_meeting_by_join_url("https://example.com/meeting")

    def test_rejects_untrusted_content_url(self):
        session = Mock(spec=requests.Session)
        session.headers = {}
        client = TeamsGraphClient("token", session=session)
        with self.assertRaises(TeamsGraphError):
            client.download_content(
                "meeting", {"id": "transcript", "transcriptContentUrl": "https://evil.test/a"}
            )
        session.get.assert_not_called()

    def test_retries_without_speakers_when_tenant_disallows_attribution(self):
        session = Mock(spec=requests.Session)
        session.headers = {}
        denied = response(
            403,
            payload={
                "error": {
                    "code": "Forbidden",
                    "innerError": {"code": "SpeakerAttributionNotAllowed"},
                }
            },
        )
        plain = response(200, content=b"00:00:01.000 --> 00:00:02.000\nHola\n")
        session.get.side_effect = [denied, plain]
        client = TeamsGraphClient("token", session=session)

        content = client.download_content("meeting", {"id": "transcript"})

        self.assertTrue(content.startswith(b"WEBVTT\n\n"))
        self.assertEqual(
            session.get.call_args.kwargs["headers"]["Accept"],
            "application/vnd.microsoft.graph.transcript+text",
        )


class TeamsGraphImporterTests(unittest.TestCase):
    def test_imports_once_and_records_state_atomically(self):
        client = Mock(spec=TeamsGraphClient)
        client.find_meeting_by_join_url.return_value = {"id": "meeting", "subject": "Revisión ASH"}
        client.list_transcripts.return_value = [{"id": "transcript-1"}]
        client.download_content.return_value = b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHola\n"
        with TemporaryDirectory() as directory:
            root = Path(directory)
            importer = TeamsGraphImporter(client, root / "inbox", root / "state.json")

            first = importer.import_join_url("https://teams.microsoft.com/l/meetup-join/a")
            second = importer.import_join_url("https://teams.microsoft.com/l/meetup-join/a")

            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            self.assertTrue(first[0].path.is_file())
            state = json.loads((root / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["transcript_ids"], ["transcript-1"])
            client.download_content.assert_called_once()


if __name__ == "__main__":
    unittest.main()
