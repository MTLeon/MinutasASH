from __future__ import annotations

import json

from src.processing_jobs import ProcessingJobStore


def test_job_lifecycle_is_persisted(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    job = store.create("reunion.vtt", "ollama_local", "qwen3:8b")

    running = store.update(job.job_id, status="running", progress=42, message="Analizando")
    completed = store.update(job.job_id, status="completed", progress=100, message="Listo")

    assert running.started_at
    assert completed.finished_at
    assert store.get(job.job_id) == completed
    assert (
        json.loads((tmp_path / f"{job.job_id}.json").read_text(encoding="utf-8"))["status"]
        == "completed"
    )


def test_running_jobs_are_recovered_as_interrupted(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    job = store.create("audio.mp3", "openai", "gpt-test")
    store.update(job.job_id, status="running", progress=15)

    recovered = ProcessingJobStore(tmp_path, recover_on_open=True)
    current = recovered.get(job.job_id)

    assert current is not None
    assert current.status == "interrupted"
    assert "interrumpio" in current.message


def test_job_progress_is_clamped_and_errors_are_limited(tmp_path) -> None:
    store = ProcessingJobStore(tmp_path)
    job = store.create("notas.txt", "gemini", "gemini-test")

    failed = store.update(job.job_id, status="failed", progress=120, error="x" * 1500)

    assert failed.progress == 100
    assert len(failed.error) == 1000
