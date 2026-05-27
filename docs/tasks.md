4. Codex Task List

Use these tasks in order. Do not skip to the UI first.

⸻

Task 001 — Initialize monorepo

Goal: Create the base project structure.

Instructions for Codex:

Create the Oops-enheimer monorepo structure exactly as specified in the PRD.
Add:
- root README.md
- .gitignore
- .env.example
- docker-compose.yml placeholder
- apps/web placeholder
- apps/api placeholder
- packages/compiler placeholder
- packages/schemas placeholder
- packages/examples placeholder
- workers/fluka_runner placeholder
- docs placeholder
Do not implement business logic yet.

Acceptance criteria:

Repository tree matches PRD.
README explains Oops-enheimer in one paragraph.
.env.example includes FLUKA_BIN, DATABASE_URL, REDIS_URL, STORAGE_ROOT.

⸻

Task 002 — Create Python compiler package

Goal: Set up packages/compiler.

Instructions for Codex:

Inside packages/compiler, create a Python package named radcraft_compiler using pyproject.toml.
Use:
- Python >= 3.11
- pydantic
- numpy
- typer
- pytest
Create modules:
- schema.py
- compiler.py
- organ_map.py
- fluka_cards.py
- emit_inp.py
- emit_vxl.py
- manifest.py
- validation.py
- cli.py
Expose a CLI command:
radcraft compile <scene_json> --out <output_dir>

Acceptance criteria:

python -m radcraft_compiler.cli --help works.
pytest runs with at least one placeholder test.

⸻

Task 003 — Implement scene Pydantic schemas

Goal: Validate scene JSON strictly.

Instructions for Codex:

Implement Pydantic models in packages/compiler/radcraft_compiler/schema.py for:
- Units
- Grid
- Boundary
- BlockDefinition
- ChunkPayload
- OrganPolicy
- World
- MaterialDefinition
- SourceDefinition
- ScoringDefinition
- RunSettings
- EmitSettings
- SceneDefinition
Add validation rules:
- schema must equal "radcraft.scene.v1"
- units.length must be "cm"
- units.energy must be "GeV"
- grid.dims values must be positive integers
- voxelSizeCm values must be positive
- axisOrder must be "x-fastest"
- organPolicy.maxOrgans must be <= 32767
- chunks must not exceed declared world dims
- chunk encoding initially only supports "rle"

Acceptance criteria:

Valid scene JSON loads successfully.
Invalid dimensions fail with clear error.
Invalid unit names fail with clear error.

⸻

Task 004 — Add first example scene

Goal: Create lead_wall.scene.json.

Instructions for Codex:

Create packages/examples/lead_wall.scene.json.
Scene:
- dims: [32, 16, 16]
- voxel size: [5, 5, 5] cm
- air default
- lead wall between source and detector
- materials: air, lead, water, concrete, silicon
- one photon beam source
- one Cartesian dose_map scorer
- histories: 100000
- cycles: 1
Represent chunks using RLE.
Keep the scene simple and deterministic.

Acceptance criteria:

The compiler schema can load the example scene.
The total RLE voxel count equals 32 * 16 * 16.

⸻

Task 005 — Implement chunk expansion

Goal: Convert RLE chunks into a dense block grid.

Instructions for Codex:

Implement chunk expansion in compiler.py or a dedicated voxel module.
Input:
- world dims
- chunk origin
- chunk size
- RLE block runs
Output:
- dense NumPy array of block IDs or palette indices with shape [nz, ny, nx] or [x, y, z], but document the convention clearly.
Use x-fastest order for RLE expansion.
Add tests:
- exact voxel count
- first/last block positions
- chunk overflow rejection
- unknown blockId rejection

Acceptance criteria:

lead_wall.scene.json expands to a dense grid.
Unit tests prove x-fastest ordering.

⸻

Task 006 — Implement material and block resolution

Goal: Resolve every block to a material.

Instructions for Codex:

Implement a resolver that maps:
blockId → BlockDefinition → materialId → MaterialDefinition
Return a dense material grid or block grid plus lookup tables.
Validation:
- every block materialId must exist in materials
- every chunk blockId must exist in world.palette
- every material must have a FLUKA-safe name

Acceptance criteria:

Unknown block ID fails.
Unknown material ID fails.
Valid scene returns a complete material lookup.

⸻

Task 007 — Implement organ mapping

Goal: Assign FLUKA organ IDs to voxels.

Instructions for Codex:

Implement organ_map.py.
For MVP:
- organ 0 is reserved for outside/air/background.
- all ordinary blocks are merged by materialId.
- detector/source blocks may be unique organs later, but not required in this task.
- organ IDs must be compact integers.
- organ count must not exceed maxOrgans.
Return:
- organ_id_grid: NumPy array
- organs list:
  - organId
  - materialId
  - blockIds
  - voxelCount
  - bboxIndex
  - flukaRegionName
