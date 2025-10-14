"""Utility helpers for the AutoReel pipeline.

Precision first, aesthetics second. Automate the boring parts. Fail closed, log everything.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from rich.console import Console
from rich.logging import RichHandler

CONFIG_PATH = Path("config/defaults.yaml")
console = Console()


class PipelineError(RuntimeError):
    """Raised when a pipeline step fails and should abort the batch."""


@dataclass
class Config:
    raw: Dict[str, Any]

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        if not path.exists():
            raise PipelineError(f"Config file missing: {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(raw=data)

    def get(self, *keys: str, default: Any = None) -> Any:
        cursor: Any = self.raw
        for key in keys:
            if isinstance(cursor, dict) and key in cursor:
                cursor = cursor[key]
            else:
                return default
        return cursor


def build_logger(name: str, log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    logfile = log_dir / f"{name}-{timestamp}.log"

    handler = RichHandler(console=console, show_time=False, show_path=False)
    handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    logger = logging.getLogger(name)
    logger.handlers = []
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    logger.debug("Logger initialised: %s", logfile)
    return logger


def run_command(cmd: List[str], logger: logging.Logger, cwd: Optional[Path] = None) -> None:
    """Run a shell command, streaming output to the provided logger."""
    logger.info("$ %s", " ".join(cmd))
    process = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        logger.info(line.rstrip())
    process.wait()
    if process.returncode != 0:
        raise PipelineError(f"Command failed ({process.returncode}): {' '.join(cmd)}")


YOUTUBE_ID_PATTERN = re.compile(r"(?:v=|/)([0-9A-Za-z_-]{11})")


def extract_video_id(url: str) -> str:
    match = YOUTUBE_ID_PATTERN.search(url)
    if not match:
        raise PipelineError(f"Unable to parse YouTube video ID from {url}")
    return match.group(1)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as exc:
        raise PipelineError(f"ffprobe failed for {path}: {exc}") from exc


def detect_device(preferred: str = "auto") -> str:
    if preferred != "auto":
        return preferred
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(*parts: str | os.PathLike[str]) -> Path:
    return project_root().joinpath(*parts)


def list_files(directory: Path, suffixes: Iterable[str]) -> List[Path]:
    suffix_tuple = tuple(suffixes)
    return [p for p in directory.iterdir() if p.suffix in suffix_tuple]


def log_exception(logger: logging.Logger, error: Exception) -> None:
    logger.error("%s", error)
    logger.debug("", exc_info=True)


__all__ = [
    "Config",
    "PipelineError",
    "append_jsonl",
    "build_logger",
    "detect_device",
    "ensure_directory",
    "extract_video_id",
    "list_files",
    "load_jsonl",
    "log_exception",
    "probe_duration",
    "project_root",
    "read_json",
    "resolve_path",
    "run_command",
    "write_json",
]
