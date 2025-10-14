"""Generate ASS karaoke captions from aligned words."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Dict, List

from .utils import Config, PipelineError, build_logger, read_json, resolve_path


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:06.3f}"


def word_to_k_tag(start: float, end: float, pad_end: float) -> int:
    duration = max((end + pad_end) - start, 0.01)
    centiseconds = max(int(round(duration * 100)), 1)
    return centiseconds


def render_dialogue(words: List[Dict[str, float]], pad_end: float) -> str:
    tokens = []
    for word in words:
        token = word.get("w", "").strip()
        if not token:
            continue
        duration = word_to_k_tag(word.get("s", 0.0), word.get("e", 0.0), pad_end)
        tokens.append(f"{{\\k{duration}}}{token}")
    return " ".join(tokens)


def build_lines(aligned: Dict[str, Any], pad_end: float) -> List[str]:
    lines: List[str] = []
    for entry in aligned.get("lines", []):
        words = entry.get("words", [])
        if not words:
            continue
        start = format_timestamp(float(entry.get("s", words[0]["s"])))
        end = format_timestamp(float(entry.get("e", words[-1]["e"])))
        text = render_dialogue(words, pad_end)
        lines.append(f"Dialogue: 0,{start},{end},Karo,,0,0,120,,{text}")
    return lines


def fill_template(template_path: Path, replacements: Dict[str, str]) -> str:
    template = template_path.read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create ASS captions from word timings")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--aligned-dir", default="data/aligned")
    parser.add_argument("--captions-dir", default="data/captions")
    args = parser.parse_args(argv)

    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("make_ass", log_dir)

    try:
        aligned_dir = resolve_path(args.aligned_dir)
        captions_dir = resolve_path(args.captions_dir)
        words_path = aligned_dir / f"{args.video_id}.words.json"
        if not words_path.exists():
            raise PipelineError(f"Alignment missing for {args.video_id}")
        aligned = read_json(words_path)
        pad_end = float(config.get("alignment", "pad_end_s", default=0.04))
        lines = build_lines(aligned, pad_end)
        replacements = {
            "{{DIALOGUE_LINES}}": "\n".join(lines),
            "{{FONT_FAMILY}}": config.get("style", "font_family", default="Montserrat"),
            "{{FONT_SIZE}}": str(config.get("style", "font_size", default=64)),
            "{{OUTLINE}}": str(config.get("style", "outline", default=4)),
            "{{MARGIN_V}}": str(config.get("style", "margin_v", default=120)),
        }
        template_path = resolve_path(config.get("style", "ass_template", default="pipeline/styles/captions.ass.template"))
        output = fill_template(template_path, replacements)
        captions_dir.mkdir(parents=True, exist_ok=True)
        out_path = captions_dir / f"{args.video_id}.ass"
        out_path.write_text(output, encoding="utf-8")
        logger.info("Wrote captions to %s", out_path)
    except Exception as exc:
        logger.exception("make_ass failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
