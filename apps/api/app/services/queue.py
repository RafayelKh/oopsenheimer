"""Simulation queue integration."""

from __future__ import annotations

from pathlib import Path
import sys

from app.config import settings


def enqueue_simulation(simulation_id: str, storage_root: Path) -> None:
    """Enqueue the current simulation pipeline.

    The worker package is still local to the monorepo, so add its directory to
    the import path when the API is run directly from apps/api.
    """
    worker_dir = Path(__file__).resolve().parents[4] / "workers" / "fluka_runner"
    if str(worker_dir) not in sys.path:
        sys.path.append(str(worker_dir))

    import tasks

    tasks.settings.storage_root = storage_root
    tasks.settings.sim_mode = settings.sim_mode
    tasks.enqueue_mock_pipeline(simulation_id)
