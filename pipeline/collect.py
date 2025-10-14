"""Collect metadata and queue jobs for AutoReel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from rich.progress import track

from .utils import (
    Config,
    PipelineError,
    append_jsonl,
    build_logger,
    extract_video_id,
    resolve_path,
)


def run_command_capture(cmd: List[str], logger) -> str:
    logger.info("$ %s", " ".join(cmd))
    from subprocess import CalledProcessError, check_output

    try:
        output = check_output(cmd, text=True)
        return output
    except CalledProcessError as exc:
        raise PipelineError(f"Command failed: {' '.join(cmd)}") from exc


def fetch_metadata(video_id: str, url: str, meta_path: Path, logger) -> dict:
    if meta_path.exists():
        logger.info("Metadata already exists for %s", video_id)
        return json.loads(meta_path.read_text(encoding="utf-8"))
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--no-warnings",
        "--dump-json",
        url,
    ]
    logger.info("Fetching metadata for %s", video_id)
    result = run_command_capture(cmd, logger)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(result, encoding="utf-8")
    return json.loads(result)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect YouTube metadata")
    parser.add_argument("--url", help="Single YouTube URL")
    parser.add_argument("--urls-file", help="Path to text file with URLs", default=None)
    args = parser.parse_args(argv)

    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("collect", log_dir)

    try:
        urls: List[str] = []
        if args.url:
            urls.append(args.url.strip())
        if args.urls_file:
            file_path = Path(args.urls_file)
            if file_path.exists():
                urls.extend(u.strip() for u in file_path.read_text().splitlines() if u.strip())
            else:
                raise PipelineError(f"URLs file missing: {file_path}")
        if not urls:
            raise PipelineError("No URLs provided")

        queue_path = resolve_path(data_paths.get("tmp", "data/tmp"), "queue.jsonl")
        if queue_path.exists():
            queue_path.unlink()
        for url in track(urls, description="Queueing videos"):
            video_id = extract_video_id(url)
            meta_path = resolve_path(data_paths.get("raw", "data/raw"), f"{video_id}.meta.json")
            metadata = fetch_metadata(video_id, url, meta_path, logger)
            append_jsonl(queue_path, {
                "video_id": video_id,
                "url": url,
                "title": metadata.get("title"),
                "duration": metadata.get("duration"),
            })
            logger.info("Queued %s", video_id)
    except Exception as exc:  # fail closed
        logger.exception("collect failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
