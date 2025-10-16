"""Whisper transcription fallback for videos without native captions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from tqdm import tqdm

from .utils import (
    Config,
    PipelineError,
    build_logger,
    detect_device,
    ensure_video,
    resolve_path,
    run_command,
    write_json,
)


def download_audio(video_id: str, url: str, audio_dir: Path, raw_dir: Path, logger) -> Path:
    audio_dir.mkdir(parents=True, exist_ok=True)
    m4a_path = audio_dir / f"{video_id}.m4a"
    if m4a_path.exists():
        logger.info("Audio already downloaded for %s", video_id)
        return m4a_path

    mp4_path = ensure_video(video_id, raw_dir, logger, url=url)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp4_path),
        "-vn",
        "-acodec",
        "copy",
        str(m4a_path),
    ]
    run_command(cmd, logger)
    return m4a_path


def convert_to_wav(m4a_path: Path, sample_rate: int, audio_dir: Path, logger) -> Path:
    wav_path = audio_dir / f"{m4a_path.stem}.wav"
    if wav_path.exists():
        logger.info("WAV already exists for %s", m4a_path.stem)
        return wav_path
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(m4a_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        str(wav_path),
    ]
    run_command(cmd, logger)
    return wav_path


def run_whisper(wav_path: Path, model: str, device: str, transcripts_dir: Path, logger) -> None:
    logger.info("Running Whisper on %s", wav_path.name)
    try:
        import whisper

        asr = whisper.load_model(model, device=device)
        result = asr.transcribe(str(wav_path))
    except Exception as exc:
        raise PipelineError(f"Whisper failed: {exc}") from exc

    segments = result.get("segments", [])
    text_path = transcripts_dir / f"{wav_path.stem}.whisper.txt"
    segments_path = transcripts_dir / f"{wav_path.stem}.whisper.segments.json"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    text_path.write_text(result.get("text", "").strip(), encoding="utf-8")
    write_json(segments_path, segments)
    logger.info("Saved Whisper outputs for %s", wav_path.stem)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transcribe pending videos with Whisper")
    parser.add_argument("--pending", default="data/transcripts/pending_asr.jsonl")
    parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)

    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("transcribe", log_dir)

    try:
        pending_path = resolve_path(args.pending)
        if not pending_path.exists():
            logger.info("No pending ASR queue found: %s", pending_path)
            return 0

        pending = [json.loads(line)["video_id"] for line in pending_path.read_text().splitlines() if line.strip()]
        if not pending:
            logger.info("No videos to transcribe")
            return 0

        audio_dir = resolve_path(data_paths.get("audio", "data/audio"))
        raw_dir = resolve_path(data_paths.get("raw", "data/raw"))
        transcripts_dir = resolve_path(data_paths.get("transcripts", "data/transcripts"))
        sample_rate = config.get("asr", "sample_rate", default=16000)
        model = args.model or config.get("asr", "whisper_model", default="small")
        device = detect_device(config.get("asr", "device", default="auto"))

        for video_id in tqdm(pending, desc="Transcribing"):
            url = f"https://www.youtube.com/watch?v={video_id}"
            m4a_path = download_audio(video_id, url, audio_dir, raw_dir, logger)
            wav_path = convert_to_wav(m4a_path, sample_rate, audio_dir, logger)
            run_whisper(wav_path, model, device, transcripts_dir, logger)
    except Exception as exc:
        logger.exception("transcribe failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
