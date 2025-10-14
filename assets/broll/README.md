# B-roll Clips

Drop `.mp4` files in this folder and list them inside `manifest.json` to make
them available inside the AutoReel UI. The manifest expects relative paths
from this directory, for example:

```
{
  "clips": [
    "desk-pan.mp4",
    "keyboard-closeup.mp4",
    "city-lights.mp4"
  ]
}
```

The front-end will cycle through the videos you specify, shuffling them to fill
the full duration of a generated voiceover. Update the manifest whenever you
add, remove, or rename clips.

If you are previewing the UI straight from disk without running a local
webserver, browsers may block manifest access. In that case, use the **B-Roll
Library** section inside `index.html` to temporarily load MP4 clips from your
computer. Those selections live only for the current browser tab and are a
handy fallback while you're experimenting.
