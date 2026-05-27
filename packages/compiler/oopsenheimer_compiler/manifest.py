"""Oops-enheimer manifest emitter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from oopsenheimer_compiler.organ_map import OrganMap
from oopsenheimer_compiler.schema import SceneDefinition

VXL_PLACEHOLDER_WARNING = (
    "scene.vxl is a Oops-enheimer placeholder. Real FLUKA runs currently use the generated "
    "combinatorial cuboid geometry in scene.inp."
)


def build_manifest(
    scene: SceneDefinition,
    organ_map: OrganMap,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "oopsenheimer.manifest.v1",
        "files": {
            "input": scene.emit.fluka_input.filename,
            "voxel": scene.emit.voxel_file.filename,
            "outputExpected": [],
        },
        "coordinateTransform": {
            "voxelIndexToCm": {
                "originCm": list(scene.world.grid.origin_cm),
                "voxelSizeCm": list(scene.world.grid.voxel_size_cm),
                "convention": "cell_min_corner",
            }
        },
        "organs": [organ.to_manifest() for organ in organ_map.organs],
        "materials": [
            {
                "materialId": material_id,
                "flukaName": material.fluka_name,
                "density": material.density,
                "densityGcm3": material.density_g_cm3,
                "label": material.label,
                "color": material.color,
            }
            for material_id, material in sorted(scene.materials.items())
        ],
        "sources": [
            {
                "id": source.id,
                "type": source.type,
                "particle": source.particle,
                "energyGeV": source.energy_gev,
                "positionCm": list(source.position_cm),
                "direction": list(source.direction),
            }
            for source in scene.sources
        ],
        "scoring": [
            {
                "id": scorer.id,
                "type": scorer.type,
                "quantity": scorer.quantity,
                "dims": list(scorer.dims),
                "minCm": list(scorer.min_cm),
                "maxCm": list(scorer.max_cm),
            }
            for scorer in scene.scoring
        ],
        "warnings": warnings if warnings is not None else [VXL_PLACEHOLDER_WARNING],
    }


def emit_manifest(
    scene: SceneDefinition,
    organ_map: OrganMap,
    output_path: Path,
    warnings: list[str] | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_manifest(scene, organ_map, warnings), indent=2) + "\n")
    return output_path


def build_meta(scene: SceneDefinition, voxel_count: int, organ_count: int) -> dict[str, Any]:
    nx, ny, nz = scene.world.grid.dims
    return {
        "schema": "oopsenheimer.meta.v1",
        "compilerVersion": "0.0.0",
        "worldId": scene.world.id,
        "dims": [nx, ny, nz],
        "voxelCount": voxel_count,
        "organCount": organ_count,
        "warnings": [VXL_PLACEHOLDER_WARNING],
    }


def emit_meta(
    scene: SceneDefinition,
    voxel_count: int,
    organ_count: int,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_meta(scene, voxel_count, organ_count), indent=2) + "\n")
    return output_path
