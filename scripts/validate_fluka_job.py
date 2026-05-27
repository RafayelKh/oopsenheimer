#!/usr/bin/env python3
"""Run a generated Oops-enheimer job through a local FLUKA installation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def validate_job(job_dir: Path) -> int:
    job_dir = job_dir.resolve()
    input_file = job_dir / "scene.inp"
    voxel_file = job_dir / "scene.vxl"

    if not job_dir.exists() or not job_dir.is_dir():
        print(f"error: job directory does not exist: {job_dir}", file=sys.stderr)
        return 2
    if not input_file.exists():
        print(f"error: missing scene.inp: {input_file}", file=sys.stderr)
        return 2
    if not voxel_file.exists():
        print(f"error: missing scene.vxl: {voxel_file}", file=sys.stderr)
        return 2

    fluka_bin = os.environ.get("FLUKA_BIN")
    if not fluka_bin:
        print("error: FLUKA_BIN is not set; export FLUKA_BIN=/path/to/fluka/bin", file=sys.stderr)
        return 2

    rfluka = Path(fluka_bin) / "rfluka"
    command = [str(rfluka), "-M", "1", input_file.name]
    print("Running:", " ".join(command))
    completed = subprocess.run(command, cwd=job_dir, text=True, capture_output=True, check=False)

    logs_dir = job_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    (logs_dir / "validate_fluka.stdout.log").write_text(completed.stdout)
    (logs_dir / "validate_fluka.stderr.log").write_text(completed.stderr)

    print(f"Exit code: {completed.returncode}")
    print("Output files:")
    for path in sorted(item for item in job_dir.rglob("*") if item.is_file()):
        print(f"- {path.relative_to(job_dir)}")

    if completed.returncode != 0:
        print("error: rfluka failed; inspect logs/validate_fluka.stderr.log", file=sys.stderr)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path, help="Path to a generated Oops-enheimer job directory.")
    args = parser.parse_args()
    return validate_job(args.job_dir)


if __name__ == "__main__":
    raise SystemExit(main())
