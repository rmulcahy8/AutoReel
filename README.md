# AI Shorts Factory UI

A minimal static prototype for the AutoReel control panel. It provides a clean shell UI that we can hook automation logic into later.

## Features

- Title header branding the tool as "AI Shorts Factory"
- Input field for entering a topic or keyword
- Generate button ready to trigger future automation
- Placeholder output panel for showing generated script text
- Built-in voiceover creation button that uses the open-source meSpeak (eSpeak)
  engine to turn scripts into downloadable WAV audio

## Prerequisites

The project is a single static HTML page. You only need a modern web browser (Chrome, Firefox, Edge, or Safari). Optionally, you can install Python 3 if you prefer to serve the file over HTTP.

## How to Run the UI

Follow one of the exact workflows below.

### Option 1 — Open the file directly in your browser

1. Download or clone this repository to your computer.
2. Open your file explorer and navigate to the project directory.
3. Locate the file named `index.html`.
4. Double-click `index.html` to launch it in your default web browser.

### Option 2 — Serve the file locally with Python

1. Ensure Python 3 is installed. You can verify it by running `python3 --version` in a terminal.
2. Open a terminal and change to the project directory. For example:
   ```bash
   cd path/to/AutoReel
   ```
3. Start a simple HTTP server on port 8000:
   ```bash
   python3 -m http.server 8000
   ```
4. Open your browser and visit [http://localhost:8000/index.html](http://localhost:8000/index.html).
5. When you are done, return to the terminal and press `Ctrl+C` to stop the server.

## Create voiceover audio

Once your scripts appear in the output panel, click **Create Voiceover** beneath any
script to synthesize narration with the free, open-source
[meSpeak.js](https://github.com/niklassaers/mespeak) wrapper for the eSpeak speech
synthesizer. The UI will embed an audio player and provide a `Download WAV` link so
you can review or save the generated voiceover immediately.

> **Note:** The text-to-speech engine loads directly from a CDN and runs entirely in
> your browser—no paid API keys or server-side components are required.

## Next Steps

- Wire up the "Generate Script" button to your backend.
- Feed the output panel with generated script text.
- Expand the UI with voice, video, and upload workflows as automation features mature.
