"""Parser abstraction for FLUKA USRBIN outputs."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ParsedResult:
    metadata_path: Path
    values_path: Path
    metadata: dict[str, Any]


def parse_usrbin_outputs(job_dir: Path, manifest: dict[str, Any], sim_mode: str = "mock") -> ParsedResult:
    if sim_mode == "mock":
        return _write_mock_dose_map(job_dir, manifest)

    return _parse_real_usrbin_outputs(job_dir, manifest)


def _write_mock_dose_map(job_dir: Path, manifest: dict[str, Any]) -> ParsedResult:
    parsed_dir = job_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    scorer = (manifest.get("scoring") or [{}])[0]
    transform = manifest.get("coordinateTransform", {}).get("voxelIndexToCm", {})
    dims = scorer.get("dims") or [1, 1, 1]
    origin_cm = transform.get("originCm") or scorer.get("minCm") or [0, 0, 0]
    voxel_size_cm = transform.get("voxelSizeCm") or [1, 1, 1]
    quantity = scorer.get("quantity") or "DOSE"

    nx, ny, nz = [int(value) for value in dims]
    values = np.linspace(0.0, 1.0, num=nx * ny * nz, dtype=np.float32).reshape((nz, ny, nx))
    values_path = parsed_dir / "dose_map.npy"
    np.save(values_path, values)

    metadata = {
        "quantity": quantity,
        "unit": _unit_for_quantity(quantity),
        "dims": [nx, ny, nz],
        "originCm": origin_cm,
        "voxelSizeCm": voxel_size_cm,
        "min": float(values.min()),
        "max": float(values.max()),
        "valuesEncoding": "npy",
        "valuesFile": "dose_map.npy",
        "source": "mock",
        "simMode": "mock",
        "sources": manifest.get("sources") or [],
    }
    metadata_path = parsed_dir / "dose_map.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return ParsedResult(metadata_path=metadata_path, values_path=values_path, metadata=metadata)


def _parse_real_usrbin_outputs(job_dir: Path, manifest: dict[str, Any]) -> ParsedResult:
    fluka_bin = os.environ.get("FLUKA_BIN")
    if not fluka_bin:
        raise RuntimeError("FLUKA_BIN is not set; cannot post-process real USRBIN output.")

    usrbin_files = sorted(job_dir.glob("*_fort.21"))
    if not usrbin_files:
        raise FileNotFoundError(f"No USRBIN fort.21 file found in {job_dir}")

    sum_prefix = "oopsenheimer_usrbin_sum"
    readout_file = job_dir / "oopsenheimer_usrbin_readout.txt"
    usbsuw = Path(fluka_bin) / "usbsuw"
    usbrea = Path(fluka_bin) / "usbrea"

    usbsuw_input = "".join(f"{path.name}\n" for path in usrbin_files) + f"\n{sum_prefix}\n"
    _run_tool(usbsuw, usbsuw_input, job_dir)
    _run_tool(usbrea, f"{sum_prefix}\n{readout_file.name}\n", job_dir)

    return _parse_usbrea_text(readout_file, job_dir, manifest)


def _run_tool(command: Path, stdin_text: str, cwd: Path) -> None:
    completed = subprocess.run(
        [str(command)],
        cwd=cwd,
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{command.name} failed with code {completed.returncode}: {completed.stderr.strip()}"
        )


def _parse_usbrea_text(readout_file: Path, job_dir: Path, manifest: dict[str, Any]) -> ParsedResult:
    text = readout_file.read_text()
    scorer = (manifest.get("scoring") or [{}])[0]
    transform = manifest.get("coordinateTransform", {}).get("voxelIndexToCm", {})
    dims = scorer.get("dims") or _parse_dims_from_usbrea_text(text)
    nx, ny, nz = [int(value) for value in dims]
    expected_count = nx * ny * nz

    data_start = text.find("this is a track-length binning")
    if data_start == -1:
        data_start = text.find("Data follow")
    if data_start == -1:
        raise ValueError(f"Could not locate USRBIN data section in {readout_file}")

    float_pattern = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)[EeDd][-+]?\d+"
    values = [
        float(match.group(0).replace("D", "E").replace("d", "e"))
        for match in re.finditer(float_pattern, text[data_start:])
    ]
    if len(values) < expected_count:
        raise ValueError(
            f"Expected {expected_count} USRBIN values, found {len(values)} in {readout_file}"
        )

    array = np.array(values[:expected_count], dtype=np.float32).reshape((nz, ny, nx))
    parsed_dir = job_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    values_path = parsed_dir / "dose_map.npy"
    np.save(values_path, array)

    quantity = scorer.get("quantity") or "DOSE"
    metadata = {
        "quantity": quantity,
        "unit": _unit_for_quantity(quantity),
        "dims": [nx, ny, nz],
        "originCm": transform.get("originCm") or scorer.get("minCm") or [0, 0, 0],
        "voxelSizeCm": transform.get("voxelSizeCm") or _voxel_size_from_scorer(scorer, [nx, ny, nz]),
        "min": float(array.min()),
        "max": float(array.max()),
        "valuesEncoding": "npy",
        "valuesFile": "dose_map.npy",
        "source": readout_file.name,
        "simMode": "fluka",
        "sources": manifest.get("sources") or [],
    }
    metadata_path = parsed_dir / "dose_map.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return ParsedResult(metadata_path=metadata_path, values_path=values_path, metadata=metadata)


def _parse_dims_from_usbrea_text(text: str) -> list[int]:
    dims: list[int] = []
    for axis in ("X", "Y", "Z"):
        match = re.search(rf"{axis} coordinate:.*?,\s+(\d+)\s+bins", text)
        if not match:
            raise ValueError(f"Could not parse {axis} bin count from USBREA output")
        dims.append(int(match.group(1)))
    return dims


def _unit_for_quantity(quantity: str) -> str:
    normalized = quantity.upper()
    if normalized == "DOSE-H2O":
        return "Gy"
    if normalized.startswith("DOSE"):
        return "GeV/g"
    return "arb. units"


def _voxel_size_from_scorer(scorer: dict[str, Any], dims: list[int]) -> list[float]:
    min_cm = scorer.get("minCm") or [0, 0, 0]
    max_cm = scorer.get("maxCm") or [1, 1, 1]
    return [
        (float(max_value) - float(min_value)) / int(count)
        for min_value, max_value, count in zip(min_cm, max_cm, dims, strict=True)
    ]
