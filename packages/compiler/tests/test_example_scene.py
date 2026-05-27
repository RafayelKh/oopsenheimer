import json
from pathlib import Path

from oopsenheimer_compiler.schema import SceneDefinition


def test_lead_wall_example_loads() -> None:
    scene_path = Path(__file__).parents[2] / "examples" / "lead_wall.scene.json"
    scene = SceneDefinition.model_validate_json(scene_path.read_text())

    assert scene.world.id == "lead_wall_demo"
    assert scene.world.grid.dims == (32, 16, 16)


def test_lead_wall_rle_count_matches_world_voxels() -> None:
    scene_path = Path(__file__).parents[2] / "examples" / "lead_wall.scene.json"
    data = json.loads(scene_path.read_text())
    chunk = data["world"]["chunks"][0]

    rle_count = sum(run["count"] for run in chunk["runs"])
    nx, ny, nz = data["world"]["grid"]["dims"]

    assert rle_count == nx * ny * nz


def test_all_example_scenes_load_and_have_complete_rle() -> None:
    for scene_path in sorted((Path(__file__).parents[2] / "examples").glob("*.scene.json")):
        data = json.loads(scene_path.read_text())
        scene = SceneDefinition.model_validate(data)
        chunk = data["world"]["chunks"][0]
        rle_count = sum(run["count"] for run in chunk["runs"])
        nx, ny, nz = scene.world.grid.dims

        assert rle_count == nx * ny * nz, scene_path.name
