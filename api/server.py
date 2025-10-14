"""FastAPI surface for AutoReel batch jobs."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.utils import Config, resolve_path

app = FastAPI(title="AutoReel API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BatchRequest(BaseModel):
    urls: list[str]
    options: Dict[str, str] | None = None


class JobInfo(BaseModel):
    job_id: str
    status: str
    log: list[str]
    outputs: list[dict] | None = None


class Job:
    def __init__(self, job_id: str, process: subprocess.Popen, log_path: Path, manifest_path: Path, log_handle):
        self.job_id = job_id
        self.process = process
        self.log_path = log_path
        self.manifest_path = manifest_path
        self.log_handle = log_handle

    def status(self) -> str:
        code = self.process.poll()
        if code is None:
            return "running"
        if code == 0:
            if not self.log_handle.closed:
                self.log_handle.close()
            return "succeeded"
        if not self.log_handle.closed:
            self.log_handle.close()
        return "failed"

    def read_log(self, tail: int = 40) -> list[str]:
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-tail:]

    def outputs(self) -> list[dict]:
        if not self.manifest_path.exists():
            return []
        results = []
        for line in self.manifest_path.read_text().splitlines():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return results


jobs: Dict[str, Job] = {}


@app.post("/api/batch", response_model=JobInfo)
async def create_batch(request: BatchRequest):
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    job_id = uuid.uuid4().hex
    config = Config.load()
    data_paths = config.get("paths") or {}
    tmp_dir = resolve_path(data_paths.get("tmp", "data/tmp"))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    urls_file = tmp_dir / f"{job_id}.txt"
    urls_file.write_text("\n".join(request.urls) + "\n", encoding="utf-8")

    log_dir = resolve_path(data_paths.get("logs", "data/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"api-{job_id}.log"
    manifest_path = resolve_path(data_paths.get("outputs", "data/outputs")) / "manifest.jsonl"

    cmd = [
        sys.executable,
        "-m",
        "pipeline.batch",
        "--urls-file",
        str(urls_file),
    ]
    if request.options and request.options.get("max"):
        cmd.extend(["--max", str(request.options["max"])])

    log_file = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    jobs[job_id] = Job(job_id, process, log_path, manifest_path, log_file)
    return JobInfo(job_id=job_id, status="running", log=[], outputs=None)


@app.get("/api/status/{job_id}", response_model=JobInfo)
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    status = job.status()
    log = job.read_log()
    outputs = job.outputs() if status == "succeeded" else None
    return JobInfo(job_id=job_id, status=status, log=log, outputs=outputs)
