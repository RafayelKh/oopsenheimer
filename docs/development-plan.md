5. Codex Master Prompt

Paste this into Codex first:

You are implementing Oops-enheimer, a FLUKA-powered voxel radiation simulation sandbox.
The MVP goal is not a full game. The goal is an end-to-end scientific simulation pipeline:
voxel scene JSON
→ Python compiler
→ scene.inp + scene.vxl + scene.map.json
→ worker runs rfluka if available
→ parser produces dose_map metadata
→ web app visualizes voxel scene and heatmap
Important constraints:
- Do not bundle or redistribute FLUKA.
- FLUKA must be installed separately and configured through FLUKA_BIN.
- Default local mode must be OOPSENHEIMER_SIM_MODE=mock.
- The first real demo is lead_wall.scene.json.
- The first scoring output is a Cartesian dose map.
- Keep the compiler modular because .vxl emission will need validation against real FLUKA/Flair.
- Do not build gameplay before the compiler/run/parse/view loop works.
Implement tasks sequentially from Task 001 onward.
After each task:
1. summarize files changed
2. mention tests added
3. mention how to run/verify
4. do not proceed to the next task unless the current task passes acceptance criteria

⸻

6. The brutally realistic risk list

Risk 1 — .vxl generation may be harder than expected

This is the biggest unknown. Keep emit_vxl.py isolated. The first version can be a placeholder, but the architecture must assume it will be replaced after real FLUKA/Flair validation.

Risk 2 — FLUKA output parsing may require real sample files

Do not guess too much. Start with mock output, then implement the parser after you have one real successful FLUKA run.

Risk 3 — Browser voxel rendering can become a distraction

Do not optimize rendering until the compile/run/parse loop works. A simple viewer is enough.

Risk 4 — Licensing can block hosted/commercial deployment

Build local educational mode first. Commercial/hosted mode is a separate decision because FLUKA commercial use requires the proper licence path.  ￼

⸻

7. First milestone definition

Milestone 1 is complete when this works:

docker compose up

Then:

Open frontend
→ Load Lead Wall Demo
→ Run Simulation in mock mode
→ Job completes
→ Artifacts appear
→ Mock dose heatmap appears

Milestone 2 is complete when this works on a FLUKA-installed machine:

export OOPSENHEIMER_SIM_MODE=fluka
export FLUKA_BIN=/path/to/fluka/bin
oopsenheimer compile packages/examples/lead_wall.scene.json --out ./job_001
python scripts/validate_fluka_job.py ./job_001

Milestone 3 is complete when a real FLUKA output is parsed and shown in the browser.
