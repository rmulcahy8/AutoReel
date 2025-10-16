"""Batch orchestrator for AutoReel."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from . import align_words, collect, fetch_transcript, make_ass, render, transcribe
from .transcribe import convert_to_wav, download_audio
from .utils import (
    Config,
    PipelineError,
    build_logger,
    load_jsonl,
    probe_duration,
    resolve_path,
)


def ensure_urls_file(urls: List[str], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(urls) + "\n", encoding="utf-8")
    return path


def orchestrate(urls_file: Path, args, logger) -> None:
    config = Config.load()
    data_paths = config.get("paths") or {}
    tmp_dir = resolve_path(data_paths.get("tmp", "data/tmp"))
    queue_path = tmp_dir / "queue.jsonl"

    logger.info("Collecting metadata")
    ret = collect.main(["--urls-file", str(urls_file)])
    if ret != 0:
        raise PipelineError("collect step failed")

    logger.info("Fetching transcripts")
    ret = fetch_transcript.main(["--queue", str(queue_path), "--lang", config.get("asr", "lang", default="en")])
    if ret != 0:
        raise PipelineError("fetch_transcript step failed")

    pending_asr = resolve_path(data_paths.get("transcripts", "data/transcripts"), "pending_asr.jsonl")
    if pending_asr.exists():
        logger.info("Transcribing pending videos with Whisper")
        ret = transcribe.main(["--pending", str(pending_asr), "--model", config.get("asr", "whisper_model", default="small")])
        if ret != 0:
            raise PipelineError("transcribe step failed")

    queue = load_jsonl(queue_path)
    if not queue:
        raise PipelineError("Queue is empty after collection")

    audio_dir = resolve_path(data_paths.get("audio", "data/audio"))
    transcripts_dir = resolve_path(data_paths.get("transcripts", "data/transcripts"))
    aligned_dir = resolve_path(data_paths.get("aligned", "data/aligned"))
    outputs_dir = resolve_path(data_paths.get("outputs", "data/outputs"))
    raw_dir = resolve_path(data_paths.get("raw", "data/raw"))

    outputs_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = outputs_dir / "manifest.jsonl"
    manifest_path.write_text("", encoding="utf-8")

    processed = 0
    for entry in queue:
        if args.max and processed >= args.max:
            break
        video_id = entry["video_id"]
        logger.info("Processing %s", video_id)
        url = entry.get("url")
        download_audio(video_id, url, audio_dir, raw_dir, logger)
        wav_path = convert_to_wav(audio_dir / f"{video_id}.m4a", config.get("asr", "sample_rate", default=16000), audio_dir, logger)

        ret = align_words.main([
            "--video-id",
            video_id,
            "--audio-dir",
            str(audio_dir),
            "--transcripts-dir",
            str(transcripts_dir),
            "--aligned-dir",
            str(aligned_dir),
            "--lang",
            config.get("asr", "lang", default="en"),
        ])
        if ret != 0:
            raise PipelineError(f"align_words failed for {video_id}")

        ret = make_ass.main([
            "--video-id",
            video_id,
            "--aligned-dir",
            str(aligned_dir),
            "--captions-dir",
            str(resolve_path(data_paths.get("captions", "data/captions"))),
        ])
        if ret != 0:
            raise PipelineError(f"make_ass failed for {video_id}")

        ret = render.main([
            "--video-id",
            video_id,
        ])
        if ret != 0:
            raise PipelineError(f"render failed for {video_id}")

        output_path = resolve_path(data_paths.get("outputs", "data/outputs"), f"{video_id}.mp4")
        duration = None
        try:
            duration = probe_duration(output_path)
        except Exception:
            duration = entry.get("duration")
        manifest_record = {
            "video_id": video_id,
            "title": entry.get("title"),
            "src": str(output_path),
            "duration": duration,
        }
        with manifest_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest_record) + "\n")
        processed += 1

    logger.info("Processed %d videos", processed)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AutoReel batch pipeline")
    parser.add_argument("--urls-file", default="examples/urls.txt")
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--model", default=None, help="Override Whisper model")
    parser.add_argument("--roi", choices=["on", "off"], default="off")
    args = parser.parse_args(argv)

    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("batch", log_dir)

    try:
        urls_file = resolve_path(args.urls_file)
        if not urls_file.exists():
            raise PipelineError(f"URLs file missing: {urls_file}")
        orchestrate(urls_file, args, logger)
    except Exception as exc:
        logger.exception("batch failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
