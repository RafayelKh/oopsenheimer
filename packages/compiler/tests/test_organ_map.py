import numpy as np
import pytest

from oopsenheimer_compiler.compiler import expand_chunks, resolve_materials
from oopsenheimer_compiler.organ_map import build_organ_map, fluka_region_name
from oopsenheimer_compiler.schema import SceneDefinition
from tests.test_chunk_expansion import make_scene


def test_fluka_region_names_start_at_voxel001() -> None:
    assert fluka_region_name(0) == "VOXEL001"
    assert fluka_region_name(1) == "VOXEL002"
    assert fluka_region_name(2) == "VOXEL003"


def test_organ_ids_are_deterministic_and_compact() -> None:
    scene = make_scene()
    first = build_organ_map(scene)
    second = build_organ_map(scene)

    assert [organ.organ_id for organ in first.organs] == [0, 1, 2]
    assert [organ.material_id for organ in first.organs] == ["air", "lead", "water"]
    np.testing.assert_array_equal(first.organ_id_grid, second.organ_id_grid)


def test_same_material_maps_to_same_organ() -> None:
    scene = make_scene()
    block_grid = expand_chunks(scene)
    material_grid = resolve_materials(scene, block_grid).material_grid
    organ_map = build_organ_map(scene, block_grid, material_grid)

    water_organ_id = next(
        organ.organ_id for organ in organ_map.organs if organ.material_id == "water"
    )
    assert set(organ_map.organ_id_grid[material_grid == "water"].tolist()) == {water_organ_id}


def test_manifest_ready_organ_metadata_is_produced() -> None:
    organ_map = build_organ_map(make_scene())
    lead = next(organ for organ in organ_map.organs if organ.material_id == "lead")

    assert lead.to_manifest() == {
        "organId": 1,
        "materialId": "lead",
        "blockIds": ["lead"],
        "voxelCount": 1,
        "bboxIndex": {"min": [1, 0, 0], "max": [1, 0, 0]},
        "flukaRegionName": "VOXEL002",
    }


def test_organ_count_must_not_exceed_max_organs() -> None:
    data = make_scene().model_dump(by_alias=True)
    data["world"]["organPolicy"]["maxOrgans"] = 2
    scene = SceneDefinition.model_validate(data)

    with pytest.raises(ValueError, match="organ count 3 exceeds maxOrgans 2"):
        build_organ_map(scene)
