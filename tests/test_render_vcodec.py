"""Tests for render codec selection behavior."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline.render as render_module
from pipeline.utils import Config


@pytest.fixture
def render_config(tmp_path: Path) -> Config:
    raw = {
        "paths": {
            "raw": str(tmp_path / "raw"),
            "captions": str(tmp_path / "captions"),
            "outputs": str(tmp_path / "outputs"),
            "aligned": str(tmp_path / "aligned"),
        },
        "render": {
            "vcodec": "h264_nvenc",
            "fps": 30,
            "vbitrate": "8M",
            "abitrate": "192k",
        },
    }

    for key in ("raw", "captions", "outputs", "aligned"):
        path = tmp_path / key
        path.mkdir(parents=True, exist_ok=True)

    captions = tmp_path / "captions" / "clip.ass"
    captions.write_text("{\n}")

    return Config(raw=raw)


def _prepare_render(monkeypatch, tmp_path: Path):
    input_video = tmp_path / "raw" / "clip.mp4"
    input_video.touch()

    def fake_ensure_video(video_id, raw_dir, logger):  # pragma: no cover - simple shim
        return input_video

    monkeypatch.setattr(render_module, "ensure_video", fake_ensure_video)
    monkeypatch.setattr(render_module, "build_filters", lambda *args, **kwargs: "vf")
    monkeypatch.setattr(render_module, "build_audio_filters", lambda *args, **kwargs: "")

    commands: dict[str, list[str]] = {}

    def capture_run(cmd, logger, cwd=None):
        commands["cmd"] = cmd

    monkeypatch.setattr(render_module, "run_command", capture_run)
    return commands


def test_render_uses_nvenc_when_available(monkeypatch, tmp_path: Path, render_config: Config):
    commands = _prepare_render(monkeypatch, tmp_path)

    monkeypatch.setattr(render_module, "is_ffmpeg_encoder_available", lambda codec: True)

    logger = logging.getLogger("test-render-available")
    logger.handlers.clear()

    output = render_module.render("clip", render_config, logger)

    assert commands["cmd"][commands["cmd"].index("-c:v") + 1] == "h264_nvenc"
    assert output.name == "clip.mp4"


def test_render_falls_back_to_cpu_when_nvenc_missing(
    monkeypatch, tmp_path: Path, render_config: Config, caplog
):
    commands = _prepare_render(monkeypatch, tmp_path)

    monkeypatch.setattr(render_module, "is_ffmpeg_encoder_available", lambda codec: False)

    logger = logging.getLogger("test-render-fallback")
    logger.handlers.clear()

    caplog.set_level(logging.WARNING)

    output = render_module.render("clip", render_config, logger)

    assert commands["cmd"][commands["cmd"].index("-c:v") + 1] == "libx264"
    assert "falling back to libx264" in caplog.text
    assert output.name == "clip.mp4"
