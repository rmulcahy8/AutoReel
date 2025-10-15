"""Download a long-form YouTube video for a requested speaker.

Usage:

    python get_video.py --name "Andrew Huberman"

The script searches YouTube for long-form appearances of the requested
speaker and downloads the first suitable match into ``input/longform``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - import guard for clearer CLI errors
    from yt_dlp import YoutubeDL
except ModuleNotFoundError:  # pragma: no cover - import guard for clearer CLI errors
    print("Error: yt-dlp is required. Install it with `pip install yt-dlp`.\n")
    sys.exit(1)


MIN_DURATION_SECONDS = 20 * 60  # prefer videos longer than 20 minutes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a long-form video for a speaker")
    parser.add_argument("--name", required=True, help="Name of the person to search for")
    parser.add_argument(
        "--min-duration",
        type=int,
        default=MIN_DURATION_SECONDS,
        help=(
            "Minimum duration in seconds for a video to be considered long-form. "
            "If no videos meet the threshold, the longest available result is used."
        ),
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="How many search results to inspect before giving up",
    )
    return parser.parse_args()


def search_for_videos(name: str, max_results: int) -> List[Dict[str, Any]]:
    """Return the raw search results for the requested speaker."""

    search_query = f"{name} interview podcast"
    search_term = f"ytsearch{max_results}:{search_query}"

    print(f"Searching YouTube for '{search_query}'...")

    search_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }

    with YoutubeDL(search_opts) as ydl:
        search_result = ydl.extract_info(search_term, download=False)

    entries = search_result.get("entries", []) if search_result else []
    if not entries:
        raise RuntimeError("No search results found. Try a different name or spelling.")

    return entries


def choose_video(entries: list[Dict[str, Any]], min_duration: int) -> Dict[str, Any]:
    """Choose a video entry that meets the duration requirement if possible."""

    preferred: Optional[Dict[str, Any]] = None
    fallback: Optional[Dict[str, Any]] = None

    for entry in entries:
        if not entry:
            continue

        duration = entry.get("duration") or 0
        if fallback is None or (duration > (fallback.get("duration") or 0)):
            fallback = entry

        if duration >= min_duration:
            preferred = entry
            break

    if preferred:
        return preferred

    if fallback:
        print(
            "No videos met the minimum duration. Using the longest available result instead."
        )
        return fallback

    raise RuntimeError("No usable video entries were found in the search results.")


def download_video(entry: Dict[str, Any], output_dir: Path) -> Path:
    """Download the selected video and return the file path."""

    output_dir.mkdir(parents=True, exist_ok=True)

    download_opts = {
        "outtmpl": str(output_dir / "%(title)s [%(id)s].%(ext)s"),
        "quiet": False,
        "no_warnings": True,
        "format": "mp4/best",
    }

    video_url = entry.get("webpage_url")
    if not video_url:
        raise RuntimeError("Selected video is missing a download URL.")

    print(f"Downloading '{entry.get('title')}' from {video_url}")

    with YoutubeDL(download_opts) as ydl:
        expected_path = Path(ydl.prepare_filename(entry))
        ydl.download([video_url])

    # In some cases the downloaded file may have a different extension (e.g. webm).
    # Fall back to finding the file by video id if the expected path does not exist.
    if not expected_path.exists():
        allowed_suffixes = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
        matches = sorted(
            f
            for f in output_dir.glob(f"*{entry.get('id')}*")
            if f.is_file()
            and f.suffix.lower() in allowed_suffixes
        )
        if matches:
            expected_path = matches[0]

    if not expected_path.exists():
        raise RuntimeError("Download finished but the video file could not be located.")

    return expected_path


def main() -> int:
    args = parse_args()

    try:
        entries = search_for_videos(args.name, args.max_results)
        selected = choose_video(entries, args.min_duration)
        output_dir = Path(__file__).resolve().parent / "input" / "longform"
        file_path = download_video(selected, output_dir)
    except Exception as exc:  # pragma: no cover - simple CLI tool
        print(f"Error: {exc}")
        return 1

    print("\nDownload complete!")
    print(f"Title: {selected.get('title')}")
    print(f"Video URL: {selected.get('webpage_url')}")
    print(f"Saved to: {file_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
