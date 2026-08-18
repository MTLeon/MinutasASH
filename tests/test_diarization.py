from __future__ import annotations

import json
from pathlib import Path

from src.audio_transcription import assess_transcription_quality, load_transcription_report
from src.diarization import assign_speakers, parse_rttm_text


def test_rttm_is_parsed_and_assigned_by_overlap() -> None:
    turns = parse_rttm_text(
        "SPEAKER reunion 1 0.00 4.00 <NA> <NA> SPEAKER_00 <NA> <NA>\n"
        "SPEAKER reunion 1 4.00 5.00 <NA> <NA> SPEAKER_01 <NA> <NA>"
    )
    segments = [
        {"start": 0.5, "end": 3.0, "text": "primero"},
        {"start": 5.0, "end": 7.0, "text": "segundo"},
    ]
    assigned = assign_speakers(segments, turns)
    assert assigned[0]["speaker"] == "SPEAKER_00"
    assert assigned[1]["speaker"] == "SPEAKER_01"


def test_quality_flags_low_language_confidence() -> None:
    report = assess_transcription_quality(
        {
            "language": "es",
            "language_probability": 0.4,
            "segments": [{"start": 0, "end": 20, "text": "texto"}],
        }
    )
    assert report.level == "baja"
    assert any("idioma" in reason for reason in report.reasons)


def test_quality_metadata_can_be_loaded(tmp_path: Path) -> None:
    transcript = tmp_path / "reunion.txt"
    transcript.write_text("texto", encoding="utf-8")
    metadata = transcript.with_suffix(".txt.metadata.json")
    metadata.write_text(
        json.dumps(
            {
                "level": "alta",
                "language": "es",
                "language_probability": 0.95,
                "duration_seconds": 10,
                "speech_seconds": 8,
                "segment_count": 2,
                "diarized": True,
                "diarization_detail": "RTTM",
                "reasons": [],
            }
        ),
        encoding="utf-8",
    )
    report = load_transcription_report(transcript)
    assert report is not None
    assert report.diarized
