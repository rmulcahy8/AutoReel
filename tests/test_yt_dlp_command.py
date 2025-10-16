"""Regression tests for yt-dlp command resolution."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline.render as render
import pipeline.transcribe as transcribe


class DummyLogger:
    def info(self, *args, **kwargs):  # pragma: no cover - logging passthrough
        logging.getLogger("tests").info(*args, **kwargs)


def test_pipeline_steps_use_module_invocation_when_shim_missing(monkeypatch, tmp_path):
    """Ensure pipeline stages fall back to `python -m yt_dlp` when binaries are absent."""

    commands: dict[str, list[str]] = {}

    def fake_transcribe_run(cmd, logger, cwd=None):
        commands["transcribe"] = cmd

    def fake_render_run(cmd, logger, cwd=None):
        commands["render"] = cmd

    monkeypatch.setattr("pipeline.transcribe.run_command", fake_transcribe_run)
    monkeypatch.setattr("pipeline.render.run_command", fake_render_run)
    monkeypatch.setattr("shutil.which", lambda _: None)

    audio_dir = tmp_path / "audio"
    raw_dir = tmp_path / "raw"

    logger = DummyLogger()

    transcribe.download_audio("abc123def45", "https://example.com", audio_dir, logger)
    render.ensure_video("abc123def45", raw_dir, logger)

    assert commands["transcribe"][:3] == [sys.executable, "-m", "yt_dlp"]
    assert commands["render"][:3] == [sys.executable, "-m", "yt_dlp"]

    assert commands["transcribe"][3:] == [
        "-f",
        "bestaudio",
        "-o",
        str(Path(audio_dir / "abc123def45.m4a")),
        "https://example.com",
    ]

    assert commands["render"][3:] == [
        "-f",
        "bestvideo+bestaudio/best",
        "-o",
        str(Path(raw_dir / "abc123def45.mp4")),
        "https://www.youtube.com/watch?v=abc123def45",
    ]
