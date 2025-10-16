"""Generate ASS karaoke captions from aligned words."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from .utils import Config, PipelineError, build_logger, read_json, resolve_path


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:06.3f}"


def word_to_k_tag(start: float, end: float) -> int:
    duration = max(end - start, 0.01)
    centiseconds = max(int(round(duration * 100)), 1)
    return centiseconds


def render_dialogue(
    words: List[Dict[str, float]], pad_end: float, next_line_start: float | None = None
) -> tuple[str, float]:
    tokens = []
    final_target_end = float(words[-1].get("e", words[-1].get("s", 0.0))) if words else 0.0
    for index, word in enumerate(words):
        token = word.get("w", "").strip()
        if not token:
            continue
        start = float(word.get("s", 0.0))
        if index + 1 < len(words):
            next_start = float(words[index + 1].get("s", start))
            duration = word_to_k_tag(start, next_start)
        else:
            end = float(word.get("e", start))
            target_end = end + pad_end
            if next_line_start is not None:
                next_line_start = float(next_line_start)
                if next_line_start < end:
                    target_end = end
                else:
                    target_end = min(target_end, next_line_start)
            duration = word_to_k_tag(start, target_end)
            final_target_end = target_end
        tokens.append(f"{{\\k{duration}}}{token}")
    return " ".join(tokens), final_target_end


def build_lines(aligned: Dict[str, Any], pad_end: float) -> List[str]:
    lines: List[str] = []
    entries = aligned.get("lines", [])
    for idx, entry in enumerate(entries):
        words = entry.get("words", [])
        if not words:
            continue
        start = format_timestamp(float(entry.get("s", words[0]["s"])))
        next_line_start: float | None = None
        if idx + 1 < len(entries):
            next_entry = entries[idx + 1]
            next_line_start = next_entry.get("s")
            if next_line_start is None:
                next_words = next_entry.get("words") or []
                if next_words:
                    next_line_start = next_words[0].get("s")
            if next_line_start is not None:
                next_line_start = float(next_line_start)
        text, final_target_end = render_dialogue(words, pad_end, next_line_start)
        end_time = final_target_end if words else float(entry.get("e", 0.0))
        end = format_timestamp(end_time)
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
