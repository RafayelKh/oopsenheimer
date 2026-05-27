"""Scene compiler orchestration and voxel expansion helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np

from radcraft_compiler.schema import MaterialDefinition
from radcraft_compiler.schema import SceneDefinition

FLUKA_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,7}$")


@dataclass(frozen=True)
class MaterialResolution:
    block_material_ids: dict[str, str]
    material_grid: np.ndarray
    materials: dict[str, MaterialDefinition]
    fluka_names: dict[str, str]


def dense_grid_shape(scene: SceneDefinition) -> tuple[int, int, int]:
    """Return dense grid shape as ``(nz, ny, nx)``.

    Scene dimensions are declared as ``[nx, ny, nz]``. The compiler stores dense
    arrays as ``grid[z, y, x]`` so NumPy's last axis remains the x-fastest axis.
    """
    nx, ny, nz = scene.world.grid.dims
    return nz, ny, nx


def default_block_id(scene: SceneDefinition) -> str:
    """Find the palette block used to initialize empty voxel cells."""
    outside_material_id = scene.world.boundary.outside_material_id
    if outside_material_id in scene.world.palette:
        return outside_material_id

    for block_id, block in scene.world.palette.items():
        if block.material_id == outside_material_id:
            return block_id

    raise ValueError(
        f"outsideMaterialId '{outside_material_id}' does not match a palette block or material"
    )


def expand_chunks(scene: SceneDefinition) -> np.ndarray:
    """Expand scene RLE chunks into a dense block-id grid.

    Returns:
        ``np.ndarray`` with shape ``(nz, ny, nx)`` and object dtype. Indexing is
        ``grid[z, y, x]``. Chunk RLE order is x-fastest: x advances first, then
        y, then z.
    """
    grid = np.full(dense_grid_shape(scene), default_block_id(scene), dtype=object)
    filled = np.zeros(dense_grid_shape(scene), dtype=bool)
    palette_ids = set(scene.world.palette)

    for chunk in scene.world.chunks:
        for run in chunk.runs:
            if run.block_id not in palette_ids:
                raise ValueError(f"unknown blockId '{run.block_id}' in chunk RLE")

        ox, oy, oz = chunk.origin
        sx, sy, sz = chunk.size
        target = np.s_[oz : oz + sz, oy : oy + sy, ox : ox + sx]

        if filled[target].any():
            chunk_id = f" '{chunk.id}'" if chunk.id else ""
            raise ValueError(f"chunk{chunk_id} overlaps an already-filled voxel region")

        expanded: list[str] = []
        for run in chunk.runs:
            expanded.extend([run.block_id] * run.count)

        chunk_grid = np.array(expanded, dtype=object).reshape((sz, sy, sx))
        grid[target] = chunk_grid
        filled[target] = True

    return grid


def validate_materials(scene: SceneDefinition) -> None:
    """Validate palette-to-material references and FLUKA material names."""
    for block_id, block in scene.world.palette.items():
        if block.material_id not in scene.materials:
            raise ValueError(
                f"blockId '{block_id}' references unknown materialId '{block.material_id}'"
            )

    for material_id, material in scene.materials.items():
        if not material.fluka_name:
            raise ValueError(f"materialId '{material_id}' is missing flukaName")
        if not FLUKA_NAME_RE.fullmatch(material.fluka_name):
            raise ValueError(
                f"materialId '{material_id}' has non-FLUKA-safe flukaName "
                f"'{material.fluka_name}'"
            )


def resolve_materials(
    scene: SceneDefinition,
    block_grid: np.ndarray | None = None,
) -> MaterialResolution:
    """Resolve every block cell to a material cell.

    Args:
        scene: Validated scene definition.
        block_grid: Optional dense block-id grid using ``grid[z, y, x]``. When
            omitted, chunks are expanded first.

    Returns:
        Material lookup metadata plus a dense material-id grid with the same
        shape as the block grid.
    """
    validate_materials(scene)
    if block_grid is None:
        block_grid = expand_chunks(scene)

    block_material_ids = {
        block_id: block.material_id for block_id, block in scene.world.palette.items()
    }
    material_grid = np.empty(block_grid.shape, dtype=object)

    for block_id in np.unique(block_grid):
        if block_id not in block_material_ids:
            raise ValueError(f"unknown blockId '{block_id}' in dense block grid")
        material_grid[block_grid == block_id] = block_material_ids[block_id]

    return MaterialResolution(
        block_material_ids=block_material_ids,
        material_grid=material_grid,
        materials=scene.materials,
        fluka_names={
            material_id: material.fluka_name
            for material_id, material in scene.materials.items()
            if material.fluka_name is not None
        },
    )
