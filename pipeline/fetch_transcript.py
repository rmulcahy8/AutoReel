"""Fetch free YouTube captions if available."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple
from xml.etree.ElementTree import ParseError

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._errors import CouldNotRetrieveTranscript

try:  # youtube-transcript-api>=0.6.3 exposes a common base error
    from youtube_transcript_api import YouTubeTranscriptApiError  # type: ignore
except ImportError:  # pragma: no cover - older versions do not expose this symbol
    YouTubeTranscriptApiError = None  # type: ignore

from .utils import (
    Config,
    PipelineError,
    append_jsonl,
    build_logger,
    resolve_path,
    write_json,
)


def _youtube_error_types() -> Tuple[type, ...]:
    """Build a tuple of youtube-transcript-api error classes to catch."""

    base_errors: Tuple[type, ...] = (
        TranscriptsDisabled,
        NoTranscriptFound,
        CouldNotRetrieveTranscript,
    )

    if YouTubeTranscriptApiError is not None:
        return base_errors + (YouTubeTranscriptApiError,)

    return base_errors


def fetch_caption(video_id: str, languages: List[str], logger) -> List[dict]:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        logger.info("Fetched %d caption segments for %s", len(transcript), video_id)
        return transcript
    except _youtube_error_types() as exc:
        logger.warning("Transcript unavailable for %s: %s", video_id, exc)
        raise PipelineError(str(exc)) from exc
    except ParseError as exc:
        logger.warning("Transcript parsing failed for %s: %s", video_id, exc)
        raise PipelineError(str(exc)) from exc


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch available YouTube transcripts")
    parser.add_argument("--video-id", help="Single video ID", default=None)
    parser.add_argument("--queue", help="Path to queue file", default=None)
    parser.add_argument("--lang", help="Preferred language code", default="en")
    args = parser.parse_args(argv)

    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("fetch_transcript", log_dir)

    try:
        languages = [args.lang, args.lang.split("-")[0]] if "-" in args.lang else [args.lang]
        pending: List[str] = []
        if args.video_id:
            pending.append(args.video_id)
        elif args.queue:
            queue_path = Path(args.queue)
            if not queue_path.exists():
                raise PipelineError(f"Queue file missing: {queue_path}")
            for line in queue_path.read_text().splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                pending.append(record["video_id"])
        else:
            raise PipelineError("Must supply --video-id or --queue")

        captions_dir = resolve_path(data_paths.get("transcripts", "data/transcripts"))
        pending_asr = resolve_path(captions_dir, "pending_asr.jsonl")

        for video_id in pending:
            out_path = captions_dir / f"{video_id}.yt.json"
            if out_path.exists():
                logger.info("Transcript already exists for %s", video_id)
                continue
            try:
                data = fetch_caption(video_id, languages, logger)
            except PipelineError:
                append_jsonl(pending_asr, {"video_id": video_id})
                continue
            write_json(out_path, data)
    except Exception as exc:
        logger.exception("fetch_transcript failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
