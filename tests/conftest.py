"""Test configuration for AutoReel pipeline tests."""
from __future__ import annotations

import logging
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "yaml" not in sys.modules:
    yaml_module = types.ModuleType("yaml")

    def _safe_load(_: str | bytes | None) -> dict:
        return {}

    yaml_module.safe_load = _safe_load
    sys.modules["yaml"] = yaml_module

if "rich" not in sys.modules:
    rich_module = types.ModuleType("rich")
    rich_console_module = types.ModuleType("rich.console")
    rich_logging_module = types.ModuleType("rich.logging")

    class _Console:
        def print(self, *args, **kwargs):  # pragma: no cover - test stub
            pass

        def log(self, *args, **kwargs):  # pragma: no cover - test stub
            pass

    class _RichHandler(logging.Handler):
        def __init__(self, *args, **kwargs):  # pragma: no cover - test stub
            super().__init__()

        def emit(self, record):  # pragma: no cover - test stub
            pass

    rich_console_module.Console = _Console
    rich_logging_module.RichHandler = _RichHandler

    rich_module.console = rich_console_module
    rich_module.logging = rich_logging_module

    sys.modules["rich"] = rich_module
    sys.modules["rich.console"] = rich_console_module
    sys.modules["rich.logging"] = rich_logging_module

if "tqdm" not in sys.modules:
    tqdm_module = types.ModuleType("tqdm")

    def _tqdm(iterable, *args, **kwargs):  # pragma: no cover - test stub
        return iterable

    tqdm_module.tqdm = _tqdm
    sys.modules["tqdm"] = tqdm_module

if "yt_dlp" not in sys.modules:
    yt_dlp_module = types.ModuleType("yt_dlp")
    sys.modules["yt_dlp"] = yt_dlp_module
