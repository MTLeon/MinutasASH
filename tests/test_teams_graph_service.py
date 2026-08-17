from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.teams_graph import ImportedTranscript, TeamsGraphError
from src.teams_graph_service import TeamsGraphImportRequest, import_teams_transcripts


def test_imports_with_injected_dependencies(tmp_path: Path) -> None:
    token_acquirer = Mock(return_value="token")
    client_factory = Mock(return_value=Mock())
    imported = [ImportedTranscript("transcript", "meeting", tmp_path / "meeting.vtt", "hash")]
    importer = Mock()
    importer.import_join_url.return_value = imported
    importer_factory = Mock(return_value=importer)
    request = TeamsGraphImportRequest(
        client_id=" client-id ",
        tenant_id="",
        join_url=" https://teams.microsoft.com/l/meetup-join/example ",
        inbox_path=tmp_path / "inbox",
        state_path=tmp_path / "state.json",
        timeout_seconds=45,
    )

    result = import_teams_transcripts(
        request,
        token_acquirer=token_acquirer,
        client_factory=client_factory,
        importer_factory=importer_factory,
    )

    token_acquirer.assert_called_once_with("client-id", "organizations")
    client_factory.assert_called_once_with("token", timeout_seconds=45)
    importer.import_join_url.assert_called_once_with(
        "https://teams.microsoft.com/l/meetup-join/example"
    )
    assert result == imported


@pytest.mark.parametrize("client_id, join_url", [("", "https://teams.microsoft.com/x"), ("id", "")])
def test_rejects_missing_required_public_data(
    client_id: str, join_url: str, tmp_path: Path
) -> None:
    request = TeamsGraphImportRequest(
        client_id, "organizations", join_url, tmp_path, tmp_path / "state"
    )
    with pytest.raises(TeamsGraphError):
        import_teams_transcripts(request)