Region name rule:
organ 0 -> VOXEL001
organ 1 -> VOXEL002
organ 2 -> VOXEL003

Acceptance criteria:

Organ IDs are deterministic.
Same material maps to same organ.
Manifest-ready organ metadata is produced.

⸻

Task 008 — Implement FLUKA card emitter foundation

Goal: Create typed FLUKA card rendering.

Instructions for Codex:

In fluka_cards.py, implement:
- FlukaCard base class
- DefaultsCard
- BeamCard
- BeamPosCard
- AssignMatCard
- UsrbinCard
- RandomizeCard
- StartCard
- StopCard
- Comment rendering helper
Do not use huge raw templates.
Each class should render a valid-looking FLUKA line with keyword and fields.
Add tests for deterministic card rendering.

Acceptance criteria:

Cards render stable text.
Tests check expected substrings.
No business logic embedded in card classes.

⸻

Task 009 — Emit minimal scene.inp

Goal: Generate the main FLUKA input file.

Instructions for Codex:

Implement emit_inp.py.
For MVP, emit:
- TITLE
- DEFAULTS
- BEAM
- BEAMPOS
- GEOBEGIN/GEOEND placeholder geometry wrapper
- VOXELS reference/comment placeholder if exact implementation is not finished
- ASSIGNMA cards for generated voxel regions
- USRBIN cards
- RANDOMIZe
- START
- STOP
Important:
If exact FLUKA voxel syntax is uncertain, mark the output with a clear TODO comment but keep code structured so syntax can be fixed after Flair validation.

Acceptance criteria:

radcraft compile example --out job creates scene.inp.
scene.inp includes material assignment lines for VOXEL001+.
scene.inp includes a scoring card.
scene.inp includes START with scene.run.histories.

⸻

Task 010 — Emit placeholder .vxl with strict abstraction

Goal: Create the voxel file emitter interface.

Instructions for Codex:

Implement emit_vxl.py with a clean interface:
emit_vxl(scene, organ_id_grid, output_path)
For first implementation:
- write a documented placeholder or simple text/binary structure if exact FLUKA unformatted .vxl writing is not finalized.
- include all metadata needed:
  - dims
  - voxel size
  - organ count
  - x-fastest organ list
Add a TODO marker saying this must be validated against FLUKA/Flair before real runs.

Acceptance criteria:

scene.vxl is created.
The organ list length equals nx * ny * nz.
Tests verify x-fastest output order.

Important realism note: This is the highest-risk technical part. The first version may not be accepted by FLUKA until validated against real FLUKA/Flair. Keep it isolated so fixing it later does not rewrite the compiler.

⸻

Task 011 — Emit manifest

Goal: Generate scene.map.json.

Instructions for Codex:

Implement manifest.py.
Manifest must include:
- schema
- input filename
- voxel filename
- coordinate transform
- organs
- materials
- scoring metadata
- warnings
Use JSON with indentation.

Acceptance criteria:

scene.map.json is generated.
Every organ has organId, flukaRegionName, materialId, voxelCount, bboxIndex.

⸻

Task 012 — Implement compiler CLI end-to-end

Goal: Make radcraft compile useful.

Instructions for Codex:

Implement CLI:
radcraft compile <scene_json> --out <output_dir>
Steps:
1. Load JSON.
2. Validate with Pydantic.
3. Expand chunks.
4. Resolve materials.
5. Build organ map.
6. Emit scene.inp.
7. Emit scene.vxl.
8. Emit scene.map.json.
9. Emit scene.meta.json.
Print a short summary:
- world dims
- voxel count
- organ count
- output directory
- warnings

Acceptance criteria:

Running compile on lead_wall.scene.json creates all expected files.
CLI exits nonzero on invalid scene.
Compiler summary prints useful counts.

⸻

Task 013 — Add compiler tests

Goal: Make compiler safe to refactor.

Instructions for Codex:

Add pytest tests for:
- schema validation
- chunk expansion
- block/material resolution
- organ mapping
- manifest generation
- CLI compile success
- CLI compile failure
Use temporary directories for outputs.

Acceptance criteria:

pytest packages/compiler/tests passes.
Tests do not require FLUKA installed.

⸻

Task 014 — Create FastAPI backend skeleton

Goal: Start API app.

Instructions for Codex:

Inside apps/api, create a FastAPI app.
Endpoints:
- GET /health
- GET /materials
- GET /examples
- POST /scenes
- GET /scenes/{scene_id}
- POST /simulations
- GET /simulations/{simulation_id}
- GET /simulations/{simulation_id}/artifacts
Use local filesystem storage first.
Use simple in-memory objects if DB is not ready yet, but keep service interfaces clean.

