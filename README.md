# AI Shorts Factory UI

A minimal static prototype for the AutoReel control panel. It provides a clean shell UI that we can hook automation logic into later.

## Features

- Title header branding the tool as "AI Shorts Factory"
- Input field for entering a topic or keyword
- Generate button ready to trigger future automation
- Placeholder output panel for showing generated script text

## Getting Started

This is a static HTML project with no build step. You can open the interface directly in a browser or serve it locally.

### Option 1: Open the file directly

1. Locate `index.html` in this repository.
2. Double-click the file to open it in your default browser.

### Option 2: Serve with a local web server

Serving the file can help avoid CORS restrictions if you add JavaScript later. From the repository root run:

```bash
python3 -m http.server 8000
```

Then visit [http://localhost:8000/index.html](http://localhost:8000/index.html) in your browser.

## Next Steps

- Wire up the "Generate Script" button to your backend.
- Feed the output panel with generated script text.
- Expand the UI with voice, video, and upload workflows as automation features mature.
