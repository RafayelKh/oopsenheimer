"""Voxel-to-FLUKA organ mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from radcraft_compiler.compiler import expand_chunks, resolve_materials
from radcraft_compiler.schema import SceneDefinition


@dataclass(frozen=True)
class Organ:
    organ_id: int
    material_id: str
    block_ids: list[str]
    voxel_count: int
    bbox_index: dict[str, list[int]]
    fluka_region_name: str

    def to_manifest(self) -> dict[str, Any]:
        return {
            "organId": self.organ_id,
            "materialId": self.material_id,
            "blockIds": self.block_ids,
            "voxelCount": self.voxel_count,
            "bboxIndex": self.bbox_index,
            "flukaRegionName": self.fluka_region_name,
        }


@dataclass(frozen=True)
class OrganMap:
    organ_id_grid: np.ndarray
    organs: list[Organ]


def fluka_region_name(organ_id: int) -> str:
    return f"VOXEL{organ_id + 1:03d}"


def _bbox_for_mask(mask: np.ndarray) -> dict[str, list[int]]:
    positions = np.argwhere(mask)
    if positions.size == 0:
        return {"min": [], "max": []}

    min_z, min_y, min_x = positions.min(axis=0).tolist()
    max_z, max_y, max_x = positions.max(axis=0).tolist()
    return {
        "min": [min_x, min_y, min_z],
        "max": [max_x, max_y, max_z],
    }


def build_organ_map(
    scene: SceneDefinition,
    block_grid: np.ndarray | None = None,
    material_grid: np.ndarray | None = None,
) -> OrganMap:
    """Assign compact FLUKA organ IDs to voxels.

    MVP policy:
    - organ 0 is reserved for the scene boundary outside material.
    - every other material present in the dense grid gets one organ.
    - material IDs are sorted for deterministic compact organ assignment.
    """
    if block_grid is None:
        block_grid = expand_chunks(scene)
    if material_grid is None:
        material_grid = resolve_materials(scene, block_grid).material_grid

    outside_material_id = scene.world.boundary.outside_material_id
    present_materials = {str(material_id) for material_id in np.unique(material_grid)}
    ordered_materials = [outside_material_id] + sorted(
        material_id for material_id in present_materials if material_id != outside_material_id
    )

    if len(ordered_materials) > scene.world.organ_policy.max_organs:
        raise ValueError(
            f"organ count {len(ordered_materials)} exceeds maxOrgans "
            f"{scene.world.organ_policy.max_organs}"
        )

    block_ids_by_material: dict[str, list[str]] = {}
    for block_id, block in sorted(scene.world.palette.items()):
        if block.material_id in present_materials:
            block_ids_by_material.setdefault(block.material_id, []).append(block_id)

    organ_id_grid = np.zeros(material_grid.shape, dtype=np.int32)
    organs: list[Organ] = []

    for organ_id, material_id in enumerate(ordered_materials):
        mask = material_grid == material_id
        organ_id_grid[mask] = organ_id
        organs.append(
            Organ(
                organ_id=organ_id,
                material_id=material_id,
                block_ids=block_ids_by_material.get(material_id, []),
                voxel_count=int(mask.sum()),
                bbox_index=_bbox_for_mask(mask),
                fluka_region_name=fluka_region_name(organ_id),
            )
        )

    return OrganMap(organ_id_grid=organ_id_grid, organs=organs)
