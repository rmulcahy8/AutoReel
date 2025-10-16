"""Tests for the transcription helpers."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from pipeline import transcribe
from pipeline import utils as pipeline_utils


@pytest.fixture()
def logger() -> logging.Logger:
    log = logging.getLogger("transcribe-test")
    log.handlers = []
    log.addHandler(logging.NullHandler())
    return log


def test_download_audio_uses_single_yt_dlp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, logger: logging.Logger) -> None:
    """Ensure we only invoke yt-dlp once while extracting audio."""

    commands: list[list[str]] = []

    def fake_run(cmd, _logger, cwd=None):  # type: ignore[override]
        commands.append(cmd)
        if "-o" in cmd:
            out = Path(cmd[cmd.index("-o") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"video")
        elif cmd and cmd[0] == "ffmpeg":
            out = Path(cmd[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"audio")

    monkeypatch.setattr(transcribe, "run_command", fake_run)
    monkeypatch.setattr(pipeline_utils, "run_command", fake_run)

    audio_dir = tmp_path / "audio"
    raw_dir = tmp_path / "raw"

    m4a_path = transcribe.download_audio("abc123xyz89", "https://youtu.be/abc123xyz89", audio_dir, raw_dir, logger)
    assert m4a_path == audio_dir / "abc123xyz89.m4a"
    assert m4a_path.exists()

    wav_path = transcribe.convert_to_wav(m4a_path, 16000, audio_dir, logger)
    assert wav_path == audio_dir / "abc123xyz89.wav"
    assert wav_path.exists()

    ytdlp_commands = [cmd for cmd in commands if any("yt-dlp" in part or "yt_dlp" in part for part in cmd)]
    assert len(ytdlp_commands) == 1
