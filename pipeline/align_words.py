"""Align transcripts to word-level timings using WhisperX."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from .utils import (
    Config,
    PipelineError,
    build_logger,
    detect_device,
    read_json,
    resolve_path,
    write_json,
)


def load_transcript(video_id: str, transcripts_dir: Path, logger) -> List[Dict[str, Any]]:
    yt_path = transcripts_dir / f"{video_id}.yt.json"
    if yt_path.exists():
        logger.info("Using YouTube transcript for %s", video_id)
        return read_json(yt_path)
    whisper_path = transcripts_dir / f"{video_id}.whisper.segments.json"
    if whisper_path.exists():
        logger.info("Using Whisper transcript for %s", video_id)
        return read_json(whisper_path)
    raise PipelineError(f"No transcript available for {video_id}")


def transcript_to_segments(transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    for item in transcript:
        if {"start", "duration", "text"}.issubset(item.keys()):
            start = float(item["start"])
            duration = float(item["duration"])
            end = start + duration
            segments.append({"text": item["text"], "start": start, "end": end})
        elif {"start", "end", "text"}.issubset(item.keys()):
            segments.append({"text": item["text"], "start": float(item["start"]), "end": float(item["end"])})
    return segments


def align(video_id: str, audio_path: Path, segments: List[Dict[str, Any]], language: str, device: str, logger) -> Dict[str, Any]:
    if not segments:
        raise PipelineError(f"Transcript segments empty for {video_id}")
    try:
        import whisperx
    except ImportError as exc:
        raise PipelineError("whisperx not installed") from exc

    logger.info("Loading WhisperX alignment model for %s", language)
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    logger.info("Aligning %d segments for %s", len(segments), video_id)
    alignment = whisperx.align(
        segments,
        align_model,
        metadata,
        str(audio_path),
        device=device,
        return_char_alignments=False,
    )

    words = [
        {"w": w.get("word", ""), "s": float(w.get("start", 0.0)), "e": float(w.get("end", 0.0))}
        for w in alignment.get("word_segments", [])
    ]

    min_gap = float(Config.load().get("alignment", "min_gap_s", default=0.3))
    lines: List[Dict[str, Any]] = []
    current_line: Dict[str, Any] = {"words": [], "s": None, "e": None}
    last_end: float | None = None

    for word in words:
        start = word["s"]
        end = word["e"]
        if last_end is not None and start - last_end >= min_gap and current_line["words"]:
            lines.append(current_line)
            current_line = {"words": [], "s": start, "e": end}
        if current_line["s"] is None:
            current_line["s"] = start
        current_line["e"] = end
        current_line["words"].append(word)
        last_end = end
    if current_line["words"]:
        lines.append(current_line)

    payload = {"video_id": video_id, "words": words, "lines": lines}
    return payload


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Align transcripts with WhisperX")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--audio-dir", default="data/audio")
    parser.add_argument("--transcripts-dir", default="data/transcripts")
    parser.add_argument("--aligned-dir", default="data/aligned")
    parser.add_argument("--lang", default=None)
    args = parser.parse_args(argv)

    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("align_words", log_dir)

    try:
        transcripts_dir = resolve_path(args.transcripts_dir)
        aligned_dir = resolve_path(args.aligned_dir)
        audio_dir = resolve_path(args.audio_dir)
        audio_path = audio_dir / f"{args.video_id}.wav"
        if not audio_path.exists():
            audio_path = audio_dir / f"{args.video_id}.m4a"
        if not audio_path.exists():
            raise PipelineError(f"Audio missing for {args.video_id}")
        transcript = load_transcript(args.video_id, transcripts_dir, logger)
        segments = transcript_to_segments(transcript)
        if not segments:
            raise PipelineError(f"Could not build segments for {args.video_id}")
        language = args.lang or config.get("asr", "lang", default="en")
        device = detect_device(config.get("asr", "device", default="auto"))
        result = align(args.video_id, audio_path, segments, language, device, logger)
        out_path = aligned_dir / f"{args.video_id}.words.json"
        write_json(out_path, result)
        logger.info("Saved alignment to %s", out_path)
    except Exception as exc:
        logger.exception("align_words failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
