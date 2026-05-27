"""Celery tasks for Oops-enheimer simulation jobs."""

from __future__ import annotations

import json
import re
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from worker import celery_app, settings

STATUS_PROGRESS = {
    "queued": 0,
    "compiling": 12,
    "compiled": 28,
    "running": 35,
    "parsing": 88,
    "completed": 100,
}

STATUS_MESSAGES = {
    "queued": "Queued",
    "compiling": "Compiling scene",
    "compiled": "Scene compiled",
    "running": "Running FLUKA",
    "parsing": "Parsing dose",
    "completed": "Completed",
    "failed": "Failed",
}

FLUKA_PROGRESS_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+")


def ensure_compiler_path() -> None:
    compiler_dir = Path(__file__).resolve().parents[2] / "packages" / "compiler"
    if compiler_dir.exists() and str(compiler_dir) not in sys.path:
        sys.path.append(str(compiler_dir))


def job_dir(simulation_id: str) -> Path:
    return settings.storage_root / "jobs" / simulation_id


def status_path(simulation_id: str) -> Path:
    return job_dir(simulation_id) / "job_status.json"


def read_job_status(simulation_id: str) -> dict:
    path = status_path(simulation_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def update_job_status(
    simulation_id: str,
    status: str,
    error_message: str | None = None,
    progress_percent: int | None = None,
    progress_message: str | None = None,
) -> dict:
    directory = job_dir(simulation_id)
    directory.mkdir(parents=True, exist_ok=True)
    existing = {}
    path = status_path(simulation_id)
    if path.exists():
        existing = json.loads(path.read_text())

    now = datetime.now(UTC).isoformat()
    resolved_progress = progress_percent
    if resolved_progress is None:
        resolved_progress = _progress_for_status(status, existing)
    data = {
        **existing,
        "simulationId": simulation_id,
        "status": status,
        "progressPercent": max(0, min(100, int(resolved_progress))),
        "progressMessage": progress_message or STATUS_MESSAGES.get(status, status),
        "updatedAt": now,
        "storagePath": str(directory),
        "errorMessage": error_message,
    }
    if status == "running" and not data.get("startedAt"):
        data["startedAt"] = now
    if status in {"completed", "failed"}:
        data["finishedAt"] = now
    path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def _progress_for_status(status: str, existing: dict) -> int:
    if status == "failed":
        return int(existing.get("progressPercent") or 0)
    return STATUS_PROGRESS.get(status, int(existing.get("progressPercent") or 0))


@celery_app.task(name="compile_scene_task")
def compile_scene_task(simulation_id: str) -> dict:
    return _compile_scene(simulation_id)


def _compile_scene(simulation_id: str) -> dict:
    try:
        update_job_status(simulation_id, "compiling")
        status = read_job_status(simulation_id)
        scene_id = status.get("sceneId")
        if not scene_id:
            raise ValueError(f"simulation '{simulation_id}' is missing sceneId in job status")

        scene_path = settings.storage_root / "scenes" / scene_id / "scene.json"
        if not scene_path.exists():
            raise FileNotFoundError(f"scene JSON not found: {scene_path}")

        ensure_compiler_path()
        from radcraft_compiler.compiler import expand_chunks, resolve_materials
        from radcraft_compiler.emit_inp import emit_inp
        from radcraft_compiler.emit_vxl import emit_vxl
        from radcraft_compiler.manifest import emit_manifest, emit_meta
        from radcraft_compiler.organ_map import build_organ_map
        from radcraft_compiler.schema import SceneDefinition

        scene = SceneDefinition.model_validate_json(scene_path.read_text())
        block_grid = expand_chunks(scene)
        material_grid = resolve_materials(scene, block_grid).material_grid
        organ_map = build_organ_map(scene, block_grid, material_grid)

        directory = job_dir(simulation_id)
        emit_inp(scene, organ_map, directory / scene.emit.fluka_input.filename)
        emit_vxl(scene, organ_map.organ_id_grid, directory / scene.emit.voxel_file.filename)
        emit_manifest(scene, organ_map, directory / scene.emit.manifest.filename)
        emit_meta(scene, block_grid.size, len(organ_map.organs), directory / "scene.meta.json")
        return update_job_status(simulation_id, "compiled")
    except Exception as exc:
        return update_job_status(simulation_id, "failed", str(exc))


@celery_app.task(name="run_fluka_task")
def run_fluka_task(simulation_id: str) -> dict:
    return _run_fluka(simulation_id)


def _run_fluka(simulation_id: str) -> dict:
    if read_job_status(simulation_id).get("status") == "failed":
        return read_job_status(simulation_id)

    update_job_status(simulation_id, "running")
    directory = job_dir(simulation_id)
    logs_dir = directory / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if settings.sim_mode == "mock":
        (logs_dir / "rfluka.stdout.log").write_text("mock FLUKA stdout\n")
        (logs_dir / "rfluka.stderr.log").write_text("")
        return update_job_status(simulation_id, "parsing")

    if settings.sim_mode != "fluka":
        return update_job_status(
            simulation_id,
            "failed",
            f"Unsupported RADCRAFT_SIM_MODE '{settings.sim_mode}'. Expected mock or fluka.",
        )

    try:
        from runner import run_rfluka

        stop_monitor = threading.Event()
        monitor_thread = threading.Thread(
            target=_monitor_fluka_progress,
            args=(simulation_id, stop_monitor),
            daemon=True,
        )
        monitor_thread.start()
        try:
            result = run_rfluka(
                job_dir=directory,
                input_file="scene.inp",
                cycles=1,
                timeout_seconds=3600,
            )
        finally:
            stop_monitor.set()
            monitor_thread.join(timeout=2)
            _update_fluka_progress_from_output(simulation_id)
    except Exception as exc:
        return update_job_status(simulation_id, "failed", str(exc))

    if result.exit_code != 0 and not _has_usrbin_output(result):
        return update_job_status(
            simulation_id,
            "failed",
            f"rfluka exited with code {result.exit_code}; {_fluka_failure_detail(directory, result)}",
        )

    return update_job_status(simulation_id, "parsing")


def _monitor_fluka_progress(
    simulation_id: str,
    stop_event: threading.Event,
    interval_seconds: float = 1.0,
) -> None:
    while not stop_event.wait(interval_seconds):
        if read_job_status(simulation_id).get("status") != "running":
            return
        _update_fluka_progress_from_output(simulation_id)


def _update_fluka_progress_from_output(simulation_id: str) -> None:
    progress = _read_fluka_progress(job_dir(simulation_id))
    if progress is None:
        return

    handled, total = progress
    if total <= 0:
        return

    fraction = max(0.0, min(1.0, handled / total))
    running_start = STATUS_PROGRESS["running"]
    parsing_start = STATUS_PROGRESS["parsing"]
    progress_percent = min(
        parsing_start - 1,
        running_start + round((parsing_start - running_start - 1) * fraction),
    )
    particle_percent = round(fraction * 100)
    update_job_status(
        simulation_id,
        "running",
        progress_percent=progress_percent,
        progress_message=f"Running FLUKA ({particle_percent}% particles)",
    )


def _read_fluka_progress(directory: Path) -> tuple[int, int] | None:
    for path in _fluka_output_candidates(directory):
        progress = _read_fluka_progress_file(path)
        if progress is not None:
            return progress
    return None


def _fluka_output_candidates(directory: Path) -> list[Path]:
    return sorted(
        directory.glob("**/scene*.out"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _read_fluka_progress_file(path: Path) -> tuple[int, int] | None:
    for line in reversed(path.read_text(errors="replace").splitlines()):
        match = FLUKA_PROGRESS_RE.match(line)
        if match is None:
            continue
        handled = int(match.group(1))
        left = int(match.group(2))
        total = handled + left
        if total > 0:
            return handled, total
    return None


def _has_usrbin_output(result: Any) -> bool:
    output_files = getattr(result, "output_files", []) or []
    return any(Path(path).name.endswith("_fort.21") for path in output_files)


def _fluka_failure_detail(directory: Path, result: Any) -> str:
    for path in _failure_log_candidates(directory, result):
        if not path.exists() or not path.is_file():
            continue
        detail = _last_nonempty_lines(path, max_lines=4)
        if detail:
            return f"see {path.relative_to(directory)}: {detail}"
    return "see logs/rfluka.stderr.log"


def _failure_log_candidates(directory: Path, result: Any) -> list[Path]:
    candidates: list[Path] = []
    stderr_log = getattr(result, "stderr_log", None)
    stdout_log = getattr(result, "stdout_log", None)
    if stderr_log:
        candidates.append(Path(stderr_log))
    candidates.extend(sorted(directory.glob("scene*.err")))
    candidates.extend(sorted(directory.glob("*.err")))
    if stdout_log:
        candidates.append(Path(stdout_log))
    return candidates


def _last_nonempty_lines(path: Path, max_lines: int) -> str:
    lines = [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]
    return " | ".join(lines[-max_lines:])


@celery_app.task(name="parse_results_task")
def parse_results_task(simulation_id: str) -> dict:
    return _parse_results(simulation_id)


def _parse_results(simulation_id: str) -> dict:
    if read_job_status(simulation_id).get("status") == "failed":
        return read_job_status(simulation_id)

    directory = job_dir(simulation_id)
    manifest_path = directory / "scene.map.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    try:
        from parser import parse_usrbin_outputs

        parse_usrbin_outputs(directory, manifest, sim_mode=settings.sim_mode)
    except Exception as exc:
        return update_job_status(simulation_id, "failed", str(exc))

    return update_job_status(simulation_id, "completed")


def enqueue_mock_pipeline(simulation_id: str) -> None:
    compiled = _compile_scene(simulation_id)
    if compiled.get("status") == "failed":
        return
    run_result = _run_fluka(simulation_id)
    if run_result.get("status") == "failed":
        return
    _parse_results(simulation_id)
