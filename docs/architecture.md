# Architecture

Oops-enheimer is a monorepo with four runtime surfaces:

- `apps/web`: Next.js frontend for loading example scenes, submitting simulations, polling job status, listing artifacts, and displaying mock heatmap slices.
- `apps/api`: FastAPI backend for scene storage, simulation creation, artifact listing, and safe artifact downloads.
- `packages/compiler`: Python compiler that validates scene JSON, expands voxel chunks, resolves materials, builds organ maps, and emits FLUKA-oriented artifacts.
- `workers/fluka_runner`: Celery worker tasks for compile, run, and parse stages.

## Flow

```text
scene JSON
  -> compiler schema validation
  -> RLE chunk expansion
  -> material resolution
  -> organ mapping
  -> scene.inp + scene.vxl + scene.map.json + scene.meta.json
  -> worker mock/FLUKA run
  -> parser emits parsed/dose_map.json + parsed/dose_map.npy
  -> web heatmap slice viewer
```

Mock mode is the default. In mock mode the worker does not call FLUKA; it writes fake logs and a deterministic dose map.

In real mode, `run_rfluka()` executes:

```bash
$FLUKA_BIN/rfluka -M <cycles> scene.inp
```

Real output parsing is intentionally blocked until a real FLUKA USRBIN output sample is available.

## Storage Layout

```text
storage/
  scenes/
    <scene_id>/
      scene.json
  jobs/
    <simulation_id>/
      job_status.json
      scene.inp
      scene.vxl
      scene.map.json
      scene.meta.json
      logs/
        rfluka.stdout.log
        rfluka.stderr.log
      parsed/
        dose_map.json
        dose_map.npy
```

`job_status.json` lets the API and worker share status even while the API still uses in-memory scene/job records.
