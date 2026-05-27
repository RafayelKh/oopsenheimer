"""In-memory API store backed by local filesystem directories."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.schemas import SceneRecord, SimulationRecord

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


class InMemoryStore:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root
        self.scenes: dict[str, SceneRecord] = {}
        self.simulations: dict[str, SimulationRecord] = {}

    def create_scene(self, scene_json: dict[str, Any]) -> SceneRecord:
        scene_id = str(uuid4())
        name = str(scene_json.get("world", {}).get("id") or scene_id)
        record = SceneRecord(
            id=scene_id,
            name=name,
            sceneJson=scene_json,
            createdAt=datetime.now(UTC),
        )
        self.scenes[scene_id] = record

        scene_dir = self.storage_root / "scenes" / scene_id
        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / "scene.json").write_text(json.dumps(scene_json, indent=2) + "\n")
        return record

    def get_scene(self, scene_id: str) -> SceneRecord | None:
        scene = self.scenes.get(scene_id)
        if scene is not None:
            return scene
        return self._load_scene_from_disk(scene_id)

    def create_simulation(self, scene_id: str) -> SimulationRecord:
        simulation_id = str(uuid4())
        job_dir = self.storage_root / "jobs" / simulation_id
        job_dir.mkdir(parents=True, exist_ok=True)
        record = SimulationRecord(
            id=simulation_id,
            sceneId=scene_id,
            status="queued",
            progressPercent=STATUS_PROGRESS["queued"],
            progressMessage=STATUS_MESSAGES["queued"],
            createdAt=datetime.now(UTC),
            storagePath=str(job_dir),
        )
        self.simulations[simulation_id] = record
        self._write_status(record)
        return record

    def get_simulation(self, simulation_id: str) -> SimulationRecord | None:
        record = self.simulations.get(simulation_id)
        if record is None:
            return self._load_simulation_from_status_file(simulation_id)
        return self._refresh_from_status_file(record)

    def list_artifacts(self, simulation_id: str) -> list[str]:
        simulation = self.get_simulation(simulation_id)
        if simulation is None or simulation.storage_path is None:
            return []

        root = Path(simulation.storage_path)
        if not root.exists():
            return []

        return sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_file()
        )

    def _write_status(self, record: SimulationRecord) -> None:
        if record.storage_path is None:
            return
        path = Path(record.storage_path) / "job_status.json"
        path.write_text(
            json.dumps(
                {
                    "simulationId": record.id,
                    "sceneId": record.scene_id,
                    "status": record.status,
                    "progressPercent": record.progress_percent,
                    "progressMessage": record.progress_message,
                    "createdAt": record.created_at.isoformat(),
                    "storagePath": record.storage_path,
                    "errorMessage": record.error_message,
                },
                indent=2,
            )
            + "\n"
        )

    def _load_scene_from_disk(self, scene_id: str) -> SceneRecord | None:
        scene_path = self.storage_root / "scenes" / scene_id / "scene.json"
        if not scene_path.exists():
            return None

        scene_json = json.loads(scene_path.read_text())
        created_at = datetime.fromtimestamp(scene_path.stat().st_mtime, UTC)
        scene = SceneRecord(
            id=scene_id,
            name=str(scene_json.get("world", {}).get("id") or scene_id),
            sceneJson=scene_json,
            createdAt=created_at,
        )
        self.scenes[scene_id] = scene
        return scene

    def _load_simulation_from_status_file(self, simulation_id: str) -> SimulationRecord | None:
        status_file = self.storage_root / "jobs" / simulation_id / "job_status.json"
        if not status_file.exists():
            return None

        data = json.loads(status_file.read_text())
        record = SimulationRecord(
            id=str(data.get("simulationId") or simulation_id),
            sceneId=str(data.get("sceneId") or ""),
            status=str(data.get("status") or "queued"),
            progressPercent=int(data.get("progressPercent") or 0),
            progressMessage=data.get("progressMessage"),
            createdAt=data.get("createdAt") or datetime.fromtimestamp(status_file.stat().st_mtime, UTC),
            storagePath=data.get("storagePath") or str(status_file.parent),
            errorMessage=data.get("errorMessage"),
        )
        self.simulations[record.id] = record
        return self._refresh_from_status_file(record)

    def _refresh_from_status_file(self, record: SimulationRecord) -> SimulationRecord:
        if record.storage_path is None:
            return record
        path = Path(record.storage_path) / "job_status.json"
        if not path.exists():
            return record
        data = json.loads(path.read_text())
        status = data.get("status", record.status)
        refreshed = record.model_copy(
            update={
                "status": status,
                "progress_percent": int(data.get("progressPercent", _progress_for_status(status, record))),
                "progress_message": data.get("progressMessage") or STATUS_MESSAGES.get(status, status),
                "error_message": data.get("errorMessage", record.error_message),
            }
        )
        self.simulations[record.id] = refreshed
        return refreshed


def _progress_for_status(status: str, record: SimulationRecord) -> int:
    if status == "failed":
        return record.progress_percent
    return STATUS_PROGRESS.get(status, record.progress_percent)
