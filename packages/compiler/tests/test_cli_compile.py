import json
from pathlib import Path

from typer.testing import CliRunner

from radcraft_compiler.cli import app


def example_scene_path() -> Path:
    return Path(__file__).parents[2] / "examples" / "lead_wall.scene.json"


def test_cli_compile_success_creates_all_expected_files(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["compile", str(example_scene_path()), "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "scene.inp").exists()
    assert (tmp_path / "scene.vxl").exists()
    assert (tmp_path / "scene.map.json").exists()
    assert (tmp_path / "scene.meta.json").exists()


def test_cli_compile_summary_prints_useful_counts(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["compile", str(example_scene_path()), "--out", str(tmp_path)])

    assert "World dims: 32 x 16 x 16" in result.output
    assert "Voxel count: 8192" in result.output
    assert "Organ count: 2" in result.output
    assert "Output directory:" in result.output
    assert "Warnings:" in result.output


def test_cli_compile_writes_meta_json(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["compile", str(example_scene_path()), "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    meta = json.loads((tmp_path / "scene.meta.json").read_text())
    assert meta["schema"] == "radcraft.meta.v1"
    assert meta["voxelCount"] == 8192
    assert meta["organCount"] == 2


def test_cli_compile_failure_exits_nonzero(tmp_path: Path) -> None:
    bad_scene = tmp_path / "bad.scene.json"
    bad_scene.write_text('{"schema": "wrong"}')

    result = CliRunner().invoke(app, ["compile", str(bad_scene), "--out", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "Compile failed:" in result.output
