"""Voice activity detection utilities using webrtcvad."""
from __future__ import annotations

import collections
import wave
from pathlib import Path
from typing import List, Tuple

import webrtcvad

from ..utils import Config, PipelineError, build_logger, resolve_path

Frame = collections.namedtuple("Frame", ["timestamp", "duration", "bytes"])


def read_wave(path: Path) -> Tuple[bytes, int]:
    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != 1:
            raise PipelineError("VAD requires mono audio")
        if wf.getsampwidth() != 2:
            raise PipelineError("VAD expects 16-bit PCM")
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    return frames, sample_rate


def frame_generator(frame_duration_ms: int, audio: bytes, sample_rate: int):
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    for offset in range(0, len(audio), n):
        yield Frame(timestamp=offset / (sample_rate * 2), duration=frame_duration_ms / 1000.0, bytes=audio[offset: offset + n])


def vad_collector(sample_rate: int, frame_duration_ms: int, padding_duration_ms: int, vad: webrtcvad.Vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    segments: List[Tuple[float, float]] = []
    start = 0.0

    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                start = ring_buffer[0][0].timestamp
                ring_buffer.clear()
        else:
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                end = frame.timestamp + frame.duration
                segments.append((start, end))
                triggered = False
                ring_buffer.clear()
    if triggered:
        end = frames[-1].timestamp + frames[-1].duration
        segments.append((start, end))
    return segments


def analyse(path: Path, aggressiveness: int = 2) -> List[Tuple[float, float]]:
    audio, sample_rate = read_wave(path)
    vad = webrtcvad.Vad(aggressiveness)
    frames = list(frame_generator(30, audio, sample_rate))
    return vad_collector(sample_rate, 30, 300, vad, frames)


def main() -> int:
    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("vad", log_dir)
    logger.info("VAD module ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
