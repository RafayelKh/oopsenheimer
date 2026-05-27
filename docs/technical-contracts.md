2. Repository Structure

Create this monorepo:

oopsenheimer/
  README.md
  .gitignore
  .env.example
  docker-compose.yml
  apps/
    web/
      package.json
      src/
        app/
        components/
        lib/
        stores/
        types/
    api/
      pyproject.toml
      app/
        main.py
        config.py
        database.py
        models.py
        schemas.py
        routes/
        services/
  packages/
    compiler/
      pyproject.toml
      oopsenheimer_compiler/
        __init__.py
        cli.py
        schema.py
        compiler.py
        organ_map.py
        fluka_cards.py
        emit_inp.py
        emit_vxl.py
        manifest.py
        validation.py
      tests/
    schemas/
      scene.schema.json
      manifest.schema.json
    examples/
      lead_wall.scene.json
  workers/
    fluka_runner/
      pyproject.toml
      worker.py
      tasks.py
      runner.py
      parser.py
  storage/
    .gitkeep
  docs/
    PRD.md
    architecture.md
    compiler_schema.md
    fluka_notes.md

⸻

3. Data Contracts

3.1 Scene JSON

The first version should support this schema shape:

{
  "schema": "oopsenheimer.scene.v1",
  "units": {
    "length": "cm",
    "energy": "GeV",
    "density": "g/cm3"
  },
  "world": {
    "id": "lead_wall_demo",
    "grid": {
      "dims": [32, 16, 16],
      "voxelSizeCm": [5, 5, 5],
      "originCm": [0, 0, 0],
      "axisOrder": "x-fastest"
    },
    "boundary": {
      "outsideMaterialId": "air",
      "blackholeMarginCm": 100,
      "worldAirMarginCm": 50
    },
    "palette": {},
    "chunks": [],
    "organPolicy": {
      "mode": "merge_by_material_and_tag",
      "maxOrgans": 32767,
      "reserveOrganZeroForOutside": true,
      "splitRules": [],
      "fallback": {
        "onTooManyOrgans": "reject_scene"
      }
    }
  },
  "materials": {},
  "sources": [],
  "scoring": [],
  "run": {
    "defaults": "PRECISIO",
    "histories": 100000,
    "randomSeed": 12345,
    "cycles": 1,
    "validation": {
      "geometryDebug": true
    }
  },
  "emit": {
    "backend": "fluka_voxel",
    "flukaInput": {
      "filename": "scene.inp",
      "title": "Oops-enheimer generated scene",
      "includeComments": true
    },
    "voxelFile": {
      "filename": "scene.vxl",
      "format": "fluka_unformatted_vxl",
      "compactOrganIds": true
    },
    "manifest": {
      "filename": "scene.map.json",
      "includeVoxelToOrganMap": false,
      "includeOrganToRegionMap": true,
      "includeMaterialMap": true
    }
  }
}

3.2 Manifest JSON

{
  "schema": "oopsenheimer.manifest.v1",
  "files": {
    "input": "scene.inp",
    "voxel": "scene.vxl",
    "outputExpected": []
  },
  "coordinateTransform": {
    "voxelIndexToCm": {
      "originCm": [0, 0, 0],
      "voxelSizeCm": [5, 5, 5],
      "convention": "cell_min_corner"
    }
  },
  "organs": [],
  "materials": [],
  "scoring": [],
  "warnings": []
}

⸻

