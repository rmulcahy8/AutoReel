"""Simple Tkinter UI for running the AutoReel caption workflow."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from autocaption import generate_captions


class AutoReelApp(tk.Tk):
    """A minimal desktop application for AutoReel."""

    def __init__(self) -> None:
        super().__init__()
        self.title("AutoReel Captioner")
        self.resizable(False, False)

        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.shorts_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.prompt_var = tk.StringVar()
        self.create_shorts_var = tk.BooleanVar(value=False)

        self._build_layout()

    def _build_layout(self) -> None:
        padding = {"padx": 10, "pady": 5}

        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # URL input
        ttk.Label(main_frame, text="YouTube URL:").grid(row=0, column=0, sticky="w", **padding)
        ttk.Entry(main_frame, textvariable=self.url_var, width=50).grid(
            row=0, column=1, columnspan=2, sticky="ew", **padding
        )

        # Output path input
        ttk.Label(main_frame, text="Output video:").grid(row=1, column=0, sticky="w", **padding)
        ttk.Entry(main_frame, textvariable=self.output_var, width=40).grid(
            row=1, column=1, sticky="ew", **padding
        )
        ttk.Button(main_frame, text="Browse…", command=self._choose_output_path).grid(
            row=1, column=2, sticky="ew", **padding
        )

        # API key input
        ttk.Label(main_frame, text="OpenAI API key (optional):").grid(
            row=2, column=0, sticky="w", **padding
        )
        ttk.Entry(main_frame, textvariable=self.api_key_var, width=50, show="*").grid(
            row=2, column=1, columnspan=2, sticky="ew", **padding
        )

        # Highlight prompt input
        ttk.Label(main_frame, text="Highlight prompt (optional):").grid(
            row=3, column=0, sticky="w", **padding
        )
        ttk.Entry(main_frame, textvariable=self.prompt_var, width=50).grid(
            row=3, column=1, columnspan=2, sticky="ew", **padding
        )

        # Shorts directory toggle + input
        ttk.Checkbutton(
            main_frame,
            text="Generate highlight shorts",
            variable=self.create_shorts_var,
            command=self._toggle_shorts_inputs,
        ).grid(row=4, column=0, columnspan=3, sticky="w", **padding)

        self.shorts_entry = ttk.Entry(main_frame, textvariable=self.shorts_var, width=40, state="disabled")
        self.shorts_entry.grid(row=5, column=1, sticky="ew", **padding)
        self.shorts_button = ttk.Button(
            main_frame, text="Choose folder…", command=self._choose_shorts_dir, state="disabled"
        )
        self.shorts_button.grid(row=5, column=2, sticky="ew", **padding)
        ttk.Label(main_frame, text="Shorts folder:").grid(row=5, column=0, sticky="w", **padding)

        # Status display
        ttk.Label(main_frame, text="Status:").grid(row=6, column=0, sticky="nw", **padding)
        self.status_text = ScrolledText(main_frame, width=60, height=8, state="disabled")
        self.status_text.grid(row=6, column=1, columnspan=2, sticky="nsew", **padding)

        # Run button
        self.run_button = ttk.Button(main_frame, text="Generate Captions", command=self._start_generation)
        self.run_button.grid(row=7, column=0, columnspan=3, pady=(0, 10))

        main_frame.columnconfigure(1, weight=1)

    def _choose_output_path(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Choose output video",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4"), ("All files", "*.*")],
        )
        if selected:
            self.output_var.set(selected)

    def _choose_shorts_dir(self) -> None:
        selected = filedialog.askdirectory(title="Choose highlight shorts folder")
        if selected:
            self.shorts_var.set(selected)

    def _toggle_shorts_inputs(self) -> None:
        state = "normal" if self.create_shorts_var.get() else "disabled"
        self.shorts_entry.configure(state=state)
        self.shorts_button.configure(state=state)

    def _append_status(self, message: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    def _start_generation(self) -> None:
        url = self.url_var.get().strip()
        output = self.output_var.get().strip()

        if not url or not output:
            messagebox.showerror("Missing information", "Please provide both a YouTube URL and an output path.")
            return

        shorts_dir = self.shorts_var.get().strip() if self.create_shorts_var.get() else None
        openai_key = self.api_key_var.get().strip() or None
        highlight_prompt = self.prompt_var.get().strip() or None

        self.run_button.configure(state="disabled")
        self._append_status("Starting caption generation. This may take several minutes…")

        thread = threading.Thread(
            target=self._run_generation,
            args=(url, output, shorts_dir, openai_key, highlight_prompt),
            daemon=True,
        )
        thread.start()

    def _run_generation(
        self,
        url: str,
        output: str,
        shorts_dir: str | None,
        api_key: str | None,
        highlight_prompt: str | None,
    ) -> None:
        try:
            result = generate_captions(
                url=url,
                output_path=output,
                shorts_dir=shorts_dir,
                openai_api_key=api_key,
                highlight_prompt=highlight_prompt,
            )
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.after(0, lambda: self._on_generation_complete(error=str(exc)))
        else:
            self.after(0, lambda: self._on_generation_complete(result=result))

    def _on_generation_complete(self, result: str | None = None, error: str | None = None) -> None:
        if error:
            self._append_status(f"Error: {error}")
            messagebox.showerror("Generation failed", error)
        else:
            assert result is not None
            success_message = f"Finished! Captioned video saved to: {result}"
            self._append_status(success_message)
            messagebox.showinfo("Generation complete", success_message)

        self.run_button.configure(state="normal")


def main() -> None:
    app = AutoReelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
