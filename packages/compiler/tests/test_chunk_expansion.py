import pytest

from radcraft_compiler.compiler import dense_grid_shape, expand_chunks
from radcraft_compiler.schema import SceneDefinition


def make_scene(chunk: dict | None = None) -> SceneDefinition:
    data = {
        "schema": "radcraft.scene.v1",
        "units": {"length": "cm", "energy": "GeV", "density": "g/cm3"},
        "world": {
            "id": "chunk_test",
            "grid": {
                "dims": [3, 2, 2],
                "voxelSizeCm": [1, 1, 1],
                "originCm": [0, 0, 0],
                "axisOrder": "x-fastest",
            },
            "boundary": {
                "outsideMaterialId": "air",
                "blackholeMarginCm": 0,
                "worldAirMarginCm": 0,
            },
            "palette": {
                "air": {"materialId": "air"},
                "lead": {"materialId": "lead"},
                "water": {"materialId": "water"},
            },
            "chunks": [
                chunk
                or {
                    "id": "main",
                    "origin": [0, 0, 0],
                    "size": [3, 2, 2],
                    "encoding": "rle",
                    "runs": [
                        {"blockId": "air", "count": 1},
                        {"blockId": "lead", "count": 1},
                        {"blockId": "water", "count": 10},
                    ],
                }
            ],
            "organPolicy": {
                "mode": "merge_by_material_and_tag",
                "maxOrgans": 32767,
                "reserveOrganZeroForOutside": True,
                "splitRules": [],
                "fallback": {"onTooManyOrgans": "reject_scene"},
            },
        },
        "materials": {
            "air": {"flukaName": "AIR"},
            "lead": {"flukaName": "LEAD"},
            "water": {"flukaName": "WATER"},
        },
        "sources": [],
        "scoring": [],
        "run": {
            "defaults": "PRECISIO",
            "histories": 10,
            "randomSeed": 12345,
            "cycles": 1,
            "validation": {"geometryDebug": True},
        },
        "emit": {
            "backend": "fluka_voxel",
            "flukaInput": {
                "filename": "scene.inp",
                "title": "Test scene",
                "includeComments": True,
            },
            "voxelFile": {
                "filename": "scene.vxl",
                "format": "fluka_unformatted_vxl",
                "compactOrganIds": True,
            },
            "manifest": {
                "filename": "scene.map.json",
                "includeVoxelToOrganMap": False,
                "includeOrganToRegionMap": True,
                "includeMaterialMap": True,
            },
        },
    }
    return SceneDefinition.model_validate(data)


def test_dense_grid_shape_uses_zyx_convention() -> None:
    scene = make_scene()
    assert dense_grid_shape(scene) == (2, 2, 3)


def test_expand_chunks_exact_voxel_count() -> None:
    grid = expand_chunks(make_scene())
    assert grid.size == 3 * 2 * 2


def test_expand_chunks_x_fastest_ordering_first_and_last_positions() -> None:
    grid = expand_chunks(make_scene())

    assert grid[0, 0, 0] == "air"
    assert grid[0, 0, 1] == "lead"
    assert grid[0, 0, 2] == "water"
    assert grid[0, 1, 0] == "water"
    assert grid[1, 1, 2] == "water"


def test_expand_chunks_rejects_chunk_overflow() -> None:
    chunk = {
        "id": "overflow",
        "origin": [2, 0, 0],
        "size": [2, 2, 2],
        "encoding": "rle",
        "runs": [{"blockId": "air", "count": 8}],
    }

    with pytest.raises(ValueError, match="exceeds world dims"):
        make_scene(chunk)


def test_expand_chunks_rejects_unknown_block_id() -> None:
    chunk = {
        "id": "bad_block",
        "origin": [0, 0, 0],
        "size": [3, 2, 2],
        "encoding": "rle",
        "runs": [{"blockId": "unknown", "count": 12}],
    }
    scene = make_scene(chunk)

    with pytest.raises(ValueError, match="unknown blockId 'unknown'"):
        expand_chunks(scene)