Acceptance criteria:

uvicorn app.main:app runs.
GET /health returns {"status": "ok"}.
POST /scenes accepts lead_wall.scene.json.

⸻

Task 015 — Add database models

Goal: Store scenes and simulation jobs.

Instructions for Codex:

Add SQLAlchemy or SQLModel models for:
Scene:
- id
- name
- scene_json
- created_at
SimulationJob:
- id
- scene_id
- status
- created_at
- started_at
- finished_at
- storage_path
- error_message
- fluka_version
- compiler_version
- histories
- cycles
Statuses:
- queued
- compiling
- compiled
- running
- parsing
- completed
- failed

Acceptance criteria:

Tables can be created.
Scene can be inserted.
Simulation job can be inserted and status updated.

⸻

Task 016 — Add Redis/Celery worker skeleton

Goal: Queue simulation jobs.

Instructions for Codex:

Inside workers/fluka_runner, create Celery app.
Tasks:
- compile_scene_task(simulation_id)
- run_fluka_task(simulation_id)
- parse_results_task(simulation_id)
For now, these can be mock tasks that update job status and create placeholder files.

Acceptance criteria:

Worker starts.
POST /simulations enqueues a job.
Job status eventually becomes completed in mock mode.

⸻

Task 017 — Implement real compiler integration in worker

Goal: Worker compiles submitted scenes.

Instructions for Codex:

Modify compile_scene_task:
- Load scene from DB/storage.
- Create storage/jobs/{simulation_id}/.
- Call radcraft_compiler compile functions directly, not shell command.
- Write scene.inp, scene.vxl, scene.map.json, scene.meta.json.
- Update status to compiled.
- On error, update status to failed with error message.

Acceptance criteria:

Submitting a simulation creates compiler artifacts under storage/jobs/{simulation_id}/.
Errors are captured cleanly.

⸻

Task 018 — Implement FLUKA runner wrapper

Goal: Run real rfluka.

Instructions for Codex:

Implement workers/fluka_runner/runner.py.
Function:
run_rfluka(job_dir: Path, input_file: str, cycles: int, timeout_seconds: int) -> RunResult
Behavior:
- Read FLUKA_BIN from environment.
- Build command:
  $FLUKA_BIN/rfluka -M <cycles> <input_file>
- Run with subprocess in job_dir.
- Capture stdout/stderr to logs.
- Enforce timeout.
- Return exit code, logs path, output file list.
Do not require FLUKA during unit tests. Mock subprocess.

Acceptance criteria:

If FLUKA_BIN is missing, fail with a clear error.
If rfluka exits nonzero, job becomes failed.
If mocked rfluka succeeds, job becomes running/parsing/completed.

⸻

Task 019 — Add dry-run/mock mode

Goal: Allow development without FLUKA installed.

Instructions for Codex:

Add env var:
RADCRAFT_SIM_MODE=mock|fluka
In mock mode:
- do not call rfluka
- generate fake dose_map.json and fake dose_map.npy
- mark job completed
In fluka mode:
- call real rfluka

Acceptance criteria:

Full API/worker flow works in mock mode on any machine.
Real mode fails clearly if FLUKA_BIN is absent.

⸻

Task 020 — Implement first output parser interface

Goal: Create a parser abstraction before real parsing.

Instructions for Codex:

Create parser.py.
Define:
parse_usrbin_outputs(job_dir, manifest) -> ParsedResult
For first implementation:
- if mock mode, read fake output
- if real mode and parser is not implemented, fail with clear NotImplementedError saying USRBIN parser must be implemented after real FLUKA output sample is available.
Also define output contract:
parsed/dose_map.json:
{
  "quantity": "DOSE",
  "dims": [nx, ny, nz],
  "originCm": [x, y, z],
  "voxelSizeCm": [dx, dy, dz],
  "min": number,
  "max": number,
  "valuesEncoding": "npy",
  "valuesFile": "dose_map.npy"
}

Acceptance criteria:

Mock parser produces dose_map.json and dose_map.npy.
API can return parsed result metadata.

⸻

Task 021 — Create frontend app skeleton

Goal: Build web shell.

Instructions for Codex:

Inside apps/web, create Next.js TypeScript app.
Pages/routes:
- /
- /scenes/[id]
- /simulations/[id]
Components:
- Header
- SceneViewer
- MaterialPalette
- SimulationPanel
- JobStatusBadge
- ArtifactList
- HeatmapPanel
Use Zustand for client state.

Acceptance criteria:

npm run dev starts.
Home page loads.
No 3D rendering required yet.

⸻

Task 022 — Implement API client in frontend

Goal: Connect frontend to backend.

