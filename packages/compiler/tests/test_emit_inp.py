from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from radcraft_compiler.cli import app
from radcraft_compiler.compiler import expand_chunks, resolve_materials
from radcraft_compiler.emit_inp import emit_inp, material_cuboids_from_grid, render_inp
from radcraft_compiler.organ_map import build_organ_map
from radcraft_compiler.schema import SceneDefinition


def load_example() -> SceneDefinition:
    scene_path = Path(__file__).parents[2] / "examples" / "lead_wall.scene.json"
    return SceneDefinition.model_validate_json(scene_path.read_text())


def test_render_inp_includes_required_sections_and_cards() -> None:
    scene = load_example()
    block_grid = expand_chunks(scene)
    material_grid = resolve_materials(scene, block_grid).material_grid
    organ_map = build_organ_map(scene, block_grid, material_grid)

    rendered = render_inp(scene, organ_map)

    assert "TITLE" in rendered
    assert "DEFAULTS" in rendered
    assert "BEAM" in rendered
    assert "BEAMPOS" in rendered
    assert "GEOBEGIN" in rendered
    assert "RPP AIRBOX" in rendered
    assert "EXTAIR" in rendered
    assert "RPP WORLD" in rendered
    assert "RPP LEADWALL" in rendered
    assert "ASSIGNMA" in rendered
    assert "BLCKHOLE" in rendered
    assert "AIRREG" in rendered
    assert "LEADREG" in rendered
    assert "USRBIN" in rendered
    assert "DOSE" in rendered
    assert "START         100000" in rendered
    assert rendered.rstrip().endswith("STOP")


def test_emit_inp_writes_scene_file(tmp_path: Path) -> None:
    scene = load_example()
    organ_map = build_organ_map(scene)
    output_path = emit_inp(scene, organ_map, tmp_path / "scene.inp")

    assert output_path.exists()
    assert "Oops-enheimer generated lead wall shielding demo" in output_path.read_text()


def test_material_grid_is_merged_into_rectangular_cuboids() -> None:
    material_grid = np.array(
        [
            [["lead", "lead", "air", "air"], ["lead", "lead", "air", "air"]],
            [["lead", "lead", "water", "water"], ["lead", "lead", "water", "water"]],
        ],
        dtype=object,
    )

    cuboids = material_cuboids_from_grid(material_grid)

    assert [(cuboid.material_id, cuboid.min_index, cuboid.max_index) for cuboid in cuboids] == [
        ("lead", (0, 0, 0), (2, 2, 2)),
        ("air", (2, 0, 0), (4, 2, 1)),
        ("water", (2, 0, 1), (4, 2, 2)),
    ]


def test_generic_voxel_geometry_emits_disjoint_region_assignments() -> None:
    scene = load_example()
    scene = scene.model_copy(
        deep=True,
        update={"world": scene.world.model_copy(update={"id": "editor_scene"})},
    )
    rendered = render_inp(scene, build_organ_map(scene))

    assert "Oops-enheimer voxel cuboid geometry (3 regions)" in rendered
    assert "RPP LEADWALL" not in rendered
    assert "RPP AIRBOX -50 210 -50 130 -50 130" in rendered
    assert "EXTAIR  5 +AIRBOX -WORLD" in rendered
    assert "RPP B000001 0 160 0 80 0 35" in rendered
    assert "RPP B000002 0 160 0 80 35 40" in rendered
    assert "RPP B000003 0 160 0 80 40 80" in rendered
    assert "R000001 5 +B000001" in rendered
    assert "R000002 5 +B000002" in rendered
    assert "R000003 5 +B000003" in rendered
    assert "ASSIGNMA         AIR    EXTAIR" in rendered
    assert "ASSIGNMA         AIR   R000001" in rendered
    assert "ASSIGNMA        LEAD   R000002" in rendered
    assert "ASSIGNMA         AIR   R000003" in rendered


def test_custom_compound_materials_are_defined_before_assignments() -> None:
    scene = load_example()
    palette = dict(scene.world.palette)
    palette["lead"] = palette["lead"].model_copy(update={"material_id": "concrete"})
    scene = scene.model_copy(
        deep=True,
        update={
            "world": scene.world.model_copy(
                update={"id": "editor_scene", "palette": palette},
            ),
        },
    )

    rendered = render_inp(scene, build_organ_map(scene))
    lines = rendered.splitlines()

    assert any(
        line.startswith("MATERIAL") and "2.3" in line and line.endswith("CONCRETE")
        for line in lines
    )
    assert any(line.startswith("MATERIAL") and line.endswith("POTASSIU") for line in lines)
    assert any(
        line.startswith("COMPOUND")
        and "HYDROGEN" in line
        and "CARBON" in line
        and "OXYGEN" in line
        and line.endswith("CONCRETE")
        for line in lines
    )
    assert rendered.index("MATERIAL") < rendered.index("ASSIGNMA    CONCRETE")
    assert rendered.index("POTASSIU") < rendered.index("COMPOUND   -0.337021")


def test_source_outside_default_air_margin_expands_airbox() -> None:
    scene = load_example()
    scene = scene.model_copy(
        deep=True,
        update={
            "world": scene.world.model_copy(update={"id": "editor_scene"}),
            "sources": [
                scene.sources[0].model_copy(update={"position_cm": (193.333333, 120.0, 153.333333)})
            ],
        },
    )

    rendered = render_inp(scene, build_organ_map(scene))

    assert "RPP AIRBOX -50 210 -50 130 -50 154.33333" in rendered
    assert "RPP BLKBODY -100 260 -100 180 -100 204.33333" in rendered


def test_cli_compile_creates_scene_inp(tmp_path: Path) -> None:
    scene_path = Path(__file__).parents[2] / "examples" / "lead_wall.scene.json"
    runner = CliRunner()

    result = runner.invoke(app, ["compile", str(scene_path), "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "scene.inp").exists()
    assert "Artifacts:" in result.output
