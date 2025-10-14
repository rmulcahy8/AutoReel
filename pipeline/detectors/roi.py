"""Simple face-based ROI detector for AutoReel."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import cv2

from ..utils import Config, PipelineError, build_logger, resolve_path


CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def detect_faces(frame) -> List[Dict[str, int]]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    results = []
    for (x, y, w, h) in faces:
        results.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
    return results


def analyse_video(path: Path, step: int = 30) -> List[Dict[str, int]]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise PipelineError(f"Unable to open video {path}")
    frames: List[Dict[str, int]] = []
    index = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if index % step == 0:
            faces = detect_faces(frame)
            if faces:
                frames.append(faces[0])
        index += 1
    cap.release()
    return frames


def main(video_path: str, output_path: str) -> None:
    frames = analyse_video(Path(video_path))
    payload = {"frames": frames}
    Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    config = Config.load()
    data_paths = config.get("paths") or {}
    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    logger = build_logger("roi", log_dir)
    logger.info("ROI detector is designed for manual invocation via batch hooks.")
