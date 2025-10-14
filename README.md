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
- GPU optional. If NVENC is absent, the renderer falls back to `libx264`.

## Troubleshooting
- YouTube transcript fetch fails → pipeline falls back to local Whisper transcription.
- WhisperX first run downloads models; rerun the batch if interrupted during downloads.
- If captions feel late, increase `alignment.pad_end_s` in `config/defaults.yaml`. For excessive line breaks, tweak `alignment.min_gap_s`.

## Legal note
Use downloaded media transformatively (commentary, criticism, education). Respect platform terms of service and avoid redistributing full original videos.
