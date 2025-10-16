"""Command line utility to download a YouTube video and burn word-level captions."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Sequence

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported lazily in functions
    import yt_dlp  # type: ignore
    import moviepy.editor as moviepy_editor  # type: ignore
    import whisper_timestamped as whisper  # type: ignore

    VideoFileClip = moviepy_editor.VideoFileClip


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


def extract_audio(video_path: str, audio_path: str) -> str:
    """Extract audio from the downloaded video and return the audio path."""
    import moviepy.editor as moviepy_editor

    VideoFileClip = moviepy_editor.VideoFileClip

    clip = VideoFileClip(video_path)
    try:
        clip.audio.write_audiofile(audio_path, logger=None)
    finally:
        clip.close()
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
        word_timestamps=True,
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


def generate_captions(
    url: str,
    output_path: str,
    model_name: str = "base",
    language: str | None = None,
    device: str | None = None,
    ffmpeg_binary: str = "ffmpeg",
) -> str:
    """High-level helper that orchestrates the full caption workflow."""
    output_path = str(Path(output_path).expanduser().resolve())
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = download_video(url, tmpdir)
        audio_path = os.path.join(tmpdir, "audio.wav")
        extract_audio(video_path, audio_path)
        words = transcribe_audio(audio_path, model_name=model_name, language=language, device=device)
        subtitle_path = os.path.join(tmpdir, "captions.srt")
        write_srt(words, subtitle_path)
        burn_captions(video_path, subtitle_path, output_path, ffmpeg_binary=ffmpeg_binary)

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
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
