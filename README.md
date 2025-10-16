# AutoReel

AutoReel is a command-line tool that downloads a YouTube video, generates word-level captions with OpenAI Whisper, and burns the subtitles directly into the exported video.

## Getting started

1. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure `ffmpeg` is available on your `PATH`.

## Usage

```bash
python autocaption.py "https://www.youtube.com/watch?v=VIDEO_ID" output/captioned.mp4
```

The script automatically downloads the video, transcribes it, and produces a captioned MP4 file.
