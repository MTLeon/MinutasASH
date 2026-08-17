from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from src.audio_transcription import AudioPreparationResult
from src.media_transcription_service import MediaTranscriptionRequest, transcribe_meeting_media


@patch("src.media_transcription_service.transcribe_media")
@patch("src.media_transcription_service.prepare_audio_copy")
def test_prepares_then_transcribes_with_all_runtime_options(
    prepare: Mock, transcribe: Mock, tmp_path: Path
) -> None:
    source = tmp_path / "reunion.mp4"
    prepared_path = tmp_path / "reunion_voz_16khz.m4a"
    transcript = tmp_path / "reunion_transcripcion.txt"
    prepare.return_value = AudioPreparationResult(source, prepared_path, 100, 20, False)
    transcribe.return_value = transcript

    result = transcribe_meeting_media(
        MediaTranscriptionRequest(
            source_path=source,
            optimize_audio=True,
            output_format="m4a",
            model_name="small",
            language="es",
            cpu_threads=8,
            diarization_enabled=True,
            diarization_worker="diarize.exe",
        )
    )

    prepare.assert_called_once_with(source.resolve(), output_format="m4a", delete_source=False)
    transcribe.assert_called_once_with(
        prepared_path,
        model_name="small",
        language="es",
        cpu_threads=8,
        diarization_enabled=True,
        diarization_worker="diarize.exe",
    )
    assert result.transcript_path == transcript
    assert result.preparation is prepare.return_value


@patch("src.media_transcription_service.transcribe_media")
@patch("src.media_transcription_service.prepare_audio_copy")
def test_transcribes_original_when_preparation_is_disabled(
    prepare: Mock, transcribe: Mock, tmp_path: Path
) -> None:
    source = tmp_path / "reunion.ogg"
    transcript = tmp_path / "reunion_transcripcion.txt"
    transcribe.return_value = transcript

    result = transcribe_meeting_media(
        MediaTranscriptionRequest(source_path=source, optimize_audio=False)
    )

    prepare.assert_not_called()
    transcribe.assert_called_once()
    assert transcribe.call_args.args[0] == source.resolve()
    assert result.preparation is None
