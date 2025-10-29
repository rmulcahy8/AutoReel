# AutoReel

AutoReel is a command-line tool that downloads a YouTube video, generates word-level captions with OpenAI Whisper, and burns the subtitles directly into the exported video.

## Getting started

1. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Provide your OpenAI API key via the `OPENAI_API_KEY` environment variable (or pass it on the
   command line with `--openai-api-key`).
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. Ensure `ffmpeg` is available on your `PATH`.

## Usage

```bash
python autocaption.py "https://www.youtube.com/watch?v=VIDEO_ID" output/captioned.mp4
```

The script automatically downloads the video, transcribes it, and produces a captioned MP4 file.

## Simple graphical interface

If you prefer a lightweight windowed app, run the Tkinter-based helper:

```bash
python autocaption_ui.py
```

The UI lets you paste a YouTube URL, choose where to save the captioned MP4, and optionally supply
an OpenAI API key, custom highlight prompt, or a folder for generating shorts. The same external
requirements apply: ensure `ffmpeg` is on your `PATH` and install the Python dependencies listed in
`requirements.txt` before launching the interface.

To additionally create shorts, provide an output directory and (optionally) a custom highlight
prompt. The default highlight prompt asks GPT to pick five moments lasting roughly 20–60 seconds,
merging adjacent transcript snippets when helpful and stretching closer to a full minute only when
the content stays compelling. Each generated short is capped at one minute to keep clips concise:

```bash
python autocaption.py \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  output/captioned.mp4 \
  --shorts-dir output/shorts \
  --highlight-prompt "Focus on the most exciting demo moments."
```
