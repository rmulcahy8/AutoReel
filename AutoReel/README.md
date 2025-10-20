# AutoReel Captioning CLI

This repository provides a small command line interface that downloads a YouTube video, generates word-level captions with Whisper, and burns the captions onto the video.

## Installation

1. Install system dependencies:
   - [ffmpeg](https://ffmpeg.org/) must be available on your `PATH` so the script can mux audio and burn subtitles.
   - [ImageMagick](https://imagemagick.org/) is **not** required because the captions are rendered by ffmpeg.
2. Create a virtual environment (optional but recommended) and install the Python dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

The minimal dependencies in `requirements.txt` are:

- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for downloading the source video and audio tracks
- [`whisper-timestamped`](https://github.com/linto-ai/whisper-timestamped) for Whisper inference with word-level timestamps
- [`moviepy`](https://github.com/Zulko/moviepy) for extracting the audio track prior to transcription

## Usage

```bash
python autocaption.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" output/captioned.mp4
```

Key options:

- `--model`: Whisper model size to load (defaults to `base`)
- `--language`: Optional language hint to improve recognition
- `--device`: Torch device (e.g., `cuda`, `cpu`)
- `--ffmpeg-binary`: Custom `ffmpeg` executable path

The script performs the following steps:

1. Downloads the best available audio/video streams with `yt-dlp`.
2. Extracts an audio WAV file using `moviepy`.
3. Runs Whisper with word-level timestamps.
4. Emits an SRT file where each word receives its own subtitle window.
5. Uses `ffmpeg` to burn the generated subtitles into the original video while copying the audio track untouched.

## Testing

Run the unit tests with:

```bash
python -m unittest discover
```

The `tests/test_autocaption.py` suite mocks external dependencies to confirm that the CLI orchestrates downloads, transcription, and subtitle burning without contacting remote services.

