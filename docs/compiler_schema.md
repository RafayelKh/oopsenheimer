# Compiler Schema

The compiler accepts scene JSON with:

- `schema`: must be `radcraft.scene.v1`.
- `units`: length `cm`, energy `GeV`, density `g/cm3`.
- `world.grid`: dimensions `[nx, ny, nz]`, voxel size in centimeters, origin, and `axisOrder: "x-fastest"`.
- `world.palette`: block definitions mapping block IDs to material IDs.
- `world.chunks`: RLE chunks with `origin`, `size`, `encoding: "rle"`, and `runs`.
- `materials`: material definitions with FLUKA-safe `flukaName` values.
- `sources`: first MVP source is `photon_beam`.
- `scoring`: first MVP scorer is `usrbin_cartesian`.
- `run`: FLUKA defaults, histories, random seed, cycles.
- `emit`: output filenames and format settings.

## Dense Grid Convention

Scene dimensions are declared as `[nx, ny, nz]`. NumPy arrays are stored as:

```python
grid[z, y, x]
```

RLE expansion is x-fastest: x advances first, then y, then z.

## Manifest Schema

`scene.map.json` uses `radcraft.manifest.v1` and includes:

- input and voxel filenames.
- voxel index to centimeter coordinate transform.
- organ metadata.
- material metadata.
- scoring metadata.
- warnings.

## Organ Mapping

The MVP organ policy merges voxels by material:

- organ `0` is reserved for the outside/background material.
- ordinary blocks sharing a material share one organ.
- organ IDs are compact deterministic integers.
- FLUKA region names start at `VOXEL001`, then `VOXEL002`, `VOXEL003`, and so on.

The current `.vxl` file is a documented placeholder, not a validated FLUKA binary voxel file.
