"""Wrapper for running FLUKA through rfluka."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess


class FlukaRunnerError(RuntimeError):
    pass


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

    try:
        completed = subprocess.run(
            command,
            cwd=job_dir,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout_log.write_text(completed.stdout)
        stderr_log.write_text(completed.stderr)
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout_log.write_text(exc.stdout or "")
        stderr_log.write_text((exc.stderr or "") + f"\nrfluka timed out after {timeout_seconds}s\n")
        exit_code = -1

    output_files = sorted(path for path in job_dir.rglob("*") if path.is_file())
    return RunResult(
        exit_code=exit_code,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        output_files=output_files,
        command=command,
    )
