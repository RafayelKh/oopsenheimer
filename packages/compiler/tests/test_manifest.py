import json
from pathlib import Path

from typer.testing import CliRunner

from radcraft_compiler.cli import app
from radcraft_compiler.manifest import build_manifest, emit_manifest
from radcraft_compiler.organ_map import build_organ_map
from tests.test_emit_inp import load_example


def test_build_manifest_includes_required_sections() -> None:
    scene = load_example()
    organ_map = build_organ_map(scene)
    manifest = build_manifest(scene, organ_map)

    assert manifest["schema"] == "radcraft.manifest.v1"
    assert manifest["files"]["input"] == "scene.inp"
    assert manifest["files"]["voxel"] == "scene.vxl"
    assert manifest["coordinateTransform"]["voxelIndexToCm"]["originCm"] == [0.0, 0.0, 0.0]
    assert manifest["coordinateTransform"]["voxelIndexToCm"]["voxelSizeCm"] == [5.0, 5.0, 5.0]
    assert manifest["materials"]
    assert manifest["scoring"][0]["id"] == "dose_map"
    assert manifest["warnings"]


def test_manifest_organs_include_manifest_ready_fields() -> None:
    manifest = build_manifest(load_example(), build_organ_map(load_example()))

    for organ in manifest["organs"]:
        assert {"organId", "flukaRegionName", "materialId", "voxelCount", "bboxIndex"}.issubset(
            organ
        )


def test_emit_manifest_writes_indented_json(tmp_path: Path) -> None:
    scene = load_example()
    output_path = emit_manifest(scene, build_organ_map(scene), tmp_path / "scene.map.json")

    data = json.loads(output_path.read_text())
    assert data["schema"] == "radcraft.manifest.v1"
    assert output_path.read_text().startswith("{\n  ")


def test_cli_compile_creates_scene_manifest(tmp_path: Path) -> None:
    scene_path = Path(__file__).parents[2] / "examples" / "lead_wall.scene.json"
    result = CliRunner().invoke(app, ["compile", str(scene_path), "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "scene.map.json").exists()
