# AI Shorts Factory UI

A minimal static prototype for the AutoReel control panel. It provides a clean shell UI that we can hook automation logic into later.

## Features

- Title header branding the tool as "AI Shorts Factory"
- Input field for entering a topic or keyword
- Generate button ready to trigger future automation
- Placeholder output panel for showing generated script text
- Built-in voiceover creation button that turns scripts into downloadable
  beep/boop WAV audio for quick previews

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
script to render a playful audio track built from alternating beeps and boops—one
sound per character in the script. The UI embeds an audio player and provides a
`Download WAV` link so you can review or save the generated file immediately.

> **Note:** This prototype voiceover is intentionally simple and runs entirely in your
> browser. Swap the generator later if you want a full text-to-speech voice.

## Next Steps

- Wire up the "Generate Script" button to your backend.
- Feed the output panel with generated script text.
- Expand the UI with voice, video, and upload workflows as automation features mature.

## Add B-roll preview clips

Place `.mp4` files inside `assets/broll/` and list them in
`assets/broll/manifest.json`. The UI loads that manifest at runtime and cycles
through the clips to match the length of each generated voiceover, giving you a
quick way to visualize how the narration pairs with your stock footage. If
you open `index.html` directly from disk (using a `file://` URL) and the
manifest can't be fetched, scroll to the **B-Roll Library** section in the UI
and add clips with the built-in file picker. Those selections stay available
until you refresh the page, making it easy to test without running a local
server.
