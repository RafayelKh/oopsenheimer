"""Command-line interface for the Oops-enheimer compiler."""

from pathlib import Path

from pydantic import ValidationError
import typer

from oopsenheimer_compiler.compiler import expand_chunks, resolve_materials
from oopsenheimer_compiler.emit_inp import emit_inp
from oopsenheimer_compiler.emit_vxl import emit_vxl
from oopsenheimer_compiler.manifest import VXL_PLACEHOLDER_WARNING, emit_manifest, emit_meta
from oopsenheimer_compiler.organ_map import build_organ_map
from oopsenheimer_compiler.schema import SceneDefinition

app = typer.Typer(help="Oops-enheimer compiler tools.", no_args_is_help=True)


@app.callback()
def root() -> None:
    """Oops-enheimer compiler tools."""


@app.command("compile")
def compile_scene(
    scene_json: Path = typer.Argument(..., help="Path to a Oops-enheimer scene JSON file."),
    out: Path = typer.Option(..., "--out", help="Directory for compiler outputs."),
) -> None:
    """Compile a scene JSON file into FLUKA-oriented artifacts."""
    try:
        scene = SceneDefinition.model_validate_json(scene_json.read_text())
        block_grid = expand_chunks(scene)
        material_grid = resolve_materials(scene, block_grid).material_grid
        organ_map = build_organ_map(scene, block_grid, material_grid)

        out.mkdir(parents=True, exist_ok=True)
        inp_path = emit_inp(scene, organ_map, out / scene.emit.fluka_input.filename)
        vxl_path = emit_vxl(scene, organ_map.organ_id_grid, out / scene.emit.voxel_file.filename)
        manifest_path = emit_manifest(scene, organ_map, out / scene.emit.manifest.filename)
        meta_path = emit_meta(scene, block_grid.size, len(organ_map.organs), out / "scene.meta.json")
    except (OSError, ValueError, ValidationError) as exc:
        typer.echo(f"Compile failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    nx, ny, nz = scene.world.grid.dims
    typer.echo(f"World dims: {nx} x {ny} x {nz}")
    typer.echo(f"Voxel count: {block_grid.size}")
    typer.echo(f"Organ count: {len(organ_map.organs)}")
    typer.echo(f"Output directory: {out}")
    typer.echo(f"Artifacts: {inp_path.name}, {vxl_path.name}, {manifest_path.name}, {meta_path.name}")
    typer.echo("Warnings:")
    typer.echo(f"- {VXL_PLACEHOLDER_WARNING}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
