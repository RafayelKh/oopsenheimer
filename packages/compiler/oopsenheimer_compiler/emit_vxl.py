"""Emit placeholder FLUKA voxel files.

This is not a validated FLUKA unformatted voxel file yet. The implementation is
intentionally isolated so it can be replaced after FLUKA/Flair validation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from oopsenheimer_compiler.compiler import dense_grid_shape
from oopsenheimer_compiler.schema import SceneDefinition


def organ_ids_x_fastest(organ_id_grid: np.ndarray) -> list[int]:
    """Return organ IDs in scene x-fastest order from a ``grid[z, y, x]`` array."""
    return [int(value) for value in organ_id_grid.reshape(-1)]


def render_vxl_placeholder(scene: SceneDefinition, organ_id_grid: np.ndarray) -> str:
    expected_shape = dense_grid_shape(scene)
    if organ_id_grid.shape != expected_shape:
        raise ValueError(
            f"organ_id_grid shape {organ_id_grid.shape} does not match expected {expected_shape}"
        )

    nx, ny, nz = scene.world.grid.dims
    voxel_ids = organ_ids_x_fastest(organ_id_grid)
    lines = [
        "# Oops-enheimer placeholder voxel file",
        "# TODO: replace with FLUKA/Flair-validated unformatted .vxl writer.",
        "schema=oopsenheimer.vxl.placeholder.v1",
        f"dims={nx} {ny} {nz}",
        "voxelSizeCm="
        + " ".join(str(value) for value in scene.world.grid.voxel_size_cm),
        f"organCount={len(set(voxel_ids))}",
        f"voxelCount={len(voxel_ids)}",
        "order=x-fastest",
        "organs=" + " ".join(str(value) for value in voxel_ids),
    ]
    return "\n".join(lines) + "\n"


def emit_vxl(scene: SceneDefinition, organ_id_grid: np.ndarray, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_vxl_placeholder(scene, organ_id_grid))
    return output_path
