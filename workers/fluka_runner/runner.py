"""Wrapper for running FLUKA through rfluka."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import signal
import subprocess
import time


class FlukaRunnerError(RuntimeError):
    pass


FLUKA_PROGRESS_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+")


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    stdout_log: Path
    stderr_log: Path
    output_files: list[Path]
    command: list[str]


def run_rfluka(
    job_dir: Path,
    input_file: str,
    cycles: int,
    timeout_seconds: int,
    stall_timeout_seconds: int | None = None,
) -> RunResult:
    fluka_bin = os.environ.get("FLUKA_BIN")
    if not fluka_bin:
        raise FlukaRunnerError("FLUKA_BIN is not set; set it to the FLUKA bin directory.")

    rfluka = Path(fluka_bin) / "rfluka"
    command = [str(rfluka), "-M", str(cycles), input_file]
    logs_dir = job_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = logs_dir / "rfluka.stdout.log"
    stderr_log = logs_dir / "rfluka.stderr.log"

    stall_timeout = stall_timeout_seconds if stall_timeout_seconds is not None else 0
    start_time = time.monotonic()
    last_progress_time = start_time
    last_progress = _read_particle_progress(job_dir)
    exit_code: int

    with stdout_log.open("w") as stdout_handle, stderr_log.open("w") as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=job_dir,
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
        while True:
            return_code = process.poll()
            if return_code is not None:
                exit_code = return_code
                break

            now = time.monotonic()
            if now - start_time >= timeout_seconds:
                _terminate_process_group(process)
                stderr_handle.write(f"\nrfluka timed out after {timeout_seconds}s\n")
                exit_code = -1
                break

            progress = _read_particle_progress(job_dir)
            if progress is not None and (last_progress is None or progress > last_progress):
                last_progress = progress
                last_progress_time = now
            elif stall_timeout > 0 and now - last_progress_time >= stall_timeout:
                _terminate_process_group(process)
                stderr_handle.write(
                    f"\nrfluka stalled after {stall_timeout}s without particle progress"
                    f" (last handled: {last_progress or 0})\n"
                )
                exit_code = -2
                break

            time.sleep(1.0)

    output_files = sorted(path for path in job_dir.rglob("*") if path.is_file())
    return RunResult(
        exit_code=exit_code,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        output_files=output_files,
        command=command,
    )


def _terminate_process_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def _read_particle_progress(directory: Path) -> int | None:
    for path in sorted(directory.glob("**/scene*.out"), key=lambda candidate: candidate.stat().st_mtime, reverse=True):
        progress = _read_particle_progress_file(path)
        if progress is not None:
            return progress
    return None


def _read_particle_progress_file(path: Path) -> int | None:
    for line in reversed(path.read_text(errors="replace").splitlines()):
        match = FLUKA_PROGRESS_RE.match(line)
        if match is not None:
            return int(match.group(1))
    return None
