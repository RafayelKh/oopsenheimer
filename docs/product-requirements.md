Oops-enheimer MVP PRD + Codex Task List

Product: Oops-enheimer
MVP: FLUKA-powered voxel radiation simulation sandbox
Primary build goal: create a working pipeline where a voxel scene compiles into FLUKA input files, runs through real FLUKA, parses scoring output, and visualizes a dose/fluence heatmap back in a browser voxel world.

The critical assumption: Oops-enheimer is not a real-time Minecraft clone at first. It is a voxel scene builder with a “Run FLUKA Simulation” button.

FLUKA simulations are steered by ASCII input files and can run directly from the command line without the Flair GUI; Flair is still recommended for editing, execution, post-processing, and geometry debugging, so we should use Flair as a validation tool, not as the production runtime.  ￼ FLUKA command-line runs use the rfluka script from the FLUKA install directory, and rfluka -M 5 example.inp is the official-style pattern for running multiple cycles.  ￼

⸻

1. Product Requirements Document

1.1 Product vision

Build a web-based voxel sandbox where users design simple radiation-shielding scenes, submit them to a real FLUKA backend, and receive scientific visualization outputs such as dose maps, fluence maps, and shielding effectiveness.

The MVP should prove this loop:

Voxel scene
→ Oops-enheimer compiler
→ scene.inp + scene.vxl + scene.map.json
→ rfluka run
→ parsed USRBIN output
→ browser heatmap visualization

1.2 Target users

Primary users:

Nuclear physics students
Radiation physics students
Accelerator/detector hobbyists
Physics educators
Monte Carlo simulation beginners

Secondary users:

Researchers who want quick visual demos
Science YouTubers / educational creators
Engineering students learning shielding intuition

1.3 Problem

FLUKA is powerful but difficult for beginners because users must understand input cards, materials, geometry, sources, scoring, command-line execution, and output interpretation before getting a useful visual result.

Oops-enheimer hides most of that complexity behind:

Voxel editing
Material selection
Source placement
Simulation button
Heatmap visualization
Generated FLUKA files for advanced users

1.4 MVP objective

The MVP is successful when a user can:

1. Open the web app.
2. Load the built-in “lead wall shielding” demo.
3. See a voxel scene with air, lead, concrete/water, source marker, and detector plane.
4. Submit the scene to the backend.
5. Backend compiles the scene into FLUKA files.
6. Backend runs FLUKA with rfluka.
7. Backend parses one Cartesian scoring output.
8. Frontend displays a 3D/2D heatmap overlay.
9. User can download or inspect generated scene.inp, scene.vxl, and scene.map.json.

1.5 MVP non-goals

Do not build these in MVP:

Real-time radiation physics
Full survival gameplay
Multiplayer
Reactors
Activation/decay chains
Custom FLUKA SOURCE routines
Commercial hosted service
Huge worlds
Weapon-like scenarios
Operational radiation-safety recommendations
Mobile app

The MVP should stay educational and simulation-focused.

1.6 Licensing and distribution constraint

Do not bundle or redistribute FLUKA inside Oops-enheimer. The official FLUKA licence page says access is governed by licence conditions, academic/educational use requires registered users accepting the Single User Licence Agreement, and commercial users need a commercial licence.  ￼

MVP assumption:

Oops-enheimer is a local educational prototype.
FLUKA must be installed separately by the developer/user.
The worker receives FLUKA path through environment variable.

Required environment variable:

FLUKA_BIN=/path/to/fluka/bin

1.7 Core user flow

User opens app
→ selects example scene
→ edits blocks/materials minimally
→ clicks “Compile”
→ sees generated compiler artifacts
→ clicks “Run FLUKA”
→ job status changes: queued → compiling → running → parsing → completed
→ heatmap overlay appears
→ user inspects result slices and summary numbers

1.8 System components

Frontend:
  Next.js + TypeScript + React Three Fiber + Three.js
Backend API:
  FastAPI + Pydantic
Compiler:
  Python package
  Pydantic schemas
  NumPy voxel processing
  typed FLUKA card emitters
Worker:
  Celery + Redis
  rfluka subprocess runner
Database:
  PostgreSQL
Storage:
  local filesystem for MVP
Simulation:
  external FLUKA installation
  Flair used manually for validation/debugging

1.9 First demo scene

Name:

lead_wall_shielding_demo

Scene:

A rectangular voxel world.
Photon beam starts outside/near one side.
A lead wall sits between source and detector plane.
Air surrounds everything.
USRBIN Cartesian scoring records dose/energy/fluence grid.

Initial materials:

AIR
LEAD
WATER
CONCRETE
SILICON
VACUUM
BLCKHOLE

FLUKA has official geometry/material examples and documentation resources, so the compiler should stay close to standard FLUKA geometry/material patterns instead of inventing unusual geometry formats first.  ￼

1.10 First scoring target

Use one scoring type first:

USRBIN Cartesian 3D mesh

FLUKA’s official scoring resources include 3D distributions with USRBIN, so this is the right first output target for a voxel heatmap.  ￼

1.11 MVP acceptance criteria

The MVP is done when this command works locally:

oopsenheimer compile packages/examples/lead_wall.scene.json --out ./job_001

and produces:

job_001/
  scene.inp
  scene.vxl
  scene.map.json
  scene.meta.json

Then this works:

oopsenheimer run ./job_001

and produces:

job_001/
  raw_outputs/
  parsed/
    dose_map.npy
    dose_map.json
  logs/
    rfluka.stdout.log
    rfluka.stderr.log

Then the web app can show:

Voxel scene
Simulation status
Heatmap overlay
Dose slice viewer
Artifact download links

⸻