Instructions for Codex:

Create apps/web/src/lib/api.ts.
Functions:
- getHealth()
- getExamples()
- createScene(sceneJson)
- createSimulation(sceneId)
- getSimulation(simulationId)
- getSimulationArtifacts(simulationId)
Use NEXT_PUBLIC_API_BASE_URL.
Handle errors cleanly.

Acceptance criteria:

Frontend can call /health and display backend status.

⸻

Task 023 — Implement example scene loader UI

Goal: Load built-in demo.

Instructions for Codex:

On home page:
- Show “Load Lead Wall Demo”
- Fetch example scene from backend
- Create scene via POST /scenes
- Navigate to /scenes/{id}

Acceptance criteria:

User can load demo from UI.
Scene JSON appears in debug panel.

⸻

Task 024 — Implement basic voxel viewer

Goal: Render the scene.

Instructions for Codex:

Implement SceneViewer using React Three Fiber.
For MVP:
- Render blocks as instanced cubes or simple merged geometry.
- Use different colors for air/lead/water/concrete/silicon/source.
- Hide air by default.
- Add orbit controls.
- Add grid/helper axes.

Acceptance criteria:

Lead wall demo displays visible lead wall/detector/source markers.
Camera can orbit.
Air is hidden.

⸻

Task 025 — Implement simulation submit button

Goal: Trigger backend job.

Instructions for Codex:

In /scenes/{id}, add SimulationPanel.
Button:
- “Run Simulation”
On click:
- POST /simulations with scene_id
- Navigate to /simulations/{simulation_id}

Acceptance criteria:

Clicking Run Simulation creates a job.
User sees job status page.

⸻

Task 026 — Implement job polling

Goal: Show job progress.

Instructions for Codex:

On /simulations/{id}:
- Poll GET /simulations/{id} every 2 seconds.
- Show status:
  queued, compiling, compiled, running, parsing, completed, failed.
- If failed, show error_message.
- If completed, fetch artifacts and parsed result metadata.

Acceptance criteria:

Mock job transitions to completed.
Failed jobs show error clearly.

⸻

Task 027 — Implement artifact links

Goal: Let user inspect generated files.

Instructions for Codex:

Show artifact list:
- scene.inp
- scene.vxl
- scene.map.json
- scene.meta.json
- logs if available
- parsed/dose_map.json
Add backend endpoint to download artifacts safely by simulation ID and relative path.
Prevent path traversal.

Acceptance criteria:

User can download scene.inp and scene.map.json.
Path traversal attempts are rejected.

⸻

Task 028 — Implement mock heatmap visualization

Goal: Show visual output before real FLUKA parser.

Instructions for Codex:

Load parsed/dose_map.json and dose_map.npy or use a JSON fallback.
Render heatmap overlay:
- start with 2D slice viewer
- choose axis X/Y/Z
- choose slice index
- show color/intensity grid over voxel scene or next to it
Do not overbuild full 3D volume rendering yet.

Acceptance criteria:

Completed mock simulation displays a dose slice.
User can change slice index.

⸻

Task 029 — Add real FLUKA validation script

Goal: Support manual validation with installed FLUKA.

Instructions for Codex:

Create scripts/validate_fluka_job.py.
Usage:
python scripts/validate_fluka_job.py storage/jobs/<simulation_id>
It should:
- check scene.inp exists
- check scene.vxl exists
- check FLUKA_BIN exists
- run rfluka manually
- print output files
- print errors clearly
This script is for local developer validation only.

Acceptance criteria:

Script fails clearly without FLUKA_BIN.
Script attempts rfluka when FLUKA_BIN is valid.

⸻

Task 030 — Add Docker Compose for local dev

Goal: Make dev startup repeatable.

Instructions for Codex:

Implement docker-compose.yml with:
- postgres
- redis
- api
- worker
- web
Important:
Do not include FLUKA in Docker image.
Use RADCRAFT_SIM_MODE=mock by default.
Mount ./storage.

Acceptance criteria:

docker compose up starts API, worker, frontend, Redis, Postgres.
Mock simulation flow works.

⸻

Task 031 — Add documentation

Goal: Make the project understandable.

Instructions for Codex:

Write docs:
docs/architecture.md:
- system overview
- compile/run/parse flow
- storage layout
docs/compiler_schema.md:
- scene schema
- manifest schema
- organ mapping
docs/fluka_notes.md:
- FLUKA must be installed separately
- FLUKA_BIN setup
- rfluka command pattern
- Flair validation workflow
- license warning
README.md:
- quickstart in mock mode
- quickstart in real FLUKA mode
- project status

Acceptance criteria:

A new developer can run mock mode from README.
Docs clearly say FLUKA is not redistributed.

⸻

