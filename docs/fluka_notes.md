# FLUKA Notes

FLUKA is not bundled, redistributed, copied, or installed by Oops-enheimer. Users must install FLUKA separately and comply with the official FLUKA license terms. Hosted or commercial use requires a separate licensing decision.

## Environment

Real mode requires:

```bash
export OOPSENHEIMER_SIM_MODE=fluka
export FLUKA_BIN=/path/to/fluka/bin
```

Mock mode does not require FLUKA:

```bash
export OOPSENHEIMER_SIM_MODE=mock
```

## rfluka Pattern

Oops-enheimer’s runner builds this command inside the generated job directory:

```bash
$FLUKA_BIN/rfluka -M <cycles> scene.inp
```

Stdout and stderr are written under `logs/`.

## Manual Validation

After compiling a job:

```bash
python scripts/validate_fluka_job.py storage/jobs/<simulation_id>
```

The script checks `scene.inp`, `scene.vxl`, and `FLUKA_BIN`, then attempts `rfluka`.

## Flair Workflow

Use Flair manually to inspect generated `scene.inp`, debug geometry, and validate the voxel syntax. The current `.vxl` emitter is intentionally isolated because it must be replaced or corrected after real FLUKA/Flair validation.

## Parser Status

Mock mode writes deterministic `parsed/dose_map.json` and `parsed/dose_map.npy`. Real USRBIN parsing raises `NotImplementedError` until a real successful FLUKA output sample is available.
