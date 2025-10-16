# AutoReel

## Overview
AutoReel mines real human-spoken videos from the internet, aligns word-level captions, and renders vertical shorts using FFmpeg.

## Quickstart
```bash
git clone <repo>
cd AutoReel
make init
make demo   # produces at least one mp4 in data/outputs/
```

The `make demo` target seeds `examples/urls.txt` with a sample YouTube link
and invokes `pipeline.batch` with `--max 1`. This downloads the referenced
video, walks it through the full transcription/alignment/rendering pipeline,
and leaves a vertically formatted `.mp4` in `data/outputs/` alongside the
intermediate artifacts in the other `data/*` folders. Run `make init` first so
the virtual environment and dependencies used by the demo are available.

## Step 1: Fetch long-form source material
Use the lightweight helper script to grab a long-form video of a requested speaker. The video is stored in `input/longform/`.

```bash
python get_video.py --name "Andrew Huberman"
```

The script prints which YouTube video was selected and the local file path once the download finishes.

## Detailed usage
- Collect URLs in `examples/urls.txt` (one per line).
- Run the batch pipeline:

```bash
python -m pipeline.batch --urls-file examples/urls.txt --max 3
```

Outputs land in `data/outputs/` alongside logs in `data/logs/`.

## Data directories
- `data/raw/` – original downloaded videos (`.mp4`) and metadata.
- `data/audio/` – extracted audio tracks (`.m4a`/`.wav`).
- `data/transcripts/` – YouTube captions (`.yt.json`) and Whisper fallback segments.
- `data/aligned/` – WhisperX word timings (`.words.json`) and optional ROI metadata.
- `data/captions/` – Karaoke `.ass` subtitle files with `{\k}` timings.
- `data/outputs/` – Final 1080×1920 rendered shorts.
- `data/logs/` – Step-by-step logs for auditing.
- `data/tmp/` – Queue files and ephemeral intermediates.

## Requirements
- `ffmpeg` available on `PATH`.
- Python 3.10+ recommended.
- `yt-dlp` version `2024.8.6` or newer (but < `2025.0`).
- GPU optional. NVENC encoders are auto-detected at runtime; when missing the renderer falls back to `libx264`.

## Troubleshooting
- YouTube transcript fetch fails → pipeline falls back to local Whisper transcription.
- WhisperX first run downloads models; rerun the batch if interrupted during downloads.
- If captions feel late, increase `alignment.pad_end_s` in `config/defaults.yaml`. For excessive line breaks, tweak `alignment.min_gap_s`.
