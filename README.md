# Oops-enheimer

<p align="center">
  <img src="apps/web/public/oopsenheimer.svg" alt="Oops-enheimer logo" width="128" />
</p>

Oops-enheimer is a local educational prototype for building simple voxel radiation-shielding scenes, compiling them into FLUKA-oriented simulation artifacts, running them through an external FLUKA installation when available, and visualizing dose or fluence outputs back in a browser-based voxel world.

FLUKA is not bundled or redistributed with this project. Mock mode is the default local development path.

## Project Status

Milestone 1 is implemented in mock mode:

- Python compiler package creates `scene.inp`, placeholder `scene.vxl`, `scene.map.json`, and `scene.meta.json`.
- FastAPI accepts scenes and creates mock simulation jobs.
- Celery worker tasks compile, mock-run, parse, and emit dose-map metadata.
- Next.js frontend loads the demo, submits simulations, polls status, lists artifacts, and shows a mock dose slice.

Milestone 2 is implemented for the lead-wall demo:

- The compiler emits real FLUKA combinatorial geometry for `lead_wall.scene.json`.
- Generic voxel scenes are greedily merged into disjoint RPP cuboid regions in `scene.inp`.
- `scripts/validate_fluka_job.py` can run `rfluka` when `FLUKA_BIN` points to a local FLUKA install.
- The worker parser can post-process real `*_fort.21` USRBIN output with `usbsuw` and `usbrea` into `parsed/dose_map.json` and `parsed/dose_map.npy`.

The `.vxl` writer remains isolated because native FLUKA voxel-body emission still needs deeper FLUKA/Flair validation. Real runs currently use the combinatorial cuboid geometry in `scene.inp`.

## Mock Quickstart

One-command local setup and run:

```bash
scripts/setup_and_run.sh
```

That script auto-detects `FLUKA_BIN` and runs real FLUKA mode when the FLUKA tools are available; otherwise it falls back to mock mode. To force a mode:

```bash
scripts/setup_and_run.sh --mode fluka --fluka-bin /Users/admin/Downloads/fluka4-5.1/bin
scripts/setup_and_run.sh --mode mock
```

It starts the API at `http://127.0.0.1:8000` and the web app at `http://127.0.0.1:3000`. Logs go to `storage/logs/api.log` and `storage/logs/web.log`.

Start everything with Docker:

```bash
docker compose up
```

Then open:

```text
http://127.0.0.1:3000
```

Local non-Docker workflow:

```bash
python -m pip install -e apps/api -e packages/compiler -e workers/fluka_runner
cd apps/web && npm install
```

In separate terminals:

```bash
cd apps/api
OOPSENHEIMER_SIM_MODE=mock STORAGE_ROOT=../../storage python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd apps/web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Compiler Quickstart

```bash
cd packages/compiler
python -m oopsenheimer_compiler.cli compile ../examples/lead_wall.scene.json --out ../../job_001
```

Expected files:

```text
job_001/
  scene.inp
  scene.vxl
  scene.map.json
  scene.meta.json
```

## Real FLUKA Quickstart

Install FLUKA separately and accept the appropriate FLUKA license terms before using real mode.

```bash
export FLUKA_BIN=/path/to/fluka/bin
cd packages/compiler
python -m oopsenheimer_compiler.cli compile ../examples/lead_wall.scene.json --out /tmp/oopsenheimer_fluka_job
cd ../..
python scripts/validate_fluka_job.py /tmp/oopsenheimer_fluka_job
```

To parse the generated USRBIN output:

```bash
FLUKA_BIN=/path/to/fluka/bin python - <<'PY'
import json
from pathlib import Path
import sys

sys.path.insert(0, "workers/fluka_runner")
from parser import parse_usrbin_outputs

job_dir = Path("/tmp/oopsenheimer_fluka_job")
manifest = json.loads((job_dir / "scene.map.json").read_text())
result = parse_usrbin_outputs(job_dir, manifest, sim_mode="fluka")
print(result.metadata_path)
print(result.values_path)
PY
```

For the full API/worker path, start the API with real mode enabled. In the current local setup, Celery runs eagerly by default, so the API process executes the compile/run/parse chain:

```bash
export OOPSENHEIMER_SIM_MODE=fluka
export FLUKA_BIN=/path/to/fluka/bin
cd apps/api
STORAGE_ROOT=../../storage python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Verification

```bash
pytest -q packages/compiler
pytest -q apps/api
pytest -q workers/fluka_runner
cd apps/web && npm run build
```
