"""Command line utility to download a YouTube video and burn word-level captions."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Sequence, Tuple

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported lazily in functions
    import yt_dlp  # type: ignore
    import whisper_timestamped as whisper  # type: ignore


def download_video(url: str, download_dir: str) -> str:
    """Download the best available video using yt_dlp and return its path."""
    import yt_dlp

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": os.path.join(download_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_path = ydl.prepare_filename(info)

    return video_path


def extract_audio(
    video_path: str,
    audio_path: str,
    ffmpeg_binary: str = "ffmpeg",
) -> str:
    """Extract audio from the downloaded video and return the audio path."""

    command = [
        ffmpeg_binary,
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        audio_path,
    ]
    subprocess.run(command, check=True)
    return audio_path


def transcribe_audio(
    audio_path: str,
    model_name: str = "base",
    language: str | None = None,
    device: str | None = None,
) -> List[dict]:
    """Transcribe audio and return the list of words with timestamps."""
    import whisper_timestamped as whisper

    model = whisper.load_model(model_name, device=device)
    result = whisper.transcribe(
        model,
        audio=audio_path,
        language=language,
        task="transcribe",
    )

    words: List[dict] = []
    for segment in result.get("segments", []):
        for word in segment.get("words", []):
            text = word.get("text", "").strip()
            if not text:
                continue
            words.append(
                {
                    "text": text,
                    "start": float(word.get("start", 0.0)),
                    "end": float(word.get("end", 0.0)),
                }
            )

    if not words:
        raise RuntimeError("No words with timestamps were produced by the transcription model.")

    return words


def write_srt(words: Sequence[dict], srt_path: str) -> str:
    """Write the words to an SRT subtitle file and return the path."""
    def format_timestamp(seconds: float) -> str:
        hours, remainder = divmod(max(seconds, 0.0), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int(round((seconds - int(seconds)) * 1000))
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"

    with open(srt_path, "w", encoding="utf-8") as subtitle_file:
        for index, word in enumerate(words, start=1):
            start_time = format_timestamp(word["start"])
            end_time = format_timestamp(word["end"])
            subtitle_file.write(f"{index}\n{start_time} --> {end_time}\n{word['text']}\n\n")

    return srt_path


def _escape_ffmpeg_subtitle_path(path: str) -> str:
    """Escape a subtitle path for use in ffmpeg filter arguments."""
    # Escape characters that ffmpeg treats as separators.
    return (
        path.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def burn_captions(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    ffmpeg_binary: str = "ffmpeg",
) -> None:
    """Burn subtitles into the video using ffmpeg."""
    escaped_sub_path = _escape_ffmpeg_subtitle_path(subtitle_path)
    command = [
        ffmpeg_binary,
        "-y",
        "-i",
        video_path,
        "-vf",
        f"subtitles='{escaped_sub_path}'",
        "-c:a",
        "copy",
        output_path,
    ]
    subprocess.run(command, check=True)


DEFAULT_HIGHLIGHT_PROMPT = (
    "Select the five most engaging, self-contained highlight moments from the transcript. "
    "Return them as start-end second ranges in the format `start-end`."
)


SHORT_CLIP_TAIL_SECONDS = 0.3


def _aggregate_words_into_segments(words: Sequence[dict]) -> List[dict]:
    """Aggregate word-level timestamps into larger text segments."""

    segments: List[dict] = []
    current_words: List[str] = []
    segment_start: float | None = None
    previous_end: float | None = None

    def flush() -> None:
        nonlocal current_words, segment_start, previous_end
        if current_words and segment_start is not None and previous_end is not None:
            text = " ".join(current_words).strip()
            if text:
                segments.append({"start": segment_start, "end": previous_end, "text": text})
        current_words = []
        segment_start = None
        previous_end = None

    for word in words:
        start = float(word.get("start", 0.0))
        end = float(word.get("end", start))
        text = str(word.get("text", "")).strip()
        if not text:
            continue

        if segment_start is None:
            segment_start = start

        if previous_end is not None and start - previous_end > 2.0:
            flush()
            segment_start = start

        current_words.append(text)
        previous_end = end

        if text.endswith(('.', '!', '?')):
            flush()

    flush()

    if not segments:
        raise RuntimeError("Unable to aggregate words into highlight segments.")

    return segments


def _response_text(response: object) -> str:
    """Extract text content from an OpenAI response object."""

    if response is None:
        return ""

    for attribute in ("output_text", "text"):
        text_value = getattr(response, attribute, None)
        if isinstance(text_value, str) and text_value.strip():
            return text_value

    output = getattr(response, "output", None)
    if output:
        for item in output:
            content = getattr(item, "content", None)
            if content:
                for block in content:
                    text_value = getattr(block, "text", None)
                    if isinstance(text_value, str) and text_value.strip():
                        return text_value

    choices = getattr(response, "choices", None)
    if choices:
        for choice in choices:
            message = getattr(choice, "message", None)
            if message:
                text_value = getattr(message, "content", None)
                if isinstance(text_value, str) and text_value.strip():
                    return text_value

    return ""


SPAN_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|to|–|,)\s*(\d+(?:\.\d+)?)")


def _parse_highlight_spans(text: str) -> List[Tuple[float, float]]:
    """Parse highlight spans from the model text output."""

    spans: List[Tuple[float, float]] = []
    for match in SPAN_PATTERN.finditer(text):
        start_str, end_str = match.groups()
        try:
            start_val = float(start_str)
            end_val = float(end_str)
        except ValueError:
            continue
        if end_val <= start_val:
            continue
        spans.append((start_val, end_val))

    # Remove duplicates while preserving order.
    seen = set()
    unique_spans: List[Tuple[float, float]] = []
    for span in spans:
        if span not in seen:
            seen.add(span)
            unique_spans.append(span)

    return unique_spans[:5]


def select_highlight_segments(
    words: Sequence[dict],
    *,
    prompt: str | None = None,
    client: object | None = None,
    api_key: str | None = None,
    log_path: str | os.PathLike[str] | None = None,
) -> List[Tuple[float, float]]:
    """Call the OpenAI API to select the top five highlight spans."""

    segments = _aggregate_words_into_segments(words)
    highlight_prompt = prompt or DEFAULT_HIGHLIGHT_PROMPT

    if client is None:
        from openai import OpenAI  # Imported lazily for testability

        client = OpenAI(api_key=api_key)

    formatted_segments = "\n".join(
        f"[{idx}] {segment['start']:.2f}-{segment['end']:.2f}: {segment['text']}"
        for idx, segment in enumerate(segments, start=1)
    )
    user_text = f"{highlight_prompt}\n\nSegments:\n{formatted_segments}"

    response = client.responses.create(
        model="gpt-5-nano",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_text,
                    }
                ],
            }
        ],
    )

    text = _response_text(response)
    spans = _parse_highlight_spans(text)
    if len(spans) < 5:
        raise RuntimeError("OpenAI response did not return five highlight spans.")

    if log_path:
        try:
            log_lines = [
                "Highlight selection log",
                "-----------------------",
                f"Prompt: {highlight_prompt}",
                "",
                "Aggregated segments:",
            ]
            for idx, segment in enumerate(segments, start=1):
                log_lines.append(
                    f"  [{idx}] {segment['start']:.2f}-{segment['end']:.2f}: {segment['text']}"
                )
            log_lines.extend(
                [
                    "",
                    "Raw model response:",
                    text or "<empty response>",
                    "",
                    "Selected highlight spans:",
                ]
            )

            for idx, (start_val, end_val) in enumerate(spans, start=1):
                matching_segment = next(
                    (
                        segment
                        for segment in segments
                        if segment["start"] <= start_val < segment["end"]
                    ),
                    None,
                )
                segment_text = matching_segment["text"] if matching_segment else ""
                log_lines.append(
                    f"  [{idx}] {start_val:.2f}-{end_val:.2f}: {segment_text}"
                )

            log_file_path = Path(log_path)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                log_file.write("\n".join(log_lines))
        except OSError as exc:
            raise RuntimeError(f"Failed to write highlight log: {exc}") from exc

    return spans


def create_shorts(
    captioned_video_path: str,
    spans: Sequence[Tuple[float, float]],
    output_dir: str,
    *,
    ffmpeg_binary: str = "ffmpeg",
) -> List[str]:
    """Render highlight clips for the given time spans from the captioned video."""

    os.makedirs(output_dir, exist_ok=True)
    outputs: List[str] = []

    for index, (start, end) in enumerate(spans, start=1):
        bounded_end = min(end + SHORT_CLIP_TAIL_SECONDS, start + 60.0)
        if bounded_end <= start:
            bounded_end = min(end, start + 60.0)
        clip_path = Path(output_dir) / f"short_{index}.mp4"
        command = [
            ffmpeg_binary,
            "-y",
            "-i",
            captioned_video_path,
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{bounded_end:.3f}",
            "-c",
            "copy",
            str(clip_path),
        ]
        subprocess.run(command, check=True)
        outputs.append(str(clip_path))

    return outputs


def generate_captions(
    url: str,
    output_path: str,
    model_name: str = "base",
    language: str | None = None,
    device: str | None = None,
    ffmpeg_binary: str = "ffmpeg",
    *,
    shorts_dir: str | None = None,
    openai_api_key: str | None = None,
    highlight_prompt: str | None = None,
    highlight_client: object | None = None,
) -> str:
    """High-level helper that orchestrates the full caption workflow."""
    output_path = str(Path(output_path).expanduser().resolve())
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = download_video(url, tmpdir)
        audio_path = os.path.join(tmpdir, "audio.wav")
        extract_audio(video_path, audio_path, ffmpeg_binary=ffmpeg_binary)
        words = transcribe_audio(audio_path, model_name=model_name, language=language, device=device)
        subtitle_path = os.path.join(tmpdir, "captions.srt")
        write_srt(words, subtitle_path)
        burn_captions(video_path, subtitle_path, output_path, ffmpeg_binary=ffmpeg_binary)

        if shorts_dir:
            os.makedirs(shorts_dir, exist_ok=True)
            log_path = Path(shorts_dir) / "highlight_log.txt"
            highlight_spans = select_highlight_segments(
                words,
                prompt=highlight_prompt,
                client=highlight_client,
                api_key=openai_api_key,
                log_path=log_path,
            )
            create_shorts(
                output_path,
                highlight_spans,
                shorts_dir,
                ffmpeg_binary=ffmpeg_binary,
            )

    return output_path


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="YouTube video URL to download and caption")
    parser.add_argument("output", help="Path for the captioned video file")
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model size to load (default: base)",
    )
    parser.add_argument("--language", help="Optional language hint for the transcription model")
    parser.add_argument(
        "--device",
        help="Torch device to run the transcription model on (e.g., cuda, cpu)",
    )
    parser.add_argument(
        "--ffmpeg-binary",
        default="ffmpeg",
        help="Path to the ffmpeg binary (defaults to `ffmpeg` in PATH)",
    )
    parser.add_argument(
        "--shorts-dir",
        help="Optional directory to export generated highlight shorts",
    )
    parser.add_argument(
        "--openai-api-key",
        help="OpenAI API key (falls back to the OPENAI_API_KEY environment variable)",
    )
    parser.add_argument(
        "--highlight-prompt",
        help="Override the default highlight selection prompt",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    try:
        generate_captions(
            url=args.url,
            output_path=args.output,
            model_name=args.model,
            language=args.language,
            device=args.device,
            ffmpeg_binary=args.ffmpeg_binary,
            shorts_dir=args.shorts_dir,
            openai_api_key=args.openai_api_key or os.getenv("OPENAI_API_KEY"),
            highlight_prompt=args.highlight_prompt,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
