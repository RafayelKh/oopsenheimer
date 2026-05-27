from pathlib import Path

import numpy as np
import pytest

from oopsenheimer_compiler.emit_vxl import emit_vxl, organ_ids_x_fastest, render_vxl_placeholder
from oopsenheimer_compiler.organ_map import build_organ_map
from oopsenheimer_compiler.schema import SceneDefinition
from tests.test_emit_inp import load_example


def test_organ_ids_x_fastest_output_order() -> None:
    grid = np.array(
        [
            [[1, 2, 3], [4, 5, 6]],
            [[7, 8, 9], [10, 11, 12]],
        ],
        dtype=np.int32,
    )

    assert organ_ids_x_fastest(grid) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


def test_render_vxl_placeholder_includes_metadata_and_all_organs() -> None:
    scene = load_example()
    organ_map = build_organ_map(scene)

    rendered = render_vxl_placeholder(scene, organ_map.organ_id_grid)

    assert "TODO: replace with FLUKA/Flair-validated" in rendered
    assert "dims=32 16 16" in rendered
    assert "voxelSizeCm=5.0 5.0 5.0" in rendered
    assert "voxelCount=8192" in rendered
    organs_line = next(line for line in rendered.splitlines() if line.startswith("organs="))
    assert len(organs_line.removeprefix("organs=").split()) == 32 * 16 * 16


def test_emit_vxl_creates_scene_file(tmp_path: Path) -> None:
    scene = load_example()
    organ_map = build_organ_map(scene)
    output_path = emit_vxl(scene, organ_map.organ_id_grid, tmp_path / "scene.vxl")

    assert output_path.exists()
    assert "order=x-fastest" in output_path.read_text()


def test_render_vxl_rejects_wrong_grid_shape() -> None:
    scene = load_example()
    bad_grid = np.zeros((1, 1, 1), dtype=np.int32)

    with pytest.raises(ValueError, match="does not match expected"):
        render_vxl_placeholder(scene, bad_grid)


def test_cli_compile_creates_scene_vxl(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from oopsenheimer_compiler.cli import app

    scene_path = Path(__file__).parents[2] / "examples" / "lead_wall.scene.json"
    result = CliRunner().invoke(app, ["compile", str(scene_path), "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "scene.vxl").exists()
