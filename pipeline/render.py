"""Render vertical shorts with FFmpeg."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .utils import (
    Config,
    PipelineError,
    build_logger,
    ensure_directory,
    resolve_path,
    run_command,
)


def build_audio_filters(config: Config, presets: Dict[str, Dict[str, str]], music_path: Optional[Path] = None) -> str:
    filters: List[str] = []
    loudnorm = presets.get("loudnorm_speech", {}).get("filter")
    if loudnorm:
        filters.append(loudnorm)
    if music_path:
        sidechain = presets.get("sidechain_ducking", {}).get("filter")
        if sidechain:
            filters.append(sidechain)
    return ",".join(filters)


def load_presets(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("presets", {})


def ensure_video(video_id: str, raw_dir: Path, logger) -> Path:
    mp4_path = raw_dir / f"{video_id}.mp4"
    if mp4_path.exists():
        return mp4_path
    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo+bestaudio/best",
        "-o",
        str(mp4_path),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    run_command(cmd, logger)
    return mp4_path


def load_roi_crop(roi_path: Path) -> Optional[str]:
    try:
        data = json.loads(roi_path.read_text())
    except Exception:
        return None
    frames = []
    if isinstance(data, dict):
        frames = data.get("frames") or data.get("segments") or []
    elif isinstance(data, list):
        frames = data
    if not frames:
        return None
    frame = frames[0]
    x = int(frame.get("x", 0))
    y = int(frame.get("y", 0))
    return f"crop=1080:1920:{x}:{y}"


def build_filters(config: Config, presets: Dict[str, Dict[str, str]], captions_path: Path, roi_path: Optional[Path]) -> str:
    filters: List[str] = []
    crop_strategy = config.get("render", "crop_strategy", default="center")
    if crop_strategy == "center":
        filters.append(presets.get("vertical_crop", {}).get("filter", "scale=-2:1920,crop=1080:1920"))
    elif crop_strategy == "roi" and roi_path and roi_path.exists():
        filters.append("scale=-2:1920")
        roi_filter = load_roi_crop(roi_path)
        filters.append(roi_filter or "crop=1080:1920")
    filters.append(f"subtitles={captions_path.as_posix()}:alpha=1")
    filters.append(presets.get("color_pop", {}).get("filter", "eq=contrast=1.12:saturation=1.2,unsharp=5:5:0.8"))
    return ",".join(filter(None, filters))


def render(video_id: str, config: Config, logger, music: Optional[Path] = None) -> Path:
    data_paths = config.get("paths") or {}
    raw_dir = resolve_path(data_paths.get("raw", "data/raw"))
    captions_dir = resolve_path(data_paths.get("captions", "data/captions"))
    outputs_dir = ensure_directory(resolve_path(data_paths.get("outputs", "data/outputs")))
    aligned_dir = resolve_path(data_paths.get("aligned", "data/aligned"))

    captions_path = captions_dir / f"{video_id}.ass"
    if not captions_path.exists():
        raise PipelineError(f"Captions missing for {video_id}")
    roi_path = aligned_dir / f"{video_id}.roi.json"

    mp4_path = ensure_video(video_id, raw_dir, logger)

    template_path = resolve_path("pipeline/styles/ffmpeg_presets.yaml")
    presets = load_presets(template_path)
    vf = build_filters(config, presets, captions_path, roi_path if roi_path.exists() else None)
    af = build_audio_filters(config, presets, music_path=music)

    vcodec = config.get("render", "vcodec", default="libx264")
    fps = str(config.get("render", "fps", default=30))
    vbitrate = config.get("render", "vbitrate", default="8M")
    abitrate = config.get("render", "abitrate", default="192k")

    output_path = outputs_dir / f"{video_id}.mp4"
    cmd: List[str] = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp4_path),
        "-vf",
        vf,
        "-r",
        fps,
        "-c:v",
        vcodec,
        "-b:v",
        vbitrate,
        "-c:a",
        "aac",
        "-b:a",
        abitrate,
    ]
    if af:
        cmd.extend(["-af", af])
    cmd.append(str(output_path))

    run_command(cmd, logger)
    return output_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render AutoReel vertical short")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--music", help="Optional background music path", default=None)
    args = parser.parse_args(argv)

    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("render", log_dir)

    try:
        music_path = Path(args.music).resolve() if args.music else None
        output_path = render(args.video_id, config, logger, music=music_path)
        logger.info("Rendered video at %s", output_path)
    except Exception as exc:
        logger.exception("render failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
