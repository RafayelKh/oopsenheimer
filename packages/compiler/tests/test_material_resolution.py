import numpy as np
import pytest
from pydantic import ValidationError

from oopsenheimer_compiler.compiler import expand_chunks, resolve_materials
from oopsenheimer_compiler.schema import SceneDefinition
from tests.test_chunk_expansion import make_scene


def test_resolve_materials_returns_complete_lookup() -> None:
    scene = make_scene()
    block_grid = expand_chunks(scene)
    resolution = resolve_materials(scene, block_grid)

    assert resolution.block_material_ids == {
        "air": "air",
        "lead": "lead",
        "water": "water",
    }
    assert resolution.fluka_names == {
        "air": "AIR",
        "lead": "LEAD",
        "water": "WATER",
    }
    assert resolution.material_grid.shape == block_grid.shape
    assert resolution.material_grid[0, 0, 1] == "lead"


def test_resolve_materials_rejects_unknown_block_id_in_dense_grid() -> None:
    scene = make_scene()
    bad_grid = np.array([[["unknown"]]], dtype=object)

    with pytest.raises(ValueError, match="unknown blockId 'unknown'"):
        resolve_materials(scene, bad_grid)


def test_resolve_materials_rejects_unknown_material_id() -> None:
    data = make_scene().model_dump(by_alias=True)
    data["world"]["palette"]["lead"]["materialId"] = "missing"
    scene = SceneDefinition.model_validate(data)

    with pytest.raises(ValueError, match="unknown materialId 'missing'"):
        resolve_materials(scene)


def test_resolve_materials_rejects_missing_fluka_name() -> None:
    data = make_scene().model_dump(by_alias=True)
    data["materials"]["lead"]["flukaName"] = None
    scene = SceneDefinition.model_validate(data)

    with pytest.raises(ValueError, match="missing flukaName"):
        resolve_materials(scene)


def test_resolve_materials_rejects_non_fluka_safe_name() -> None:
    data = make_scene().model_dump(by_alias=True)
    data["materials"]["lead"]["flukaName"] = "lead-metal"
    scene = SceneDefinition.model_validate(data)

    with pytest.raises(ValueError, match="non-FLUKA-safe"):
        resolve_materials(scene)
